import pytest
from unittest.mock import patch
from report import compute_stats, generate_report, save_report

SAMPLE_FACETS = [
    {"conversation_id": "a", "source": "claude_code", "underlying_goal": "déboguer",
     "outcome": "achieved", "key_points": ["pdb"], "friction": "", "brief_summary": "Débogage réussi"},
    {"conversation_id": "b", "source": "claude_code", "underlying_goal": "configurer NAS",
     "outcome": "not_achieved", "key_points": ["fstab"], "friction": "Permissions",
     "brief_summary": "Problème de montage non résolu"},
    {"conversation_id": "c", "source": "chatgpt", "underlying_goal": "créer API REST",
     "outcome": "mostly_achieved", "key_points": ["FastAPI"], "friction": "Auth",
     "brief_summary": "API créée, auth manquante"},
]

class TestComputeStats:
    def test_counts_total(self):
        stats = compute_stats(SAMPLE_FACETS)
        assert stats["total"] == 3

    def test_counts_outcomes(self):
        stats = compute_stats(SAMPLE_FACETS)
        assert stats["outcomes"]["achieved"] == 1
        assert stats["outcomes"]["not_achieved"] == 1
        assert stats["outcomes"]["mostly_achieved"] == 1

    def test_counts_sources(self):
        stats = compute_stats(SAMPLE_FACETS)
        assert stats["sources"]["claude_code"] == 2
        assert stats["sources"]["chatgpt"] == 1

    def test_outcomes_sorted(self):
        stats = compute_stats(SAMPLE_FACETS)
        keys = list(stats["outcomes"].keys())
        assert keys == sorted(keys)

    def test_sources_sorted(self):
        stats = compute_stats(SAMPLE_FACETS)
        keys = list(stats["sources"].keys())
        assert keys == sorted(keys)

    def test_missing_source_defaults_to_unknown(self):
        facets = [{"outcome": "achieved", "source": None, "brief_summary": "x", "friction": ""}]
        # None as source key — should not raise
        stats = compute_stats([{"outcome": "achieved", "brief_summary": "x"}])
        assert stats["sources"]["unknown"] == 1

    def test_missing_outcome_defaults_to_unknown(self):
        stats = compute_stats([{"source": "claude_code", "brief_summary": "x"}])
        assert stats["outcomes"]["unknown"] == 1

class TestGenerateReport:
    def test_report_contains_stats(self):
        with patch("report.generate", return_value="Analyse narrative du rapport"):
            md = generate_report(SAMPLE_FACETS, date="2026-03-21")
        assert "3" in md  # total conversations
        assert "2026-03-21" in md

    def test_report_has_required_sections(self):
        with patch("report.generate", return_value="Section narrative"):
            md = generate_report(SAMPLE_FACETS, date="2026-03-21")
        assert "## Vue d'ensemble" in md
        assert "Section narrative" in md

    def test_report_has_frontmatter(self):
        with patch("report.generate", return_value="narrative"):
            md = generate_report(SAMPLE_FACETS, date="2026-03-21")
        assert md.startswith("---")
        assert "date: 2026-03-21" in md

    def test_empty_facets_does_not_crash(self):
        with patch("report.generate", return_value="narrative"):
            md = generate_report([], date="2026-03-21")
        assert "date: 2026-03-21" in md
        assert "0" in md  # zero conversations

    def test_date_none_uses_today(self):
        with patch("report.generate", return_value="narrative"):
            md = generate_report(SAMPLE_FACETS)
        assert "date:" in md

class TestSaveReport:
    def test_save_report_writes_file(self, tmp_path):
        content = "# Test report"
        returned_path = save_report(content, "2026-03-21", tmp_path)
        expected = tmp_path / "insights-2026-03-21.md"
        assert expected.exists()
        assert expected.read_text() == content

    def test_save_report_returns_path_string(self, tmp_path):
        returned_path = save_report("content", "2026-03-21", tmp_path)
        assert isinstance(returned_path, str)
        assert returned_path.endswith("insights-2026-03-21.md")

    def test_save_report_creates_missing_dirs(self, tmp_path):
        nested_dir = tmp_path / "a" / "b" / "c"
        save_report("content", "2026-03-21", nested_dir)
        assert (nested_dir / "insights-2026-03-21.md").exists()
