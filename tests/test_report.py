import pytest
from unittest.mock import patch
from report import compute_stats, generate_report

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
