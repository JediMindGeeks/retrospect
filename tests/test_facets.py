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

    def test_save_raises_if_missing_source(self, tmp_path):
        facet = {"conversation_id": "abc", "underlying_goal": "x",
                 "outcome": "achieved", "brief_summary": "y"}
        with pytest.raises(ValueError, match="source"):
            save_facet(facet, base_dir=tmp_path)

    def test_save_raises_if_missing_conversation_id(self, tmp_path):
        facet = {"source": "claude_code", "underlying_goal": "x",
                 "outcome": "achieved", "brief_summary": "y"}
        with pytest.raises(ValueError, match="conversation_id"):
            save_facet(facet, base_dir=tmp_path)

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

    def test_llm_failure_raises_value_error(self, sample_claude_dir):
        from parsers.claude_code import parse
        conv = parse(sample_claude_dir)[0]
        with patch("facets.generate", side_effect=RuntimeError("API timeout")):
            with pytest.raises(ValueError, match="LLM call failed"):
                generate_facet(conv, source="claude_code")

    def test_invalid_json_from_llm_raises(self, sample_claude_dir):
        from parsers.claude_code import parse
        conv = parse(sample_claude_dir)[0]
        with patch("facets.generate", return_value="Here is your analysis: not json at all"):
            with pytest.raises(ValueError, match="Failed to parse JSON"):
                generate_facet(conv, source="claude_code")

    def test_missing_required_fields_in_llm_response_raises(self, sample_claude_dir):
        from parsers.claude_code import parse
        conv = parse(sample_claude_dir)[0]
        # LLM returns JSON but omits 'outcome'
        incomplete = json.dumps({
            "underlying_goal": "debug",
            "brief_summary": "some summary"
            # 'outcome' is missing
        })
        with patch("facets.generate", return_value=incomplete):
            with pytest.raises(ValueError, match="missing required fields"):
                generate_facet(conv, source="claude_code")

    def test_chatgpt_message_format(self):
        """generate_facet handles flat message format (role at top level, no 'message' key)."""
        conv = {
            "conversation_id": "chatgpt-001",
            "messages": [
                {"role": "user", "content": "Bonjour"},
                {"role": "assistant", "content": "Bonjour, comment puis-je aider ?"},
            ]
        }
        mock_response = json.dumps({
            "underlying_goal": "greeting",
            "outcome": "achieved",
            "key_points": ["salutation"],
            "friction": "",
            "brief_summary": "Échange de salutations"
        })
        with patch("facets.generate", return_value=mock_response):
            facet = generate_facet(conv, source="chatgpt")
        assert facet["conversation_id"] == "chatgpt-001"
        assert facet["source"] == "chatgpt"
        assert facet["outcome"] == "achieved"

    def test_unknown_message_format_skipped(self):
        """Messages with neither nested nor flat format are silently skipped."""
        conv = {
            "session_id": "test-skip",
            "messages": [
                {"role": "user", "content": "Valid message"},
                {"unknown_key": "no role or content here"},
            ]
        }
        mock_response = json.dumps({
            "underlying_goal": "test",
            "outcome": "achieved",
            "key_points": [],
            "friction": "",
            "brief_summary": "Test"
        })
        with patch("facets.generate", return_value=mock_response) as mock_gen:
            generate_facet(conv, source="claude_code")
        # The prompt should only contain the valid message line
        call_prompt = mock_gen.call_args[0][0]
        assert "[user]: Valid message" in call_prompt
        assert "unknown_key" not in call_prompt
