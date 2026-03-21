---
name: my-insights
description: Use when asked to generate insights or analyze conversations from Claude Code logs or ChatGPT exports
---

# My Insights

Génère un rapport d'insights sur des conversations Claude Code ou ChatGPT, en utilisant le pipeline local `insights.py`.

## Usage

Reçois un chemin en argument (répertoire Claude Code ou fichier conversations.json ChatGPT).

```bash
python ~/projects/insights/insights.py <chemin>
```

## Comportement

1. Si un chemin est fourni dans la demande → utilise-le directement
2. Si aucun chemin → demande : "Quel chemin analyser ? (ex: ~/.claude/usage-data/ ou ~/exports/chatgpt/conversations.json)"
3. Lance la commande avec Bash
4. Affiche le rapport markdown produit dans la conversation

## Variables d'environnement optionnelles

- `INSIGHTS_LLM=claude` → utilise Claude API au lieu d'Ollama
- `INSIGHTS_MODEL=<model>` → change le modèle Ollama (défaut : mistral-small3.1:24b)

## Exemple

Utilisateur : "Lance my-insights sur mes logs Claude Code"
→ `Bash: python ~/projects/insights/insights.py ~/.claude/usage-data/`
→ Affiche le rapport dans la conversation
