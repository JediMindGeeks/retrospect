from datetime import date as date_type
from collections import Counter
from llm import generate

NARRATIVE_PROMPT = """Tu es un analyste de sessions de travail. Voici un résumé de {total} conversations analysées.

Résumés des conversations :
{summaries}

Frictions identifiées :
{frictions}

Rédige un rapport structuré en markdown avec exactement ces sections :
## Ce qui fonctionne
(patterns positifs récurrents, 3-5 bullet points)

## Frictions récurrentes
(problèmes qui reviennent, 3-5 bullet points)

## Suggestions
(recommandations concrètes, 3-5 bullet points)

Sois concis, factuel, et base-toi uniquement sur les données fournies."""

def compute_stats(facets: list[dict]) -> dict:
    outcomes = Counter(f["outcome"] for f in facets)
    sources = Counter(f["source"] for f in facets)
    return {
        "total": len(facets),
        "outcomes": dict(outcomes),
        "sources": dict(sources),
    }

def generate_report(facets: list[dict], date: str = None) -> str:
    if date is None:
        date = str(date_type.today())
    stats = compute_stats(facets)
    summaries = "\n".join(f"- {f['brief_summary']}" for f in facets)
    frictions = "\n".join(f"- {f['friction']}" for f in facets if f.get("friction"))
    narrative = generate(NARRATIVE_PROMPT.format(
        total=stats["total"],
        summaries=summaries,
        frictions=frictions or "Aucune friction majeure identifiée.",
    ))
    sources_str = ", ".join(f"{k}: {v}" for k, v in stats["sources"].items())
    outcomes_str = ", ".join(f"{k}: {v}" for k, v in stats["outcomes"].items())
    return f"""---
date: {date}
conversations_analyzed: {stats['total']}
sources: {sources_str}
outcomes: {outcomes_str}
---

# Insights — {date}

## Vue d'ensemble

**{stats['total']} conversations analysées** | {sources_str}
Résultats : {outcomes_str}

{narrative}
"""

def save_report(content: str, date: str, reports_dir) -> str:
    from pathlib import Path
    path = Path(reports_dir) / f"insights-{date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)
