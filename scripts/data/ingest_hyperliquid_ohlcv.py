#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Hyperliquid OHLCV into canonical dataset artifacts.")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", required=True, choices=sorted(INTERVAL_MS.keys()))
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--end-ms", type=int, default=0)
    args = ap.parse_args()

    now = int(datetime.now(UTC).timestamp() * 1000) if args.end_ms <= 0 else args.end_ms
    start = now - args.lookback_days * 24 * 60 * 60 * 1000

    rows = fetch(args.symbol, args.timeframe, start, now)
    ok, median_sec = validate(rows, args.timeframe)
    if not ok:
        raise SystemExit("HYPERLIQUID_DATA_INVALID")

    rows = sorted(rows, key=lambda x: int(x["t"]))
    first_ts = datetime.fromtimestamp(int(rows[0]["t"]) / 1000, tz=UTC)
    last_ts = datetime.fromtimestamp(int(rows[-1]["t"]) / 1000, tz=UTC)

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
