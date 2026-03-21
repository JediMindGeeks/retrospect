import json
from pathlib import Path
from config import Config

def detect(path: Path) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text())
        return isinstance(data, list) and len(data) > 0 and "mapping" in data[0]
    except (json.JSONDecodeError, KeyError, IndexError):
        return False

def parse(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    conversations = []
    for conv in data:
        messages = _extract_messages(conv.get("mapping", {}))
        if len(messages) < Config.MIN_MESSAGES:
            continue
        conversations.append({
            "conversation_id": conv["id"],
            "title": conv.get("title", ""),
            "messages": messages,
        })
    return conversations

def _extract_messages(mapping: dict) -> list[dict]:
    messages = []
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        role = msg.get("author", {}).get("role")
        if role not in ("user", "assistant"):
            continue
        parts = msg.get("content", {}).get("parts", [])
        content = " ".join(str(p) for p in parts if p)
        if not content.strip():
            continue
        messages.append({
            "role": role,
            "content": content,
            "timestamp": msg.get("create_time", 0),
        })
    return sorted(messages, key=lambda m: m["timestamp"])
