#!/usr/bin/env python3
"""
compare.py — Compare nos facets vs ceux d'Anthropic sur les mêmes sessions.

Usage:
    python compare.py
    python compare.py --limit 10    # comparer seulement 10 sessions
    python compare.py --detail      # afficher les comparaisons textuelles complètes
"""
import json
import sys
import argparse
from pathlib import Path

ANTHROPIC_FACETS_DIR = Path.home() / ".claude" / "usage-data" / "facets"
OUR_FACETS_DIR = Path.home() / "notes" / "insights" / "facets"

# Champs communs (présents des deux côtés)
COMMON_FIELDS = {"underlying_goal", "outcome", "brief_summary"}

# Normalisation des outcomes : Anthropic utilise des synonymes (fully_achieved, partially_achieved)
OUTCOME_MAP = {
    "achieved":                "achieved",
    "fully_achieved":          "achieved",           # synonyme Anthropic
    "mostly_achieved":         "mostly_achieved",
    "partially_achieved":      "mostly_achieved",    # synonyme Anthropic
    "not_achieved":            "not_achieved",
    "unclear_from_transcript": "unclear_from_transcript",
}


def load_anthropic_facets() -> dict[str, dict]:
    facets = {}
    for f in ANTHROPIC_FACETS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            sid = data.get("session_id", f.stem)
            facets[sid] = data
        except json.JSONDecodeError:
            continue
    return facets


def load_our_facets() -> dict[str, dict]:
    """Charge nos facets (préfixés claude_code-<session_id>.json)."""
    facets = {}
    if not OUR_FACETS_DIR.exists():
        return facets
    for f in OUR_FACETS_DIR.glob("claude_code-*.json"):
        try:
            data = json.loads(f.read_text())
            sid = data.get("conversation_id", f.stem.removeprefix("claude_code-"))
            facets[sid] = data
        except json.JSONDecodeError:
            continue
    return facets


def outcome_normalized(outcome: str) -> str:
    return OUTCOME_MAP.get(outcome, outcome)


def compare(limit: int = None, detail: bool = False):
    anthropic = load_anthropic_facets()
    ours = load_our_facets()

    print(f"\n{'='*60}")
    print("COUVERTURE")
    print(f"{'='*60}")
    print(f"  Anthropic : {len(anthropic)} facets")
    print(f"  Nous      : {len(ours)} facets")

    common_ids = set(anthropic.keys()) & set(ours.keys())
    only_anthropic = set(anthropic.keys()) - set(ours.keys())
    only_ours = set(ours.keys()) - set(anthropic.keys())

    print(f"  En commun : {len(common_ids)}")
    print(f"  Seulement Anthropic : {len(only_anthropic)}")
    print(f"  Seulement nous : {len(only_ours)}")

    if not common_ids:
        print("\n⚠️  Aucune session en commun. Lance d'abord :")
        print("  python insights.py ~/.claude/usage-data/")
        return

    sample = sorted(common_ids)
    if limit:
        sample = sample[:limit]

    # --- Outcome agreement ---
    print(f"\n{'='*60}")
    print(f"ACCORD SUR OUTCOME ({len(sample)} sessions)")
    print(f"{'='*60}")

    agreements = 0
    disagreements = []
    for sid in sample:
        a_outcome = outcome_normalized(anthropic[sid].get("outcome", ""))
        o_outcome = outcome_normalized(ours[sid].get("outcome", ""))
        if a_outcome == o_outcome:
            agreements += 1
        else:
            disagreements.append((sid, a_outcome, o_outcome))

    pct = agreements / len(sample) * 100
    print(f"  Accord : {agreements}/{len(sample)} ({pct:.0f}%)")
    if disagreements:
        print(f"  Désaccords :")
        for sid, a, o in disagreements[:5]:
            print(f"    {sid[:8]}…  Anthropic={a}  Nous={o}")

    # --- Schema delta ---
    print(f"\n{'='*60}")
    print("CHAMPS ANTHROPIC ABSENTS CHEZ NOUS")
    print(f"{'='*60}")
    sample_anthropic = anthropic[list(common_ids)[0]]
    sample_ours = ours[list(common_ids)[0]]
    extra_anthropic = set(sample_anthropic.keys()) - set(sample_ours.keys()) - {"session_id"}
    extra_ours = set(sample_ours.keys()) - set(sample_anthropic.keys()) - {"conversation_id", "source"}
    for field in sorted(extra_anthropic):
        val = sample_anthropic[field]
        print(f"  + {field}: {json.dumps(val)[:80]}")
    if extra_ours:
        print(f"\nCHAMPS QU'ON A ET PAS EUX :")
        for field in sorted(extra_ours):
            val = sample_ours[field]
            print(f"  + {field}: {json.dumps(val)[:80]}")

    # --- Comparaison textuelle ---
    if detail:
        print(f"\n{'='*60}")
        print(f"COMPARAISON SESSION PAR SESSION ({len(sample)} sessions)")
        print(f"{'='*60}")
        for sid in sample:
            a = anthropic[sid]
            o = ours[sid]
            print(f"\n── {sid[:16]}… ──")
            print(f"  underlying_goal")
            def s(v, n=100): return str(v or "")[:n]
            print(f"    ANTHROPIC : {s(a.get('underlying_goal'), 100)}")
            print(f"    NOUS      : {s(o.get('underlying_goal'), 100)}")
            print(f"  outcome     : {a.get('outcome')} → {o.get('outcome')}")
            print(f"  brief_summary")
            print(f"    ANTHROPIC : {s(a.get('brief_summary'), 120)}")
            print(f"    NOUS      : {s(o.get('brief_summary'), 120)}")
            a_friction = a.get("friction_detail") or a.get("friction", "")
            o_friction = o.get("friction", "")
            if a_friction or o_friction:
                print(f"  friction")
                print(f"    ANTHROPIC : {s(a_friction, 100)}")
                print(f"    NOUS      : {s(o_friction, 100)}")
    else:
        print(f"\n(Relance avec --detail pour la comparaison session par session)")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare nos facets vs Anthropic")
    parser.add_argument("--limit", type=int, default=None, help="Nombre de sessions à comparer")
    parser.add_argument("--detail", action="store_true", help="Afficher les comparaisons textuelles")
    args = parser.parse_args()
    compare(limit=args.limit, detail=args.detail)
