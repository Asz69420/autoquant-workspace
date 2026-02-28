#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / "artifacts" / "library" / "RUN_INDEX.json"
OUT_PATH = ROOT / "artifacts" / "reports" / "daily_intel.txt"
ACTIONS_LOG = ROOT / "data" / "logs" / "actions.ndjson"
PROMO_ROOT = ROOT / "artifacts" / "promotions"

AEST = ZoneInfo("Australia/Brisbane")
NOW_UTC = datetime.now(timezone.utc)
SINCE_24H = NOW_UTC - timedelta(hours=24)

TF_ORDER = {"4h": 0, "1h": 1, "15m": 2}
ASSET_ORDER = {"BTC": 0, "ETH": 1}
EMOJI = {"BTC": "🟠", "ETH": "🔵"}
MAX_WIDTH = 42

# Locked alignment format (header uses the exact same format string)
FMT = "{arrow:<1} {name:<12} {pf:>4} {wr:>4} {tc:>3} {dd:>4} {pnl:>5}"
MIN_TRADES = 50

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
    "ema": "EMA",
    "sma": "SMA",
    "rsi": "RSI",
    "atr": "ATR",
    "macd": "MACD",
}
STOP = {"strategy", "thesis", "spec", "variant", "entry", "exit", "generated", "model"}


@dataclass
class Row:
    created: datetime
    asset: str
    tf: str
    name: str
    key: str
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


def to_dt(v):
    if not v:
        return None
    s = str(v).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


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


def pct(v):
    if v is None:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def limit42(s: str) -> str:
    return s if len(s) <= MAX_WIDTH else s[:MAX_WIDTH]


def build_name(spec_path: str, variant: str) -> tuple[str, str]:
    spec = jload(Path(spec_path), {}) if spec_path else {}
    thesis_path = str(spec.get("source_thesis_path") or "")
    thesis = jload(Path(thesis_path), {}) if thesis_path else {}

    raw = (
        str(thesis.get("title") or "").strip()
        or str(spec.get("description") or "").strip()
        or str(spec.get("strategy_family") or "").strip()
        or str(thesis.get("strategy_family") or "").strip()
        or str(variant or "").strip()
    )

    cleaned = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in raw)
    toks = [t for t in cleaned.replace("-", " ").replace("_", " ").split() if t]
    lo_toks = [t.lower() for t in toks]

    # Prefer descriptive aliases over generic/person names.
    if "baseline" in lo_toks and "exploit" in lo_toks:
        name = "Base_Exploit"
        return name, name.lower()
    if "multi" in lo_toks and "timeframe" in lo_toks:
        name = "MTF_Trend"
        return name, name.lower()

    picks = []
    banned = {"soheil", "baseline", "multi", "timeframe"}
    for t in toks:
        lo = t.lower()
        if lo in STOP or lo.isdigit() or lo in banned:
            continue
        picks.append(ALIAS.get(lo, t[:6].title()))
        if len(picks) >= 2:
            break

    if picks:
        name = (picks[0] if len(picks) == 1 else f"{picks[0]}_{picks[1]}")[:12]
    else:
        stem = Path(spec_path).stem if spec_path else "spec"
        m = re.findall(r"[0-9a-fA-F]{4,}", stem)
        token = (m[-1][:4] if m else ("".join(ch for ch in stem if ch.isalnum())[-4:] or "Spec"))
        name = f"{token}_Spec"[:12]

    if "soheil" in name.lower():
        name = "MTF_Alpha"

    key = name.lower()
    return name, key


def trend(prev_pf: float | None, curr_pf: float) -> str:
    if prev_pf is None:
        return "○"
    d = curr_pf - prev_pf
    if d > 0.02:
        return "↑"
    if d < -0.02:
        return "↓"
    return "→"


def metrics(backtest_path: str, run: dict):
    bj = jload(Path(backtest_path), {}) if backtest_path and Path(backtest_path).exists() else {}
    res = bj.get("results") or {}

    wr = pct(fnum(res.get("win_rate") or run.get("win_rate")))
    tc = inum(res.get("total_trades") or res.get("trades") or run.get("trades"))
    dd = pct(fnum(res.get("max_drawdown_pct") or run.get("max_drawdown_pct")))
    pnl = pct(fnum(res.get("net_profit_pct") or run.get("net_profit_pct")))

    # Fallback when max_drawdown_pct is missing: derive from absolute max_drawdown and inferred start equity.
    if dd is None:
        dd_abs = fnum(res.get("max_drawdown") or res.get("max_dd") or res.get("drawdown") or run.get("max_drawdown"))
        net_abs = fnum(res.get("net_profit") or run.get("net_profit"))
        net_pct_raw = fnum(res.get("net_profit_pct") or run.get("net_profit_pct"))
        if dd_abs is not None and net_abs is not None and net_pct_raw not in (None, 0):
            net_frac = net_pct_raw if abs(net_pct_raw) <= 1 else (net_pct_raw / 100.0)
            if net_frac:
                start_equity = net_abs / net_frac
                if start_equity:
                    dd = (dd_abs / abs(start_equity)) * 100.0
        elif dd_abs is not None:
            # Last-resort assumption when only absolute drawdown is available.
            dd = (dd_abs / 10000.0) * 100.0

    if pnl is None:
        net = fnum(run.get("net_profit"))
        pnl = (net / 10000.0) * 100.0 if net is not None else None

    return wr, tc, dd, pnl


