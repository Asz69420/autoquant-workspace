#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _log(action: str, reason: str, summary: str, status: str = 'INFO') -> None:
    try:
        cmd = [
            PY,
            'scripts/log_event.py',
            '--run-id', f"asr-{int(datetime.now(UTC).timestamp())}",
            '--agent', 'Reader',
            '--model-id', 'openai-codex/gpt-5.3-codex',
            '--action', action,
            '--status-word', status,
            '--status-emoji', ('▶️' if status == 'START' else ('✅' if status == 'OK' else ('❌' if status == 'FAIL' else 'ℹ️'))),
            '--reason-code', reason,
            '--summary', summary,
        ]
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_caption_payload(payload: str) -> str:
    t = payload.strip()
    if not t:
        return ""
    if t.startswith("WEBVTT"):
        lines = []
        for ln in payload.splitlines():
            x = ln.strip()
            if not x:
                continue
            if x.startswith("WEBVTT") or x.startswith("NOTE"):
                continue
            if re.match(r"^\d\d:\d\d:\d\d", x) or re.match(r"^\d+:\d\d", x):
                continue
            if x.isdigit():
                continue
            lines.append(x)
        return _clean_text(" ".join(lines))
    if t.startswith("<"):
        try:
            root = ET.fromstring(payload)
            parts: list[str] = []
            for e in root.iter():
                tag = e.tag.lower() if isinstance(e.tag, str) else ""
                if tag.endswith("p"):
                    txt = "".join(e.itertext()).strip()
                    if txt:
                        parts.append(txt)
            return _clean_text(" ".join(parts))
        except Exception:
            return ""
    return _clean_text(payload)


def via_youtube_transcript_api(video_id: str) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    t = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
    text = "\n".join([x.text for x in t])
    text = _clean_text(text)
    if not text:
        raise RuntimeError("empty transcript from youtube_transcript_api")
    return {"ok": True, "method": "youtube_transcript_api", "quality": "caption", "text": text}


def via_ytdlp(url: str) -> dict:
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}

    chosen = None
    chosen_lang = ""
    chosen_type = ""
    for cand in ["en", "en-US", "en-GB"]:
        if cand in subs and subs[cand]:
            chosen = subs[cand][0]
            chosen_lang = cand
            chosen_type = "manual"
            break
    if not chosen:
        for cand in ["en", "en-US", "en-GB"]:
            if cand in autos and autos[cand]:
                chosen = autos[cand][0]
            chosen_lang = cand if chosen else chosen_lang
            if chosen:
                chosen_type = "auto"
                break
    if not chosen:
        pool = subs or autos
        if pool:
            k = next(iter(pool.keys()))
            chosen = pool[k][0]
            chosen_lang = k
            chosen_type = "manual" if pool is subs else "auto"

    if not chosen or not chosen.get("url"):
        raise RuntimeError("no captions discovered by yt-dlp")

    payload = urlopen(chosen["url"], timeout=30).read().decode("utf-8", errors="ignore")
    text = _parse_caption_payload(payload)
    if not text:
        raise RuntimeError("yt-dlp caption payload parsed empty")

    return {
        "ok": True,
        "method": "yt_dlp_subtitles",
        "quality": "caption" if chosen_type == "manual" else "auto_caption",
        "text": text,
        "lang": chosen_lang,
    }


