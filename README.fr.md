# retrospect

Un CLI Python portable qui reproduit le pipeline d'analyse de Claude Code — analyse les logs de conversations, génère des "facets" structurées par session via LLM, et agrège le tout en un rapport narratif markdown.

Compatible avec les sessions **Claude Code** et les exports **ChatGPT**.

> Inspiré par la commande `/insights` de Claude Code (Anthropic).

## Ce que ça fait

1. **Parse** les logs de conversations (JSONL Claude Code ou export JSON ChatGPT)
2. **Génère des facets** — des résumés JSON structurés par conversation (objectif, résultat, points clés, frictions) via LLM
3. **Met en cache** les facets localement pour que les relances soient instantanées
4. **Agrège** le tout en un rapport markdown avec statistiques et narration

## Prérequis

- Python 3.11+
- [Ollama](https://ollama.com/) en local **ou** une clé API Anthropic

## Installation

```bash
git clone https://github.com/JediMindGeeks/retrospect
cd retrospect
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation

```bash
# Analyser les sessions Claude Code depuis ~/.claude/usage-data/session-meta/
python insights.py ~/.claude/usage-data/session-meta/

# Analyser un export ChatGPT
python insights.py ~/Téléchargements/conversations.json

# Utiliser Claude au lieu d'Ollama
INSIGHTS_LLM=claude python insights.py ~/.claude/usage-data/session-meta/
```

## Configuration

Tous les paramètres sont configurables via variables d'environnement :

| Variable | Défaut | Description |
|---|---|---|
| `INSIGHTS_LLM` | `ollama` | Backend LLM : `ollama` ou `claude` |
| `INSIGHTS_MODEL` | `mistral-small3.1:24b` | Modèle Ollama à utiliser |
| `OLLAMA_URL` | `http://localhost:11434` | URL du serveur Ollama |
| `INSIGHTS_MAX_CHARS` | `32000` | Taille max de conversation envoyée au LLM (début + fin) |
| `INSIGHTS_TIMEOUT` | `300` | Timeout des requêtes LLM en secondes |

Les répertoires de sortie sont par défaut `~/notes/insights/facets/` et `~/notes/insights/reports/`.

## Comparer avec les facets natives d'Anthropic

```bash
# Après avoir lancé le pipeline sur des sessions Claude Code :
python compare.py --detail
```

Compare les facets générées avec celles produites nativement par Anthropic (stockées dans `~/.claude/usage-data/facets/`) — utile pour évaluer la qualité du pipeline.

## Structure du projet

```
insights.py          # Point d'entrée CLI + orchestration
config.py            # Configuration (variables d'env + chemins)
llm.py               # Backends LLM (Ollama / Claude)
facets.py            # Génération, validation et cache des facets
report.py            # Agrégation du rapport
compare.py           # Comparaison de nos facets vs celles d'Anthropic
parsers/
  claude_code.py     # Parser des session-meta Claude Code
  chatgpt.py         # Parser des exports ChatGPT
```

## Lancer les tests

```bash
pytest
```

## Schéma d'une facet

Chaque facet est un fichier JSON avec ces champs :

```json
{
  "underlying_goal": "Ce que l'utilisateur cherchait vraiment à faire",
  "outcome": "achieved | mostly_achieved | not_achieved | unclear_from_transcript",
  "key_points": ["Point 1", "Point 2"],
  "friction": "Principale difficulté rencontrée, ou chaîne vide",
  "brief_summary": "Résumé factuel en 1-2 phrases",
  "conversation_id": "id-de-session",
  "source": "claude_code | chatgpt"
}
```
