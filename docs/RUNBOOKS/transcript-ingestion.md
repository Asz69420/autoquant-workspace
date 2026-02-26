# Transcript Ingestion Runbook

## Overview

Two complementary paths for getting video transcripts into the pipeline:

1. **Transcript Drop Folder** (manual/user-provided transcripts)
2. **ASR Fallback** (automatic speech recognition when captions unavailable)

---

## Path 1: Transcript Drop Folder

### How It Works

User manually places transcript text files in `data/inbox/transcripts/`:
- Worker periodically scans folder
- Reads `.txt` files (name = video ID or description)
- Emits research cards + bundles for each
- Moves processed files to `data/inbox/transcripts/processed/`

### Manual Run

```bash
python scripts/pipeline/transcript_ingest_worker.py
```

Output:
- Processed count + failed count
- Files moved to `processed/` or `failed/`
- Log events: `TRANSCRIPT_INGEST_START`, `TRANSCRIPT_INGEST_OK`, `TRANSCRIPT_INGEST_FAIL`

### Scheduled Task Setup (Windows)

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\Clamps\.openclaw\workspace\scripts\pipeline\transcript_ingest_worker.py"
$trigger = New-ScheduledTaskTrigger -Daily -At "09:30"
Register-ScheduledTask -TaskName "AutoQuant-transcript-ingest" -Action $action -Trigger $trigger -Description "Ingest manually uploaded transcripts daily" -Force
```

**Frequency:** Once daily (configurable).

### File Naming

- **Video ID (preferred):** `ydjTTG7Ik5U.txt` → becomes URL `https://www.youtube.com/watch?v=ydjTTG7Ik5U`
- **Descriptive name:** `my_strategy_breakdown.txt` → becomes `transcript_drop://my_strategy_breakdown`

### Example Content

```
In this strategy we require trend alignment using EMA 50 and EMA 200.
Enter long when RSI crosses above 55 and MACD histogram turns positive.
Stop loss is 1.5 ATR below entry and take profit is 2.5 ATR.
Risk per trade is 1 percent.
```

---

## Path 2: ASR Fallback

### How It Works

When captions unavailable (IP-blocked, deleted, etc.):
1. `transcript_resolver.py` attempts YouTube captions (as before)
2. If blocked/rate-limited, **ASR is now default** (not optional)
3. Downloads audio via yt-dlp, transcribes with faster-whisper
4. Returns transcript if successful, else fails over gracefully

### Dependencies

Already installed:
- `faster-whisper` (speech-to-text model)
- `imageio-ffmpeg` (audio handling)
- `yt-dlp` (video download)

**Note:** First run downloads the "small" Whisper model (~1.5GB) and may take 5–10 minutes.

### Configuration

**Default behavior (ASR enabled):**
```bash
python scripts/pipeline/transcript_resolver.py --video-id <vid> --url <url>
```

**Force disable ASR:**
```bash
python scripts/pipeline/transcript_resolver.py --video-id <vid> --url <url> --disable-asr
```

### Logging

- `ASR_TRANSCRIBE_START` when ASR attempt begins
- `ASR_TRANSCRIBE_OK` on success (chars=<count>)
- `ASR_TRANSCRIBE_FAIL` on failure (with detail)

---

## Log Events Reference

All events use:
- **Agent:** `Reader` (🔗 emoji)
- **Model:** `openai-codex/gpt-5.3-codex`
- **Format:** 3-line code block (header | reason | summary)

### Transcript Drop Events

```
🔗 Reader | codex 5.3 | ▶️ START
(TRANSCRIPT_INGEST_START)
Ingest start file=ydjTTG7Ik5U.txt
```

```
🔗 Reader | codex 5.3 | ✅ OK
(TRANSCRIPT_INGEST_OK)
Ingest ok file=ydjTTG7Ik5U.txt bundle=ydjTTG7Ik5U.bundle.json
```

### ASR Events

```
🔗 Reader | codex 5.3 | ▶️ START
(ASR_TRANSCRIBE_START)
ASR start url=https://www.youtube.com/watch?v=ydjTTG7Ik5U
```

```
🔗 Reader | codex 5.3 | ✅ OK
(ASR_TRANSCRIBE_OK)
ASR ok chars=1247
```

---

## Troubleshooting

### Transcript Drop

**Q: File not in `processed/` after running worker?**
- Check `failed/` folder for errors
- Review `data/logs/actions.ndjson` for `TRANSCRIPT_INGEST_FAIL` events

**Q: Research card is a stub (no indicators/rules)?**
- Transcript content may be too brief or missing trading logic
- Verify file contains strategy details (entry, exit, risk rules)

### ASR

**Q: ASR very slow on first run?**
- Normal: downloading ~1.5GB model. Subsequent runs use cache.
- Runs in CPU mode; GPU acceleration available but not configured

**Q: "ffmpeg not found" warning?**
- ASR still works (uses fallback encoding)
- Optional: install FFmpeg for faster audio processing

---

## End-to-End Example

### Manual Transcript Drop

```bash
# 1. Create transcript file
echo "EMA crossover with RSI confirmation. Enter at 50+ RSI crossing EMA 50 above EMA 200. Stop 1.5 ATR, target 2.5 ATR." > data/inbox/transcripts/my_strategy.txt

# 2. Run worker
python scripts/pipeline/transcript_ingest_worker.py

# Output:
# {"processed": 1, "failed": 0, ...}

# 3. Check logs
grep TRANSCRIPT_INGEST data/logs/actions.ndjson | tail -2

# 4. Verify bundle created
ls artifacts/bundles/20260226/my_strategy.bundle.json
```

### ASR on Rate-Limited Video

```bash
# resolver auto-attempts ASR when captions blocked
python scripts/pipeline/transcript_resolver.py --video-id ydjTTG7Ik5U --url https://www.youtube.com/watch?v=ydjTTG7Ik5U

# Output (on success):
# {"ok": true, "method": "asr_whisper", "quality": "asr", "text": "...transcript..."}

# Check logs
grep ASR_TRANSCRIBE data/logs/actions.ndjson | tail -3
```

---

## Integration

Both paths feed into `emit_research_card.py` → `link_research_indicators.py` → bundle creation.
Bundles are picked up by downstream analysis (content-worker, promotion, etc.) automatically.