def via_asr(url: str) -> dict:
    _log('ASR_TRANSCRIBE_START', 'ASR_TRANSCRIBE_START', f'ASR start url={url}', 'START')
    try:
        import yt_dlp  # noqa: F401
    except Exception as e:
        _log('ASR_TRANSCRIBE_FAIL', 'ASR_TRANSCRIBE_FAIL', f'ASR fail: yt-dlp missing detail={e}', 'FAIL')
        raise RuntimeError("yt-dlp missing for audio download")

    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        _log('ASR_TRANSCRIBE_FAIL', 'ASR_TRANSCRIBE_FAIL', f'ASR fail: faster-whisper missing detail={e}', 'FAIL')
        raise RuntimeError("faster-whisper not installed")

    with tempfile.TemporaryDirectory(prefix="ytasr_") as td:
        out = Path(td) / "audio"
        cmd = [
            PY,
            "-m",
            "yt_dlp",
            "-f",
            "bestaudio/best",
            "-o",
            str(out) + ".%(ext)s",
            url,
        ]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            msg = (cp.stderr or cp.stdout or "yt-dlp audio download failed").strip()[:500]
            _log('ASR_TRANSCRIBE_FAIL', 'ASR_TRANSCRIBE_FAIL', f'ASR fail: audio download detail={msg}', 'FAIL')
            raise RuntimeError(msg)

        files = list(Path(td).glob("audio.*"))
        if not files:
            _log('ASR_TRANSCRIBE_FAIL', 'ASR_TRANSCRIBE_FAIL', 'ASR fail: audio file not produced', 'FAIL')
            raise RuntimeError("audio file not produced")

        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(files[0]), language="en")
        text = _clean_text(" ".join([seg.text for seg in segments]))
        if not text:
            _log('ASR_TRANSCRIBE_FAIL', 'ASR_TRANSCRIBE_FAIL', 'ASR fail: empty transcript', 'FAIL')
            raise RuntimeError("ASR produced empty transcript")
        _log('ASR_TRANSCRIBE_OK', 'ASR_TRANSCRIBE_OK', f'ASR ok chars={len(text)}', 'OK')
        return {"ok": True, "method": "asr_whisper", "quality": "asr", "text": text}


def _is_rate_limited(err: str) -> bool:
    s = (err or "").lower()
    needles = [
        "ipblocked",
        "requestblocked",
        "http error 429",
        "too many requests",
        "rate limit",
        "youtube is blocking requests from your ip",
    ]
    return any(n in s for n in needles)


def _rate_limit_result(errors: list[str], retry_after_seconds: int | None = None) -> dict:
    if retry_after_seconds is None:
        retry_after_seconds = 900 + random.randint(0, 600)
    return {
        "ok": False,
        "status": "RETRY_LATER",
        "error_code": "YOUTUBE_RATE_LIMIT",
        "retry_after_seconds": int(retry_after_seconds),
        "method": "none",
        "quality": "none",
        "text": "",
        "errors": errors,
    }


def resolve(video_id: str, url: str, enable_asr: bool = True) -> dict:
    if os.getenv("TRANSCRIPT_RESOLVER_FORCE_429", "").strip() in {"1", "true", "TRUE"}:
        return _rate_limit_result(["forced:HTTPError:HTTP Error 429: Too Many Requests"], retry_after_seconds=900)

    errors = []
    rate_limited = False

    for fn in (via_youtube_transcript_api,):
        try:
            out = fn(video_id)
            out.setdefault("status", "OK")
            return out
        except Exception as e:
            err = f"youtube_transcript_api:{type(e).__name__}:{e}"
            errors.append(err)
            if _is_rate_limited(err):
                rate_limited = True

    try:
        out = via_ytdlp(url)
        out.setdefault("status", "OK")
        return out
    except Exception as e:
        err = f"yt_dlp_subtitles:{type(e).__name__}:{e}"
        errors.append(err)
        if _is_rate_limited(err):
            rate_limited = True

    if enable_asr:
        try:
            out = via_asr(url)
            out.setdefault("status", "OK")
            return out
        except Exception as e:
            errors.append(f"asr_whisper:{type(e).__name__}:{e}")

    if rate_limited:
        return _rate_limit_result(errors)

    return {"ok": False, "status": "FAILED", "method": "none", "quality": "none", "text": "", "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve YouTube transcript with layered fallback")
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--enable-asr", action="store_true", help='Force-enable ASR (default on).')
    ap.add_argument("--disable-asr", action="store_true", help='Disable ASR fallback.')
    args = ap.parse_args()
    enable_asr = False if args.disable_asr else True
    if args.enable_asr:
        enable_asr = True
    out = resolve(args.video_id, args.url, enable_asr=enable_asr)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
