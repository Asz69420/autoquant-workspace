#!/usr/bin/env python3
"""
Telegram ↔ Claude Code bridge bot for the AutoQuant Noodle group.

Commands:
  /cli <query>   — read-only Claude query (no writes, no bash)
  /write <query>  — Claude query with Write tool (docs/claude-reports/ + artifacts/claude-specs/ only)
  /run <task>     — trigger a task script from scripts/claude-tasks/
  /status         — quick pipeline health check
  /stop           — gracefully shut down the bot

Security:
  - Only responds to the authorized user (CLAUDE_BRIDGE_USER_ID)
  - Only in the allowed group (CLAUDE_BRIDGE_GROUP_ID) or direct messages
  - Blocks dangerous shell patterns before forwarding to Claude
  - Logs every command to data/logs/claude-bridge/ as NDJSON
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

BOT_TOKEN: str = os.environ["CLAUDE_BRIDGE_BOT_TOKEN"]
USER_ID: int = int(os.environ["CLAUDE_BRIDGE_USER_ID"])
GROUP_ID: int = int(os.environ["CLAUDE_BRIDGE_GROUP_ID"])
WORKSPACE: Path = Path(os.environ["CLAUDE_BRIDGE_WORKSPACE"])

TELEGRAM_MAX_LEN = 4000
AEST = timedelta(hours=10)

LOG_DIR = WORKSPACE / "data" / "logs" / "claude-bridge"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TASK_DIR = WORKSPACE / "scripts" / "claude-tasks"

ALLOWED_WRITE_PATHS = [
    "docs/shared/",
]

# Patterns that must never appear in any user-supplied query
DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"rm\s+-rf", re.IGNORECASE),
    re.compile(r"rm\s+-r\s", re.IGNORECASE),
    re.compile(r"rmdir\s+/s", re.IGNORECASE),
    re.compile(r"del\s+/[sfq]", re.IGNORECASE),
    re.compile(r"format\s+[a-z]:", re.IGNORECASE),
    re.compile(r"(BOT_TOKEN|API_KEY|SECRET|PASSWORD|CREDENTIAL|AUTH_TOKEN)", re.IGNORECASE),
    re.compile(r"openclaw\.json", re.IGNORECASE),
    re.compile(r"\\\.openclaw[/\\]", re.IGNORECASE),
    re.compile(r"--no-verify", re.IGNORECASE),
    re.compile(r"git\s+push", re.IGNORECASE),
    re.compile(r"pip\s+install", re.IGNORECASE),
    re.compile(r"curl\s.*\|.*sh", re.IGNORECASE),
    re.compile(r"powershell\s.*-enc", re.IGNORECASE),
    re.compile(r"Invoke-WebRequest", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
]

# Map friendly names → script filenames
KNOWN_TASKS: dict[str, str] = {
    "researcher":  "run-strategy-researcher.ps1",
    "generator":   "run-strategy-generator.ps1",
    "doctrine":    "run-doctrine-synthesizer.ps1",
    "auditor":     "run-backtest-auditor.ps1",
    "firewall":    "run-firewall-audit.ps1",
}

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("claude-bridge")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def truncate(text: str, limit: int = TELEGRAM_MAX_LEN) -> str:
    """Truncate text to fit Telegram's message size limit."""
    if len(text) <= limit:
        return text
    return text[: limit - 30] + "\n\n… [truncated]"


def is_dangerous(text: str) -> str | None:
    """Return the matched pattern description if dangerous, else None."""
    for pat in DANGEROUS_PATTERNS:
        if pat.search(text):
            return pat.pattern
    return None


def now_aest() -> str:
    """Return current time as an AEST string."""
    utc = datetime.now(timezone.utc)
    aest = utc + AEST
    return aest.strftime("%Y-%m-%d %H:%M:%S AEST")


def log_command(user_id: int, command: str, query: str, result: str, ok: bool) -> None:
    """Append an NDJSON log line for every command."""
    ts = datetime.now(timezone.utc).isoformat() + "Z"
    entry = {
        "ts": ts,
        "user_id": user_id,
        "command": command,
        "query": query[:500],
        "result_preview": result[:300],
        "ok": ok,
    }
    log_file = LOG_DIR / f"bridge_{datetime.now(timezone.utc).strftime('%Y%m%d')}.ndjson"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def authorized(update: Update) -> bool:
    """Check that the message is from the authorized user in an allowed chat."""
    if update.effective_user is None:
        return False
    if update.effective_user.id != USER_ID:
        return False
    chat_id = update.effective_chat.id
    # Allow DMs (positive chat id == private) or the specific group
    if chat_id == USER_ID or chat_id == GROUP_ID:
        return True
    return False


async def deny(update: Update) -> None:
    """Send a short denial message."""
    await update.message.reply_text("⛔ Not authorised.")


