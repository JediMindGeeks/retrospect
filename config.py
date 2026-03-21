import os
from pathlib import Path

class Config:
    LLM_BACKEND: str = os.getenv("INSIGHTS_LLM", "ollama")
    OLLAMA_MODEL: str = os.getenv("INSIGHTS_MODEL", "mistral-small3.1:24b")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"

    _base = Path.home() / "notes" / "insights"
    FACETS_DIR: Path = _base / "facets"
    REPORTS_DIR: Path = _base / "reports"

    MIN_MESSAGES: int = 3

    @classmethod
    def ensure_dirs(cls):
        cls.FACETS_DIR.mkdir(parents=True, exist_ok=True)
        cls.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
