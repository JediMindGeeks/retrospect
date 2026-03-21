import json
from pathlib import Path
from config import Config

# Répertoire de fallback pour chercher les fichiers .jsonl (structure réelle de Claude Code)
_CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
_JSONL_INDEX: dict[str, Path] | None = None


def _build_jsonl_index() -> dict[str, Path]:
    """Construit un index session_id → chemin .jsonl en parcourant ~/.claude/projects/."""
    index: dict[str, Path] = {}
    if not _CLAUDE_PROJECTS_DIR.exists():
        return index
    for f in _CLAUDE_PROJECTS_DIR.glob("*/*.jsonl"):
        index[f.stem] = f
    return index


def _find_jsonl(session_id: str, local_dir: Path) -> Path | None:
    """Cherche le .jsonl co-localisé d'abord, puis dans ~/.claude/projects/ en fallback."""
    local = local_dir / f"{session_id}.jsonl"
    if local.exists():
        return local
    global _JSONL_INDEX
    if _JSONL_INDEX is None:
        _JSONL_INDEX = _build_jsonl_index()
    return _JSONL_INDEX.get(session_id)


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
        jsonl_file = _find_jsonl(session_id, p)
        if not jsonl_file:
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
