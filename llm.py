import os
import httpx
from config import Config

# JSON schema pour forcer la structure du facet au niveau des tokens (Ollama structured output)
_FACET_SCHEMA = {
    "type": "object",
    "properties": {
        "underlying_goal":    {"type": "string"},
        "outcome":            {"type": "string", "enum": ["achieved", "mostly_achieved", "not_achieved", "unclear_from_transcript"]},
        "claude_helpfulness": {"type": "string", "enum": ["helpful", "mostly_helpful", "unhelpful", "unclear"]},
        "session_type":       {"type": "string", "enum": ["deep_work", "quick_question", "ritual", "config", "debug", "unclear"]},
        "primary_success":    {"type": "boolean"},
        "key_points":         {"type": "array", "items": {"type": "string"}},
        "friction":           {"type": "string"},
        "friction_type":      {"type": "string", "enum": ["wrong_approach", "tool_failure", "model_incompatibility", "environment", "misunderstanding", "none"]},
        "user_satisfaction":  {"type": "string", "enum": ["satisfied", "neutral", "frustrated", "unclear"]},
        "brief_summary":      {"type": "string"},
    },
    "required": [
        "underlying_goal", "outcome", "claude_helpfulness", "session_type",
        "primary_success", "key_points", "friction", "friction_type",
        "user_satisfaction", "brief_summary",
    ],
}

class LLMUnavailableError(Exception):
    pass

def generate(prompt: str) -> str:
    backend = os.getenv("INSIGHTS_LLM", Config.LLM_BACKEND)
    try:
        if backend == "claude":
            return _call_claude(prompt)
        return _call_ollama(prompt)
    except LLMUnavailableError:
        raise
    except Exception as e:
        raise LLMUnavailableError(f"LLM inaccessible ({backend}): {e}") from e

def _call_ollama(prompt: str) -> str:
    model = os.getenv("INSIGHTS_MODEL", Config.OLLAMA_MODEL)
    try:
        r = httpx.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": _FACET_SCHEMA},
            timeout=int(os.getenv("INSIGHTS_TIMEOUT", "300")),
        )
        r.raise_for_status()
        return r.json()["response"]
    except httpx.ConnectError as e:
        raise LLMUnavailableError(
            f"Ollama inaccessible. Lance : ollama serve\nModèle requis : {model}"
        ) from e

def _call_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise LLMUnavailableError(
            "Package 'anthropic' non installé. Lance : pip install anthropic"
        )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
