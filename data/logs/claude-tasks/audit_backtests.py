#!/usr/bin/env python3
"""
Comprehensive backtest result auditor.
Parses all *.backtest_result.json files from 20260228 and 20260301,
extracts key fields, and produces aggregated audit output.
"""

import json
import glob
import os
import re
import math
from collections import defaultdict

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "artifacts", "backtests")
BASE = os.path.normpath(BASE)

DAYS = ["20260228", "20260301"]

def safe_get(d, *keys, default=None):
    """Safely traverse nested dict."""
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            return default
    return cur

def is_nan_or_none(v):
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return False

def extract_symbol_timeframe(data):
    """Extract symbol and timeframe from dataset_meta or dataset_csv path."""
    for key in ["dataset_meta", "dataset_csv"]:
        path = safe_get(data, "inputs", key, default="")
        if not path:
            continue
        m = re.search(r'hyperliquid[/\\]([A-Za-z0-9]+)[/\\](\w+)[/\\]', path)
        if m:
            return m.group(1), m.group(2)
    return None, None

def parse_file(filepath):
    """Parse a single backtest result JSON file and extract key fields."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = safe_get(data, "results", default={})
    inputs = safe_get(data, "inputs", default={})
    gate = safe_get(data, "gate", default={})
    regime_breakdown = safe_get(results, "regime_breakdown", default={})
    regime_pf = safe_get(results, "regime_pf", default={})

    symbol, timeframe = extract_symbol_timeframe(data)

    rec = {
        "id": safe_get(data, "id", default=None),
        "variant": safe_get(inputs, "variant", default=None),
        "strategy_spec": safe_get(inputs, "strategy_spec", default=None),
        "symbol": symbol,
        "timeframe": timeframe,
        "total_trades": safe_get(results, "total_trades", default=None),
        "profit_factor": safe_get(results, "profit_factor", default=None),
        "win_rate": safe_get(results, "win_rate", default=None),
        "max_drawdown": safe_get(results, "max_drawdown", default=None),
        "max_drawdown_pct": safe_get(results, "max_drawdown_pct", default=None),
        "net_profit": safe_get(results, "net_profit", default=None),
        "regime_breakdown": {
            "trending_trades": safe_get(regime_breakdown, "trending_trades", default=None),
            "ranging_trades": safe_get(regime_breakdown, "ranging_trades", default=None),
            "transitional_trades": safe_get(regime_breakdown, "transitional_trades", default=None),
        },
        "regime_pf": {
            "trending": safe_get(regime_pf, "trending", default=None),
            "ranging": safe_get(regime_pf, "ranging", default=None),
            "transitional": safe_get(regime_pf, "transitional", default=None),
        },
        "gate_pass": safe_get(gate, "gate_pass", default=None),
        "source_file": os.path.basename(filepath),
        "day": None,
    }
    return rec

def main():
    all_results = []
    day_counts = {}

    for day in DAYS:
        day_dir = os.path.join(BASE, day)
        pattern = os.path.join(day_dir, "*.backtest_result.json")
        files = glob.glob(pattern)
        day_counts[day] = len(files)
        for fp in sorted(files):
            try:
                rec = parse_file(fp)
                rec["day"] = day
                all_results.append(rec)
            except Exception as e:
                print(f"  ERROR parsing {fp}: {e}")

    print(f"Total files parsed: {len(all_results)}")
    for day in DAYS:
        print(f"  {day}: {day_counts.get(day, 0)} backtests")

    # 3. overfit_suspects
    overfit_suspects = []
    for r in all_results:
        pf = r.get("profit_factor")
        tt = r.get("total_trades")
        wr = r.get("win_rate")
        variant = (r.get("variant") or "").lower()

        if pf is None or tt is None:
            continue

        reasons = []
        if pf > 2.0 and tt < 30:
            reasons.append("PF>2.0 AND trades<30")
        if wr is not None and wr > 0.70 and "trend" in variant:
            reasons.append("win_rate>0.70 for trend variant")
        if pf > 3.0:
            reasons.append("PF>3.0")

        if reasons:
            overfit_suspects.append({
                "id": r["id"],
                "variant": r["variant"],
                "profit_factor": pf,
                "total_trades": tt,
                "win_rate": wr,
                "reasons": reasons,
                "day": r["day"],
            })

    # 4. zero_trade
    zero_trade = [
        {"id": r["id"], "variant": r["variant"], "day": r["day"], "strategy_spec": r["strategy_spec"]}
        for r in all_results
        if r.get("total_trades") == 0
    ]

    # 5. data_quality_issues
    data_quality_issues = []
    for r in all_results:
        issues = []
        if r.get("max_drawdown") == 0:
            issues.append("max_drawdown==0")
        if r.get("max_drawdown_pct") == 0:
            issues.append("max_drawdown_pct==0")
        tt = r.get("total_trades")
        if tt is not None and tt < 0:
            issues.append("total_trades<0")
        if is_nan_or_none(r.get("net_profit")):
            issues.append("net_profit is null/NaN")
        if issues:
            data_quality_issues.append({
                "id": r["id"],
                "variant": r["variant"],
                "day": r["day"],
                "issues": issues,
            })

    # 6. duplicate_fingerprints
    fingerprint_groups = defaultdict(list)
    for r in all_results:
        pf = r.get("profit_factor")
        tt = r.get("total_trades")
        wr = r.get("win_rate")
        if pf is None or tt is None or wr is None:
            continue
        key = (round(pf, 5), tt, round(wr, 5))
        fingerprint_groups[key].append({
            "id": r["id"],
            "variant": r["variant"],
            "day": r["day"],
            "profit_factor": pf,
            "total_trades": tt,
            "win_rate": wr,
        })
    duplicate_fingerprints = []
    for key, members in fingerprint_groups.items():
        if len(members) >= 2:
            duplicate_fingerprints.append({
                "fingerprint": {
                    "profit_factor": key[0],
                    "total_trades": key[1],
                    "win_rate": key[2],
                },
                "count": len(members),
                "members": members,
            })
    duplicate_fingerprints.sort(key=lambda x: x["count"], reverse=True)

    # 7. high_pf_low_trades
    high_pf_low_trades = [
        {
            "id": r["id"],
            "variant": r["variant"],
            "profit_factor": r["profit_factor"],
            "total_trades": r["total_trades"],
            "day": r["day"],
        }
        for r in all_results
        if r.get("profit_factor") is not None
        and r.get("total_trades") is not None
        and r["profit_factor"] > 1.5
        and r["total_trades"] < 30
    ]

    # 8. regime_single_regime_profitable
    regime_single_regime_profitable = []
    for r in all_results:
        rpf = r.get("regime_pf", {})
        trending = rpf.get("trending")
        ranging = rpf.get("ranging")
        transitional = rpf.get("transitional")

        vals = {"trending": trending, "ranging": ranging, "transitional": transitional}
        non_none = {k: v for k, v in vals.items() if v is not None}
        if len(non_none) < 2:
            continue

        for regime_name, regime_val in non_none.items():
            if regime_val > 1.0:
                others = {k: v for k, v in non_none.items() if k != regime_name}
                if others and all(v < 0.9 for v in others.values()):
                    regime_single_regime_profitable.append({
                        "id": r["id"],
                        "variant": r["variant"],
                        "day": r["day"],
                        "profitable_regime": regime_name,
                        "profitable_regime_pf": regime_val,
                        "other_regime_pfs": others,
                    })
                    break

    # 9. extreme_dd
    extreme_dd = [
        {
            "id": r["id"],
            "variant": r["variant"],
            "max_drawdown_pct": r["max_drawdown_pct"],
            "day": r["day"],
        }
        for r in all_results
        if r.get("max_drawdown_pct") is not None
        and r["max_drawdown_pct"] > 100
    ]

    # Build output
    output = {
        "total_count": day_counts,
        "all_results": all_results,
        "overfit_suspects": overfit_suspects,
        "zero_trade": zero_trade,
        "data_quality_issues": data_quality_issues,
        "duplicate_fingerprints": duplicate_fingerprints,
        "high_pf_low_trades": high_pf_low_trades,
        "regime_single_regime_profitable": regime_single_regime_profitable,
        "extreme_dd": extreme_dd,
    }

    # Write to /tmp/ (on Windows Git Bash this resolves to a temp dir)
    # Also write to workspace for accessibility
    import tempfile
    tmp_dir = tempfile.gettempdir()
    out_path = os.path.join(tmp_dir, "audit_results.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nOutput written to: {out_path}")
    print(f"\n--- SUMMARY ---")
    print(f"Total backtests:                   {len(all_results)}")
    for day in DAYS:
        print(f"  {day}:                          {day_counts.get(day, 0)}")
    print(f"Overfit suspects:                  {len(overfit_suspects)}")
    print(f"Zero-trade results:                {len(zero_trade)}")
    print(f"Data quality issues:               {len(data_quality_issues)}")
    print(f"Duplicate fingerprint groups:      {len(duplicate_fingerprints)}")
    dup_member_total = sum(g["count"] for g in duplicate_fingerprints)
    print(f"  (total members in dup groups):   {dup_member_total}")
    print(f"High PF + low trades (PF>1.5, <30):{len(high_pf_low_trades)}")
    print(f"Single-regime profitable:          {len(regime_single_regime_profitable)}")
    print(f"Extreme drawdown (>100%%):          {len(extreme_dd)}")

    if overfit_suspects:
        print(f"\n--- TOP 10 OVERFIT SUSPECTS (by PF) ---")
        top = sorted(overfit_suspects, key=lambda x: x["profit_factor"], reverse=True)[:10]
        for i, s in enumerate(top, 1):
            print(f"  {i}. {s['id']} | PF={s['profit_factor']:.4f} | trades={s['total_trades']} | WR={s['win_rate']:.4f} | reasons={s['reasons']}")

    if duplicate_fingerprints:
        print(f"\n--- TOP 5 DUPLICATE FINGERPRINT GROUPS ---")
        for i, g in enumerate(duplicate_fingerprints[:5], 1):
            fp = g["fingerprint"]
            print(f"  {i}. PF={fp['profit_factor']} trades={fp['total_trades']} WR={fp['win_rate']} -> {g['count']} members")
            for m in g["members"][:3]:
                print(f"       - {m['id']} ({m['variant']}) [{m['day']}]")
            if g["count"] > 3:
                print(f"       ... and {g['count']-3} more")

    if extreme_dd:
        print(f"\n--- EXTREME DRAWDOWN (>100%) ---")
        top_dd = sorted(extreme_dd, key=lambda x: x["max_drawdown_pct"], reverse=True)[:10]
        for i, d in enumerate(top_dd, 1):
            print(f"  {i}. {d['id']} | DD%={d['max_drawdown_pct']:.2f}% | variant={d['variant']}")

if __name__ == "__main__":
    main()
