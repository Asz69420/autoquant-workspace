#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _norm_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_")


def _f(row: dict, *keys: str, default=None):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def load_our(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj.get("trades", [])


def load_tv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = []
        for raw in r:
            row = {_norm_header(k): v for k, v in raw.items()}
            rows.append({
                "entry_time": _f(row, "entry_time", "entry_date/time", "entry_time_(utc)"),
                "entry_price": float(_f(row, "entry_price", "entry", "entry_price_usd", default=0) or 0),
                "exit_time": _f(row, "exit_time", "exit_date/time", "exit_time_(utc)"),
                "exit_price": float(_f(row, "exit_price", "exit", "exit_price_usd", default=0) or 0),
                "side": str(_f(row, "side", "type", "direction", default="")).lower(),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare canonical trade list with TradingView exported trades CSV.")
    ap.add_argument("--our", required=True)
    ap.add_argument("--tv", required=True)
    args = ap.parse_args()

    our = load_our(Path(args.our))
    tv = load_tv(Path(args.tv))

    compared = min(len(our), len(tv))
    exact = 0
    first = None
    summary = {"entry_time_shift": 0, "price_shift": 0, "missing_trades": abs(len(our) - len(tv))}

    for i in range(compared):
        a, b = our[i], tv[i]
        entry_time_eq = str(a.get("entry_time")) == str(b.get("entry_time"))
        exit_time_eq = str(a.get("exit_time")) == str(b.get("exit_time"))
        entry_price_eq = abs(float(a.get("entry_price", 0)) - float(b.get("entry_price", 0))) < 1e-8
        exit_price_eq = abs(float(a.get("exit_price", 0)) - float(b.get("exit_price", 0))) < 1e-8
        if entry_time_eq and exit_time_eq and entry_price_eq and exit_price_eq:
            exact += 1
        else:
            if not entry_time_eq or not exit_time_eq:
                summary["entry_time_shift"] += 1
            if not entry_price_eq or not exit_price_eq:
                summary["price_shift"] += 1
            if first is None:
                first = {
                    "trade_index": i,
                    "our": {
                        "entry_time": a.get("entry_time"),
                        "entry_price": a.get("entry_price"),
                        "exit_time": a.get("exit_time"),
                        "exit_price": a.get("exit_price"),
                    },
                    "tv": {
                        "entry_time": b.get("entry_time"),
                        "entry_price": b.get("entry_price"),
                        "exit_time": b.get("exit_time"),
                        "exit_price": b.get("exit_price"),
                    },
                }

    match_rate = (exact / max(1, compared))
    report = {
        "schema_version": "1.0",
        "id": f"parity_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "match_rate": round(match_rate, 8),
        "first_mismatch": first,
        "summary": summary,
        "counts": {"our_trades": len(our), "tv_trades": len(tv), "compared": compared},
    }

    out_dir = ROOT / "artifacts" / "parity" / datetime.now().strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report['id']}.parity_report.json"
    out_path.write_text(json.dumps(report, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"parity_report": str(out_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
