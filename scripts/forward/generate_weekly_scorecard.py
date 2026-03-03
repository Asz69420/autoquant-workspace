#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _jload(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _to_dt(v: str | None):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def _read_ndjson(path: Path):
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def _auto_promotion(champions: list[dict], lookback_days: int = 14) -> list[dict]:
    weakest = None
    active = [c for c in champions if str(c.get("status")) in {"active", "watch"}]
    for c in active:
        pf = float((c.get("canonical_backtest") or {}).get("pf") or 0.0)
        if weakest is None or pf < weakest[0]:
            weakest = (pf, c)
    if weakest is None:
        return []

    weak_pf = weakest[0]
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    suggestions = []
    for fp in sorted((ROOT / "artifacts" / "backtests").rglob("*.backtest_result.json"))[-800:]:
        obj = _jload(fp, {})
        created = _to_dt(obj.get("created_at"))
        if created is None or created < cutoff:
            continue
        meta = obj.get("dataset_meta") or {}
        if str(meta.get("symbol") or "").upper() != "ETH":
            continue
        if str(meta.get("timeframe") or "").lower() != "4h":
            continue
        res = obj.get("results") or {}
        pf = float(res.get("profit_factor") or 0.0)
        trades = int(res.get("total_trades") or 0)
        if pf > weak_pf and trades >= 50:
            suggestions.append({
                "backtest_path": str(fp).replace("\\", "/"),
                "profit_factor": pf,
                "trades": trades,
                "weakest_champion_pf": weak_pf,
            })
    uniq = []
    seen = set()
    for s in sorted(suggestions, key=lambda x: x["profit_factor"], reverse=True):
        k = s["backtest_path"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
        if len(uniq) >= 10:
            break
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--champions", default="docs/shared/CHAMPIONS.json")
    ap.add_argument("--log", default="data/forward/FORWARD_LOG.ndjson")
    ap.add_argument("--out-md", default="docs/shared/LEADERBOARD.md")
    ap.add_argument("--out-json", default="data/forward/WEEKLY_SCORECARD.json")
    ap.add_argument("--suggestions-md", default="docs/shared/FORWARD_PROMOTION_SUGGESTIONS.md")
    args = ap.parse_args()

    cfg = _jload(ROOT / args.champions, {})
    champions = cfg.get("champions") or []
    by_id = {str(c.get("id")): c for c in champions}

    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    events = [e for e in _read_ndjson(ROOT / args.log) if (_to_dt(e.get("ts_iso")) or now) >= week_ago]

    stats = defaultdict(lambda: {
        "signals": 0,
        "entries": 0,
        "closes": 0,
        "wins": 0,
        "losses": 0,
        "gross_win": 0.0,
        "gross_loss": 0.0,
        "realized": 0.0,
        "max_dd": 0.0,
        "eq": 10000.0,
        "peak": 10000.0,
        "regimes": defaultdict(int),
    })

    for e in events:
        cid = str(e.get("champion_id") or "")
        if not cid:
            continue
        s = stats[cid]
        reg = str(e.get("regime") or "")
        if reg:
            s["regimes"][reg] += 1
        ev = str(e.get("event"))
        if ev == "SIGNAL_EVAL":
            s["signals"] += 1
        elif ev == "POSITION_OPEN":
            s["entries"] += 1
        elif ev == "POSITION_CLOSE":
            pnl = float(e.get("pnl") or 0.0)
            s["closes"] += 1
            s["realized"] += pnl
            s["eq"] += pnl
            s["peak"] = max(s["peak"], s["eq"])
            dd = ((s["peak"] - s["eq"]) / s["peak"]) * 100.0 if s["peak"] > 0 else 0.0
            s["max_dd"] = max(s["max_dd"], dd)
            if pnl >= 0:
                s["wins"] += 1
                s["gross_win"] += pnl
            else:
                s["losses"] += 1
                s["gross_loss"] += abs(pnl)

    rows = []
    for cid, s in stats.items():
        c = by_id.get(cid, {})
        cb = c.get("canonical_backtest") or {}
        live_pf = (s["gross_win"] / s["gross_loss"]) if s["gross_loss"] > 0 else (999.0 if s["gross_win"] > 0 else 0.0)
        back_pf = float(cb.get("pf") or 0.0)
        drift = ((live_pf / back_pf) - 1.0) * 100.0 if back_pf > 0 else 0.0
        wr = (s["wins"] / s["closes"] * 100.0) if s["closes"] > 0 else 0.0
        verdict = "KEEP"
        if s["max_dd"] > 25.0 or live_pf < 1.2:
            verdict = "WATCH"
        if s["entries"] == 0:
            verdict = "WATCH"

        rows.append({
            "champion_id": cid,
            "strategy_name": c.get("strategy_name", cid),
            "asset": c.get("asset", ""),
            "timeframe": c.get("timeframe", ""),
            "signals": s["signals"],
            "trades": s["closes"],
            "win_rate_pct": round(wr, 2),
            "live_pf": round(live_pf, 4),
            "backtest_pf": round(back_pf, 4),
            "pf_drift_pct": round(drift, 2),
            "max_drawdown_pct": round(s["max_dd"], 2),
            "realized_pnl": round(s["realized"], 2),
            "regime_mix": dict(s["regimes"]),
            "verdict": verdict,
        })

    rows.sort(key=lambda x: x["live_pf"], reverse=True)

    out_json = {
        "generated_at": now.isoformat(),
        "window_days": 7,
        "rows": rows,
    }

    oj = ROOT / args.out_json
    oj.parent.mkdir(parents=True, exist_ok=True)
    oj.write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Forward Leaderboard (Rolling 7d)",
        "",
        "| Champion | Asset | TF | Signals | Trades | Live PF | Backtest PF | Drift % | DD % | PnL | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['strategy_name']} | {r['asset']} | {r['timeframe']} | {r['signals']} | {r['trades']} | {r['live_pf']:.3f} | {r['backtest_pf']:.3f} | {r['pf_drift_pct']:.1f}% | {r['max_drawdown_pct']:.1f}% | {r['realized_pnl']:.2f} | {r['verdict']} |"
        )
    (ROOT / args.out_md).write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    suggestions = _auto_promotion(champions, 14)
    s_lines = ["# Auto-Promotion Suggestions", ""]
    if not suggestions:
        s_lines.append("No qualifying challengers this week.")
    else:
        s_lines.append("Candidates beating weakest active champion PF:")
        s_lines.append("")
        for s in suggestions:
            s_lines.append(f"- PF {s['profit_factor']:.3f} | trades {s['trades']} | {s['backtest_path']}")
    (ROOT / args.suggestions_md).write_text("\n".join(s_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "rows": len(rows), "suggestions": len(suggestions), "leaderboard": args.out_md}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
