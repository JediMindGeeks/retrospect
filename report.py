import json
from datetime import date as _date_cls
from pathlib import Path
from collections import Counter
from llm import generate_narrative as generate

# ─── 6 prompts d'agrégation spécialisés (inspirés du pipeline Anthropic) ──────

_AREAS_PROMPT = """Tu es un analyste de workflows IA. Voici les objectifs et résumés de {total} sessions de travail avec Claude Code.

Sessions :
{sessions}

Identifie 4 à 5 zones de projet distinctes (ex : "Infra & DevOps", "Développement features", "Debugging").
Pour chaque zone, compte les sessions concernées et décris en 2-3 phrases l'activité réelle observée.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"areas": [{{"name": "...", "session_count": N, "description": "..."}}]}}"""

_STYLE_PROMPT = """Tu es un analyste de comportement. Voici les données de {total} sessions de travail avec Claude Code.

Types de sessions : {session_types}
Types de friction : {friction_types}
Satisfaction utilisateur : {satisfaction}
Exemples de résumés :
{summaries_sample}

Décris en 3-4 phrases le style d'interaction de cet utilisateur avec Claude Code.
Formule ensuite un "key_pattern" — une phrase qui capture l'essence de sa façon de travailler.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"narrative": "...", "key_pattern": "..."}}"""

_WORKS_PROMPT = """Tu es un analyste de succès. Voici les sessions qui ont bien fonctionné (outcome: achieved ou mostly_achieved).

Sessions réussies :
{successful_sessions}

Identifie 3 workflows ou accomplissements impressionnants. Pour chacun, donne un titre court et une description concrète de ce qui a été accompli.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"intro": "...", "impressive_workflows": [{{"title": "...", "description": "..."}}]}}"""

_FRICTION_PROMPT = """Tu es un analyste de friction. Voici les sessions où des problèmes ont été identifiés.

Sessions avec friction :
{friction_sessions}

Identifie 3 catégories de friction récurrentes. Pour chacune : nom de la catégorie, description du problème, 2 exemples concrets tirés des données.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"intro": "...", "categories": [{{"category": "...", "description": "...", "examples": ["...", "..."]}}]}}"""

_SUGGESTIONS_PROMPT = """Tu es un consultant Claude Code. Voici un résumé de {total} sessions.

Statistiques :
- Outcomes : {outcomes}
- Frictions dominantes : {top_frictions}
- Types de sessions : {session_types}
Contexte :
{context}

Génère des recommandations concrètes dans trois catégories :
1. Ajouts CLAUDE.md — instructions pour éviter les frictions récurrentes
2. Features à essayer — fonctionnalités Claude Code pertinentes mais sous-utilisées
3. Patterns d'usage — habitudes à changer ou optimiser

Réponds UNIQUEMENT avec un objet JSON valide :
{{"claude_md_additions": [{{"addition": "...", "why": "..."}}], "features_to_try": [{{"feature": "...", "one_liner": "...", "why_for_you": "..."}}], "usage_patterns": [{{"title": "...", "suggestion": "...", "detail": "..."}}]}}"""

_HORIZON_PROMPT = """Tu es un stratège IA. Voici le profil d'usage de {total} sessions Claude Code.

Style de travail : {key_pattern}
Zones de projet : {areas}
Frictions identifiées : {friction_categories}

Identifie 3 opportunités ambitieuses — des workflows que cet utilisateur pourrait réaliser avec Claude Code dans les prochains mois.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"intro": "...", "opportunities": [{{"title": "...", "whats_possible": "...", "how_to_try": "..."}}]}}"""


# ─── Utilitaires internes ──────────────────────────────────────────────────────

