import json
from datetime import datetime
from collections import defaultdict

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def analyze_trade_list(filepath, label):
    with open(filepath) as f:
        data = json.load(f)
    trades = data["trades"]
    n = len(trades)

    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"  ID: {data['id']}  |  {n} trades")
    print(f"{'='*80}")

    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in winners)
    gross_loss = abs(sum(t["pnl"] for t in losers))
    net_pnl = sum(t["pnl"] for t in trades)

    print(f"\n  BASIC STATS:")
    print(f"    Winners: {len(winners)}/{n} ({100*len(winners)/n:.1f}%)")
    print(f"    Gross Profit: ${gross_profit:,.2f}  |  Gross Loss: ${gross_loss:,.2f}")
    print(f"    Net PnL: ${net_pnl:,.2f}")
    if gross_loss > 0:
        print(f"    Profit Factor: {gross_profit/gross_loss:.3f}")

    sorted_winners = sorted(winners, key=lambda t: t["pnl"], reverse=True)
    print(f"\n  1. PROFIT CONCENTRATION:")
    if gross_profit > 0:
        for k in [1, 3, 5]:
            top_k = sorted_winners[:min(k, len(sorted_winners))]
            top_k_sum = sum(t["pnl"] for t in top_k)
            pct = 100 * top_k_sum / gross_profit
            print(f"    Top {k} trade(s): ${top_k_sum:,.2f} = {pct:.1f}% of gross profit")
        print(f"\n    Top 5 winning trades:")
        for i, t in enumerate(sorted_winners[:5]):
            print(f"      #{i+1}: ${t['pnl']:,.2f} ({t['pnl_pct']:.1f}%) | {t['entry_time']} -> {t['exit_time']} | {t['side']} | {t['entry_regime']} | {t['reason']}")

    sorted_all = sorted(trades, key=lambda t: t["pnl"], reverse=True)
    top3_pnl = sum(t["pnl"] for t in sorted_all[:3])
    if net_pnl > 0:
        print(f"\n    Top 3 trades as % of NET profit: {100*top3_pnl/net_pnl:.1f}%")
    elif net_pnl < 0:
        print(f"\n    Net PnL is NEGATIVE. Top 3 best trades sum: ${top3_pnl:,.2f}")

    print(f"\n  2. TIME CLUSTERING / DISTRIBUTION:")
    entry_dates = [parse_date(t["entry_time"]) for t in trades]
    min_date = min(entry_dates)
    max_date = max(entry_dates)
    span_days = (max_date - min_date).days
    print(f"    Backtest span: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')} ({span_days} days)")

    quarter_trades = defaultdict(list)
    for t in trades:
        d = parse_date(t["entry_time"])
        q = f"{d.year}-Q{(d.month-1)//3+1}"
        quarter_trades[q].append(t)

    print(f"\n    Quarterly distribution:")
    for q in sorted(quarter_trades.keys()):
        qt = quarter_trades[q]
        q_pnl = sum(t["pnl"] for t in qt)
        q_wins = sum(1 for t in qt if t["pnl"] > 0)
        print(f"      {q}: {len(qt)} trades, {q_wins} wins, PnL=${q_pnl:,.2f}")

    month_set = set()
    for d in entry_dates:
        month_set.add(f"{d.year}-{d.month:02d}")
    all_months = set()
    cur = min_date.replace(day=1)
    while cur <= max_date:
        all_months.add(f"{cur.year}-{cur.month:02d}")
        if cur.month == 12:
            cur = cur.replace(year=cur.year+1, month=1)
        else:
            cur = cur.replace(month=cur.month+1)
    gaps = sorted(all_months - month_set)
    if gaps:
        print(f"\n    Months with ZERO trades: {', '.join(gaps)}")

    print(f"\n  3. STREAK ANALYSIS:")
    max_win_streak = 0
    max_lose_streak = 0
    cur_win = 0
    cur_lose = 0
    for t in trades:
        if t["pnl"] > 0:
            cur_win += 1
            cur_lose = 0
        else:
            cur_lose += 1
            cur_win = 0
        max_win_streak = max(max_win_streak, cur_win)
        max_lose_streak = max(max_lose_streak, cur_lose)
    print(f"    Max winning streak: {max_win_streak}")
    print(f"    Max losing streak: {max_lose_streak}")

    loss_runs = []
    run_len = 0
    run_pnl = 0
    for t in trades:
        if t["pnl"] <= 0:
            run_len += 1
            run_pnl += t["pnl"]
        else:
            if run_len > 0:
                loss_runs.append((run_len, run_pnl))
            run_len = 0
            run_pnl = 0
    if run_len > 0:
        loss_runs.append((run_len, run_pnl))

    worst_runs = sorted(loss_runs, key=lambda x: x[1])[:3]
    print(f"    Worst loss runs:")
    for length, pnl in worst_runs:
        print(f"      {length} consecutive losses, total PnL=${pnl:,.2f}")

    print(f"\n  4. REGIME BREAKDOWN:")
    regime_trades = defaultdict(list)
    for t in trades:
        regime_trades[t["entry_regime"]].append(t)

    for regime in sorted(regime_trades.keys()):
        rt = regime_trades[regime]
        r_wins = [t for t in rt if t["pnl"] > 0]
        r_gp = sum(t["pnl"] for t in r_wins) if r_wins else 0
        r_gl = abs(sum(t["pnl"] for t in rt if t["pnl"] <= 0))
        r_net = sum(t["pnl"] for t in rt)
        r_pf = r_gp / r_gl if r_gl > 0 else float('inf')
        print(f"    {regime}: {len(rt)} trades, {len(r_wins)} wins, GP=${r_gp:,.2f}, GL=${r_gl:,.2f}, PF={r_pf:.3f}, Net=${r_net:,.2f}")
        if regime == "transitional" and r_pf > 5:
            print(f"      *** ANOMALY: Transitional PF={r_pf:.2f} flagged for investigation ***")
            for t in r_wins:
                print(f"          WIN: ${t['pnl']:,.2f} ({t['pnl_pct']:.1f}%) {t['entry_time']} {t['side']} bars={t['bars_held']} reason={t['reason']}")
            for t in rt:
                if t['pnl'] <= 0:
                    print(f"          LOSS: ${t['pnl']:,.2f} ({t['pnl_pct']:.1f}%) {t['entry_time']} {t['side']} bars={t['bars_held']} reason={t['reason']}")

    print(f"\n  5. OVERFITTING FLAGS:")
    flags = []

    if gross_profit > 0:
        top3_gp_pct = 100 * sum(t["pnl"] for t in sorted_winners[:min(3, len(sorted_winners))]) / gross_profit
        if top3_gp_pct > 50:
            flags.append(f"HIGH CONCENTRATION: Top 3 trades = {top3_gp_pct:.1f}% of gross profit")

    if net_pnl > 0 and top3_pnl / net_pnl > 0.8:
        flags.append(f"EXTREME NET DEPENDENCY: Top 3 trades = {100*top3_pnl/net_pnl:.1f}% of net profit")

    win_rate = len(winners) / n
    if gross_loss > 0 and win_rate < 0.3 and gross_profit / gross_loss > 1.5:
        flags.append(f"TAIL DEPENDENCY: Win rate {100*win_rate:.1f}% but PF={gross_profit/gross_loss:.2f}")

    if max_lose_streak >= 8:
        flags.append(f"LONG LOSING STREAK: {max_lose_streak} consecutive losses")

    for regime, rt in regime_trades.items():
        r_wins = [t for t in rt if t["pnl"] > 0]
        r_gp = sum(t["pnl"] for t in r_wins) if r_wins else 0
        r_gl = abs(sum(t["pnl"] for t in rt if t["pnl"] <= 0))
        if r_gl > 0:
            rpf = r_gp / r_gl
            if rpf > 10 and len(rt) < 10:
                flags.append(f"REGIME ANOMALY: {regime} PF={rpf:.2f} on only {len(rt)} trades")

    entry_dates_sorted = sorted(entry_dates)
    for i in range(1, len(entry_dates_sorted)):
        gap = (entry_dates_sorted[i] - entry_dates_sorted[i-1]).days
        if gap > 60:
            flags.append(f"TIME GAP: {gap} days between trades ({entry_dates_sorted[i-1].strftime('%Y-%m-%d')} to {entry_dates_sorted[i].strftime('%Y-%m-%d')})")

    if len(sorted_winners) >= 3:
        top3_dates = [parse_date(t["entry_time"]) for t in sorted_winners[:3]]
        top3_span = (max(top3_dates) - min(top3_dates)).days
        if top3_span < 90 and span_days > 365:
            flags.append(f"TEMPORAL CLUSTERING: Top 3 winners all within {top3_span} days (backtest={span_days} days)")

    if gross_profit > 0:
        max_trade = sorted_winners[0]["pnl"]
        if max_trade / gross_profit > 0.25:
            flags.append(f"SINGLE TRADE DOMINANCE: Best trade = {100*max_trade/gross_profit:.1f}% of gross profit (${max_trade:,.2f})")

    tp_wins = [t for t in winners if t["reason"] == "tp"]
    non_tp_wins = [t for t in winners if t["reason"] != "tp"]
    tp_profit = sum(t["pnl"] for t in tp_wins)
    non_tp_profit = sum(t["pnl"] for t in non_tp_wins)
    if gross_profit > 0:
        print(f"\n    TP-sourced profit: ${tp_profit:,.2f} ({100*tp_profit/gross_profit:.1f}%)")
        print(f"    Non-TP profit: ${non_tp_profit:,.2f} ({100*non_tp_profit/gross_profit:.1f}%)")
        if tp_profit > 0 and 100*tp_profit/gross_profit > 80:
            flags.append(f"TP DEPENDENCY: {100*tp_profit/gross_profit:.1f}% of gross profit from TP exits only")

    if not flags:
        flags.append("No major overfitting flags detected.")

    for f in flags:
        print(f"    *** {f}")

    return flags

files = [
    ("C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_db2af052.trade_list.json",
     "1. Vortex v3a ETH 4h | PF=2.034 | 84 trades | TOP RESULT"),
    ("C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_be4177e1.trade_list.json",
     "2. KAMA Stoch v1 ETH 1h | PF=1.857 | 42 trades"),
    ("C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_4409e998.trade_list.json",
     "3. Vortex v2c ETH 4h | PF=1.892 | 84 trades"),
    ("C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_880e9fc2.trade_list.json",
     "4. KAMA Stoch v1 ETH 4h | PF=0.399 | 43 trades | TRANSITIONAL ANOMALY CHECK"),
    ("C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_1147a757.trade_list.json",
     "5. KAMA Stoch v2 ETH 1h | PF=1.709 | 42 trades"),
]

all_flags = {}
for filepath, label in files:
    flags = analyze_trade_list(filepath, label)
    all_flags[label] = flags

print(f"\n{'='*80}")
print(f"  CROSS-STRATEGY OVERFITTING SUMMARY")
print(f"{'='*80}")
for label, flags in all_flags.items():
    print(f"\n  {label}:")
    for f in flags:
        print(f"    - {f}")
