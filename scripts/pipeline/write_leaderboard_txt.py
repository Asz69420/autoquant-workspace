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


def short_strategy(name: str, width: int = 18) -> str:
    return name if len(name) <= width else name[: width - 1] + "…"


def norm_pct(v: float | None) -> float | None:
    if v is None:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def pf_trend(prev_pf: float | None, curr_pf: float | None) -> str:
    if prev_pf is None:
        return "NEW"
    if curr_pf is None:
        return "→"
    delta = curr_pf - prev_pf
    if delta > 0.02:
        return "↑"
    if delta < -0.02:
        return "↓"
    return "→"


@dataclass
class Row:
    created_at: datetime
    asset: str
    tf: str
    strategy: str
    strategy_key: str
    pf: float
    wr_pct: float | None
    tc: int
    dd_pct: float | None
    pnl_pct: float | None
    trend: str


def extract_strategy_name(spec_path: str, fallback_variant: str) -> tuple[str, str]:
    p = Path(spec_path)
    fallback = p.stem or fallback_variant or "unknown"
    try:
        j = load_json(Path(spec_path), {})
        fam = str(j.get("strategy_family") or j.get("id") or fallback).strip()
        return fam, fam
    except Exception:
        return fallback, fallback


def metrics_from_backtest(backtest_path: str, run_obj: dict) -> tuple[float | None, float | None, float | None, int | None]:
    wr = None
    dd_pct = None
    pnl_pct = None
    tc = None

    if backtest_path and Path(backtest_path).exists():
        bj = load_json(Path(backtest_path), {})
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
                # infer start equity from net profit percentage: pct = net/start
                pct = net_pct if abs(net_pct) <= 1.0 else (net_pct / 100.0)
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


def collect_rows() -> tuple[list[Row], dict]:
    runs = load_json(RUN_INDEX, [])
    rows: list[Row] = []

    # Build previous-PF chain by strategy key.
    pf_history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    tmp = []
    for r in runs:
        created = parse_dt(r.get("created_at"))
        pf = as_float(r.get("profit_factor"))
        sp = str(r.get("strategy_spec_path") or "")
        variant = str(r.get("variant_name") or "")
        strategy_name, strategy_key = extract_strategy_name(sp, variant)
        tmp.append((r, created, pf, strategy_name, strategy_key))
        if created and pf is not None:
            pf_history[strategy_key].append((created, pf))

    for k in pf_history:
        pf_history[k].sort(key=lambda x: x[0])

    for r, created, pf, strategy_name, strategy_key in tmp:
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

        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, dd_pct, pnl_pct, tc = metrics_from_backtest(bt, r)
        if tc is None or tc <= 0:
            continue

        prev_pf = None
        hist = pf_history.get(strategy_key, [])
        for dt, p in hist:
            if dt < created:
                prev_pf = p
            else:
                break

        rows.append(
            Row(
                created_at=created,
                asset=asset,
                tf=tf,
                strategy=short_strategy(strategy_name, 18),
                strategy_key=strategy_key,
                pf=pf,
                wr_pct=wr,
                tc=tc,
                dd_pct=dd_pct,
                pnl_pct=pnl_pct,
                trend=pf_trend(prev_pf, pf),
            )
        )

    # 24h activity
    cycles = 0
    backtests = 0
    new_specs = set()
    errors = 0

    for row in rows:
        if row.created_at >= SINCE_24H:
            backtests += 1

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
            summary = j.get("summary") or {}
            errors += int(as_int(summary.get("failed_runs")) or 0)

    meta = {
        "cycles": cycles,
        "backtests": backtests,
        "new_specs": len(new_specs),
        "errors": errors,
    }
    return rows, meta