def run_claude(prompt: str, allowed_tools: str, timeout: int = 600) -> str:
    """Run `claude -p` as a subprocess and return stdout.

    Saves output to docs/shared/QUANDALF_LATEST_RESPONSE.md before returning,
    so Opus reasoning is never lost to Telegram timeouts or truncation.
    """
    cmd = [
        "claude",
        "-p",
        prompt,
        "--allowedTools",
        allowed_tools,
    ]
    response_file = WORKSPACE / "docs" / "shared" / "QUANDALF_LATEST_RESPONSE.md"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKSPACE),
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\n\n[stderr] {result.stderr.strip()}"

        output = output if output else "(no output)"

        try:
            response_file.parent.mkdir(parents=True, exist_ok=True)
            with open(response_file, "w", encoding="utf-8") as f:
                f.write(f"# Quandalf Latest Response\n\n")
                f.write(f"**Timestamp:** {now_aest()}\n")
                f.write(f"**Prompt:** {prompt[:200]}...\n")
                f.write(f"**Status:** COMPLETE\n\n---\n\n")
                f.write(output)
        except Exception:
            pass

        return output

    except subprocess.TimeoutExpired:
        timeout_msg = "\u23f1 Claude timed out after {}s. Check docs/shared/QUANDALF_LATEST_RESPONSE.md for any partial output.".format(timeout)

        try:
            response_file.parent.mkdir(parents=True, exist_ok=True)
            with open(response_file, "w", encoding="utf-8") as f:
                f.write(f"# Quandalf Latest Response\n\n")
                f.write(f"**Timestamp:** {now_aest()}\n")
                f.write(f"**Prompt:** {prompt[:200]}...\n")
                f.write(f"**Status:** TIMED OUT after {timeout}s\n\n---\n\n")
                f.write("(Response timed out — Opus may have been mid-reasoning)\n")
        except Exception:
            pass

        return timeout_msg

    except FileNotFoundError:
        return "\u274c `claude` CLI not found on PATH."
    except Exception as e:
        return f"\u274c Error: {e}"


