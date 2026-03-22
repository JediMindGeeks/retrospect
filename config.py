import os
from pathlib import Path

class Config:
    LLM_BACKEND: str = os.getenv("INSIGHTS_LLM", "ollama")
    OLLAMA_MODEL: str = os.getenv("INSIGHTS_MODEL", "qwen2.5-coder-16k:latest")
    OLLAMA_REPORT_MODEL: str = os.getenv("INSIGHTS_REPORT_MODEL", "mistral-small3.2-16k:latest")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"

    _base = Path.home() / "notes" / "insights"
    FACETS_DIR: Path = _base / "facets"
    REPORTS_DIR: Path = _base / "reports"

    MIN_MESSAGES: int = 3
    MAX_CONV_CHARS: int = int(os.getenv("INSIGHTS_MAX_CHARS", "32000"))

    @classmethod
    def ensure_dirs(cls, base_dir: Path = None):
        base = Path(base_dir) if base_dir else cls._base
        (base / "facets").mkdir(parents=True, exist_ok=True)
        (base / "reports").mkdir(parents=True, exist_ok=True)
