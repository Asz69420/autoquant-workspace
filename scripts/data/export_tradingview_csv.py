#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "artifacts" / "data" / "tradingview_export" / "INDEX.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def _sanitize_symbol(s: str) -> str:
    return s.replace(":", "__").replace("/", "_")


def _parse_ts(v: str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(v.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)


def _read(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        hdr = r.fieldnames or []
    low = {h.lower().strip(): h for h in hdr}
    m = {"time": low.get("time") or low.get("date"), "open": low.get("open"), "high": low.get("high"), "low": low.get("low"), "close": low.get("close"), "volume": low.get("volume") or low.get("vol")}
    return rows, hdr, m


def _alignment(rows, tcol, tf):
    ts = [_parse_ts(r[tcol]) for r in rows if r.get(tcol)]
    bad = [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts if tf == "15" and t.minute not in {0, 15, 30, 45}][:5]
    deltas = [int((ts[i] - ts[i-1]).total_seconds()) for i in range(1, len(ts))]
    med = int(median(deltas)) if deltas else None
    ok = (not bad) and (med == 900 if tf == "15" else True)
    return ok, med, bad


def _synthetic_stats(rows, close_col, vol_col):
    closes = [float(r[close_col]) for r in rows if r.get(close_col) not in (None, "")]
    vols = [str(r[vol_col]) for r in rows if r.get(vol_col) not in (None, "")]
    close_min, close_max = (min(closes), max(closes)) if closes else (None, None)
    vur = (len(set(vols)) / len(vols)) if vols else 0.0
    vol_med = median([float(v) for v in vols]) if vols else 0.0
    most_common_ratio = 0.0
    if vols:
        counts = {}
        for v in vols:
            counts[v] = counts.get(v, 0) + 1
        most_common_ratio = max(counts.values()) / len(vols)
    tiny_range = False
    if close_min and close_max:
        tiny_range = ((close_max - close_min) / max(close_min, 1e-9)) < 0.005
    synthetic = (vur < 0.01) or tiny_range or (most_common_ratio > 0.95)
    return {
        "close_min": close_min,
        "close_max": close_max,
        "volume_unique_ratio": round(vur, 8),
        "volume_median": float(vol_med),
        "synthetic_detected": synthetic,
    }


def _save_failed(target, mode, src, reason, extra):
    d = ROOT / "artifacts" / "data" / "tradingview_export" / "_failed" / _sanitize_symbol(target["tv_symbol"]) / str(target["timeframe"]) / mode
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_csv = d / f"{ts}.csv"
    out_meta = d / f"{ts}.meta.json"
    out_csv.write_bytes(src.read_bytes())
    base = {"status": "PARTIAL", "reason_code": reason, "tv_symbol": target["tv_symbol"], "timeframe": str(target["timeframe"]), "history_mode": mode, "source": "tradingview_export", "backend": "openclaw"}
    base.update(extra)
    out_meta.write_text(json.dumps(base, separators=(",", ":")), encoding="utf-8")
    return out_meta


def _write_index(ptr):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else []
    idx.append(ptr)
    INDEX_PATH.write_text(json.dumps(idx[-200:], indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/tv_export_targets.json")
    ap.add_argument("--target", default="eth_perp_15m")
    ap.add_argument("--mode", choices=["incremental", "deep"], required=True)
    ap.add_argument("--downloaded-csv", required=True)
    ap.add_argument("--download-timeout-seconds", type=int, default=45)
    ap.add_argument("--chart-url-used", required=True)
    ap.add_argument("--tv-symbol-ui", required=True)
    ap.add_argument("--timeframe-ui", required=True)
    args = ap.parse_args()

    cfg = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    target = next((t for t in cfg.get("targets", []) if t.get("name") == args.target), None)
    if not target:
        raise SystemExit("target_not_found")

    src = Path(args.downloaded_csv)
    if not src.exists():
        print(json.dumps({"status": "PARTIAL", "reason_code": "TV_EXPORT_DOWNLOAD_MISSING", "meta_path": None, "csv_path": None, "index_path": str(INDEX_PATH)}))
        return 0

    rows, hdr, m = _read(src)
    if not rows or any(m[k] is None for k in ("time", "open", "high", "low", "close", "volume")):
        meta = _save_failed(target, args.mode, src, "TV_EXPORT_INCOMPLETE", {"row_count": len(rows), "columns": hdr})
        print(json.dumps({"status": "PARTIAL", "reason_code": "TV_EXPORT_INCOMPLETE", "meta_path": str(meta), "csv_path": None, "index_path": str(INDEX_PATH)}))
        return 0

    tf = str(target["timeframe"])
    if tf == "15" and args.timeframe_ui not in ("15", "15m", "15min", "15 minutes"):
        meta = _save_failed(target, args.mode, src, "TV_EXPORT_TIMEFRAME_MISMATCH", {"timeframe_ui": args.timeframe_ui})
        print(json.dumps({"status": "PARTIAL", "reason_code": "TV_EXPORT_TIMEFRAME_MISMATCH", "meta_path": str(meta), "csv_path": None, "index_path": str(INDEX_PATH)}))
        return 0

    align_ok, med_delta, bad = _alignment(rows, m["time"], tf)
    stats = _synthetic_stats(rows, m["close"], m["volume"])

    if not align_ok:
        meta = _save_failed(target, args.mode, src, "TV_EXPORT_TIMEFRAME_MISMATCH", {"timeframe_alignment_ok": False, "median_bar_delta_seconds": med_delta, "bad_timestamp_samples": bad})
        print(json.dumps({"status": "PARTIAL", "reason_code": "TV_EXPORT_TIMEFRAME_MISMATCH", "meta_path": str(meta), "csv_path": None, "index_path": str(INDEX_PATH)}))
        return 0

    if stats["synthetic_detected"]:
        meta = _save_failed(target, args.mode, src, "TV_EXPORT_SYNTHETIC_DETECTED", {"sanity_stats": stats, "chart_url_used": args.chart_url_used, "tv_symbol_ui": args.tv_symbol_ui, "timeframe_ui": args.timeframe_ui, "download_filename": src.name})
        print(json.dumps({"status": "PARTIAL", "reason_code": "TV_EXPORT_SYNTHETIC_DETECTED", "meta_path": str(meta), "csv_path": None, "index_path": str(INDEX_PATH)}))
        return 0

    first_ts = _parse_ts(rows[0][m["time"]])
    last_ts = _parse_ts(rows[-1][m["time"]])
    sym = _sanitize_symbol(target["tv_symbol"])
    out_dir = ROOT / "artifacts" / "data" / "tradingview_export" / sym / tf / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{first_ts.strftime('%Y%m%dT%H%M%SZ')}-{last_ts.strftime('%Y%m%dT%H%M%SZ')}"
    out_csv = out_dir / f"{stem}.csv"
    out_meta = out_dir / f"{stem}.meta.json"
    out_csv.write_bytes(src.read_bytes())

    meta = {
        "source": "tradingview_export", "backend": "openclaw", "tv_symbol": target["tv_symbol"], "timeframe": tf,
        "history_mode": args.mode, "export_ts": datetime.now(timezone.utc).isoformat(), "row_count": len(rows),
        "first_ts": first_ts.isoformat(), "last_ts": last_ts.isoformat(), "sha256": _sha256(out_csv),
        "chart_url_used": args.chart_url_used, "tv_symbol_ui": args.tv_symbol_ui, "timeframe_ui": args.timeframe_ui,
        "download_filename": src.name, "timeframe_alignment_ok": True, "median_bar_delta_seconds": med_delta,
        "bad_timestamp_samples": bad, "sanity_stats": stats, "volume_present": True, "columns": hdr
    }
    out_meta.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")

    _write_index({"tv_symbol": target["tv_symbol"], "tf": tf, "mode": args.mode, "first_ts": meta["first_ts"], "last_ts": meta["last_ts"], "sha256": meta["sha256"], "path": str(out_csv).replace("\\", "/")})
    print(json.dumps({"status": "PASS", "reason_code": "OK", "meta_path": str(out_meta), "csv_path": str(out_csv), "index_path": str(INDEX_PATH)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
