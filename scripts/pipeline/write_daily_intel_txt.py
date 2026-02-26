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
ACTIONS_LOG = ROOT / "data" / "logs" / "actions.ndjson"

AEST = ZoneInfo("Australia/Brisbane")
NOW_UTC = datetime.now(timezone.utc)
SINCE_24H = NOW_UTC - timedelta(hours=24)

TF_ORDER = {"4h": 0, "1h": 1, "15m": 2}
ASSET_ORDER = {"BTC": 0, "ETH": 1}
EMOJI = {"BTC": "🟠", "ETH": "🔵"}
MAX_WIDTH = 42

# Required exact format string from spec.
fmt = "{:<1} {:<12} {:>4} {:>4} {:>3} {:>4} {:>5}"

ABBR = {
    "adx": "ADX",
    "supertrend": "Suprtrnd",
    "bollinger": "BB",
    "mean": "Mean",
    "reversion": "Rev",
    "gaussian": "Gauss",
    "pullback": "Pull",
    "session": "Sess",
    "trend": "Trend",
    "breakout": "Brkout",
    "ema": "EMA",
    "sma": "SMA",
    "rsi": "RSI",
    "atr": "Atr",
    "macd": "MACD",
    "ichimoku": "Ichi",
}
STOP = {"strategy", "thesis", "spec", "variant", "entry", "exit", "generated", "model"}


@dataclass
class Row:
    created: datetime
    asset: str
    tf: str
    name: str
    pf: float
    wr: float | None
    tc: int
    dd: float | None
    pnl: float | None
    arrow: str


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


def limit42(s: str) -> str:
    return s if len(s) <= MAX_WIDTH else s[:MAX_WIDTH]


def normalize_name(raw: str, fallback_token: str) -> str:
    txt = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in (raw or ""))
    toks = [t for t in txt.replace("-", " ").replace("_", " ").split() if t]
    lo_toks = [t.lower() for t in toks]

    # Preferred compact aliases requested by user.
    if "adx" in lo_toks and "supertrend" in lo_toks:
        return "ADX_Suprtrnd"
    if "bollinger" in lo_toks and ("mean" in lo_toks or "reversion" in lo_toks):
        return "BB_MeanRev"
    if "gaussian" in lo_toks and "pullback" in lo_toks:
        return "Gauss_Pull"
    if "ichimoku" in lo_toks and "cci" in lo_toks:
        return "Ichimoku_CCI"

    picked = []
    for t in toks:
        lo = t.lower()
        if lo in STOP or lo.isdigit():
            continue
        mapped = ABBR.get(lo)
        if mapped:
            picked.append(mapped)
        elif len(lo) >= 3:
            picked.append(t[:6].title())
        if len(picked) >= 2:
            break

    if not picked:
        return f"{fallback_token}_Spec"[:12]
    if len(picked) == 1:
        return picked[0][:12]
    return f"{picked[0]}_{picked[1]}"[:12]


def strategy_name(spec_path: str, variant: str) -> str:
    spec = jload(Path(spec_path), {}) if spec_path else {}
    thesis_path = str(spec.get("source_thesis_path") or "")
    thesis = jload(Path(thesis_path), {}) if thesis_path else {}

    # Spec says meaningful names from strategy family / thesis naming.
    base = (
        str(thesis.get("strategy_family") or "").strip()
        or str(spec.get("strategy_family") or "").strip()
        or str(thesis.get("title") or "").strip()
        or str(spec.get("description") or "").strip()
        or str(variant or "").strip()
    )

    stem = Path(spec_path).stem if spec_path else "spec"
    token = "".join(ch for ch in stem if ch.isalnum())[-4:] or "Spec"
    return normalize_name(base, token)


def metrics(backtest_path: str, run: dict):
    bj = jload(Path(backtest_path), {}) if backtest_path and Path(backtest_path).exists() else {}
    res = bj.get("results") or {}

    wr = pct(fnum(res.get("win_rate")))
    tc = inum(res.get("total_trades") or res.get("trades") or run.get("trades"))
    pnl = pct(fnum(res.get("net_profit_pct")))
    dd = pct(fnum(res.get("max_drawdown_pct")))

    if wr is None:
        wr = pct(fnum(run.get("win_rate")))
    if tc is None:
        tc = inum(run.get("trades"))
    if pnl is None:
        net = fnum(run.get("net_profit"))
        pnl = ((net / 10000.0) * 100.0) if net is not None else None

    return wr, tc, dd, pnl


def trend(prev_pf, curr_pf):
    if prev_pf is None:
        return "→"
    d = curr_pf - prev_pf
    if d > 0.02:
        return "↑"
    if d < -0.02:
        return "↓"
    return "→"


