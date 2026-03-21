import json, pytest
from unittest.mock import patch
from pathlib import Path
from facets import generate_facet, load_cached, save_facet, is_valid_facet, REQUIRED_FIELDS

class TestFacetValidation:
    def test_valid_facet_passes(self):
        f = {"underlying_goal": "x", "outcome": "achieved", "brief_summary": "y",
             "key_points": [], "friction": "", "conversation_id": "id1", "source": "claude_code"}
        assert is_valid_facet(f) is True

    def test_missing_field_fails(self):
        f = {"outcome": "achieved", "brief_summary": "y"}
        assert is_valid_facet(f) is False

class TestFacetCache:
    def test_save_and_load(self, tmp_path):
        facet = {"conversation_id": "abc", "source": "claude_code",
                 "underlying_goal": "test", "outcome": "achieved",
                 "key_points": ["a"], "friction": "", "brief_summary": "résumé"}
        save_facet(facet, base_dir=tmp_path)
        loaded = load_cached("claude_code", "abc", base_dir=tmp_path)
        assert loaded == facet

    def test_returns_none_if_not_cached(self, tmp_path):
        assert load_cached("claude_code", "nonexistent", base_dir=tmp_path) is None

    def test_corrupted_cache_returns_none(self, tmp_path):
        f = tmp_path / "claude_code-broken.json"
        f.write_text("not json")
        assert load_cached("claude_code", "broken", base_dir=tmp_path) is None

    def test_missing_fields_returns_none(self, tmp_path):
        data = {"conversation_id": "x", "source": "claude_code"}
        f = tmp_path / "claude_code-x.json"
        f.write_text(json.dumps(data))
        assert load_cached("claude_code", "x", base_dir=tmp_path) is None

class TestFacetGeneration:
    def test_generate_calls_llm(self, sample_claude_dir):
        from parsers.claude_code import parse
        conv = parse(sample_claude_dir)[0]
        mock_response = json.dumps({
            "underlying_goal": "déboguer un script Python",
            "outcome": "achieved",
            "key_points": ["utilisé pdb", "erreur résolue"],
            "friction": "",
            "brief_summary": "Session de débogage réussie"
        })
        with patch("facets.generate", return_value=mock_response):
            facet = generate_facet(conv, source="claude_code")
        assert facet["underlying_goal"] == "déboguer un script Python"
        assert facet["conversation_id"] == conv["session_id"]
        assert facet["source"] == "claude_code"
