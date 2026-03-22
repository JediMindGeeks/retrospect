import os
import httpx
from config import Config

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
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
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
