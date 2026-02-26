#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / "artifacts" / "library" / "RUN_INDEX.json"
OUT_PATH = ROOT / "artifacts" / "reports" / "daily_intel.txt"
BATCH_ROOT = ROOT / "artifacts" / "batches"
PROMO_ROOT = ROOT / "artifacts" / "promotions"
ACTIONS_LOG = ROOT / "data" / "logs" / "actions.ndjson"

AEST = ZoneInfo("Australia/Brisbane")
NOW_UTC = datetime.now(timezone.utc)
SINCE_24H = NOW_UTC - timedelta(hours=24)

TF_ORDER = {"4h": 0, "1h": 1, "15m": 2}
ASSET_ORDER = {"BTC": 0, "ETH": 1}
EMOJI = {"BTC": "🟠", "ETH": "🔵"}
MAX_WIDTH = 42

fmt = "{:<1} {:<12} {:>4} {:>4} {:>3} {:>4} {:>5}"

ALIAS = {
    "adx": "ADX",
    "supertrend": "Suprtrnd",
    "bollinger": "BB",
    "mean": "Mean",
    "reversion": "Rev",
    "gaussian": "Gauss",
    "pullback": "Pull",
    "ichimoku": "Ichimoku",
    "cci": "CCI",
    "donchian": "Donch",
    "obv": "OBV",
    "session": "Session",
    "trend": "Trend",
    "squeeze": "Squeeze",
    "ema": "EMA",
    "rsi": "RSI",
    "macd": "MACD",
}


