import json
from pathlib import Path
from config import Config
from llm import generate

REQUIRED_FIELDS = {"underlying_goal", "outcome", "brief_summary"}

FACET_PROMPT = """Analyse cette conversation et retourne un objet JSON avec exactement ces champs :
- underlying_goal (string): l'objectif réel de l'utilisateur
- outcome (string): "achieved", "mostly_achieved", ou "not_achieved"
- key_points (array): 2-5 points clés de la conversation
- friction (string): principale difficulté rencontrée, ou "" si aucune
- brief_summary (string): résumé en 1-2 phrases

Conversation :
{messages}

Réponds UNIQUEMENT avec le JSON, sans texte autour."""

def is_valid_facet(facet: dict) -> bool:
    return REQUIRED_FIELDS.issubset(facet.keys())

def _cache_path(source: str, conv_id: str, base_dir: Path) -> Path:
    return Path(base_dir) / f"{source}-{conv_id}.json"

def load_cached(source: str, conv_id: str, base_dir: Path = None) -> dict | None:
    base_dir = base_dir or Config.FACETS_DIR
    path = _cache_path(source, conv_id, base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if is_valid_facet(data) else None
    except (json.JSONDecodeError, KeyError):
        return None

def save_facet(facet: dict, base_dir: Path = None):
    base_dir = Path(base_dir or Config.FACETS_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(facet["source"], facet["conversation_id"], base_dir)
    path.write_text(json.dumps(facet, ensure_ascii=False, indent=2))

def generate_facet(conv: dict, source: str) -> dict:
    conv_id = conv.get("session_id") or conv.get("conversation_id")
    messages_text = "\n".join(
        f"[{m['message']['role'] if 'message' in m else m['role']}]: "
        f"{m['message']['content'] if 'message' in m else m['content']}"
        for m in conv["messages"]
    )
    prompt = FACET_PROMPT.format(messages=messages_text[:8000])
    raw = generate(prompt)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["conversation_id"] = conv_id
    data["source"] = source
    return data
