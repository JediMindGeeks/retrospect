import pytest
from pathlib import Path
import json

@pytest.fixture
def sample_claude_dir(tmp_path):
    """Crée un répertoire Claude Code factice avec session-meta/ et .jsonl"""
    (tmp_path / "session-meta").mkdir()
    meta = {
        "session_id": "abc123",
        "project_path": "/home/user/project",
        "start_time": "2026-03-01T10:00:00Z",
        "duration_minutes": 30,
        "input_tokens": 5000,
        "output_tokens": 1200
    }
    (tmp_path / "session-meta" / "abc123.json").write_text(json.dumps(meta))
    messages = [
        {"type": "user", "uuid": "u1", "parentUuid": None, "sessionId": "abc123",
         "timestamp": "2026-03-01T10:00:01Z", "isMeta": False,
         "message": {"role": "user", "content": "Comment déboguer ce script Python ?"}},
        {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "sessionId": "abc123",
         "timestamp": "2026-03-01T10:00:05Z",
         "message": {"role": "assistant", "content": "Voici comment déboguer..."}},
        {"type": "user", "uuid": "u2", "parentUuid": "a1", "sessionId": "abc123",
         "timestamp": "2026-03-01T10:01:00Z", "isMeta": False,
         "message": {"role": "user", "content": "Merci, ça marche !"}},
    ]
    with (tmp_path / "abc123.jsonl").open("w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")
    return tmp_path

@pytest.fixture
def sample_chatgpt_file(tmp_path):
    """Crée un fichier conversations.json ChatGPT factice"""
    data = [{
        "id": "conv-xyz",
        "title": "Comment faire une API REST",
        "create_time": 1740000000,
        "mapping": {
            "node1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["Comment créer une API REST en Python ?"]},
                    "create_time": 1740000001
                },
                "parent": None, "children": ["node2"]
            },
            "node2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": ["Voici comment créer une API REST..."]},
                    "create_time": 1740000005
                },
                "parent": "node1", "children": ["node3"]
            },
            "node3": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["Et avec FastAPI ?"]},
                    "create_time": 1740000060
                },
                "parent": "node2", "children": []
            }
        }
    }]
    f = tmp_path / "conversations.json"
    f.write_text(json.dumps(data))
    return f
