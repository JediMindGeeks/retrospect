import json
from pathlib import Path
from config import Config

def detect(path: Path) -> bool:
    p = Path(path)
    return p.is_dir() and (p / "session-meta").is_dir() and any((p / "session-meta").glob("*.json"))

def parse(path: Path) -> list[dict]:
    p = Path(path)
    conversations = []
    for meta_file in (p / "session-meta").glob("*.json"):
        session_id = meta_file.stem
        try:
            meta = json.loads(meta_file.read_text())
        except json.JSONDecodeError:
            continue
        jsonl_file = p / f"{session_id}.jsonl"
        if not jsonl_file.exists():
            continue
        messages = _parse_jsonl(jsonl_file)
        if len(messages) < Config.MIN_MESSAGES:
            continue
        conversations.append({
            "session_id": session_id,
            "messages": messages,
            "meta": meta,
        })
    return conversations

def _parse_jsonl(path: Path) -> list[dict]:
    messages = []
    for line in path.read_text().splitlines():
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
    return messages
