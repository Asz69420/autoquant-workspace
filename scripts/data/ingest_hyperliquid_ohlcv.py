#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "artifacts" / "data" / "hyperliquid" / "INDEX.json"
API_URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[dict]:
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }
    req = request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def validate(rows: list[dict], tf: str) -> tuple[bool, int | None]:
    if not rows:
        return False, None
    required = {"t", "o", "h", "l", "c", "v"}
    for r in rows:
        if not required.issubset(r.keys()):
            return False, None
    times = sorted(int(r["t"]) for r in rows)
    if len(times) < 2:
        return True, INTERVAL_MS[tf] // 1000
    deltas = [times[i] - times[i - 1] for i in range(1, len(times))]
    med = int(statistics.median(deltas))
    return med == INTERVAL_MS[tf], med // 1000


def update_index(ptr: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else []
    idx.append(ptr)
    INDEX_PATH.write_text(json.dumps(idx[-200:], indent=2), encoding="utf-8")


def emit_warn(reason_code: str, summary: str) -> None:
    try:
        rid = f"ingest-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        subprocess.run([
            sys.executable,
            str((ROOT / "scripts" / "log_event.py").resolve()),
            "--run-id", rid,
            "--agent", "oQ",
            "--model-id", "openai-codex/gpt-5.3-codex",
            "--action", "data_ingest",
            "--status-word", "WARN",
            "--status-emoji", "WARN",
            "--reason-code", reason_code,
            "--summary", summary,
        ], cwd=ROOT, check=False, capture_output=True, text=True)
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Hyperliquid OHLCV into canonical dataset artifacts.")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", required=True, choices=sorted(INTERVAL_MS.keys()))
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--end-ms", type=int, default=0)
    args = ap.parse_args()

    fetch_ts_ms = int(datetime.now(UTC).timestamp() * 1000)
    now = fetch_ts_ms if args.end_ms <= 0 else args.end_ms
    start = now - args.lookback_days * 24 * 60 * 60 * 1000

    rows = fetch(args.symbol, args.timeframe, start, now)
    ok, median_sec = validate(rows, args.timeframe)
    if not ok:
        raise SystemExit("HYPERLIQUID_DATA_INVALID")

    rows = sorted(rows, key=lambda x: int(x["t"]))
    interval_ms = INTERVAL_MS[args.timeframe]
    filtered_rows = [r for r in rows if (int(r["t"]) + interval_ms) < fetch_ts_ms]
    dropped_unclosed_count = len(rows) - len(filtered_rows)
    if not filtered_rows:
        raise SystemExit("HYPERLIQUID_DATA_NO_CLOSED_CANDLES")
    if dropped_unclosed_count > 0:
        emit_warn("UNFINISHED_CANDLE_DROPPED", f"Dropped {dropped_unclosed_count} unfinished candle(s) for {args.symbol} {args.timeframe}")

    rows = filtered_rows
    first_ts = datetime.fromtimestamp(int(rows[0]["t"]) / 1000, tz=UTC)
    last_ts = datetime.fromtimestamp(int(rows[-1]["t"]) / 1000, tz=UTC)
    last_closed_candle_ts = datetime.fromtimestamp((int(rows[-1]["t"]) + interval_ms) / 1000, tz=UTC)

    out_dir = ROOT / "artifacts" / "data" / "hyperliquid" / args.symbol / args.timeframe
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{first_ts.strftime('%Y%m%dT%H%M%SZ')}-{last_ts.strftime('%Y%m%dT%H%M%SZ')}"
    out_csv = out_dir / f"{stem}.csv"
    out_meta = out_dir / f"{stem}.meta.json"

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "open", "high", "low", "close", "volume"])
        w.writeheader()
        for r in rows:
            w.writerow({
                "time": datetime.fromtimestamp(int(r["t"]) / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "open": r["o"],
                "high": r["h"],
                "low": r["l"],
                "close": r["c"],
                "volume": r["v"],
            })

    meta = {
        "source": "hyperliquid",
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "tz": "UTC",
        "start": first_ts.isoformat(),
        "end": last_ts.isoformat(),
        "fetch_ts": datetime.fromtimestamp(fetch_ts_ms / 1000, tz=UTC).isoformat(),
        "last_closed_candle_ts": last_closed_candle_ts.isoformat(),
        "dropped_unclosed_count": dropped_unclosed_count,
        "row_count": len(rows),
        "sha256": sha256(out_csv),
        "fetch_params": {"start_ms": start, "end_ms": now, "lookback_days": args.lookback_days},
        "validation": {"bar_spacing_ok": ok, "median_bar_delta_seconds": median_sec, "required_columns_ok": True},
    }
    out_meta.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")

    update_index({
        "symbol": args.symbol,
        "tf": args.timeframe,
        "start": meta["start"],
        "end": meta["end"],
        "sha256": meta["sha256"],
        "path": str(out_csv).replace("\\", "/"),
    })

    print(json.dumps({"dataset_csv": str(out_csv), "dataset_meta": str(out_meta), "index_path": str(INDEX_PATH)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
