import pytest
from parsers.claude_code import parse as parse_claude, detect as detect_claude
from parsers.chatgpt import parse as parse_chatgpt, detect as detect_chatgpt

class TestClaudeCodeDetection:
    def test_detects_valid_claude_dir(self, sample_claude_dir):
        assert detect_claude(sample_claude_dir) is True

    def test_rejects_empty_dir(self, tmp_path):
        assert detect_claude(tmp_path) is False

    def test_rejects_chatgpt_file(self, sample_chatgpt_file):
        assert detect_claude(sample_chatgpt_file) is False

class TestClaudeCodeParser:
    def test_returns_list_of_conversations(self, sample_claude_dir):
        convs = parse_claude(sample_claude_dir)
        assert isinstance(convs, list)
        assert len(convs) == 1

    def test_conversation_has_required_fields(self, sample_claude_dir):
        conv = parse_claude(sample_claude_dir)[0]
        assert "session_id" in conv
        assert "messages" in conv
        assert "meta" in conv

    def test_messages_filtered_no_meta(self, sample_claude_dir):
        conv = parse_claude(sample_claude_dir)[0]
        for msg in conv["messages"]:
            assert msg.get("isMeta") is not True

    def test_skips_short_conversations(self, tmp_path):
        import json
        (tmp_path / "session-meta").mkdir()
        (tmp_path / "session-meta" / "short.json").write_text(
            json.dumps({"session_id": "short", "project_path": "/", "start_time": "2026-01-01T00:00:00Z"})
        )
        msgs = [
            {"type": "user", "uuid": "u1", "sessionId": "short",
             "timestamp": "2026-01-01T00:00:01Z", "isMeta": False,
             "message": {"role": "user", "content": "hello"}},
        ]
        with (tmp_path / "short.jsonl").open("w") as f:
            for m in msgs:
                f.write(json.dumps(m) + "\n")
        convs = parse_claude(tmp_path)
        assert len(convs) == 0

class TestChatGPTDetection:
    def test_detects_valid_chatgpt_file(self, sample_chatgpt_file):
        assert detect_chatgpt(sample_chatgpt_file) is True

    def test_rejects_claude_dir(self, sample_claude_dir):
        assert detect_chatgpt(sample_claude_dir) is False

    def test_rejects_non_chatgpt_json(self, tmp_path):
        f = tmp_path / "other.json"
        f.write_text('{"key": "value"}')
        assert detect_chatgpt(f) is False

class TestChatGPTParser:
    def test_returns_list_of_conversations(self, sample_chatgpt_file):
        convs = parse_chatgpt(sample_chatgpt_file)
        assert len(convs) == 1

    def test_conversation_has_required_fields(self, sample_chatgpt_file):
        conv = parse_chatgpt(sample_chatgpt_file)[0]
        assert "conversation_id" in conv
        assert "messages" in conv
        assert "title" in conv

    def test_messages_exclude_system_role(self, sample_chatgpt_file):
        conv = parse_chatgpt(sample_chatgpt_file)[0]
        roles = [m["role"] for m in conv["messages"]]
        assert "system" not in roles

    def test_messages_sorted_by_create_time(self, sample_chatgpt_file):
        conv = parse_chatgpt(sample_chatgpt_file)[0]
        times = [m["timestamp"] for m in conv["messages"]]
        assert times == sorted(times)
