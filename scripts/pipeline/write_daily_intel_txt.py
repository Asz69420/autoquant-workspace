#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / "artifacts" / "library" / "RUN_INDEX.json"
OUT_PATH = ROOT / "artifacts" / "reports" / "daily_intel.txt"
BATCH_ROOT = ROOT / "artifacts" / "batches"
PROMO_ROOT = ROOT / "artifacts" / "promotions"

AEST = ZoneInfo("Australia/Brisbane")
NOW_UTC = datetime.now(timezone.utc)
SINCE_24H = NOW_UTC - timedelta(hours=24)
TF_ORDER = {"4h": 0, "1h": 1, "15m": 2}
ASSET_ORDER = {"BTC": 0, "ETH": 1}
MAX_WIDTH = 42

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


def dt(v: str | None):
    if not v:
        return None
    s = str(v).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def pct(v: float | None):
    if v is None:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def alias12(name: str):
    cleaned = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in (name or ""))
    toks = [t for t in cleaned.replace("-", " ").replace("_", " ").split() if t]
    if not toks:
        return "Unknown"
    mapped = [ALIAS.get(t.lower(), t[:5].title()) for t in toks]
    if len(mapped) >= 2:
        s = f"{mapped[0]}_{mapped[1]}"
    else:
        s = mapped[0]
    return s[:12]


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
    strategy: str
    key: str
    pf: float
    wr: float | None
    tc: int
    dd: float | None
    pnl: float | None
    t: str


def strategy_name(spec_path: str, variant: str):
    spec = jload(Path(spec_path), {}) if spec_path else {}
    thesis = jload(Path(str(spec.get("source_thesis_path") or "")), {}) if spec.get("source_thesis_path") else {}

    sigs = thesis.get("candidate_signals") if isinstance(thesis, dict) else None
    pair = []
    if isinstance(sigs, list):
        for s in sigs:
            if isinstance(s, dict) and isinstance(s.get("uses_indicators"), list):
                pair.extend([str(x) for x in s["uses_indicators"] if str(x).strip()])
            if len(pair) >= 2:
                break

    base = ""
    if len(pair) >= 2:
        base = f"{pair[0]} {pair[1]}"
    if not base:
        base = (
            str(thesis.get("strategy_family") or "").strip()
            or str(thesis.get("title") or "").strip()
            or str(spec.get("strategy_family") or "").strip()
            or variant
            or Path(spec_path).stem
        )

    short = alias12(base)
    return short, short.lower()


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


def collect():
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

        sp = str(r.get("strategy_spec_path") or "")
        var = str(r.get("variant_name") or "")
        sname, skey = strategy_name(sp, var)

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, tc, dd, pnl = metrics(bt, r)
        if tc is None or tc <= 0:
            continue

        staged.append((created, asset, tf, sname, skey, pf, wr, tc, dd, pnl))
        pf_hist[skey].append((created, pf))

    for k in pf_hist:
        pf_hist[k].sort(key=lambda x: x[0])

    rows = []
    for created, asset, tf, sname, skey, pf, wr, tc, dd, pnl in staged:
        prev = None
        for hdt, hpf in pf_hist[skey]:
            if hdt < created:
                prev = hpf
            else:
                break
        rows.append(Row(created, asset, tf, sname, skey, pf, wr, tc, dd, pnl, trend(prev, pf)))

    # global dedupe: strategy appears once, keep best row only
    best = {}
    for r in rows:
        cur = best.get(r.strategy)
        if cur is None or (r.pf, r.wr or -999, r.pnl or -999) > (cur.pf, cur.wr or -999, cur.pnl or -999):
            best[r.strategy] = r
    deduped = list(best.values())

    meta = {
        "cycles": 0,
        "backtests": sum(1 for r in rows if r.created >= SINCE_24H),
        "specs": len({str(x[3]) for x in staged if x[0] >= SINCE_24H}),
        "errors": 0,
    }

    if BATCH_ROOT.exists():
        for p in BATCH_ROOT.rglob("*.batch_backtest.json"):
            j = jload(p, {})
            c = dt(j.get("created_at"))
            if not c or c < SINCE_24H:
                continue
            meta["cycles"] += 1
            meta["errors"] += int(inum((j.get("summary") or {}).get("failed_runs")) or 0)

    return deduped, meta


