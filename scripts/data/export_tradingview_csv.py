#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "artifacts" / "data" / "tradingview_export" / "INDEX.json"


@dataclass
class ExportResult:
    status: str
    reason_code: str
    meta_path: str | None
    csv_path: str | None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sanitize_symbol(s: str) -> str:
    return s.replace(":", "__").replace("/", "_")


def _parse_ts(v: str) -> datetime:
    v = v.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)


def _read_csv_rows(path: Path) -> tuple[list[dict], list[str], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        headers = r.fieldnames or []
    low = {h.lower().strip(): h for h in headers}
    mapping = {
        "time": low.get("time") or low.get("date"),
        "open": low.get("open"),
        "high": low.get("high"),
        "low": low.get("low"),
        "close": low.get("close"),
        "volume": low.get("volume") or low.get("vol") or low.get("volume usdt"),
    }
    return rows, headers, mapping


def _bars_per_day(tf: str) -> float:
    mins = int(tf)
    return (24 * 60) / mins


def _write_index(pointer: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    idx = []
    if INDEX_PATH.exists():
        try:
            idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            idx = []
    idx.append(pointer)
    idx = idx[-200:]
    INDEX_PATH.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def _timeframe_alignment(rows: list[dict], time_col: str, timeframe: str) -> tuple[bool, int | None, list[str]]:
    if not rows:
        return False, None, []
    ts = [_parse_ts(r[time_col]) for r in rows if r.get(time_col)]
    bad = []
    if timeframe == "15":
        for t in ts:
            if t.minute not in {0, 15, 30, 45}:
                bad.append(t.strftime("%Y-%m-%d %H:%M:%S"))
                if len(bad) >= 5:
                    break
    deltas = []
    for i in range(1, len(ts)):
        deltas.append(int((ts[i] - ts[i - 1]).total_seconds()))
    median_delta = sorted(deltas)[len(deltas) // 2] if deltas else None
    ok = (len(bad) == 0)
    if timeframe == "15" and median_delta != 900:
        ok = False
    return ok, median_delta, bad


def export_one(target: dict, mode: str, source_csv: Path, simulate_plateau: bool = False) -> ExportResult:
    tv_symbol = target["tv_symbol"]
    tf = str(target["timeframe"])
    rows, headers, mapping = _read_csv_rows(source_csv)

    if not rows:
        return ExportResult("PARTIAL", "TV_EXPORT_INCOMPLETE", None, None)

    if mapping["volume"] is None:
        failed = _save_failed(target, mode, source_csv, "TV_EXPORT_MISSING_VOLUME", False, 0)
        return ExportResult("PARTIAL", "TV_EXPORT_MISSING_VOLUME", str(failed), None)

    tf_ui_verified = True  # UI verification stub; browser flow should set/check chart label with retries.
    if not tf_ui_verified:
        failed = _save_failed(target, mode, source_csv, "TV_EXPORT_TIMEFRAME_MISMATCH", True, len(rows), None, ["ui_timeframe_label_mismatch"])
        return ExportResult("PARTIAL", "TV_EXPORT_TIMEFRAME_MISMATCH", str(failed), None)

    first_ts = _parse_ts(rows[0][mapping["time"]])
    last_ts = _parse_ts(rows[-1][mapping["time"]])
    row_count = len(rows)

    alignment_ok, median_delta, bad_samples = _timeframe_alignment(rows, mapping["time"], tf)
    if not alignment_ok:
        failed = _save_failed(target, mode, source_csv, "TV_EXPORT_TIMEFRAME_MISMATCH", True, row_count, median_delta, bad_samples)
        return ExportResult("PARTIAL", "TV_EXPORT_TIMEFRAME_MISMATCH", str(failed), None)

    # validation freshness: within ~4 bars
    now_utc = datetime.now(timezone.utc)
    bars_late = (now_utc - last_ts).total_seconds() / (int(tf) * 60)
    if bars_late > 4.5 and mode == "incremental":
        failed = _save_failed(target, mode, source_csv, "TV_EXPORT_INCOMPLETE", True, row_count)
        return ExportResult("PARTIAL", "TV_EXPORT_INCOMPLETE", str(failed), None)

    if mode == "incremental":
        lookback = int(target.get("incremental", {}).get("lookback_days", 30))
        expected_min = math.floor(0.8 * (lookback * _bars_per_day(tf)))
        if row_count < expected_min:
            failed = _save_failed(target, mode, source_csv, "TV_EXPORT_INCOMPLETE", True, row_count)
            return ExportResult("PARTIAL", "TV_EXPORT_INCOMPLETE", str(failed), None)
    else:
        prev_inc = _latest_incremental_count(tv_symbol, tf)
        if prev_inc > 0 and row_count <= prev_inc and not simulate_plateau:
            failed = _save_failed(target, mode, source_csv, "TV_EXPORT_INCOMPLETE", True, row_count)
            return ExportResult("PARTIAL", "TV_EXPORT_INCOMPLETE", str(failed), None)

    sym = _sanitize_symbol(tv_symbol)
    start = first_ts.strftime("%Y%m%dT%H%M%SZ")
    end = last_ts.strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "artifacts" / "data" / "tradingview_export" / sym / tf / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"{start}-{end}.csv"
    out_meta = out_dir / f"{start}-{end}.meta.json"

    out_csv.write_bytes(source_csv.read_bytes())
    meta = {
        "source": "tradingview_export",
        "backend": "openclaw",
        "tv_symbol": tv_symbol,
        "timeframe": tf,
        "history_mode": mode,
        "export_ts": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "first_ts": first_ts.isoformat(),
        "last_ts": last_ts.isoformat(),
        "sha256": _sha256(out_csv),
        "deep_plateau_reached": bool(simulate_plateau if mode == "deep" else False),
        "stagnation_count": int(target.get("deep", {}).get("stagnation_checks", 0) if mode == "deep" else 0),
        "volume_present": True,
        "timeframe_alignment_ok": alignment_ok,
        "median_bar_delta_seconds": median_delta,
        "bad_timestamp_samples": bad_samples,
        "columns": headers,
    }
    out_meta.write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    _write_index({
        "tv_symbol": tv_symbol,
        "tf": tf,
        "mode": mode,
        "first_ts": meta["first_ts"],
        "last_ts": meta["last_ts"],
        "sha256": meta["sha256"],
        "path": str(out_csv).replace("\\", "/"),
    })
    return ExportResult("PASS", "OK", str(out_meta), str(out_csv))


def _latest_incremental_count(tv_symbol: str, tf: str) -> int:
    if not INDEX_PATH.exists():
        return 0
    try:
        idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return 0
    for p in reversed(idx):
        if p.get("tv_symbol") == tv_symbol and str(p.get("tf")) == str(tf) and p.get("mode") == "incremental":
            meta = Path(str(p.get("path")).replace("/", "\\")).with_suffix(".meta.json")
            if meta.exists():
                try:
                    return int(json.loads(meta.read_text(encoding="utf-8")).get("row_count", 0))
                except Exception:
                    return 0
    return 0


def _save_failed(target: dict, mode: str, source_csv: Path, reason: str, volume_present: bool, row_count: int, median_bar_delta_seconds: int | None = None, bad_timestamp_samples: list[str] | None = None) -> Path:
    sym = _sanitize_symbol(target["tv_symbol"])
    tf = str(target["timeframe"])
    fail_dir = ROOT / "artifacts" / "data" / "tradingview_export" / "_failed" / sym / tf / mode
    fail_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_csv = fail_dir / f"{ts}.csv"
    out_meta = fail_dir / f"{ts}.meta.json"
    out_csv.write_bytes(source_csv.read_bytes())
    out_meta.write_text(json.dumps({
        "status": "PARTIAL",
        "reason_code": reason,
        "tv_symbol": target["tv_symbol"],
        "timeframe": str(target["timeframe"]),
        "history_mode": mode,
        "row_count": row_count,
        "volume_present": volume_present,
        "timeframe_alignment_ok": False,
        "median_bar_delta_seconds": median_bar_delta_seconds,
        "bad_timestamp_samples": bad_timestamp_samples or [],
        "source": "tradingview_export",
        "backend": "openclaw",
    }, separators=(",", ":")), encoding="utf-8")
    return out_meta


def main() -> int:
    ap = argparse.ArgumentParser(description="TradingView CSV exporter workflow (artifact + validation layer).")
    ap.add_argument("--config", default="config/tv_export_targets.json")
    ap.add_argument("--target", default="eth_perp_15m")
    ap.add_argument("--mode", choices=["incremental", "deep"], required=True)
    ap.add_argument("--source-csv", required=True, help="Captured TradingView export CSV path.")
    ap.add_argument("--simulate-plateau", action="store_true")
    args = ap.parse_args()

    cfg = _load_json(ROOT / args.config)
    target = next((t for t in cfg.get("targets", []) if t.get("name") == args.target), None)
    if not target:
        raise SystemExit("target_not_found")

    res = export_one(target, args.mode, Path(args.source_csv), simulate_plateau=args.simulate_plateau)
    print(json.dumps({
        "status": res.status,
        "reason_code": res.reason_code,
        "meta_path": res.meta_path,
        "csv_path": res.csv_path,
        "index_path": str(INDEX_PATH),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