def jload(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def inum(v):
    try:
        return int(v)
    except Exception:
        return None


def dt(v):
    if not v:
        return None
    s = str(v).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def pct(v):
    if v is None:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def alias12(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in (name or ""))
    toks = [t for t in cleaned.replace("-", " ").replace("_", " ").split() if t]
    if not toks:
        return "Unknown"

    stop = {"strategy", "thesis", "spec", "variant", "directive", "entry", "exit", "generated"}
    picked = []
    for t in toks:
        lo = t.lower()
        if lo in stop:
            continue
        if lo.isdigit():
            continue
        if lo.startswith("strategy") and any(ch.isdigit() for ch in lo):
            continue
        mapped = ALIAS.get(lo)
        if mapped:
            picked.append(mapped)
        elif len(lo) >= 3:
            picked.append(t[:5].title())
        if len(picked) >= 2:
            break

    if not picked:
        picked = ["Strat"]
    out = f"{picked[0]}_{picked[1]}" if len(picked) >= 2 else picked[0]
    return out[:12]


def trend(prev_pf, curr_pf):
    if prev_pf is None:
        return "NEW"
    d = curr_pf - prev_pf
    if d > 0.02:
        return "↑"
    if d < -0.02:
        return "↓"
    return "→"


@dataclass
class Row:
    created: datetime
    asset: str
    tf: str
    name: str
    key: str
    spec_path: str
    pf: float
    wr: float | None
    tc: int
    dd: float | None
    pnl: float | None
    arrow: str


def strategy_name(spec_path: str, variant: str):
    spec = jload(Path(spec_path), {}) if spec_path else {}
    thesis_path = str(spec.get("source_thesis_path") or "")
    thesis = jload(Path(thesis_path), {}) if thesis_path else {}

    # Primary: thesis title or spec description.
    base = (
        str(thesis.get("title") or "").strip()
        or str(spec.get("description") or "").strip()
    )

    # Secondary: strategy family from spec/thesis.
    if not base:
        base = (
            str(spec.get("strategy_family") or "").strip()
            or str(thesis.get("strategy_family") or "").strip()
        )

    # Fallback: spec stem token (e.g. b9d7_Spec).
    if not base:
        stem = Path(spec_path).stem if spec_path else "spec"
        tail = stem[-12:] if len(stem) > 12 else stem
        tail = ''.join(ch for ch in tail if ch.isalnum())
        token = (tail[:4] if len(tail) >= 4 else tail) or "Spec"
        base = f"{token}_Spec"

    short = alias12(base)
    # Guard against non-meaningful generic names.
    if short.lower() in {"strat", "trat", "unknown"} or short.lower().startswith("strat"):
        stem = Path(spec_path).stem if spec_path else "spec"
        m = re.findall(r"[0-9a-fA-F]{4,}", stem)
        token = (m[-1][:4] if m else (''.join(ch for ch in stem if ch.isalnum())[-4:] or "Spec"))
        short = f"{token}_Spec"[:12]
    return short, short.lower(), {
        "primary_field": "thesis.title|spec.description",
        "secondary_field": "spec.strategy_family|thesis.strategy_family",
        "fallback_field": "spec filename stem",
        "resolved_base": base,
    }


def metrics(backtest_path: str, run: dict):
    bj = jload(Path(backtest_path), {}) if backtest_path and Path(backtest_path).exists() else {}
    res = bj.get("results") or {}

    wr = pct(fnum(res.get("win_rate")))
    tc = inum(res.get("total_trades") or res.get("trades") or run.get("trades"))
    pnl = pct(fnum(res.get("net_profit_pct")))
    dd = pct(fnum(res.get("max_drawdown_pct")))

    if dd is None:
        dd_raw = fnum(res.get("max_drawdown"))
        net_raw = fnum(res.get("net_profit"))
        net_pct = fnum(res.get("net_profit_pct"))
        if dd_raw is not None and net_raw is not None and net_pct not in (None, 0):
            p = net_pct if abs(net_pct) <= 1 else net_pct / 100.0
            if p:
                start = net_raw / p
                if start:
                    dd = (dd_raw / abs(start)) * 100.0

    if wr is None:
        wr = pct(fnum(run.get("win_rate")))
    if tc is None:
        tc = inum(run.get("trades"))
    if pnl is None:
        net = fnum(run.get("net_profit"))
        if net is not None:
            pnl = (net / 10000.0) * 100.0

    return wr, tc, dd, pnl


def collect_rows():
    runs = jload(RUN_INDEX, [])
    pf_hist = defaultdict(list)
    staged = []

    for r in runs:
        created = dt(r.get("created_at"))
        pf = fnum(r.get("profit_factor"))
        if not created or pf is None:
            continue

        ds = r.get("datasets_tested") or []
        if not ds:
            continue
        d = ds[0] if isinstance(ds, list) else ds
        asset = str(d.get("symbol") or "").upper().strip()
        tf = str(d.get("timeframe") or "").lower().strip()
        if not asset or not tf:
            continue

        spec_path = str(r.get("strategy_spec_path") or "")
        variant = str(r.get("variant_name") or "")
        name, key, _name_debug = strategy_name(spec_path, variant)

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, tc, dd, pnl = metrics(bt, r)
        if tc is None or tc <= 0:
            continue

        staged.append((created, asset, tf, name, key, spec_path, pf, wr, tc, dd, pnl))
        pf_hist[key].append((created, pf))

    for k in pf_hist:
        pf_hist[k].sort(key=lambda x: x[0])

    rows = []
    for created, asset, tf, name, key, spec_path, pf, wr, tc, dd, pnl in staged:
        prev = None
        for hdt, hpf in pf_hist[key]:
            if hdt < created:
                prev = hpf
            else:
                break
        rows.append(Row(created, asset, tf, name, key, spec_path, pf, wr, tc, dd, pnl, trend(prev, pf)))

    # Deduplicate repeated identical backtest rows (same metrics in same asset/timeframe).
    deduped = []
    seen_results = set()
    for r in sorted(rows, key=lambda x: (x.asset, x.tf, -(x.pf or -999), -(x.wr or -999), -(x.pnl or -999))):
        sig = (
            r.asset,
            r.tf,
            round(r.pf or 0.0, 4),
            round(r.wr or 0.0, 2),
            int(r.tc or 0),
            round(r.dd or 0.0, 2),
            round(r.pnl or 0.0, 2),
        )
        if sig in seen_results:
            continue
        seen_results.add(sig)
        deduped.append(r)

    # Keep best row per strategy per asset/timeframe.
    by_strategy = {}
    for r in deduped:
        k = (r.asset, r.tf, r.key)
        cur = by_strategy.get(k)
        if cur is None or (r.pf, r.wr or -999, r.pnl or -999) > (cur.pf, cur.wr or -999, cur.pnl or -999):
            by_strategy[k] = r
    deduped = list(by_strategy.values())

    # Ensure row names are unique and meaningful when collisions happen.
    name_counts = defaultdict(int)
    for r in deduped:
        name_counts[(r.asset, r.tf, r.name)] += 1
    if any(v > 1 for v in name_counts.values()):
        for r in deduped:
            if name_counts[(r.asset, r.tf, r.name)] <= 1:
                continue
            stem = Path(r.spec_path).stem if r.spec_path else "spec"
            m = re.findall(r"[0-9a-fA-F]{4,}", stem)
            if m:
                tail = m[-1][:4]
            else:
                tail = (''.join(ch for ch in stem if ch.isalnum())[-4:] or "Spec")
            r.name = (r.name[:7] + "_" + tail)[:12]

    # 24h meta
    cycles = 0
    errors = 0
    backtests = sum(1 for r in rows if r.created >= SINCE_24H)
    specs = len({str((x.get('strategy_spec_path') or '')) for x in runs if dt(x.get('created_at')) and dt(x.get('created_at')) >= SINCE_24H})

    if BATCH_ROOT.exists():
        for p in BATCH_ROOT.rglob("*.batch_backtest.json"):
            j = jload(p, {})
            c = dt(j.get("created_at"))
            if not c or c < SINCE_24H:
                continue
            cycles += 1
            errors += int(inum((j.get("summary") or {}).get("failed_runs")) or 0)

    top_error = ""
    top_error_count = 0
    if ACTIONS_LOG.exists():
        buckets = defaultdict(int)
        try:
            for line in ACTIONS_LOG.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
                if not line.strip().startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                t = dt(obj.get("ts_iso") or obj.get("created_at"))
                if not t or t < SINCE_24H:
                    continue
                sw = str(obj.get("status_word") or "").upper()
                if sw != "FAIL":
                    continue
                rc = str(obj.get("reason_code") or obj.get("action") or "UNKNOWN")
                buckets[rc] += 1
            if buckets:
                top_error, top_error_count = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)[0]
        except Exception:
            pass

    return deduped, {"cycles": cycles, "backtests": backtests, "specs": specs, "errors": errors, "top_error": top_error, "top_error_count": top_error_count}


