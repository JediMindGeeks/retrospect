import json
import pytest
from unittest.mock import patch
from report import (
    compute_stats, generate_report, save_report,
    _parse_json_safe, _sessions_text,
    _analyze_areas, _analyze_style, _analyze_works,
    _analyze_friction, _analyze_suggestions, _analyze_horizon,
    _render_areas, _render_style, _render_works,
    _render_friction, _render_suggestions, _render_horizon,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_FACETS = [
    {
        "conversation_id": "a", "source": "claude_code",
        "underlying_goal": "déboguer un script Python",
        "outcome": "achieved", "session_type": "debug",
        "friction_type": "none", "friction": "",
        "user_satisfaction": "satisfied",
        "key_points": ["pdb utilisé"], "brief_summary": "Débogage réussi avec pdb",
    },
    {
        "conversation_id": "b", "source": "claude_code",
        "underlying_goal": "configurer un montage NAS",
        "outcome": "not_achieved", "session_type": "config",
        "friction_type": "environment", "friction": "Permissions fstab incorrectes",
        "user_satisfaction": "frustrated",
        "key_points": ["fstab", "CIFS"], "brief_summary": "Montage NAS échoué — permissions",
    },
    {
        "conversation_id": "c", "source": "claude_code",
        "underlying_goal": "créer une API REST FastAPI",
        "outcome": "mostly_achieved", "session_type": "deep_work",
        "friction_type": "wrong_approach", "friction": "Claude a décrit les étapes sans exécuter",
        "user_satisfaction": "neutral",
        "key_points": ["FastAPI", "routes"], "brief_summary": "API créée, auth manquante",
    },
]

# Réponses JSON mockées pour chaque analyse
MOCK_AREAS = json.dumps({"areas": [
    {"name": "Développement", "session_count": 2, "description": "Sessions de dev et debug."},
    {"name": "Infra", "session_count": 1, "description": "Configuration NAS."},
]})
MOCK_STYLE = json.dumps({
    "narrative": "L'utilisateur travaille de façon itérative et corrige fréquemment Claude.",
    "key_pattern": "Itératif et correctif — dirige activement chaque session",
})
MOCK_WORKS = json.dumps({
    "intro": "Deux sessions ont produit des résultats concrets.",
    "impressive_workflows": [
        {"title": "Débogage Python réussi", "description": "Utilisation efficace de pdb."},
        {"title": "API FastAPI fonctionnelle", "description": "Routes REST créées rapidement."},
    ],
})
MOCK_FRICTION = json.dumps({
    "intro": "Deux types de friction récurrents identifiés.",
    "categories": [
        {
            "category": "Wrong approach",
            "description": "Claude décrit au lieu d'exécuter.",
            "examples": ["Étapes décrites manuellement", "Pas d'utilisation des outils"],
        },
        {
            "category": "Environnement",
            "description": "Problèmes de permissions système.",
            "examples": ["fstab incorrect", "Droits manquants"],
        },
    ],
})
MOCK_SUGGESTIONS = json.dumps({
    "claude_md_additions": [
        {"addition": "Toujours exécuter, ne jamais décrire", "why": "Friction récurrente."},
    ],
    "features_to_try": [
        {"feature": "Hooks", "one_liner": "Auto-validation à chaque commit", "why_for_you": "Évite les erreurs silencieuses."},
    ],
    "usage_patterns": [
        {"title": "Pre-flight check", "suggestion": "Valider l'infra avant chaque session.", "detail": ""},
    ],
})
MOCK_HORIZON = json.dumps({
    "intro": "Trois opportunités ambitieuses identifiées.",
    "opportunities": [
        {"title": "Pipeline autonome", "whats_possible": "Infra auto-validante.", "how_to_try": "Agents en boucle."},
    ],
})

MOCK_RESPONSES = [
    MOCK_AREAS, MOCK_STYLE, MOCK_WORKS,
    MOCK_FRICTION, MOCK_SUGGESTIONS, MOCK_HORIZON,
]


# ─── Tests utilitaires ─────────────────────────────────────────────────────────

class TestParseJsonSafe:
    def test_valid_json(self):
        result = _parse_json_safe('{"key": "value"}', {})
        assert result == {"key": "value"}

    def test_json_with_prefix(self):
        result = _parse_json_safe('Voici le JSON : {"key": "value"} fin', {})
        assert result == {"key": "value"}

    def test_invalid_json_returns_fallback(self):
        fallback = {"error": True}
        result = _parse_json_safe("pas du JSON", fallback)
        assert result == fallback

    def test_empty_string_returns_fallback(self):
        fallback = {"default": 1}
        assert _parse_json_safe("", fallback) == fallback

    def test_no_closing_brace_returns_fallback(self):
        assert _parse_json_safe('{"incomplete": ', {}) == {}


class TestSessionsText:
    def test_formats_sessions(self):
        text = _sessions_text(SAMPLE_FACETS)
        assert "[debug]" in text
        assert "déboguer un script Python" in text

    def test_max_items(self):
        many = SAMPLE_FACETS * 20
        text = _sessions_text(many, max_items=5)
        assert text.count("\n") == 4  # 5 lignes = 4 sauts

    def test_empty_list(self):
        assert _sessions_text([]) == ""


# ─── Tests compute_stats ───────────────────────────────────────────────────────

class TestComputeStats:
    def test_counts_total(self):
        assert compute_stats(SAMPLE_FACETS)["total"] == 3

    def test_counts_outcomes(self):
        stats = compute_stats(SAMPLE_FACETS)
        assert stats["outcomes"]["achieved"] == 1
        assert stats["outcomes"]["not_achieved"] == 1
        assert stats["outcomes"]["mostly_achieved"] == 1

    def test_counts_sources(self):
        stats = compute_stats(SAMPLE_FACETS)
        assert stats["sources"]["claude_code"] == 3

    def test_outcomes_sorted(self):
        stats = compute_stats(SAMPLE_FACETS)
        keys = list(stats["outcomes"].keys())
        assert keys == sorted(keys)

    def test_missing_source_defaults_to_unknown(self):
        stats = compute_stats([{"outcome": "achieved", "brief_summary": "x"}])
        assert stats["sources"]["unknown"] == 1

    def test_missing_outcome_defaults_to_unknown(self):
        stats = compute_stats([{"source": "claude_code", "brief_summary": "x"}])
        assert stats["outcomes"]["unknown"] == 1

    def test_empty_facets(self):
        stats = compute_stats([])
        assert stats["total"] == 0
        assert stats["outcomes"] == {}
        assert stats["sources"] == {}


# ─── Tests des 6 analyses ─────────────────────────────────────────────────────

class TestAnalyzeAreas:
    def test_calls_generate(self):
        with patch("report.generate", return_value=MOCK_AREAS) as mock:
            result = _analyze_areas(SAMPLE_FACETS)
        mock.assert_called_once()
        assert "areas" in result
        assert len(result["areas"]) == 2

    def test_empty_facets_no_llm_call(self):
        with patch("report.generate") as mock:
            result = _analyze_areas([])
        mock.assert_not_called()
        assert result == {"areas": []}

    def test_invalid_json_returns_fallback(self):
        with patch("report.generate", return_value="réponse invalide"):
            result = _analyze_areas(SAMPLE_FACETS)
        assert result == {"areas": []}


class TestAnalyzeStyle:
    def test_returns_narrative_and_pattern(self):
        with patch("report.generate", return_value=MOCK_STYLE):
            result = _analyze_style(SAMPLE_FACETS)
        assert "narrative" in result
        assert "key_pattern" in result
        assert len(result["narrative"]) > 0

    def test_empty_facets_no_llm_call(self):
        with patch("report.generate") as mock:
            result = _analyze_style([])
        mock.assert_not_called()
        assert result == {"narrative": "", "key_pattern": ""}


class TestAnalyzeWorks:
    def test_filters_successful_sessions(self):
        with patch("report.generate", return_value=MOCK_WORKS) as mock:
            result = _analyze_works(SAMPLE_FACETS)
        mock.assert_called_once()
        assert "impressive_workflows" in result

    def test_no_successful_sessions_no_llm_call(self):
        all_failed = [{**f, "outcome": "not_achieved"} for f in SAMPLE_FACETS]
        with patch("report.generate") as mock:
            result = _analyze_works(all_failed)
        mock.assert_not_called()
        assert result == {"intro": "", "impressive_workflows": []}

    def test_fully_achieved_counts_as_successful(self):
        facets = [{**SAMPLE_FACETS[0], "outcome": "fully_achieved"}]
        with patch("report.generate", return_value=MOCK_WORKS) as mock:
            _analyze_works(facets)
        mock.assert_called_once()


class TestAnalyzeFriction:
    def test_filters_friction_sessions(self):
        with patch("report.generate", return_value=MOCK_FRICTION) as mock:
            result = _analyze_friction(SAMPLE_FACETS)
        mock.assert_called_once()
        assert "categories" in result

    def test_no_friction_no_llm_call(self):
        no_friction = [{**f, "friction_type": "none"} for f in SAMPLE_FACETS]
        with patch("report.generate") as mock:
            result = _analyze_friction(no_friction)
        mock.assert_not_called()
        assert result == {"intro": "", "categories": []}


class TestAnalyzeSuggestions:
    def test_returns_three_sections(self):
        stats = compute_stats(SAMPLE_FACETS)
        style = {"narrative": "...", "key_pattern": "Itératif"}
        friction = {"intro": "", "categories": [{"category": "Wrong approach", "description": "..."}]}
        with patch("report.generate", return_value=MOCK_SUGGESTIONS):
            result = _analyze_suggestions(SAMPLE_FACETS, stats, style, friction)
        assert "claude_md_additions" in result
        assert "features_to_try" in result
        assert "usage_patterns" in result


class TestAnalyzeHorizon:
    def test_returns_opportunities(self):
        style = {"key_pattern": "Itératif"}
        areas = {"areas": [{"name": "Dev"}]}
        friction = {"categories": [{"category": "Wrong approach"}]}
        with patch("report.generate", return_value=MOCK_HORIZON):
            result = _analyze_horizon(SAMPLE_FACETS, style, areas, friction)
        assert "opportunities" in result
        assert len(result["opportunities"]) >= 1


# ─── Tests du rendu markdown ──────────────────────────────────────────────────

class TestRenderAreas:
    def test_renders_section_header(self):
        areas = json.loads(MOCK_AREAS)
        md = _render_areas(areas)
        assert "## Zones de projet" in md
        assert "Développement" in md
        assert "Infra" in md

    def test_empty_returns_empty_string(self):
        assert _render_areas({"areas": []}) == ""


class TestRenderStyle:
    def test_renders_narrative(self):
        style = json.loads(MOCK_STYLE)
        md = _render_style(style)
        assert "## Style d'interaction" in md
        assert "itérative" in md
        assert "**En résumé :**" in md

    def test_empty_returns_empty_string(self):
        assert _render_style({"narrative": "", "key_pattern": ""}) == ""


class TestRenderWorks:
    def test_renders_workflows(self):
        works = json.loads(MOCK_WORKS)
        md = _render_works(works)
        assert "## Ce qui fonctionne bien" in md
        assert "Débogage Python réussi" in md

    def test_empty_returns_empty_string(self):
        assert _render_works({"impressive_workflows": []}) == ""


class TestRenderFriction:
    def test_renders_categories(self):
        friction = json.loads(MOCK_FRICTION)
        md = _render_friction(friction)
        assert "## Frictions récurrentes" in md
        assert "Wrong approach" in md
        assert "- Étapes décrites manuellement" in md

    def test_empty_returns_empty_string(self):
        assert _render_friction({"categories": []}) == ""


class TestRenderSuggestions:
    def test_renders_all_subsections(self):
        suggestions = json.loads(MOCK_SUGGESTIONS)
        md = _render_suggestions(suggestions)
        assert "## Suggestions" in md
        assert "### Ajouts CLAUDE.md" in md
        assert "### Features à essayer" in md
        assert "### Patterns d'usage" in md

    def test_empty_returns_empty_string(self):
        assert _render_suggestions({"claude_md_additions": [], "features_to_try": [], "usage_patterns": []}) == ""


class TestRenderHorizon:
    def test_renders_opportunities(self):
        horizon = json.loads(MOCK_HORIZON)
        md = _render_horizon(horizon)
        assert "## Sur l'horizon" in md
        assert "Pipeline autonome" in md

    def test_empty_returns_empty_string(self):
        assert _render_horizon({"opportunities": []}) == ""


# ─── Tests generate_report (intégration) ──────────────────────────────────────

class TestGenerateReport:
    def test_frontmatter_present(self):
        with patch("report.generate", side_effect=MOCK_RESPONSES):
            md = generate_report(SAMPLE_FACETS, date="2026-03-22")
        assert md.startswith("---")
        assert "date: 2026-03-22" in md
        assert "conversations_analyzed: 3" in md

    def test_vue_ensemble_present(self):
        with patch("report.generate", side_effect=MOCK_RESPONSES):
            md = generate_report(SAMPLE_FACETS, date="2026-03-22")
        assert "## Vue d'ensemble" in md
        assert "3 conversations analysées" in md

    def test_six_sections_rendered(self):
        with patch("report.generate", side_effect=MOCK_RESPONSES):
            md = generate_report(SAMPLE_FACETS, date="2026-03-22")
        assert "## Zones de projet" in md
        assert "## Style d'interaction" in md
        assert "## Ce qui fonctionne bien" in md
        assert "## Frictions récurrentes" in md
        assert "## Suggestions" in md
        assert "## Sur l'horizon" in md

    def test_six_llm_calls_made(self):
        with patch("report.generate", side_effect=MOCK_RESPONSES) as mock:
            generate_report(SAMPLE_FACETS, date="2026-03-22")
        assert mock.call_count == 6

    def test_date_none_uses_today(self):
        with patch("report.generate", side_effect=MOCK_RESPONSES):
            md = generate_report(SAMPLE_FACETS)
        assert "date:" in md

    def test_empty_facets_no_llm_call(self):
        with patch("report.generate") as mock:
            md = generate_report([], date="2026-03-22")
        assert "date: 2026-03-22" in md
        assert "0" in md
        assert mock.call_count == 0

    def test_llm_failure_graceful(self):
        """Si toutes les analyses LLM retournent du JSON invalide, le rapport ne crash pas."""
        with patch("report.generate", return_value="réponse invalide"):
            md = generate_report(SAMPLE_FACETS, date="2026-03-22")
        assert "## Vue d'ensemble" in md
        assert "conversations analysées" in md


# ─── Tests save_report ────────────────────────────────────────────────────────

class TestSaveReport:
    def test_writes_file(self, tmp_path):
        content = "# Test report"
        save_report(content, "2026-03-22", tmp_path)
        assert (tmp_path / "insights-2026-03-22.md").read_text() == content

    def test_returns_path_string(self, tmp_path):
        path = save_report("content", "2026-03-22", tmp_path)
        assert isinstance(path, str)
        assert path.endswith("insights-2026-03-22.md")

    def test_creates_missing_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        save_report("content", "2026-03-22", nested)
        assert (nested / "insights-2026-03-22.md").exists()
