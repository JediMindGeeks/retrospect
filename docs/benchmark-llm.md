# Benchmark LLM — Sélection du modèle optimal pour retrospect

## Contexte

Le pipeline retrospect génère des "facets" structurées (JSON) à partir de transcriptions de conversations IA. La tâche est fondamentalement différente d'un agent avec tool calling :

- **Pas de tool calling** — aucun outil à invoquer
- **Pas de persona** — aucun SOUL.md, aucune règle IF/THEN
- **Tâche unique** : lire un texte de conversation → analyser → sortir un objet JSON valide

Ce benchmark évalue **tous les modèles Ollama locaux disponibles** sans biais préalable. Les résultats de benchmarks précédents (CORTEX, ZeroClaw) ne sont pas transférables ici car la tâche est différente.

## Schéma attendu

```json
{
  "underlying_goal": "Ce que l'utilisateur cherchait vraiment à faire",
  "outcome": "achieved | mostly_achieved | not_achieved | unclear_from_transcript",
  "key_points": ["Point 1", "Point 2"],
  "friction": "Principale difficulté, ou chaîne vide",
  "brief_summary": "Résumé factuel en 1-2 phrases",
  "conversation_id": "...",
  "source": "claude_code"
}
```

Le champ `outcome` est l'indicateur de qualité principal car :
1. C'est un enum strict — facile à évaluer objectivement
2. Anthropic génère ses propres facets sur les mêmes sessions → vérité de référence disponible
3. Notre pipeline actuel (mistral-small3.1:24b) présente un **biais optimiste** marqué :
   accord avec Anthropic sur outcome = **9/47 (19%)**, systématiquement trop "achieved"

## Sessions de référence (vérité terrain)

Sessions courtes avec verdict Anthropic connu, utilisées comme cas de test :

| Session | Msgs | Notre verdict | Anthropic | Notes |
|---------|------|---------------|-----------|-------|
| `01390feb` | 4 | achieved | **not_achieved** | Claude décrit les étapes au lieu d'exécuter — cas clé du biais optimiste |
| `119d6ac9` | 7 | achieved | **not_achieved** | Même pattern |
| `762cfc61` | 4 | not_achieved | ? | Cas négatif court |
| `e455a82a` | 4 | unclear_from_transcript | ? | Cas ambigu |
| `2b0f9fd8` | 3 | achieved | ? | Cas positif minimal |

## Méthodologie en deux phases

### Phase 1 — Élimination rapide

**Objectif :** identifier les modèles capables de produire un JSON valide.

- 1 session de test : `01390feb` (4 msgs, résultat Anthropic connu)
- 1 run par modèle
- Timeout : 5 minutes par modèle
- Critère binaire : ✅ JSON valide avec tous les champs requis / ❌ échec

**Sortie :** liste des modèles qui passent en Phase 2.

### Phase 2 — Batterie complète

**Objectif :** évaluer la qualité d'analyse sur 5 sessions représentatives.

- 5 sessions de test (voir tableau ci-dessus)
- 2 runs par session × modèle (mesure de stabilité/variance)
- Timeout : 10 minutes par appel

**Grille d'évaluation :**

| Critère | Description | Poids |
|---------|-------------|-------|
| **Outcome correct** | Accord avec Anthropic sur les sessions de référence | Principal |
| **JSON valide** | Champs exacts, enum respecté (sans structured output forcé) | Éliminatoire |
| **Goal précis** | Identifie le vrai objectif, pas juste le sujet général | Qualitatif |
| **Friction détectée** | Repère les vrais problèmes quand présents | Qualitatif |
| **Vitesse** | Temps de génération (secondes) | Pratique |
| **Stabilité** | Variance entre run 1 et run 2 sur même session | Fiabilité |

## Modèles testés

Tous les modèles locaux Ollama disponibles au 2026-03-22. Exclusions :
- Modèles d'embedding (`nomic-embed-text`, `embeddinggemma`) — non génératifs
- Modèles cloud (`minimax-m2.7:cloud`, `kimi-k2.5:cloud`, `qwen3-coder-next:cloud`)
- Doublons base : quand un modèle a une version `-16k` Modelfile, on teste la version 16k (contexte explicitement configuré)

## Résultats Phase 1

> À remplir après exécution de `python benchmark.py --phase 1`

## Résultats Phase 2

> À remplir après exécution de `python benchmark.py --phase 2`

## Décision finale

> À remplir après analyse des résultats Phase 2.