def collect_rows():
    runs = jload(RUN_INDEX, [])
    staged = []
    hist = defaultdict(list)

    for r in runs:
        created = to_dt(r.get("created_at"))
        pf = fnum(r.get("profit_factor"))
        if not created or pf is None:
            continue

        ds = r.get("datasets_tested") or []
        if not ds:
            continue
        d = ds[0] if isinstance(ds, list) else ds
        asset = str(d.get("symbol") or "").upper().strip()
        tf = str(d.get("timeframe") or "").lower().strip()
        if asset not in {"BTC", "ETH"} or tf not in TF_ORDER:
            continue

        spec_path = str(r.get("strategy_spec_path") or "")
        variant = str(r.get("variant_name") or "")
        name, key = build_name(spec_path, variant)

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, tc, dd, pnl = metrics(bt, r)
        if tc is None or tc < MIN_TRADES:
            continue

        staged.append((created, asset, tf, name, key, pf, wr, tc, dd, pnl))
        hist[(asset, tf, key)].append((created, pf))

    for k in hist:
        hist[k].sort(key=lambda x: x[0])

    rows: list[Row] = []
    for created, asset, tf, name, key, pf, wr, tc, dd, pnl in staged:
        prev = None
        for hdt, hpf in hist[(asset, tf, key)]:
            if hdt < created:
                prev = hpf
            else:
                break
        rows.append(Row(created, asset, tf, name, key, pf, wr, tc, dd, pnl, trend(prev, pf)))

    # Dedup 1: each strategy once (best) per asset/timeframe.
    best = {}
    for r in rows:
        k = (r.asset, r.tf, r.key)
        cur = best.get(k)
        if cur is None or (r.pf, r.wr or -999, r.pnl or -999) > (cur.pf, cur.wr or -999, cur.pnl or -999):
            best[k] = r
    rows = list(best.values())

    # Dedup 2: collapse repeated identical results.
    uniq = {}
    for r in rows:
        sig = (r.asset, r.tf, round(r.pf, 2), round(r.wr or 0.0, 1), int(r.tc), round(r.dd or 0.0, 1), round(r.pnl or 0.0, 1))
        if sig not in uniq:
            uniq[sig] = r
    rows = list(uniq.values())

    return rows


def format_v(v, d=1, signed=False):
    if v is None:
        return "-"
    return f"{v:+.{d}f}" if signed else f"{v:.{d}f}"


def render_tables(rows: list[Row]) -> list[str]:
    lines: list[str] = []
    assets = sorted({r.asset for r in rows}, key=lambda a: ASSET_ORDER.get(a, 99))

    header = FMT.format(arrow="△", name="Strategy", pf="PF", wr="WR%", tc="TC", dd="DD%", pnl="P&L%")
    width = min(MAX_WIDTH, len(header))

    for asset in assets:
        lines.append(f"{EMOJI.get(asset, '⚪')} {asset}")
        lines.append(limit42(header))

        a_rows = [r for r in rows if r.asset == asset]
        for tf in sorted({r.tf for r in a_rows}, key=lambda x: TF_ORDER.get(x, 99)):
            t_rows = [r for r in a_rows if r.tf == tf]
            top3 = sorted(t_rows, key=lambda r: (r.pf, r.wr or -999, r.pnl or -999), reverse=True)[:3]
            if not top3:
                continue

            prefix = f"○── {tf} "
            lines.append(limit42(prefix + "─" * max(0, width - len(prefix))))

            for r in top3:
                row = FMT.format(
                    arrow=r.arrow,
                    name=r.name[:12],
                    pf=f"{r.pf:.2f}",
                    wr=format_v(r.wr),
                    tc=str(r.tc),
                    dd=format_v(r.dd),
                    pnl=format_v(r.pnl, signed=True),
                )
                lines.append(limit42(row))

        lines.append("")

    return lines


def collect_activity(rows: list[Row]) -> dict:
    backtests = sum(1 for r in rows if r.created >= SINCE_24H)

    runs = jload(RUN_INDEX, [])
    specs = len({str(r.get("strategy_spec_path") or "") for r in runs if (to_dt(r.get("created_at")) or NOW_UTC) >= SINCE_24H})

    fail_buckets = defaultdict(int)
    if ACTIONS_LOG.exists():
        for line in ACTIONS_LOG.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            if not line.strip().startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            t = to_dt(obj.get("ts_iso") or obj.get("created_at"))
            if not t or t < SINCE_24H:
                continue
            if str(obj.get("status_word") or "").upper() != "FAIL":
                continue
            rc = str(obj.get("reason_code") or obj.get("action") or "UNKNOWN")
            fail_buckets[rc] += 1

    fail_total = sum(fail_buckets.values())
    top_error, top_count = ("", 0)
    if fail_buckets:
        top_error, top_count = sorted(fail_buckets.items(), key=lambda kv: kv[1], reverse=True)[0]

    # Activity cycles via promotion runs within 24h (best available signal).
    cycles = 0
    if PROMO_ROOT.exists():
        for p in PROMO_ROOT.rglob("*.promotion_run.json"):
            j = jload(p, {})
            t = to_dt(j.get("created_at"))
            if t and t >= SINCE_24H:
                cycles += 1

    return {
        "cycles": cycles,
        "backtests": backtests,
        "specs": specs,
        "fail_total": fail_total,
        "top_error": top_error,
        "top_count": top_count,
    }


