"""LLM client for No-Slop Research — makes actual API calls to any OpenAI-compatible endpoint.

Reads config from .env or Hermes environment, sends prompts, returns responses.
Makes the standalone pipeline path actually execute instead of just returning prompts.
"""

import os
import json
import sys
import requests
from typing import Optional


def load_config() -> dict:
    """Load LLM configuration from environment."""
    # Try Hermes env vars first, then .env, then defaults
    config = {
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "base_url": os.environ.get("LLM_BASE_URL", ""),
        "model": os.environ.get("LLM_MODEL_NAME", ""),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "8192")),
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.3")),
    }

    # Check for explicit project .env first
    project_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(project_env):
        try:
            from dotenv import load_dotenv
            load_dotenv(project_env)
            for k in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME"]:
                v = os.environ.get(k, "")
                if v and k in ["LLM_BASE_URL", "LLM_MODEL_NAME"]:
                    k_lower = k.lower().replace("llm_", "").replace("model_name", "model")
                    config[k_lower] = v
        except Exception:
            pass

    # Try Hermes credential pool (has real API keys unlike masked .env file)
    try:
        hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
        sys_path = os.path.join(hermes_home, "hermes-agent")
        if os.path.exists(sys_path):
            sys.path.insert(0, sys_path)
        from hermes_cli.config import load_env
        hermes_env = load_env()
        opencode_key = hermes_env.get("OPENCODE_GO_API_KEY", "")
        if opencode_key and not config.get("api_key"):
            config["api_key"] = opencode_key
    except Exception:
        pass

    # Fallback to Hermes config.yaml for base_url/model
    if not config.get("base_url") or not config.get("model"):
        hermes_config_path = os.path.expanduser("~/.hermes/config.yaml")
        if os.path.exists(hermes_config_path):
            try:
                import yaml
                with open(hermes_config_path) as f:
                    hc = yaml.safe_load(f)
                if not config.get("base_url"):
                    config["base_url"] = hc.get("model", {}).get("base_url", "https://opencode.ai/zen/go/v1")
                if not config.get("model"):
                    config["model"] = hc.get("model", {}).get("model", "deepseek-v4-flash")
            except Exception:
                pass

    # Ultimate defaults
    if not config.get("base_url"):
        config["base_url"] = "https://api.openai.com/v1"
    if not config.get("model"):
        config["model"] = "gpt-4o"

    return config


def _build_headers(config: dict) -> dict:
    """Build request headers based on provider."""
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    headers = {
        "Content-Type": "application/json",
    }

    if "openrouter" in base_url:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "https://github.com/epaproditus/no-slop-research"
        headers["X-Title"] = "No-Slop Research"
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


def call_llm(prompt: str, system_prompt: Optional[str] = None, config: Optional[dict] = None) -> str:
    """Call an LLM with the given prompt and return the response text.

    Uses OpenAI-compatible chat completions API.
    """
    cfg = config or load_config()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = _build_headers(cfg)
    base_url = cfg["base_url"].rstrip("/")

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": cfg["max_tokens"],
        "temperature": cfg["temperature"],
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
        )
        # Try to parse JSON even on error status — some endpoints return 500
        # with a valid response body
        try:
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    return content.strip()
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        # Retry once on 500/502/503
        if hasattr(e, 'response') and e.response and e.response.status_code in (500, 502, 503):
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300,
                )
                try:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        if content and content.strip():
                            return content.strip()
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.RequestException:
                pass
        raise RuntimeError(f"LLM API call failed: {e}") from e


def call_llm_json(prompt: str, system_prompt: Optional[str] = None, config: Optional[dict] = None) -> dict:
    """Call LLM and parse response as JSON."""
    result = call_llm(prompt, system_prompt, config)
    # Try to extract JSON from markdown code blocks if present
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].split("```")[0].strip()
    return json.loads(result)
