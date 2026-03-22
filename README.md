# insights

A portable Python CLI that reproduces the Claude Code `/insights` pipeline — analyzes conversation logs, generates structured "facets" per conversation via LLM, and aggregates them into a markdown narrative report.

Works with **Claude Code** session logs and **ChatGPT** exports.

## What it does

1. **Parses** conversation logs (Claude Code JSONL or ChatGPT JSON export)
2. **Generates facets** — structured JSON summaries per conversation (goal, outcome, key points, friction) via LLM
3. **Caches** facets locally so reruns are instant
4. **Aggregates** into a markdown report with statistics and narrative

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) running locally **or** an Anthropic API key

## Installation

```bash
git clone https://github.com/<you>/insights
cd insights
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Analyze Claude Code sessions from ~/.claude/usage-data/session-meta/
python insights.py ~/.claude/usage-data/session-meta/

# Analyze a ChatGPT export
python insights.py ~/Downloads/conversations.json

# Use Claude instead of Ollama
INSIGHTS_LLM=claude python insights.py ~/.claude/usage-data/session-meta/
```

## Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `INSIGHTS_LLM` | `ollama` | Backend: `ollama` or `claude` |
| `INSIGHTS_MODEL` | `mistral-small3.1:24b` | Ollama model to use |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `INSIGHTS_MAX_CHARS` | `32000` | Max chars per conversation sent to LLM (uses head + tail) |
| `INSIGHTS_TIMEOUT` | `300` | LLM request timeout in seconds |

Output directories default to `~/notes/insights/facets/` and `~/notes/insights/reports/`.

## Comparing with Anthropic's native facets

```bash
# After running the pipeline on Claude Code sessions:
python compare.py --detail
```

This compares your generated facets against Anthropic's own `/insights` facets (stored in `~/.claude/usage-data/facets/`) — useful for evaluating pipeline quality.

## Project layout

```
insights.py          # CLI entry point + orchestration
config.py            # Configuration (env vars + paths)
llm.py               # LLM backends (Ollama / Claude)
facets.py            # Facet generation, validation, caching
report.py            # Report aggregation
compare.py           # Compare our facets vs Anthropic's
parsers/
  claude_code.py     # Claude Code session-meta parser
  chatgpt.py         # ChatGPT export parser
```

## Running tests

```bash
pytest
```

## Facet schema

Each facet is a JSON file with these fields:

```json
{
  "underlying_goal": "What the user was actually trying to do",
  "outcome": "achieved | mostly_achieved | not_achieved | unclear_from_transcript",
  "key_points": ["Point 1", "Point 2"],
  "friction": "Main difficulty encountered, or empty string",
  "brief_summary": "1-2 sentence factual summary",
  "conversation_id": "session-id",
  "source": "claude_code | chatgpt"
}
```