def run_task_script(script_name: str, timeout: int = 300) -> str:
    """Run a PowerShell task script and return its output."""
    script_path = TASK_DIR / script_name
    if not script_path.is_file():
        return f"❌ Script not found: {script_name}"
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKSPACE),
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\n\n[stderr] {result.stderr.strip()}"
        return output if output else "(completed, no output)"
    except subprocess.TimeoutExpired:
        return f"⏱ Task timed out after {timeout}s."
    except Exception as e:
        return f"❌ Error: {e}"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_cli(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cli <query> — read-only Claude query."""
    if not authorized(update):
        return await deny(update)

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /cli <your question>")
        return

    threat = is_dangerous(query)
    if threat:
        log_command(USER_ID, "/cli", query, f"BLOCKED:{threat}", False)
        await update.message.reply_text(f"🚫 Blocked — matched safety filter: `{threat}`")
        return

    await update.message.reply_text("🔍 Querying Claude (read-only)…")
    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(None, run_claude, query, "Read,Glob,Grep")
    log_command(USER_ID, "/cli", query, output, True)
    await update.message.reply_text(truncate(output))


async def cmd_write(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/write <query> — Claude query with Write restricted to safe paths."""
    if not authorized(update):
        return await deny(update)

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /write <your instruction>")
        return

    threat = is_dangerous(query)
    if threat:
        log_command(USER_ID, "/write", query, f"BLOCKED:{threat}", False)
        await update.message.reply_text(f"🚫 Blocked — matched safety filter: `{threat}`")
        return

    # Build allowed tools with path-restricted Write/Edit
    write_rules = ",".join(f"Write({p}*)" for p in ALLOWED_WRITE_PATHS)
    edit_rules = ",".join(f"Edit({p}*)" for p in ALLOWED_WRITE_PATHS)
    multiedit_rules = ",".join(f"MultiEdit({p}*)" for p in ALLOWED_WRITE_PATHS)
    allowed = f"Read,Glob,Grep,Bash(scripts/tg_notify.py*),{write_rules},{edit_rules},{multiedit_rules}"

    await update.message.reply_text("✏️ Running Claude with write access…")
    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(None, run_claude, query, allowed)
    log_command(USER_ID, "/write", query, output, True)
    await update.message.reply_text(truncate(output))


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/run <task> — trigger a task script from scripts/claude-tasks/."""
    if not authorized(update):
        return await deny(update)

    task_name = context.args[0].lower().strip() if context.args else ""

    if not task_name or task_name not in KNOWN_TASKS:
        names = ", ".join(sorted(KNOWN_TASKS.keys()))
        await update.message.reply_text(f"Usage: /run <task>\nAvailable: {names}")
        return

    script = KNOWN_TASKS[task_name]
    await update.message.reply_text(f"🚀 Running task `{task_name}` ({script})…")
    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(None, run_task_script, script)
    log_command(USER_ID, "/run", task_name, output, True)
    await update.message.reply_text(truncate(output))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — quick pipeline health check."""
    if not authorized(update):
        return await deny(update)

    lines: list[str] = [f"📊 *Pipeline Status* — {now_aest()}\n"]

    # Latest outcome notes
    outcomes_dir = WORKSPACE / "artifacts" / "outcomes"
    if outcomes_dir.is_dir():
        date_dirs = sorted(outcomes_dir.iterdir(), reverse=True)
        if date_dirs:
            latest_dir = date_dirs[0]
            jsons = sorted(latest_dir.glob("*.json"), reverse=True)
            lines.append(f"*Outcomes:* {latest_dir.name}/ — {len(jsons)} files")
            if jsons:
                try:
                    data = json.loads(jsons[0].read_text(encoding="utf-8"))
                    verdict = data.get("verdict", "?")
                    pf = data.get("metrics", {}).get("pf", "?")
                    lines.append(f"  └ Latest: {jsons[0].name} → {verdict} (PF {pf})")
                except Exception:
                    lines.append(f"  └ Latest: {jsons[0].name} (parse error)")
        else:
            lines.append("*Outcomes:* (no date folders)")
    else:
        lines.append("*Outcomes:* (directory missing)")

    # Latest backtest results
    bt_dir = WORKSPACE / "artifacts" / "backtests"
    if bt_dir.is_dir():
        date_dirs = sorted(bt_dir.iterdir(), reverse=True)
        if date_dirs:
            latest_dir = date_dirs[0]
            jsons = sorted(latest_dir.glob("*.json"), reverse=True)
            lines.append(f"*Backtests:* {latest_dir.name}/ — {len(jsons)} files")
        else:
            lines.append("*Backtests:* (no date folders)")
    else:
        lines.append("*Backtests:* (directory missing)")

    # Strategy specs
    specs_dir = WORKSPACE / "artifacts" / "strategy_specs"
    if specs_dir.is_dir():
        date_dirs = sorted(specs_dir.iterdir(), reverse=True)
        if date_dirs:
            latest_dir = date_dirs[0]
            jsons = sorted(latest_dir.glob("*.json"), reverse=True)
            lines.append(f"*Specs:* {latest_dir.name}/ — {len(jsons)} files")
        else:
            lines.append("*Specs:* (no date folders)")
    else:
        lines.append("*Specs:* (directory missing)")

    # Advisory age
    advisory = WORKSPACE / "docs" / "claude-reports" / "STRATEGY_ADVISORY.md"
    if advisory.is_file():
        mtime = datetime.fromtimestamp(advisory.stat().st_mtime, tz=timezone.utc)
        age_h = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
        lines.append(f"*Advisory:* updated {age_h:.1f}h ago")
    else:
        lines.append("*Advisory:* not yet generated")

    # Recent bridge logs
    today_log = LOG_DIR / f"bridge_{datetime.now(timezone.utc).strftime('%Y%m%d')}.ndjson"
    if today_log.is_file():
        count = sum(1 for _ in open(today_log, encoding="utf-8"))
        lines.append(f"*Bridge log:* {count} commands today")
    else:
        lines.append("*Bridge log:* no commands today")

    msg = "\n".join(lines)
    log_command(USER_ID, "/status", "", msg, True)
    await update.message.reply_text(truncate(msg))


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop — gracefully shut down the bot."""
    if not authorized(update):
        return await deny(update)

    log_command(USER_ID, "/stop", "", "shutdown", True)
    await update.message.reply_text("👋 Bridge shutting down.")
    # Graceful shutdown
    asyncio.get_running_loop().call_soon(
        lambda: asyncio.ensure_future(_shutdown(context.application))
    )


async def _shutdown(app: Application) -> None:
    """Stop the application's updater and shutdown."""
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


async def handle_plain_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text in DMs as read-only /cli queries."""
    if update.effective_chat is None or update.effective_chat.type != "private":
        return
    if not authorized(update):
        return await deny(update)
    if update.message is None or not update.message.text:
        return

    query = update.message.text.strip()
    if not query:
        return

    threat = is_dangerous(query)
    if threat:
        log_command(USER_ID, "/cli(dm)", query, f"BLOCKED:{threat}", False)
        await update.message.reply_text(f"🚫 Blocked — matched safety filter: `{threat}`")
        return

    await update.message.reply_text("🔍 Querying Claude (DM mode)…")
    loop = asyncio.get_running_loop()
    # DM mode: allow write/edit only under docs/shared/
    dm_allowed = "Read,Glob,Grep,Write(docs/shared/*),Edit(docs/shared/*),MultiEdit(docs/shared/*)"
    output = await loop.run_in_executor(None, run_claude, query, dm_allowed)
    log_command(USER_ID, "/cli(dm)", query, output, True)
    await update.message.reply_text(truncate(output))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting Telegram Claude Bridge…")
    logger.info("Workspace: %s", WORKSPACE)
    logger.info("Authorised user: %s | Group: %s", USER_ID, GROUP_ID)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("cli", cmd_cli))
    app.add_handler(CommandHandler("write", cmd_write))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_dm))

    logger.info("Bot is polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
