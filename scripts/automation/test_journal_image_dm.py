import os
import re
import json
import base64
from pathlib import Path

import requests

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace")
LOG = ROOT / "data" / "logs" / "journal-image-test.log"


def load_dotenv(path: Path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and (k not in os.environ or not os.environ.get(k)):
            os.environ[k] = v


def get_latest_entry_text(journal_path: Path) -> str:
    raw = journal_path.read_text(encoding="utf-8", errors="ignore")
    matches = list(re.finditer(r"(?ms)^## Entry\b.*?(?=^## Entry\b|\Z)", raw))
    if matches:
        return matches[-1].group(0).strip()
    return raw.strip()


def summarize_for_prompt(text: str, max_chars: int = 1800) -> str:
    t = re.sub(r"(?is)(?:^|\n)\s*(?:---\s*)?machine\s+directives\b.*", "", text)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > max_chars:
        t = t[:max_chars]
    return t


def main():
    load_dotenv(ROOT / ".env")
    LOG.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CMD_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    if not bot_token:
        raise RuntimeError("Telegram bot token missing (TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN)")
    if not chat_id:
        raise RuntimeError("Telegram chat id missing (TELEGRAM_CMD_CHAT_ID/TELEGRAM_CHAT_ID)")

    journal_path = ROOT / "docs" / "shared" / "QUANDALF_JOURNAL.md"
    if not journal_path.exists():
        raise RuntimeError(f"Journal missing: {journal_path}")

    entry = get_latest_entry_text(journal_path)
    core = summarize_for_prompt(entry)

    prompt = (
        "Create a cinematic fantasy-tech illustration for a trading AI journal update. "
        "Tone: calm, strategic, high-signal. Avoid text overlays. "
        "Visualize key themes from this journal entry:\n\n" + core
    )

    img_resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "gpt-image-1",
            "size": "1536x1024",
            "quality": "medium",
            "background": "auto",
            "response_format": "b64_json",
            "prompt": prompt,
        },
        timeout=180,
    )
    img_resp.raise_for_status()
    payload = img_resp.json()
    b64 = payload["data"][0]["b64_json"]

    tmp = ROOT / "data" / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    out_path = tmp / "quandalf_journal_test.png"
    out_path.write_bytes(base64.b64decode(b64))

    caption = "🖼️ Quandalf journal image test (latest entry)"
    with out_path.open("rb") as f:
        tg = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f},
            timeout=120,
        )
        tg.raise_for_status()

    LOG.write_text(json.dumps({"ok": True, "image_path": str(out_path)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "image_path": str(out_path)}))


if __name__ == "__main__":
    try:
      main()
    except Exception as e:
      LOG.parent.mkdir(parents=True, exist_ok=True)
      LOG.write_text(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2), encoding="utf-8")
      print(json.dumps({"ok": False, "error": str(e)}))
      raise
