#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _iso(v: str, tz: str) -> str:
    v = v.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(v, fmt)
            return f"{dt.isoformat()}{tz}"
        except ValueError:
            pass
    return v


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest TradingView exported OHLCV CSV into canonical artifact layout.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", required=True)
    ap.add_argument("--timezone", default="+00:00", help="Exchange-time timezone offset suffix to persist in meta.")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(src)

    with src.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    if not rows:
        raise ValueError("Input CSV has no rows")

    lower_map = {h.lower().strip(): h for h in headers}
    col_map = {
        "time": lower_map.get("time") or lower_map.get("date"),
        "open": lower_map.get("open"),
        "high": lower_map.get("high"),
        "low": lower_map.get("low"),
        "close": lower_map.get("close"),
        "volume": lower_map.get("volume") or lower_map.get("vol") or lower_map.get("volume usdt"),
    }
    if any(v is None for v in col_map.values()):
        missing = [k for k, v in col_map.items() if v is None]
        raise ValueError(f"Missing required columns: {missing}; headers={headers}")

    normalized = []
    for row in rows:
        normalized.append({
            "time": row[col_map["time"]].strip(),
            "open": row[col_map["open"]].strip(),
            "high": row[col_map["high"]].strip(),
            "low": row[col_map["low"]].strip(),
            "close": row[col_map["close"]].strip(),
            "volume": row[col_map["volume"]].strip(),
        })

    start = _iso(normalized[0]["time"], args.timezone)
    end = _iso(normalized[-1]["time"], args.timezone)

    start_slug = start.replace(":", "").replace("+", "p").replace("-", "m")
    end_slug = end.replace(":", "").replace("+", "p").replace("-", "m")

    base = ROOT / "artifacts" / "data" / "tradingview_export" / args.symbol / args.timeframe
    base.mkdir(parents=True, exist_ok=True)
    stem = f"{start_slug}-{end_slug}"
    out_csv = base / f"{stem}.csv"
    out_meta = base / f"{stem}.meta.json"

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(normalized)

    meta = {
        "schema_version": "1.0",
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "start": start,
        "end": end,
        "timezone": args.timezone,
        "row_count": len(normalized),
        "sha256": _sha256(out_csv),
        "column_mapping": col_map,
        "source_file": str(src),
    }
    out_meta.write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"dataset_csv": str(out_csv), "dataset_meta": str(out_meta)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