def fmt(v, d=1, signed=False):
    if v is None:
        return "-"
    return f"{v:+.{d}f}" if signed else f"{v:.{d}f}"


def clamp(line: str):
    return line if len(line) <= MAX_WIDTH else line[:MAX_WIDTH]


def render_tables(rows: list[Row]):
    lines = []
    for asset in sorted({r.asset for r in rows}, key=lambda a: ASSET_ORDER.get(a, 99)):
        lines.append("🏆 BTC" if asset == "BTC" else "🔵 ETH" if asset == "ETH" else f"⚪ {asset}")
        aset = [r for r in rows if r.asset == asset]
        tfs = sorted({r.tf for r in aset}, key=lambda t: TF_ORDER.get(t, 99))
        for tf in tfs:
            tf_rows = [r for r in aset if r.tf == tf]
            top = sorted(tf_rows, key=lambda r: (r.pf, r.wr or -999, r.pnl or -999), reverse=True)[:3]
            if not top:
                continue
            lines.append(clamp(f"── {tf} ─────────────────────────────"))
            lines.append(clamp("△ Strategy     PF WR% TC DD% P&L%"))
            for r in top:
                row = f"{r.t:<3} {r.strategy:<12} {r.pf:>4.2f} {fmt(r.wr):>4} {r.tc:>3} {fmt(r.dd):>4} {fmt(r.pnl,1,True):>5}"
                lines.append(clamp(row))
        lines.append("")
    return lines


def milestones(rows: list[Row]):
    out = []
    firsts = [r for r in rows if r.pf >= 1.0 and r.created >= SINCE_24H]
    if firsts:
        out.append("• PF>1 firsts: " + ", ".join(x.strategy for x in firsts[:2]))

    if rows:
        top = sorted(rows, key=lambda r: r.pf, reverse=True)[:2]
        out.append("• New records: " + ", ".join(f"{x.strategy} {x.pf:.2f}" for x in top))

    promoted = []
    if PROMO_ROOT.exists():
        for p in PROMO_ROOT.rglob("*.promotion_run.json"):
            j = jload(p, {})
            c = dt(j.get("created_at"))
            if c and c >= SINCE_24H and str(j.get("status") or "").upper() == "OK":
                promoted.append("near-promo")
                if len(promoted) >= 1:
                    break
    if promoted:
        out.append("• Near-promotion seen")

    if not out:
        out.append("• None")
    return [clamp(x) for x in out]


def attention(meta):
    a = []
    if meta["errors"] > 0:
        a.append(clamp(f"• Errors: {meta['errors']} failed runs/24h"))
        a.append(clamp("• Investigate next session"))
    if meta["cycles"] == 0:
        a.append(clamp("• Stall: no cycles in 24h"))
    if not a:
        a.append("• System healthy ✅")
    return a


def build(rows, meta):
    now = datetime.now(AEST)
    lines = [clamp(f"📊 DAILY INTEL — {now:%Y-%m-%d} 5:30 AEST"), ""]
    lines += render_tables(rows)
    lines += [
        "⚡ 24H ACTIVITY",
        clamp(f"Cycles:{meta['cycles']} Backtests:{meta['backtests']}"),
        clamp(f"Specs:{meta['specs']} Errors:{meta['errors']}"),
        "",
        "🎯 MILESTONES",
    ]
    lines += milestones(rows)
    lines += ["", "⚠️ ATTENTION"]
    lines += attention(meta)
    lines.append("")
    return "\n".join(lines)


def send(path: Path):
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--send-telegram", action="store_true")
    args = ap.parse_args()

    rows, meta = collect()
    text = build(rows, meta)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")

    if args.send_telegram:
        send(OUT_PATH)

    print(json.dumps({"ok": True, "path": str(OUT_PATH).replace('\\', '/'), "rows": len(rows), "errors": meta["errors"]}))


if __name__ == "__main__":
    main()
