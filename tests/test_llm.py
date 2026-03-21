import pytest
from unittest.mock import patch
from llm import generate, LLMUnavailableError

def test_generate_returns_string():
    with patch("llm._call_ollama", return_value="réponse test"):
        result = generate("mon prompt")
    assert isinstance(result, str)
    assert result == "réponse test"

def test_generate_raises_on_unavailable():
    with patch("llm._call_ollama", side_effect=Exception("connection refused")):
        with pytest.raises(LLMUnavailableError):
            generate("mon prompt")

def test_generate_uses_claude_when_configured():
    import os
    os.environ["INSIGHTS_LLM"] = "claude"
    with patch("llm._call_claude", return_value="réponse claude") as mock:
        result = generate("mon prompt")
        mock.assert_called_once()
    assert result == "réponse claude"
    del os.environ["INSIGHTS_LLM"]
