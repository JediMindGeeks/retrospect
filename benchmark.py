#!/usr/bin/env python3
"""
benchmark.py — Évalue les modèles Ollama locaux sur la tâche de génération de facets.

Phase 1 : test rapide sur 1 session — élimination par validité JSON
Phase 2 : batterie complète sur 5 sessions — qualité, vitesse, stabilité

Usage:
    python benchmark.py --phase 1
    python benchmark.py --phase 2
    python benchmark.py           # les deux phases en séquence

Voir docs/benchmark-llm.md pour la méthodologie complète.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Ajoute le répertoire courant au path pour les imports locaux
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from facets import FACET_PROMPT, VALID_OUTCOMES, REQUIRED_FIELDS, _extract_text, _truncate
from config import Config

# ---------------------------------------------------------------------------
# Modèles à tester
# Tous les modèles locaux disponibles (hors embedding, hors cloud, doublons résolus
# en faveur des versions -16k quand disponibles)
# ---------------------------------------------------------------------------
MODELS = [
    # Famille qwen3
    "qwen3-14b-16k:latest",
    "qwen3-16k:latest",            # 8b
    "qwen3-vl-thinking-32k:latest",

    # Famille qwen2.5
    "qwen2.5-14b-16k:latest",
    "qwen2.5-coder-16k:latest",

    # Famille mistral
    "mistral-small3.1-24b-16k:latest",   # baseline actuelle
    "mistral-small3.2-16k:latest",
    "mistral-16k:latest",

    # Famille llama
    "llama3.1-16k:latest",
    "llama3.2-16k:latest",
    "llama3-groq-tool-16k:latest",
    "Llama-3-Admin:latest",

    # Famille deepseek-r1
    "deepseek-r1-16k:latest",           # qwen3 distill
    "deepseek-r1-llama-16k:latest",
    "deepseek-r1-tc-16k:latest",        # MFDoom tool-calling patch

    # Famille phi / granite
    "phi4-mini-16k:latest",
    "granite4-3b-16k:latest",
    "granite4:tiny-h",
    "granite4:1b",
]

# ---------------------------------------------------------------------------
# Sessions de test
# Voir docs/benchmark-llm.md pour le détail et les verdicts Anthropic de référence
# ---------------------------------------------------------------------------
TEST_SESSIONS = {
    "01390feb": {
        "desc": "4 msgs — Claude décrit au lieu d'exécuter",
        "anthropic_outcome": "not_achieved",   # vérité terrain
    },
    "119d6ac9": {
        "desc": "7 msgs — même pattern biais optimiste",
        "anthropic_outcome": "not_achieved",
    },
    "762cfc61": {
        "desc": "4 msgs — cas négatif court",
        "anthropic_outcome": None,
    },
    "e455a82a": {
        "desc": "4 msgs — cas ambigu",
        "anthropic_outcome": None,
    },
    "2b0f9fd8": {
        "desc": "3 msgs — cas positif minimal",
        "anthropic_outcome": None,
    },
}

PHASE1_SESSION = "01390feb"
PHASE1_TIMEOUT = 300   # 5 min
PHASE2_TIMEOUT = 600   # 10 min

SESSION_META_DIR = Path.home() / ".claude" / "usage-data" / "session-meta"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# ---------------------------------------------------------------------------
# Chargement des sessions
# ---------------------------------------------------------------------------
_jsonl_index: dict[str, Path] | None = None

def _get_jsonl_index() -> dict[str, Path]:
    global _jsonl_index
    if _jsonl_index is None:
        _jsonl_index = {}
        if CLAUDE_PROJECTS_DIR.exists():
            for f in CLAUDE_PROJECTS_DIR.glob("*/*.jsonl"):
                _jsonl_index[f.stem] = f
    return _jsonl_index

def load_session(session_prefix: str) -> dict | None:
    """Charge une session depuis session-meta + jsonl en cherchant par préfixe d'ID."""
    matches = list(SESSION_META_DIR.glob(f"{session_prefix}*.json"))
    if not matches:
        return None
    meta_path = matches[0]
    session_id = meta_path.stem

    idx = _get_jsonl_index()
    jsonl_path = idx.get(session_id)
    if not jsonl_path:
        return None

    messages = []
    for line in jsonl_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") not in ("user", "assistant"):
            continue
        if entry.get("isMeta"):
            continue
        messages.append(entry)

    return {"session_id": session_id, "messages": messages}

