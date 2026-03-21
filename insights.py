#!/usr/bin/env python3
"""
insights.py — Génère un rapport d'insights sur des conversations Claude Code ou ChatGPT.

Usage:
    python insights.py <chemin>
    INSIGHTS_LLM=claude python insights.py <chemin>
"""
import sys
from pathlib import Path
from datetime import date

import parsers.claude_code as cc_parser
import parsers.chatgpt as gpt_parser
from facets import generate_facet, load_cached, save_facet
from report import generate_report, save_report
from llm import generate, LLMUnavailableError
from config import Config

PARSERS = {
    "claude_code": cc_parser,
    "chatgpt": gpt_parser,
}

def detect_format(path: Path) -> str:
    path = Path(path)
    for name, parser in PARSERS.items():
        if parser.detect(path):
            return name
    raise ValueError(
        f"Format non supporté : {path}\n"
        f"Formats acceptés : {', '.join(PARSERS.keys())}"
    )

def run(path: Path, facets_dir: Path = None, reports_dir: Path = None) -> str:
    path = Path(path)
    facets_dir = facets_dir or Config.FACETS_DIR
    reports_dir = reports_dir or Config.REPORTS_DIR
    source = detect_format(path)
    parser = PARSERS[source]
    conversations = parser.parse(path)
    print(f"[insights] {len(conversations)} conversations trouvées ({source})")
    facets = []
    for i, conv in enumerate(conversations, 1):
        conv_id = conv.get("session_id") or conv.get("conversation_id")
        cached = load_cached(source, conv_id, base_dir=facets_dir)
        if cached:
            print(f"  [{i}/{len(conversations)}] {conv_id[:8]}… (cache)")
            facets.append(cached)
            continue
        print(f"  [{i}/{len(conversations)}] {conv_id[:8]}… (LLM)")
        facet = generate_facet(conv, source=source)
        save_facet(facet, base_dir=facets_dir)
        facets.append(facet)
    today = str(date.today())
    report = generate_report(facets, date=today)
    save_report(report, date=today, reports_dir=reports_dir)
    return report

def main():
    if len(sys.argv) < 2:
        print("Usage: python insights.py <chemin>")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Erreur : chemin introuvable : {path}")
        sys.exit(1)
    Config.ensure_dirs()
    try:
        report = run(path)
        print("\n" + "=" * 60)
        print(report)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)
    except LLMUnavailableError as e:
        print(f"Erreur LLM : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
