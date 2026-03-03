#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / "artifacts" / "library" / "RUN_INDEX.json"
OUT_PATH = ROOT / "artifacts" / "reports" / "leaderboard.txt"
BATCH_ROOT = ROOT / "artifacts" / "batches"
PROMO_ROOT = ROOT / "artifacts" / "promotions"
AEST = ZoneInfo("Australia/Brisbane")
NOW_UTC = datetime.now(timezone.utc)
SINCE_24H = NOW_UTC - timedelta(hours=24)


ALIASES = {
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
    "rsi": "RSI",
    "macd": "MACD",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def as_float(v):
    try:
        return float(v)
    except Exception:
        return None


def as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def parse_dt(v: str | None) -> datetime | None:
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def norm_pct(v: float | None) -> float | None:
    if v is None:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def to_alias(title: str, max_len: int = 12) -> str:
    raw = "".join(ch if ch.isalnum() or ch in " _-" else " " for ch in (title or ""))
    tokens = [t for t in raw.replace("-", " ").replace("_", " ").split() if t]
    if not tokens:
        return "Unknown"

    mapped = []
    for t in tokens:
        k = t.lower()
        mapped.append(ALIASES.get(k, t[:4].title()))

    if len(mapped) >= 2:
        candidate = f"{mapped[0]}_{mapped[1]}"
    else:
        candidate = mapped[0]

    return candidate[:max_len]


def trend(prev_pf: float | None, curr_pf: float) -> str:
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
    created_at: datetime
    asset: str
    tf: str
    strategy_key: str
    strategy_name: str
    pf: float
    wr: float | None
    tc: int
    dd: float | None
    pnl: float | None
    delta: str


def extract_strategy_info(spec_path: str, variant: str) -> tuple[str, str]:
    spec = load_json(Path(spec_path), {}) if spec_path else {}
    thesis_path = str(spec.get("source_thesis_path") or "")
    thesis = load_json(Path(thesis_path), {}) if thesis_path else {}

    # Prefer thesis indicator combos for human-meaningful aliases.
    cand = thesis.get("candidate_signals") if isinstance(thesis, dict) else None
    indicator_pair = []
    if isinstance(cand, list):
        for c in cand:
            if not isinstance(c, dict):
                continue
            ui = c.get("uses_indicators")
            if isinstance(ui, list):
                for x in ui:
                    sx = str(x).strip()
                    if sx:
                        indicator_pair.append(sx)
            if len(indicator_pair) >= 2:
                break

    if len(indicator_pair) >= 2:
        base_name = f"{indicator_pair[0]}_{indicator_pair[1]}"
    else:
        base_name = (
            str(thesis.get("strategy_family") or "").strip()
            or str(thesis.get("title") or "").strip()
            or str(spec.get("strategy_family") or "").strip()
            or variant
            or Path(spec_path).stem
        )

    alias = to_alias(base_name, 12)
    key = alias.lower()
    return alias, key


def backtest_metrics(backtest_path: str, run_obj: dict) -> tuple[float | None, float | None, float | None, int | None]:
    wr = None
    dd_pct = None
    pnl_pct = None
    tc = None

    bj = load_json(Path(backtest_path), {}) if backtest_path and Path(backtest_path).exists() else {}
    res = bj.get("results") or {}

    wr = norm_pct(as_float(res.get("win_rate")))
    tc = as_int(res.get("total_trades") or res.get("trades") or run_obj.get("trades"))
    pnl_pct = norm_pct(as_float(res.get("net_profit_pct")))
    dd_pct = norm_pct(as_float(res.get("max_drawdown_pct")))

    if dd_pct is None:
        dd_raw = as_float(res.get("max_drawdown"))
        net_raw = as_float(res.get("net_profit"))
        net_pct = as_float(res.get("net_profit_pct"))
        if dd_raw is not None and net_raw is not None and net_pct not in (None, 0):
            pct = net_pct if abs(net_pct) <= 1.0 else net_pct / 100.0
            if pct != 0:
                start_equity = net_raw / pct
                if start_equity:
                    dd_pct = (dd_raw / abs(start_equity)) * 100.0

    if wr is None:
        wr = norm_pct(as_float(run_obj.get("win_rate")))
    if tc is None:
        tc = as_int(run_obj.get("trades"))
    if pnl_pct is None:
        net = as_float(run_obj.get("net_profit"))
        if net is not None:
            pnl_pct = (net / 10000.0) * 100.0

    return wr, dd_pct, pnl_pct, tc


def collect_rows() -> tuple[list[Row], dict]:
    runs = load_json(RUN_INDEX, [])
    staged = []
    pf_hist = defaultdict(list)

    for r in runs:
        created = parse_dt(r.get("created_at"))
        pf = as_float(r.get("profit_factor"))
        if created is None or pf is None:
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
        sname, skey = extract_strategy_info(spec_path, variant)

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, dd, pnl, tc = backtest_metrics(bt, r)
        if tc is None or tc <= 0:
            continue

        staged.append((created, asset, tf, skey, sname, pf, wr, tc, dd, pnl))
        pf_hist[skey].append((created, pf))

    for k in pf_hist:
        pf_hist[k].sort(key=lambda x: x[0])

    rows = []
    for created, asset, tf, skey, sname, pf, wr, tc, dd, pnl in staged:
        prev = None
        for dt, p in pf_hist[skey]:
            if dt < created:
                prev = p
            else:
                break
        rows.append(Row(created, asset, tf, skey, sname, pf, wr, tc, dd, pnl, trend(prev, pf)))

    cycles = 0
    backtests = sum(1 for r in rows if r.created_at >= SINCE_24H)
    new_specs = set()
    errors = 0

    for r in runs:
        created = parse_dt(r.get("created_at"))
        if created and created >= SINCE_24H:
            sp = str(r.get("strategy_spec_path") or "")
            if sp:
                new_specs.add(sp)

    if BATCH_ROOT.exists():
        for bf in BATCH_ROOT.rglob("*.batch_backtest.json"):
            j = load_json(bf, {})
            created = parse_dt(j.get("created_at"))
            if not created or created < SINCE_24H:
                continue
            cycles += 1
            errors += int(as_int((j.get("summary") or {}).get("failed_runs")) or 0)

    return rows, {"cycles": cycles, "backtests": backtests, "new_specs": len(new_specs), "errors": errors}


def fmt(v: float | None, d: int = 1, signed: bool = False) -> str:
    if v is None:
        return "-"
    return f"{v:+.{d}f}" if signed else f"{v:.{d}f}"


def render_top(rows: list[Row], asset: str) -> list[str]:
    if asset == "BTC":
        title = "🏆 TOP 5 BTC (by PF)"
    elif asset == "ETH":
        title = "🔵 TOP 5 ETH (by PF)"
    else:
        title = "🟣 TOP 5 SOL (by PF)"
    out = [title, "# △ TF Strategy PF WR% TC DD% P&L%", "──────────────────────────────────────────"]

    pool = [r for r in rows if r.asset == asset]
    # Dedup by displayed strategy alias: keep best PF once.
    best_by_strategy = {}
    for r in pool:
        cur = best_by_strategy.get(r.strategy_name)
        if cur is None or (r.pf, r.wr or -999, r.pnl or -999) > (cur.pf, cur.wr or -999, cur.pnl or -999):
            best_by_strategy[r.strategy_name] = r

    ranked = sorted(best_by_strategy.values(), key=lambda r: (r.pf, r.wr or -999, r.pnl or -999), reverse=True)[:5]

    for i, r in enumerate(ranked, 1):
        # compact mobile row (target <= ~42 chars)
        out.append(f"{i} {r.delta} {r.tf} {r.strategy_name} {r.pf:.2f} {fmt(r.wr)} {r.tc} {fmt(r.dd)} {fmt(r.pnl,1,True)}")

    if not ranked:
        out.append("- no backtested rows")
    return out


def milestones(rows: list[Row]) -> list[str]:
    by_strategy = defaultdict(list)
    for r in sorted(rows, key=lambda x: x.created_at):
        by_strategy[r.strategy_key].append(r)

    lines = []
    first_pf = []
    recs = []
    for sk, arr in by_strategy.items():
        first = next((x for x in arr if x.pf >= 1.0), None)
        if first and first.created_at >= SINCE_24H:
            first_pf.append(f"{first.strategy_name} {first.pf:.2f}")

        best = -999
        for x in arr:
            if x.pf > best:
                if x.created_at >= SINCE_24H and best > -998:
                    recs.append(f"{x.strategy_name} {x.pf:.2f}")
                best = x.pf

    if first_pf:
        lines.append("• PF>1 first-time: " + ", ".join(first_pf[:3]))
    if recs:
        lines.append("• New PF records: " + ", ".join(recs[:3]))

    promoted = []
    if PROMO_ROOT.exists():
        for p in PROMO_ROOT.rglob("*.promotion_run.json"):
            j = load_json(p, {})
            if parse_dt(j.get("created_at")) and parse_dt(j.get("created_at")) >= SINCE_24H:
                if str(j.get("status") or "").upper() == "OK":
                    sp = str(j.get("strategy_spec_artifact_path") or "")
                    alias, _ = extract_strategy_info(sp, "")
                    promoted.append(alias)
    if promoted:
        lines.append("• Promoted/near: " + ", ".join(promoted[:3]))

    if not lines:
        lines.append("• None in last 24h")
    return lines


def attention(meta: dict) -> list[str]:
    msgs = []
    if meta["errors"] >= 5:
        msgs.append(f"• Repeated errors: {meta['errors']} failed runs/24h")
        msgs.append("• Note: investigate error sources next session")
    if meta["backtests"] == 0:
        msgs.append("• Starvation warning: no backtests in 24h")
    if meta["cycles"] == 0:
        msgs.append("• Stall warning: no cycles in 24h")
    if not msgs:
        msgs.append("• None — system healthy")
    return msgs


def build_report(rows: list[Row], meta: dict) -> str:
    now = datetime.now(AEST)
    lines = [f"📊 DAILY BRIEF — {now.strftime('%Y-%m-%d')} 5:30 AEST", ""]
    lines += render_top(rows, "BTC") + [""]
    lines += render_top(rows, "ETH") + [""]
    if any(r.asset == "SOL" for r in rows):
        lines += render_top(rows, "SOL") + [""]
    lines += [
        "⚡ 24H ACTIVITY",
        f"Cycles: {meta['cycles']} | Backtests: {meta['backtests']} | New specs: {meta['new_specs']} | Errors: {meta['errors']}",
        "",
        "🎯 MILESTONES",
    ]
    lines += milestones(rows) + ["", "⚠️ ATTENTION"]
    lines += attention(meta) + [""]
    return "\n".join(lines)


def send_file_to_telegram(path: Path) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CMD_CHAT_ID") or os.getenv("TELEGRAM_LOG_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CMD_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with path.open("rb") as f:
        files = {"document": (path.name, f, "text/plain")}
        data = {"chat_id": chat_id, "caption": "leaderboard.txt"}
        r = requests.post(url, data=data, files=files, timeout=20)
        r.raise_for_status()


def emit_fail(reason_code: str, summary: str) -> None:
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/log_event.py",
                "--run-id",
                f"leaderboard-{reason_code.lower()}",
                "--agent",
                "oQ",
                "--model-id",
                "openai-codex/gpt-5.3-codex",
                "--action",
                "leaderboard_txt",
                "--status-word",
                "FAIL",
                "--status-emoji",
                "❌",
                "--reason-code",
                reason_code,
                "--summary",
                summary,
            ],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send-telegram", action="store_true")
    args = ap.parse_args()

    rows, meta = collect_rows()
    text = build_report(rows, meta)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")

    if "<pre>" in text.lower():
        emit_fail("LEADERBOARD_PLACEHOLDER_DETECTED", "Placeholder token found in leaderboard.txt")
        print(json.dumps({"ok": False, "path": str(OUT_PATH).replace('\\', '/')}))
        return 2

    if args.send_telegram:
        send_file_to_telegram(OUT_PATH)

    print(json.dumps({"ok": True, "path": str(OUT_PATH).replace('\\', '/'), "rows_considered": len(rows), "errors_24h": meta['errors']}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