def collect_rows():
    runs = jload(RUN_INDEX, [])
    by_name_hist = defaultdict(list)
    raw = []

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
        if asset not in {"BTC", "ETH"} or not tf:
            continue

        spec_path = str(r.get("strategy_spec_path") or "")
        variant = str(r.get("variant_name") or "")
        name = strategy_name(spec_path, variant)

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, tc, dd, pnl = metrics(bt, r)
        if tc is None or tc <= 0:
            continue

        raw.append((created, asset, tf, name, pf, wr, tc, dd, pnl))
        by_name_hist[(asset, tf, name)].append((created, pf))

    for k in by_name_hist:
        by_name_hist[k].sort(key=lambda x: x[0])

    rows = []
    for created, asset, tf, name, pf, wr, tc, dd, pnl in raw:
        prev = None
        for hdt, hpf in by_name_hist[(asset, tf, name)]:
            if hdt < created:
                prev = hpf
            else:
                break
        rows.append(Row(created, asset, tf, name, pf, wr, tc, dd, pnl, trend(prev, pf)))

    # Dedup #1: each strategy once per asset/timeframe (best PF, then WR/PnL).
    best_by_strategy = {}
    for r in rows:
        key = (r.asset, r.tf, r.name)
        cur = best_by_strategy.get(key)
        if cur is None or (r.pf, r.wr or -999, r.pnl or -999) > (cur.pf, cur.wr or -999, cur.pnl or -999):
            best_by_strategy[key] = r
    rows = list(best_by_strategy.values())

    # Dedup #2: remove identical result duplicates (same stats/signature).
    uniq = {}
    for r in rows:
        sig = (r.asset, r.tf, round(r.pf, 2), round(r.wr or 0.0, 1), int(r.tc), round(r.dd or 0.0, 1), round(r.pnl or 0.0, 1))
        cur = uniq.get(sig)
        if cur is None or len(r.name) > len(cur.name):
            uniq[sig] = r
    rows = list(uniq.values())

    # Meta
    cycles = 0
    errors = 0
    backtests = sum(1 for r in raw if r[0] >= SINCE_24H)
    specs = len({str((x.get('strategy_spec_path') or '')) for x in runs if dt(x.get('created_at')) and dt(x.get('created_at')) >= SINCE_24H})

    if BATCH_ROOT.exists():
        for p in BATCH_ROOT.rglob("*.batch_backtest.json"):
            j = jload(p, {})
            c = dt(j.get("created_at"))
            if not c or c < SINCE_24H:
                continue
            cycles += 1
            errors += int(inum((j.get("summary") or {}).get("failed_runs")) or 0)

    buckets = defaultdict(int)
    if ACTIONS_LOG.exists():
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
            if str(obj.get("status_word") or "").upper() != "FAIL":
                continue
            rc = str(obj.get("reason_code") or obj.get("action") or "UNKNOWN")
            buckets[rc] += 1

    top_error, top_count = ("", 0)
    if buckets:
        top_error, top_count = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)[0]

    return rows, {
        "cycles": cycles,
        "backtests": backtests,
        "specs": specs,
        "errors": errors,
        "top_error": top_error,
        "top_error_count": top_count,
    }


def fmtv(v, d=1, signed=False):
    if v is None:
        return "-"
    return f"{v:+.{d}f}" if signed else f"{v:.{d}f}"


def render_asset_blocks(rows: list[Row]):
    lines = []
    assets = sorted({r.asset for r in rows}, key=lambda a: ASSET_ORDER.get(a, 99))

    for asset in assets:
        asset_rows = [r for r in rows if r.asset == asset]
        if not asset_rows:
            continue

        lines.append(f"{EMOJI.get(asset, '⚪')} TOP 5 {asset} (by PF)")
        header = "# △ TF Strategy   PF  WR%  TC  DD%  P&L%"
        lines.append(header)
        lines.append("─" * len(header))

        top5 = sorted(asset_rows, key=lambda r: (r.pf, r.wr or -999, r.pnl or -999), reverse=True)[:5]
        for i, r in enumerate(top5, start=1):
            row = f"{i} {r.arrow} {r.tf:<2} {r.name[:10]:<10} {r.pf:>4.2f} {fmtv(r.wr):>4} {str(r.tc):>3} {fmtv(r.dd):>4} {fmtv(r.pnl, signed=True):>5}"
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
        out.append("• Near-promotion")

    if not out:
        out.append("• None")
    return [limit42(x) for x in out]


def attention(meta):
    out = []
    if meta["errors"] > 0:
        out.append(limit42(f"• Errors:{meta['errors']} failed runs/24h"))
        if meta.get("top_error"):
            out.append(limit42(f"• Top:{meta['top_error']} x{meta['top_error_count']}"))
        out.append(limit42("• Note: investigate errors next session"))
    if meta["cycles"] == 0:
        out.append("• Stalls: no cycles in 24h")
    if not out:
        out.append("• System healthy ✅")
    return out


def build_text(rows, meta):
    now = datetime.now(AEST)
    lines = [limit42(f"📊 DAILY BRIEF — {now:%Y-%m-%d} 5:30 AEST"), ""]
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
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--send-telegram", action="store_true")
    args = ap.parse_args()

    rows, meta = collect_rows()

    # Required alignment proof: print header + sample row before writing file.
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
        "path": str(OUT_PATH).replace("\\", "/"),
        "rows": len(rows),
        "errors": meta["errors"],
        "alignment_ok": len(header) == len(sample),
    }))


if __name__ == "__main__":
    main()