def milestones(rows: list[Row]) -> list[str]:
    out: list[str] = []
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
            t = to_dt(j.get("created_at"))
            if t and t >= SINCE_24H and str(j.get("status") or "").upper() == "OK":
                near = True
                break
    if near:
        out.append("• Near-promotion")

    if not out:
        out.append("• None")
    return [limit42(x) for x in out]


def attention(meta: dict) -> list[str]:
    if meta["fail_total"] <= 0:
        return ["• System healthy ✅"]
    out = [limit42(f"• FAIL errors:{meta['fail_total']}/24h")]
    if meta["top_error"]:
        out.append(limit42(f"• Top:{meta['top_error']} x{meta['top_count']}"))
    return out


def _read_error_summary() -> list[str]:
    """Read last 24h errors from action log."""
    import time
    log_path = Path(__file__).resolve().parents[2] / "data" / "logs" / "actions.ndjson"
    if not log_path.exists():
        return ["(no action log found)"]
    try:
        cutoff = time.time() - 86400
        errors = {}
        for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("ts", 0)
                if isinstance(ts, str):
                    from datetime import datetime as _dt
                    ts = _dt.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                if ts < cutoff:
                    continue
                status = str(entry.get("status_word", "")).upper()
                if status in ("FAIL", "ERROR", "BLOCKED"):
                    reason = entry.get("reason_code") or entry.get("summary", "unknown")[:40]
                    errors[reason] = errors.get(reason, 0) + 1
            except Exception:
                continue
        if not errors:
            return [" No errors in last 24h"]
        sorted_errors = sorted(errors.items(), key=lambda x: -x[1])[:5]
        return [f" {reason}: {count}x" for reason, count in sorted_errors]
    except Exception:
        return ["(error reading log)"]


def _read_advisory_suggestions() -> list[str]:
    """Pull the Suggestions For Asz section from Quandalf's advisory."""
    advisory_path = Path(__file__).resolve().parents[2] / "docs" / "claude-reports" / "STRATEGY_ADVISORY.md"
    if not advisory_path.exists():
        return ["(no advisory available)"]
    try:
        text = advisory_path.read_text(encoding="utf-8")
        lines_out = []
        in_section = False
        for line in text.split("\n"):
            if "suggestions for asz" in line.lower():
                in_section = True
                continue
            if in_section and line.startswith("#"):
                break
            if in_section and line.strip():
                clean = line.strip().lstrip("- ").lstrip("* ")
                if clean:
                    lines_out.append(f" {clean}")
        return lines_out[:5] if lines_out else ["(no suggestions in latest advisory)"]
    except Exception:
        return ["(advisory read error)"]


def build_text(rows: list[Row], meta: dict) -> str:
    now = datetime.now(AEST)
    lines = [limit42(f"📊 DAILY INTEL — {now:%Y-%m-%d} 5:30 AEST"), ""]
    lines += render_tables(rows)

    lines += [
        "⚡ 24H ACTIVITY",
        limit42(f"Cycles:{meta['cycles']} Backtests:{meta['backtests']} Specs:{meta['specs']} Errors:{meta['fail_total']}"),
        "",
        "🎯 MILESTONES",
    ]
    lines += milestones(rows)
    lines += ["", "⚠️ ATTENTION"]
    lines += attention(meta)
    lines += ["", "⚡ ERRORS (24h)"]
    lines += _read_error_summary()
    # Balrog violations
    balrog_dir = Path(__file__).resolve().parents[2] / "data" / "logs" / "balrog"
    if balrog_dir.exists():
        balrog_logs = sorted(balrog_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        violation_count = 0
        for bl in balrog_logs:
            violation_count += bl.read_text(encoding="utf-8").count("❌")
        if violation_count > 0:
            lines.append(f" 🔥 Balrog: {violation_count} violations in last 5 checks")
        else:
            lines.append(" 🔥 Balrog: all clear")
    lines += ["", "🧙 QUANDALF SUGGESTS"]
    lines += _read_advisory_suggestions()
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

    rows = collect_rows()
    meta = collect_activity(rows)

    # Required alignment printout before write.
    header = FMT.format(arrow="△", name="Strategy", pf="PF", wr="WR%", tc="TC", dd="DD%", pnl="P&L%")
    sample = FMT.format(arrow="↑", name="ADX_Suprtrnd", pf="1.09", wr="34.3", tc="172", dd="2.5", pnl="+1.8")
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
        "fail_errors": meta["fail_total"],
        "alignment_ok": len(header) == len(sample),
    }))


if __name__ == "__main__":
    main()