def milestones(rows: list[Row]) -> list[str]:
    out: list[str] = []

    by_strategy = defaultdict(list)
    for r in sorted(rows, key=lambda x: x.created_at):
        by_strategy[r.strategy_key].append(r)

    first_cross = []
    best_records = []
    for sk, arr in by_strategy.items():
        first = next((x for x in arr if x.pf >= 1.0), None)
        if first and first.created_at >= SINCE_24H:
            first_cross.append(f"{short_strategy(sk,16)} PF {first.pf:.2f}")

        best_so_far = -10**9
        for x in arr:
            if x.pf > best_so_far:
                if x.created_at >= SINCE_24H and best_so_far > -10**8:
                    best_records.append(f"{short_strategy(sk,16)} PF {x.pf:.2f}")
                best_so_far = x.pf

    if first_cross:
        out.append("• First PF≥1.0: " + ", ".join(first_cross[:3]))
    if best_records:
        out.append("• New PF records: " + ", ".join(best_records[:3]))

    promoted = []
    if PROMO_ROOT.exists():
        for p in PROMO_ROOT.rglob("*.promotion_run.json"):
            j = load_json(p, {})
            created = parse_dt(j.get("created_at"))
            if not created or created < SINCE_24H:
                continue
            if str(j.get("status") or "").upper() == "OK":
                sp = str(j.get("strategy_spec_artifact_path") or "")
                promoted.append(short_strategy(Path(sp).stem or "promotion", 16))
    if promoted:
        out.append("• Promotions/near-gate: " + ", ".join(promoted[:3]))

    if not out:
        out.append("• None in last 24h")
    return out


def attention(meta: dict) -> list[str]:
    msgs = []
    if meta.get("errors", 0) >= 5:
        msgs.append(f"• Repeated batch errors detected ({meta['errors']} failed runs/24h)")
    if meta.get("backtests", 0) == 0:
        msgs.append("• Starvation warning: no backtests in last 24h")
    if meta.get("cycles", 0) == 0:
        msgs.append("• Stall warning: no batch cycles in last 24h")
    if not msgs:
        msgs.append("• None — system healthy")
    return msgs


def fmt_num(v: float | None, digits: int = 1, signed: bool = False) -> str:
    if v is None:
        return "-"
    if signed:
        return f"{v:+.{digits}f}"
    return f"{v:.{digits}f}"


def render_top(rows: list[Row], asset: str) -> list[str]:
    header = [
        ("🏆 TOP 5 BTC (by PF)" if asset == "BTC" else "🔵 TOP 5 ETH (by PF)"),
        "# TF Strategy            PF   WR%   TC  DD%   P&L%  △",
    ]

    pool = [r for r in rows if r.asset == asset]
    ranked = sorted(pool, key=lambda x: (x.pf, x.wr_pct or -999, x.pnl_pct or -999), reverse=True)

    uniq = []
    seen = set()
    for r in ranked:
        key = (r.tf, r.strategy_key, round(r.pf, 4), round(r.wr_pct or -999, 2), r.tc)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
        if len(uniq) >= 5:
            break

    lines = []
    for i, r in enumerate(uniq, 1):
        lines.append(
            f"{i:<1} {r.tf:<2} {r.strategy:<18} {r.pf:>4.2f} {fmt_num(r.wr_pct,1):>5} {r.tc:>4} {fmt_num(r.dd_pct,1):>5} {fmt_num(r.pnl_pct,1,True):>6} {r.trend:>3}"
        )

    if not lines:
        lines.append("- no backtested rows")

    return header + lines


def build_report_text(rows: list[Row], meta: dict) -> str:
    now_local = datetime.now(AEST)
    title = f"📊 DAILY BRIEF — {now_local.strftime('%Y-%m-%d')} 5:30 AM AEST"

    lines = [title, ""]
    lines.extend(render_top(rows, "BTC"))
    lines.append("")
    lines.extend(render_top(rows, "ETH"))
    lines.append("")
    lines.append("⚡ 24H ACTIVITY")
    lines.append(f"Cycles: {meta['cycles']} | Backtests: {meta['backtests']} | New specs: {meta['new_specs']} | Errors: {meta['errors']}")
    lines.append("")
    lines.append("🎯 MILESTONES")
    lines.extend(milestones(rows))
    lines.append("")
    lines.append("⚠️ ATTENTION")
    lines.extend(attention(meta))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    rows, meta = collect_rows()
    text = build_report_text(rows, meta)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")

    if "<pre>" in text.lower():
        emit_fail("LEADERBOARD_PLACEHOLDER_DETECTED", "Placeholder token found in leaderboard.txt")
        print(json.dumps({"ok": False, "reason_code": "LEADERBOARD_PLACEHOLDER_DETECTED", "path": str(OUT_PATH).replace("\\", "/")}))
        return 2

    if args.send_telegram:
        send_file_to_telegram(OUT_PATH)

    print(
        json.dumps(
            {
                "ok": True,
                "path": str(OUT_PATH).replace("\\", "/"),
                "rows_considered": len(rows),
                "cycles_24h": meta["cycles"],
                "backtests_24h": meta["backtests"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