def fmtv(v, d=1, signed=False):
    if v is None:
        return "-"
    return f"{v:+.{d}f}" if signed else f"{v:.{d}f}"


def limit42(s: str) -> str:
    return s if len(s) <= MAX_WIDTH else s[:MAX_WIDTH]


def render_asset_blocks(rows: list[Row]):
    lines = []
    assets = sorted({r.asset for r in rows}, key=lambda a: ASSET_ORDER.get(a, 99))
    for asset in assets:
        lines.append(f"{EMOJI.get(asset, '⚪')} {asset}")

        header = fmt.format("△", "Strategy", "PF", "WR%", "TC", "DD%", "P&L%")
        lines.append(limit42(header))
        row_width = len(header)

        tf_rows = [r for r in rows if r.asset == asset]
        tfs = sorted({r.tf for r in tf_rows}, key=lambda t: TF_ORDER.get(t, 99))
        for tf in tfs:
            group = [r for r in tf_rows if r.tf == tf]
            top3 = sorted(group, key=lambda r: (r.pf, r.wr or -999, r.pnl or -999), reverse=True)[:3]
            if not top3:
                continue
            prefix = f"○── {tf} "
            sep = prefix + ("─" * max(0, row_width - len(prefix)))
            lines.append(limit42(sep))
            for r in top3:
                row = fmt.format(
                    r.arrow,
                    r.name[:12],
                    f"{r.pf:.2f}",
                    fmtv(r.wr),
                    str(r.tc),
                    fmtv(r.dd),
                    fmtv(r.pnl, signed=True),
                )
                lines.append(limit42(row))

        lines.append("")
    return lines


