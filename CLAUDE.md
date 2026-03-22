# retrospect — CLAUDE.md

## Environnement
- Python : toujours `.venv/bin/python` — jamais `python` ou `python3` directement
- Tests : `.venv/bin/python -m pytest`
- Dépendances : `.venv/bin/pip install` — ne jamais installer globalement

## Chemins critiques
- Facets cache : `~/notes/insights/facets/`
- Rapports : `~/notes/insights/reports/`
- Sessions Claude Code : `~/.claude/usage-data/session-meta/` (meta JSON)
- JSONL conversations : `~/.claude/projects/<projet>/<session_id>.jsonl`
- Facets Anthropic (référence) : `~/.claude/usage-data/facets/`

## Pipeline
- `python insights.py <chemin>` — point d'entrée principal
- `python compare.py --detail` — comparaison avec facets Anthropic
- `python benchmark.py --phase 1` — élimination rapide des modèles
- `python benchmark.py --phase 2 --models <m1> <m2>` — batterie complète
- Les benchmarks sont longs (>1h) — toujours lancer en arrière-plan

## Git
- Remote : `https://github.com/JediMindGeeks/retrospect.git`
- Branche principale : `master`
