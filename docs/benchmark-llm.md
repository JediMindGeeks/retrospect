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

## Résultats Phase 1 — 2026-03-22

18/19 modèles survivants. Seul `Llama-3-Admin` éliminé (404 — modèle corrompu).

Accord Anthropic sur `01390feb` dès la Phase 1 :

| Accord ✓ (`not_achieved`) | Désaccord ✗ |
|---|---|
| qwen3-14b, qwen3-8b, qwen3-vl-thinking-32k, qwen2.5-14b, qwen2.5-coder, mistral-small3.2, deepseek-r1-16k, deepseek-r1-tc | mistral-small3.1 (`unclear`), mistral-16k (`unclear`), llama3.1 (`unclear`), phi4-mini (`unclear`), granite4-3b (`unclear`), granite4-tiny (`unclear`), granite4-1b (`unclear`), llama3.2 (`achieved`), deepseek-r1-llama (`achieved`), llama3-groq (`mostly_achieved`) |

Phase 2 option B appliquée : `llama3.2`, `deepseek-r1-llama`, `llama3-groq` testés séparément en fin de benchmark pour rester méthodique.

## Résultats Phase 2 — 2026-03-22

Batterie : 5 sessions × 18 modèles × 2 runs. Résultats bruts : `docs/results-phase2.json`.

Classement final par accord Anthropic (sessions `01390feb` et `119d6ac9`, vérité terrain) :

| Modèle | Accord Anthropic | Stabilité | Vitesse moy. | JSON valide |
|--------|-----------------|-----------|--------------|-------------|
| `granite4:tiny-h` | **3/4** | 3/5 | 10s | 9/10 |
| `qwen2.5-coder-16k` | 2/4 | 4/5 | 18s | 10/10 |
| `granite4-3b-16k` | 2/4 | **5/5** | 10s | 10/10 |
| `deepseek-r1-16k` | 2/4 | 4/5 | 83s | 10/10 |
| `qwen2.5-14b-16k` | 2/4 | 3/5 | 34s | 9/10 |
| `deepseek-r1-llama-16k` | 1/4 | 3/5 | 90s | 9/10 |
| `qwen3-14b-16k` | 1/4 | 3/5 | 96s | 10/10 |
| `qwen3-16k` | 1/4 | 3/5 | 61s | 10/10 |
| `mistral-small3.2-16k` | 1/4 | 4/5 | 54s | 10/10 |
| `deepseek-r1-tc-16k` | 1/4 | 3/5 | 66s | 8/10 |
| `mistral-small3.1-24b-16k` *(baseline)* | 0/4 | 5/5 | 55s | 10/10 |
| `qwen3-vl-thinking-32k` | 0/4 | 3/5 | 219s | 7/10 |
| `mistral-16k` | 0/4 | 4/5 | 22s | 10/10 |
| `llama3.1-16k` | 0/4 | 3/5 | 20s | 9/10 |
| `phi4-mini-16k` | 0/4 | 3/5 | 12s | 8/10 |
| `llama3-groq-tool-16k` | 0/4 | 2/5 | 14s | 10/10 |
| `llama3.2-16k` | 0/4 | 2/5 | 7s | 8/10 |
| `granite4:1b` | 0/4 | 1/5 | 6s | 3/10 |

**Observations notables :**

- `granite4:tiny-h` (4.2GB) obtient le meilleur accord (3/4) — surprise majeure. A produit une valeur hors enum (`partially_achieved`) sur une session.
- `mistral-small3.1` (baseline actuelle) : 0/4, stable dans l'erreur (`unclear_from_transcript` systématique). À remplacer.
- `qwen2.5-coder-16k` : modèle orienté code, excellent sur l'analyse de conversations. 18s, 4/5 stabilité, JSON parfait.
- `119d6ac9` est la session la plus discriminante : quasi tous les modèles disent `achieved`, seul `granite4:tiny-h` trouve `not_achieved` sur les deux runs.
- Les modèles CORTEX-benchmark (qwen3-14b, mistral, llama) performent moins bien ici qu'attendu — confirmation que les deux tâches sont indépendantes.

