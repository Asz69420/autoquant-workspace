#!/usr/bin/env python3
"""Convert ActionEvent JSON to Telegram message (triple backticks)."""
import json
import sys

# Force UTF-8 output on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def to_model_label(model_id: str) -> str:
    """Return short human-friendly model label for Telegram logs."""
    known = {
        "openai-codex/gpt-5.3-codex": "codex 5.3",
        "opencode/claude-opus-4-6": "opus 4.6",
        "anthropic/claude-sonnet-4-6": "sonnet 4.6",
        "anthropic/claude-haiku-4-5-20251001": "haiku 4.5",
    }
    if model_id in known:
        return known[model_id]

    if model_id in {"system", "build1-mock"}:
        return model_id

    # Fallback: shorten to last path segment and clean separators
    short = model_id.split("/")[-1]
    short = short.replace("gpt-", "").replace("claude-", "")
    short = short.replace("-", " ").strip()
    return short if short else model_id


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("event_path", nargs="?", default=None, help="Path to event.json file")
    args = parser.parse_args()
    
    # Read event from file or stdin
    try:
        if args.event_path:
            with open(args.event_path) as f:
                event = json.load(f)
        else:
            # Read from stdin
            raw = sys.stdin.read()
            event = json.loads(raw)
        
        # Extract fields
        agent = event["agent"]
        model_id = event["model_id"]
        model_label = to_model_label(model_id)
        status_emoji = event["status_emoji"]
        status_word = event["status_word"]
        reason_code = event.get("reason_code")
        summary = event["summary"]
        run_id = event["run_id"]
        
        # Header: status_emoji STATUS_WORD | Agent | model_id (reason_code if present)
        # Omit parentheses if reason_code is null/missing
        if reason_code:
            header = f"{status_emoji} {status_word} | {agent} | {model_label} ({reason_code})"
        else:
            header = f"{status_emoji} {status_word} | {agent} | {model_label}"
        
        # Body: summary (max 50 chars, truncate if needed) + run_id
        summary_truncated = (summary[:47] + "...") if len(summary) > 50 else summary
        
        lines = [header, summary_truncated, f"Run: {run_id}"]
        
        # Wrap in backticks
        body = "\n".join(lines)
        telegram_msg = f"```\n{body}\n```"
        
        print(telegram_msg)
        sys.exit(0)
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