# ---------------------------------------------------------------------------
# Appel LLM direct (contourne generate() pour contrôler le modèle sans env var)
# ---------------------------------------------------------------------------
def call_ollama(model: str, prompt: str, timeout: int) -> tuple[str, float]:
    """Appelle Ollama directement. Retourne (réponse brute, durée en secondes)."""
    t0 = time.time()
    r = httpx.post(
        f"{Config.OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    elapsed = time.time() - t0
    return r.json()["response"], elapsed

def build_prompt(conv: dict) -> str:
    lines = [_extract_text(m) for m in conv["messages"]]
    messages_text = "\n".join(l for l in lines if l)
    return FACET_PROMPT.format(messages=_truncate(messages_text, Config.MAX_CONV_CHARS))

# ---------------------------------------------------------------------------
# Évaluation d'une réponse brute
# ---------------------------------------------------------------------------
def evaluate(raw: str, elapsed: float, reference_outcome: str | None) -> dict:
    result = {
        "raw_preview": raw[:120].replace("\n", " "),
        "elapsed": round(elapsed, 1),
        "json_valid": False,
        "fields_ok": False,
        "outcome": None,
        "outcome_match": None,   # True/False/None (None = pas de référence)
    }
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            return result
        data = json.loads(raw[start:end])
        result["json_valid"] = True

        missing = REQUIRED_FIELDS - data.keys()
        result["fields_ok"] = len(missing) == 0
        result["missing_fields"] = sorted(missing)

        outcome = data.get("outcome")
        result["outcome"] = outcome
        if reference_outcome is not None:
            result["outcome_match"] = (outcome == reference_outcome)
    except (json.JSONDecodeError, KeyError):
        pass
    return result

# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------
def run_phase1() -> list[str]:
    print("\n" + "=" * 70)
    print("PHASE 1 — ÉLIMINATION RAPIDE")
    print(f"Session : {PHASE1_SESSION} — {TEST_SESSIONS[PHASE1_SESSION]['desc']}")
    print(f"Référence Anthropic : {TEST_SESSIONS[PHASE1_SESSION]['anthropic_outcome']}")
    print("=" * 70)

    conv = load_session(PHASE1_SESSION)
    if not conv:
        print(f"ERREUR : session {PHASE1_SESSION} introuvable")
        sys.exit(1)

    prompt = build_prompt(conv)
    ref_outcome = TEST_SESSIONS[PHASE1_SESSION]["anthropic_outcome"]

    survivors = []
    results = []

    for model in MODELS:
        print(f"\n  [{model}]", end=" ", flush=True)
        try:
            raw, elapsed = call_ollama(model, prompt, PHASE1_TIMEOUT)
            ev = evaluate(raw, elapsed, ref_outcome)
            status = "✅" if ev["fields_ok"] else "❌"
            outcome_info = ev["outcome"] or "—"
            match_info = ""
            if ev["outcome_match"] is True:
                match_info = " ✓ accord Anthropic"
            elif ev["outcome_match"] is False:
                match_info = f" ✗ (Anthropic={ref_outcome})"
            print(f"{status} {elapsed:.0f}s | outcome={outcome_info}{match_info}")
            if not ev["fields_ok"] and ev.get("missing_fields"):
                print(f"    champs manquants : {ev['missing_fields']}")
            results.append({"model": model, **ev})
            if ev["fields_ok"]:
                survivors.append(model)
        except httpx.TimeoutException:
            print(f"❌ TIMEOUT ({PHASE1_TIMEOUT}s)")
            results.append({"model": model, "timeout": True})
        except httpx.ConnectError:
            print("❌ Ollama inaccessible")
            sys.exit(1)
        except Exception as e:
            print(f"❌ ERREUR : {e}")
            results.append({"model": model, "error": str(e)})

    print("\n" + "-" * 70)
    print(f"Survivants Phase 1 : {len(survivors)}/{len(MODELS)}")
    for m in survivors:
        print(f"  ✅ {m}")

    # Sauvegarde résultats
    out = Path("docs/results-phase1.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nRésultats sauvegardés : {out}")
    return survivors

# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------
def run_phase2(models: list[str]):
    print("\n" + "=" * 70)
    print("PHASE 2 — BATTERIE COMPLÈTE")
    print(f"Modèles : {len(models)} | Sessions : {len(TEST_SESSIONS)} | Runs : 2")
    print("=" * 70)

    # Chargement de toutes les sessions
    sessions = {}
    for sid, info in TEST_SESSIONS.items():
        conv = load_session(sid)
        if not conv:
            print(f"  AVERTISSEMENT : session {sid} introuvable — ignorée")
        else:
            sessions[sid] = conv
            print(f"  ✓ {sid} — {info['desc']} ({len(conv['messages'])} msgs)")

    all_results = {}

    for model in models:
        print(f"\n{'─' * 70}")
        print(f"  {model}")
        print(f"{'─' * 70}")
        model_results = {}

        for sid, conv in sessions.items():
            ref_outcome = TEST_SESSIONS[sid]["anthropic_outcome"]
            prompt = build_prompt(conv)
            runs = []

            for run_n in range(1, 3):
                print(f"  [{sid[:8]}] run {run_n}/2 ...", end=" ", flush=True)
                try:
                    raw, elapsed = call_ollama(model, prompt, PHASE2_TIMEOUT)
                    ev = evaluate(raw, elapsed, ref_outcome)
                    status = "✅" if ev["fields_ok"] else "❌"
                    outcome_info = ev["outcome"] or "—"
                    match_info = " ✓" if ev["outcome_match"] is True else (" ✗" if ev["outcome_match"] is False else "")
                    print(f"{status} {elapsed:.0f}s outcome={outcome_info}{match_info}")
                    runs.append(ev)
                except httpx.TimeoutException:
                    print(f"❌ TIMEOUT")
                    runs.append({"timeout": True, "elapsed": PHASE2_TIMEOUT})
                except Exception as e:
                    print(f"❌ {e}")
                    runs.append({"error": str(e)})

            # Stabilité : est-ce que les deux runs donnent le même outcome ?
            outcomes = [r.get("outcome") for r in runs if r.get("outcome")]
            stable = len(set(outcomes)) == 1 if len(outcomes) == 2 else None
            model_results[sid] = {"runs": runs, "stable": stable}

        all_results[model] = model_results

    # Sauvegarde résultats bruts
    out = Path("docs/results-phase2.json")
    out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    print(f"\n\nRésultats bruts sauvegardés : {out}")

    # Tableau récapitulatif
    _print_summary(all_results, sessions)

def _print_summary(all_results: dict, sessions: dict):
    print("\n" + "=" * 70)
    print("RÉCAPITULATIF PHASE 2")
    print("=" * 70)

    ref_sessions = [sid for sid, info in TEST_SESSIONS.items() if info["anthropic_outcome"] and sid in sessions]

    for model, model_results in all_results.items():
        valid_runs = 0
        total_runs = 0
        outcome_matches = 0
        total_ref = 0
        speeds = []
        stable_count = 0
        session_count = 0

        for sid, sdata in model_results.items():
            for run in sdata["runs"]:
                total_runs += 1
                if run.get("fields_ok"):
                    valid_runs += 1
                if run.get("elapsed") and not run.get("timeout"):
                    speeds.append(run["elapsed"])
                if sid in ref_sessions:
                    total_ref += 1
                    if run.get("outcome_match") is True:
                        outcome_matches += 1
            if sdata.get("stable") is True:
                stable_count += 1
            session_count += 1

        avg_speed = f"{sum(speeds)/len(speeds):.0f}s" if speeds else "—"
        accord = f"{outcome_matches}/{total_ref}" if total_ref else "—"
        stability = f"{stable_count}/{session_count}"

        print(f"\n  {model}")
        print(f"    JSON valide : {valid_runs}/{total_runs} runs")
        print(f"    Accord Anthropic (outcome) : {accord}")
        print(f"    Stabilité (outcome identique run1=run2) : {stability}")
        print(f"    Vitesse moyenne : {avg_speed}")

# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Benchmark modèles Ollama pour retrospect")
    parser.add_argument("--phase", type=int, choices=[1, 2], nargs="+",
                        help="Phase(s) à exécuter (défaut : 1 puis 2)")
    parser.add_argument("--models", nargs="+",
                        help="Forcer une liste de modèles pour la Phase 2 (contourne Phase 1)")
    args = parser.parse_args()

    phases = args.phase or [1, 2]

    survivors = args.models or MODELS  # par défaut tous si on saute la Phase 1

    if 1 in phases:
        survivors = run_phase1()
        if not survivors:
            print("\nAucun survivant — arrêt.")
            sys.exit(1)

    if 2 in phases:
        run_phase2(survivors)

if __name__ == "__main__":
    main()
