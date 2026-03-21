import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from insights import detect_format, run
from facets import save_facet

class TestFormatDetection:
    def test_detects_claude_code(self, sample_claude_dir):
        assert detect_format(sample_claude_dir) == "claude_code"

    def test_detects_chatgpt(self, sample_chatgpt_file):
        assert detect_format(sample_chatgpt_file) == "chatgpt"

    def test_raises_on_unknown_format(self, tmp_path):
        with pytest.raises(ValueError, match="Format non supporté"):
            detect_format(tmp_path)

class TestRun:
    def test_run_claude_code_end_to_end(self, sample_claude_dir, tmp_path):
        mock_facet = {
            "conversation_id": "abc123", "source": "claude_code",
            "underlying_goal": "déboguer", "outcome": "achieved",
            "key_points": ["résolu"], "friction": "", "brief_summary": "Succès"
        }
        with patch("insights.generate_facet", return_value=mock_facet), \
             patch("report.generate", return_value="Analyse narrative"):
            report = run(sample_claude_dir, facets_dir=tmp_path, reports_dir=tmp_path)
        assert "Insights" in report
        assert "1" in report  # 1 conversation analysée

    def test_run_saves_report_file(self, sample_claude_dir, tmp_path):
        mock_facet = {
            "conversation_id": "abc123", "source": "claude_code",
            "underlying_goal": "test", "outcome": "achieved",
            "key_points": [], "friction": "", "brief_summary": "OK"
        }
        with patch("insights.generate_facet", return_value=mock_facet), \
             patch("report.generate", return_value="narrative"):
            run(sample_claude_dir, facets_dir=tmp_path, reports_dir=tmp_path)
        reports = list(tmp_path.glob("insights-*.md"))
        assert len(reports) == 1

    def test_run_uses_cache_when_available(self, sample_claude_dir, tmp_path):
        cached_facet = {
            "conversation_id": "abc123", "source": "claude_code",
            "underlying_goal": "test cache", "outcome": "achieved",
            "key_points": ["cache hit"], "friction": "", "brief_summary": "From cache"
        }
        save_facet(cached_facet, base_dir=tmp_path)
        with patch("insights.generate_facet") as mock_gen, \
             patch("report.generate", return_value="narrative"):
            run(sample_claude_dir, facets_dir=tmp_path, reports_dir=tmp_path)
        mock_gen.assert_not_called()

    def test_run_skips_conversation_on_generate_facet_error(self, sample_claude_dir, tmp_path):
        with patch("insights.generate_facet", side_effect=ValueError("LLM failed")), \
             patch("report.generate", return_value="narrative"):
            # Should not raise; failing conversation is skipped
            report = run(sample_claude_dir, facets_dir=tmp_path, reports_dir=tmp_path)
        assert report is not None