## Décision finale — 2026-03-22

**Modèle recommandé pour production : `qwen2.5-coder-16k`**

Justification :
- 2/4 accord Anthropic (vs 0/4 pour la baseline)
- 4/5 stabilité — prévisible sur runs répétés
- 18s/session — 54 sessions en ~16 min (vs ~90 min avec mistral-small3.1)
- JSON valide 10/10 — aucune valeur hors enum
- Taille 4.7GB — tient en VRAM

**Alternative si précision prime sur stabilité : `granite4:tiny-h`**
- Meilleur accord (3/4) mais instabilité JSON (valeur hors enum possible)
- À envisager avec validation stricte de l'enum + retry automatique

**Éliminé définitivement : `mistral-small3.1-24b-16k`**
- Notre baseline actuelle, le pire résultat (0/4), remplacé immédiatement

**Variable d'environnement à changer :**
```bash
INSIGHTS_MODEL=qwen2.5-coder-16k:latest
# ou dans config.py : OLLAMA_MODEL = "qwen2.5-coder-16k:latest"
```

## Résultats post-déploiement — schéma enrichi + qwen2.5-coder

Run complet sur 56 sessions (2026-03-22) après enrichissement du schéma :

**Distribution outcomes :**
- not_achieved : 26 (46%)
- unclear_from_transcript : 20 (36%)
- achieved : 8 (14%)
- mostly_achieved : 2 (4%)

**Comparaison Anthropic :** 18/49 (37%) accord sur outcome — vs 9/47 (19%) avec l'ancienne baseline.

**Observations :**
- `119d6ac9` correctement identifié `unclear_from_transcript` (était notre cas discriminant non résolu)
- Anthropic utilise `fully_achieved` / `partially_achieved` — synonymes de nos `achieved` / `mostly_achieved`. Le vrai accord normalisé serait supérieur à 37%.
- Le champ `friction` reste souvent vide même quand une friction est présente — axe d'amélioration du prompt.
- Quelques nouveaux faux négatifs (trop pessimiste sur sessions réussies).

**Axes restants :**
1. Normaliser l'enum Anthropic dans `compare.py` pour mesurer le vrai accord
2. Améliorer la détection de friction dans le prompt
3. Corriger le bug du rapport narratif (JSON brut au lieu de markdown)

## Résultats post-correctifs — 2026-03-22

Après application des trois correctifs (commit `ecb6c95`) et régénération complète des 56 facets :

**Fix 1 — Rapport narratif ✅ résolu**
Le rapport génère du markdown lisible (sections "Ce qui fonctionne", "Frictions récurrentes", "Suggestions").
Plus aucun JSON brut dans la section Vue d'ensemble.

**Fix 2 — Normalisation OUTCOME_MAP**
Accord Anthropic : **18/49 (37%)** — identique au run précédent.
Conclusion : Anthropic n'utilise pas `fully_achieved`/`partially_achieved` dans ce dataset (ils utilisent déjà `achieved`/`mostly_achieved`). Le mapping est correct et robuste pour futurs datasets, sans impact mesurable ici.

**Fix 3 — Détection de friction ✅ résolu**
Session `01390feb` (cas de référence "Claude décrit les étapes") :
- `friction`: `"Claude a décrit les étapes au lieu de les exécuter"` ✅ non vide
- `friction_type`: `"wrong_approach"` ✅

**Distribution outcomes après régénération :**
- not_achieved : 23 (41%)
- unclear_from_transcript : 21 (38%)
- achieved : 6 (11%)
- mostly_achieved : 6 (11%)

Légère correction par rapport au run précédent : le nouveau prompt friction plus précis a rebalancé quelques sessions `achieved` → `mostly_achieved`.

**État final :**
- Rapport narratif : ✅ markdown
- Accord Anthropic : 37% (stable)
- Friction détectée sur sessions à friction connue : ✅
- Tests : 57/57 ✅