def _parse_json_safe(raw: str, fallback: dict) -> dict:
    """Parse le premier objet JSON trouvé dans raw, retourne fallback si échec."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            return fallback
        return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        return fallback


def _sessions_text(facets: list[dict], max_items: int = 40) -> str:
    """Résumé compact des sessions pour injection dans les prompts."""
    lines = []
    for f in facets[:max_items]:
        stype = f.get("session_type", "")
        goal = f.get("underlying_goal", "")
        summary = f.get("brief_summary", "")
        lines.append(f"- [{stype}] {goal} — {summary}")
    return "\n".join(lines)


# ─── 6 fonctions d'analyse ────────────────────────────────────────────────────

def _analyze_areas(facets: list[dict]) -> dict:
    if not facets:
        return {"areas": []}
    raw = generate(_AREAS_PROMPT.format(
        total=len(facets),
        sessions=_sessions_text(facets),
    ))
    return _parse_json_safe(raw, {"areas": []})


def _analyze_style(facets: list[dict]) -> dict:
    if not facets:
        return {"narrative": "", "key_pattern": ""}
    session_types = Counter(f.get("session_type", "unknown") for f in facets)
    friction_types = Counter(
        f.get("friction_type") for f in facets
        if f.get("friction_type") and f.get("friction_type") != "none"
    )
    satisfaction = Counter(f.get("user_satisfaction", "unclear") for f in facets)
    summaries_sample = "\n".join(f"- {f.get('brief_summary', '')}" for f in facets[:15])
    raw = generate(_STYLE_PROMPT.format(
        total=len(facets),
        session_types=", ".join(f"{k}: {v}" for k, v in session_types.most_common()),
        friction_types=", ".join(f"{k}: {v}" for k, v in friction_types.most_common()) or "aucune",
        satisfaction=", ".join(f"{k}: {v}" for k, v in satisfaction.most_common()),
        summaries_sample=summaries_sample,
    ))
    return _parse_json_safe(raw, {"narrative": "", "key_pattern": ""})


def _analyze_works(facets: list[dict]) -> dict:
    successful = [
        f for f in facets
        if f.get("outcome") in ("achieved", "mostly_achieved", "fully_achieved")
    ]
    if not successful:
        return {"intro": "", "impressive_workflows": []}
    raw = generate(_WORKS_PROMPT.format(successful_sessions=_sessions_text(successful)))
    return _parse_json_safe(raw, {"intro": "", "impressive_workflows": []})


def _analyze_friction(facets: list[dict]) -> dict:
    friction_facets = [
        f for f in facets
        if f.get("friction_type") and f.get("friction_type") != "none"
    ]
    if not friction_facets:
        return {"intro": "", "categories": []}
    lines = []
    for f in friction_facets[:30]:
        lines.append(
            f"- [{f.get('friction_type', '')}] {f.get('friction', '')} "
            f"({f.get('brief_summary', '')})"
        )
    raw = generate(_FRICTION_PROMPT.format(friction_sessions="\n".join(lines)))
    return _parse_json_safe(raw, {"intro": "", "categories": []})


def _analyze_suggestions(
    facets: list[dict], stats: dict, style: dict, friction: dict
) -> dict:
    if not facets:
        return {"claude_md_additions": [], "features_to_try": [], "usage_patterns": []}
    outcomes_str = ", ".join(f"{k}: {v}" for k, v in stats["outcomes"].items())
    friction_types = Counter(
        f.get("friction_type") for f in facets
        if f.get("friction_type") and f.get("friction_type") != "none"
    )
    top_frictions = ", ".join(f"{k}: {v}" for k, v in friction_types.most_common(5)) or "aucune"
    session_types = Counter(f.get("session_type", "unknown") for f in facets)
    session_types_str = ", ".join(f"{k}: {v}" for k, v in session_types.most_common())
    context_lines = []
    if style.get("key_pattern"):
        context_lines.append(style["key_pattern"])
    for cat in friction.get("categories", []):
        context_lines.append(f"{cat.get('category', '')}: {cat.get('description', '')}")
    raw = generate(_SUGGESTIONS_PROMPT.format(
        total=len(facets),
        outcomes=outcomes_str,
        top_frictions=top_frictions,
        session_types=session_types_str,
        context="\n".join(context_lines) or "Pas de contexte supplémentaire.",
    ))
    return _parse_json_safe(raw, {
        "claude_md_additions": [], "features_to_try": [], "usage_patterns": []
    })


def _analyze_horizon(
    facets: list[dict], style: dict, areas: dict, friction: dict
) -> dict:
    if not facets:
        return {"intro": "", "opportunities": []}
    areas_str = ", ".join(a.get("name", "") for a in areas.get("areas", []))
    friction_cats = ", ".join(c.get("category", "") for c in friction.get("categories", []))
    raw = generate(_HORIZON_PROMPT.format(
        total=len(facets),
        key_pattern=style.get("key_pattern", ""),
        areas=areas_str or "non déterminées",
        friction_categories=friction_cats or "aucune",
    ))
    return _parse_json_safe(raw, {"intro": "", "opportunities": []})


# ─── Rendu markdown ────────────────────────────────────────────────────────────

def _render_areas(areas: dict) -> str:
    items = areas.get("areas", [])
    if not items:
        return ""
    lines = ["## Zones de projet\n"]
    for a in items:
        lines.append(f"### {a.get('name', '?')} ({a.get('session_count', '?')} sessions)")
        lines.append(a.get("description", ""))
        lines.append("")
    return "\n".join(lines)


def _render_style(style: dict) -> str:
    narrative = style.get("narrative", "")
    key_pattern = style.get("key_pattern", "")
    if not narrative and not key_pattern:
        return ""
    out = "## Style d'interaction\n\n"
    if narrative:
        out += narrative + "\n\n"
    if key_pattern:
        out += f"**En résumé :** {key_pattern}\n"
    return out


def _render_works(works: dict) -> str:
    workflows = works.get("impressive_workflows", [])
    if not workflows:
        return ""
    lines = ["## Ce qui fonctionne bien\n"]
    if works.get("intro"):
        lines.append(works["intro"] + "\n")
    for w in workflows:
        lines.append(f"### {w.get('title', '?')}")
        lines.append(w.get("description", ""))
        lines.append("")
    return "\n".join(lines)


def _render_friction(friction: dict) -> str:
    categories = friction.get("categories", [])
    if not categories:
        return ""
    lines = ["## Frictions récurrentes\n"]
    if friction.get("intro"):
        lines.append(friction["intro"] + "\n")
    for cat in categories:
        lines.append(f"### {cat.get('category', '?')}")
        lines.append(cat.get("description", ""))
        for ex in cat.get("examples", []):
            lines.append(f"- {ex}")
        lines.append("")
    return "\n".join(lines)


def _render_suggestions(suggestions: dict) -> str:
    additions = suggestions.get("claude_md_additions", [])
    features = suggestions.get("features_to_try", [])
    patterns = suggestions.get("usage_patterns", [])
    if not additions and not features and not patterns:
        return ""
    lines = ["## Suggestions\n"]
    if additions:
        lines.append("### Ajouts CLAUDE.md\n")
        for a in additions:
            lines.append(f"**{a.get('addition', '?')}**")
            if a.get("why"):
                lines.append(f"*Pourquoi :* {a['why']}")
            lines.append("")
    if features:
        lines.append("### Features à essayer\n")
        for f in features:
            lines.append(f"**{f.get('feature', '?')}** — {f.get('one_liner', '')}")
            if f.get("why_for_you"):
                lines.append(f.get("why_for_you"))
            lines.append("")
    if patterns:
        lines.append("### Patterns d'usage\n")
        for p in patterns:
            lines.append(f"**{p.get('title', '?')}**")
            lines.append(p.get("suggestion", ""))
            if p.get("detail"):
                lines.append(p.get("detail"))
            lines.append("")
    return "\n".join(lines)


def _render_horizon(horizon: dict) -> str:
    opportunities = horizon.get("opportunities", [])
    if not opportunities:
        return ""
    lines = ["## Sur l'horizon\n"]
    if horizon.get("intro"):
        lines.append(horizon["intro"] + "\n")
    for opp in opportunities:
        lines.append(f"### {opp.get('title', '?')}")
        lines.append(opp.get("whats_possible", ""))
        if opp.get("how_to_try"):
            lines.append(f"\n*Comment essayer :* {opp['how_to_try']}")
        lines.append("")
    return "\n".join(lines)


# ─── API publique ──────────────────────────────────────────────────────────────

def compute_stats(facets: list[dict]) -> dict:
    outcomes = Counter(f.get("outcome", "unknown") for f in facets)
    sources = Counter(f.get("source", "unknown") for f in facets)
    return {
        "total": len(facets),
        "outcomes": dict(sorted(outcomes.items())),
        "sources": dict(sorted(sources.items())),
    }


def generate_report(facets: list[dict], date: str | None = None) -> str:
    """Génère un rapport markdown structuré via 6 analyses LLM spécialisées."""
    if date is None:
        date = str(_date_cls.today())
    stats = compute_stats(facets)

    # 6 analyses spécialisées (pipeline inspiré d'Anthropic)
    areas = _analyze_areas(facets)
    style = _analyze_style(facets)
    works = _analyze_works(facets)
    friction = _analyze_friction(facets)
    suggestions = _analyze_suggestions(facets, stats, style, friction)
    horizon = _analyze_horizon(facets, style, areas, friction)

    sources_str = ", ".join(f"{k}: {v}" for k, v in stats["sources"].items())
    outcomes_str = ", ".join(f"{k}: {v}" for k, v in stats["outcomes"].items())

    header = f"""---
date: {date}
conversations_analyzed: {stats['total']}
sources: {sources_str}
outcomes: {outcomes_str}
---

# Insights — {date}

## Vue d'ensemble

**{stats['total']} conversations analysées** | {sources_str}
Résultats : {outcomes_str}"""

    sections = [
        header,
        _render_areas(areas),
        _render_style(style),
        _render_works(works),
        _render_friction(friction),
        _render_suggestions(suggestions),
        _render_horizon(horizon),
    ]
    return "\n\n".join(s for s in sections if s.strip())


def save_report(content: str, date: str, reports_dir: str | Path) -> str:
    path = Path(reports_dir) / f"insights-{date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)
