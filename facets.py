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
    """Return True if facet contains all required fields, False otherwise."""
    return REQUIRED_FIELDS.issubset(facet.keys())

def _cache_path(source: str, conv_id: str, base_dir: Path) -> Path:
    return Path(base_dir) / f"{source}-{conv_id}.json"

def _extract_text(m: dict) -> str:
    """Extract message text from a conversation message dict.

    Handles both nested format (``m['message']['content']``) and flat format
    (``m['content']``).  Returns an empty string if neither format is found.
    """
    if "message" in m:
        msg = m["message"]
        role = msg.get("role", "")
        content = msg.get("content", "")
    elif "role" in m and "content" in m:
        role = m.get("role", "")
        content = m.get("content", "")
    else:
        return ""
    return f"[{role}]: {content}"

def load_cached(source: str, conv_id: str, base_dir: Path = None) -> dict | None:
    """Load a cached facet for the given source and conversation ID.

    Returns the facet dict if it exists and is valid, otherwise None.
    """
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
    """Persist a facet dict to the cache directory as a JSON file.

    Raises ValueError if ``facet`` is missing ``source`` or ``conversation_id``.
    """
    if "source" not in facet or "conversation_id" not in facet:
        raise ValueError(
            "facet must contain 'source' and 'conversation_id' keys, "
            f"got: {list(facet.keys())}"
        )
    base_dir = Path(base_dir or Config.FACETS_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(facet["source"], facet["conversation_id"], base_dir)
    path.write_text(json.dumps(facet, ensure_ascii=False, indent=2))

def generate_facet(conv: dict, source: str) -> dict:
    """Generate a facet for a conversation by calling the LLM.

    Parses the JSON response from the LLM, validates required fields, and
    returns the facet dict augmented with ``conversation_id`` and ``source``.

    Raises ValueError on LLM failure, invalid JSON, or missing required fields.
    """
    conv_id = conv.get("session_id") or conv.get("conversation_id")
    lines = [_extract_text(m) for m in conv["messages"]]
    messages_text = "\n".join(line for line in lines if line)
    prompt = FACET_PROMPT.format(messages=messages_text[:8000])

    try:
        raw = generate(prompt)
    except Exception as exc:
        raise ValueError(f"LLM call failed: {exc}") from exc

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            raise json.JSONDecodeError(
                "No JSON object found in LLM response", raw, 0
            )
        data = json.loads(raw[start:end])
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse JSON from LLM response: {exc}\nRaw response: {raw!r}"
        ) from exc

    if not is_valid_facet(data):
        missing = REQUIRED_FIELDS - data.keys()
        raise ValueError(
            f"LLM response is missing required fields: {missing}\nRaw response: {raw!r}"
        )

    data["conversation_id"] = conv_id
    data["source"] = source
    return data
