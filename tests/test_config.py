import os
from config import Config

def test_default_llm_backend():
    assert Config.LLM_BACKEND == "ollama"

def test_default_model_is_set():
    # L'override via env var est testé dans test_llm.py via generate()
    # car LLM_BACKEND est un class attr évalué à l'import, pas à l'appel
    assert Config.OLLAMA_MODEL != ""

def test_default_model():
    assert "llama" in Config.OLLAMA_MODEL or Config.OLLAMA_MODEL != ""

def test_output_dir_exists_after_init():
    from pathlib import Path
    Config.ensure_dirs()
    assert Path(Config.FACETS_DIR).exists()
    assert Path(Config.REPORTS_DIR).exists()