def milestones(rows: list[Row]):
    out = []
    firsts = [r for r in rows if r.pf >= 1.0 and r.created >= SINCE_24H]
    if firsts:
        out.append("• PF>1 firsts: " + ", ".join(x.name for x in firsts[:2]))

    if rows:
        top = sorted(rows, key=lambda r: r.pf, reverse=True)[:2]
        out.append("• New records: " + ", ".join(f"{x.name} {x.pf:.2f}" for x in top))

    near = False
    if PROMO_ROOT.exists():
        for p in PROMO_ROOT.rglob("*.promotion_run.json"):
            j = jload(p, {})
            c = dt(j.get("created_at"))
            if c and c >= SINCE_24H and str(j.get("status") or "").upper() == "OK":
                near = True
                break
    if near:
        out.append("• Near-promotion seen")

    if not out:
        out.append("• None")
    return [limit42(x) for x in out]


def attention(meta):
    out = []
    if meta["errors"] > 0:
        out.append(limit42(f"• Errors:{meta['errors']} failed runs/24h"))
        if meta.get("top_error"):
            out.append(limit42(f"• Top:{meta['top_error']} x{meta.get('top_error_count',0)}"))
    if meta["cycles"] == 0:
        out.append("• Stalls: no cycles in 24h")
    if not out:
        out.append("• System healthy ✅")
    return out


def build_text(rows, meta):
    now = datetime.now(AEST)
    lines = [limit42(f"📊 DAILY INTEL — {now:%Y-%m-%d} 5:30 AEST"), ""]
    lines += render_asset_blocks(rows)
    lines += [
        "⚡ 24H ACTIVITY",
        limit42(f"Cycles:{meta['cycles']} Backtests:{meta['backtests']}"),
        limit42(f"Specs:{meta['specs']} Errors:{meta['errors']}"),
        "",
        "🎯 MILESTONES",
    ]
    lines += milestones(rows)
    lines += ["", "⚠️ ATTENTION"]
    lines += attention(meta)
    lines.append("")
    return "\n".join(lines)


def send_file(path: Path):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CMD_CHAT_ID") or os.getenv("TELEGRAM_LOG_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CMD_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with path.open("rb") as f:
        files = {"document": (path.name, f, "text/plain")}
        data = {"chat_id": chat_id, "caption": "daily_intel.txt"}
        r = requests.post(url, data=data, files=files, timeout=20)
        r.raise_for_status()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--send-telegram", action="store_true")
    args = ap.parse_args()

    rows, meta = collect_rows()

    # Required alignment check printed to console
    header = fmt.format("△", "Strategy", "PF", "WR%", "TC", "DD%", "P&L%")
    sample = fmt.format("↑", "EMA_Atr", "1.09", "34.3", "172", "2.5", "+1.8")
    print(header)
    print(sample)

    text = build_text(rows, meta)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")

    if args.send_telegram:
        send_file(OUT_PATH)

    print(json.dumps({
        "ok": True,
        "path": str(OUT_PATH).replace('\\', '/'),
        "rows": len(rows),
        "errors": meta["errors"],
        "alignment_ok": len(header) == len(sample),
        "name_source_fields": "primary=thesis.title|spec.description; secondary=spec.strategy_family|thesis.strategy_family; fallback=spec filename stem",
    }))


if __name__ == "__main__":
    main()
