import os
from config import Config

def test_default_llm_backend():
    assert Config.LLM_BACKEND == "ollama"

def test_default_model_is_set():
    # L'override via env var est testé dans test_llm.py via generate()
    # car LLM_BACKEND est un class attr évalué à l'import, pas à l'appel
    assert Config.OLLAMA_MODEL != ""

def test_default_model():
    assert Config.OLLAMA_MODEL == "qwen2.5-coder-16k:latest"

def test_output_dir_exists_after_init(tmp_path):
    Config.ensure_dirs(base_dir=tmp_path)
    assert (tmp_path / "facets").exists()
    assert (tmp_path / "reports").exists()
