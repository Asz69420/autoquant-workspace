"""
Overfitting analysis for high-PF backtests.
Checks:
1. TRADE CLUSTERING: Are winning trades concentrated in a narrow time window?
2. SINGLE-TRADE DOMINANCE: Does 1-2 trades account for >50% of total profit?
3. REGIME CONCENTRATION: Are all trades in one regime type only?
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

def load_trades(trade_list_path):
    with open(os.path.join(WORKSPACE, trade_list_path)) as f:
        data = json.load(f)
    return data['trades']

def parse_dt(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

def analyze_overfit(name, trades, pf, total_trades, dd):
    print('=' * 80)
    print('STRATEGY: %s' % name)
    print('PF=%.3f | Trades=%d | DD=%.1f%%' % (pf, total_trades, dd))
    print('=' * 80)

    if not trades:
        print('  NO TRADES')
        return

    # Separate winners and losers
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] <= 0]

    total_profit = sum(t['pnl'] for t in winners)
    total_loss = sum(abs(t['pnl']) for t in losers)
    net_pnl = sum(t['pnl'] for t in trades)

    print('\n--- BASIC STATS ---')
    print('  Winners: %d (%.1f%%)' % (len(winners), 100*len(winners)/len(trades)))
    print('  Losers:  %d (%.1f%%)' % (len(losers), 100*len(losers)/len(trades)))
    print('  Total gross profit: $%.2f' % total_profit)
    print('  Total gross loss:   $%.2f' % total_loss)
    print('  Net PnL:            $%.2f' % net_pnl)

    # ===== CHECK 1: SINGLE-TRADE DOMINANCE =====
    print('\n--- CHECK 1: SINGLE-TRADE DOMINANCE ---')
    sorted_winners = sorted(winners, key=lambda t: t['pnl'], reverse=True)

    if total_profit > 0:
        # Top 1 trade
        top1_pnl = sorted_winners[0]['pnl']
        top1_pct = 100 * top1_pnl / total_profit
        print('  Top 1 winner: $%.2f (%.1f%% of gross profit, %.1f%% pnl_pct)' % (
            top1_pnl, top1_pct, sorted_winners[0]['pnl_pct']))
        print('    Entry: %s | Exit: %s | Side: %s | Regime: %s' % (
            sorted_winners[0]['entry_time'], sorted_winners[0]['exit_time'],
            sorted_winners[0]['side'], sorted_winners[0]['entry_regime']))

        # Top 2 trades
        if len(sorted_winners) >= 2:
            top2_pnl = sorted_winners[0]['pnl'] + sorted_winners[1]['pnl']
            top2_pct = 100 * top2_pnl / total_profit
            print('  Top 2 winners: $%.2f (%.1f%% of gross profit)' % (top2_pnl, top2_pct))
            print('    #2: $%.2f (%.1f%% pnl_pct) Entry: %s Side: %s Regime: %s' % (
                sorted_winners[1]['pnl'], sorted_winners[1]['pnl_pct'],
                sorted_winners[1]['entry_time'], sorted_winners[1]['side'],
                sorted_winners[1]['entry_regime']))

        # Top 3 trades
        if len(sorted_winners) >= 3:
            top3_pnl = sum(t['pnl'] for t in sorted_winners[:3])
            top3_pct = 100 * top3_pnl / total_profit
            print('  Top 3 winners: $%.2f (%.1f%% of gross profit)' % (top3_pnl, top3_pct))

        # Top 5 trades
        if len(sorted_winners) >= 5:
            top5_pnl = sum(t['pnl'] for t in sorted_winners[:5])
            top5_pct = 100 * top5_pnl / total_profit
            print('  Top 5 winners: $%.2f (%.1f%% of gross profit)' % (top5_pnl, top5_pct))

        # Would strategy be profitable without top trade?
        net_without_top1 = net_pnl - sorted_winners[0]['pnl']
        print('  Net PnL WITHOUT top 1 trade: $%.2f (%s)' % (
            net_without_top1, 'STILL PROFITABLE' if net_without_top1 > 0 else 'UNPROFITABLE'))

        if len(sorted_winners) >= 2:
            net_without_top2 = net_pnl - sorted_winners[0]['pnl'] - sorted_winners[1]['pnl']
            print('  Net PnL WITHOUT top 2 trades: $%.2f (%s)' % (
                net_without_top2, 'STILL PROFITABLE' if net_without_top2 > 0 else 'UNPROFITABLE'))

        # FLAG if top 2 > 50%
        if top1_pct > 50:
            print('  >>> FLAG: Top 1 trade = %.1f%% of gross profit (>50%%)' % top1_pct)
        if len(sorted_winners) >= 2 and top2_pct > 50:
            print('  >>> FLAG: Top 2 trades = %.1f%% of gross profit (>50%%)' % top2_pct)

    # ===== CHECK 2: TRADE CLUSTERING =====
    print('\n--- CHECK 2: TRADE CLUSTERING (winning trades temporal distribution) ---')

    if winners:
        # Group winners by quarter
        quarter_profit = defaultdict(float)
        quarter_count = defaultdict(int)
        for t in winners:
            dt = parse_dt(t['entry_time'])
            q = '%d-Q%d' % (dt.year, (dt.month - 1) // 3 + 1)
            quarter_profit[q] += t['pnl']
            quarter_count[q] += 1

        # Group ALL trades by quarter for context
        all_quarter_count = defaultdict(int)
        all_quarter_pnl = defaultdict(float)
        for t in trades:
            dt = parse_dt(t['entry_time'])
            q = '%d-Q%d' % (dt.year, (dt.month - 1) // 3 + 1)
            all_quarter_count[q] += 1
            all_quarter_pnl[q] += t['pnl']

        # Get full date range
        all_dates = [parse_dt(t['entry_time']) for t in trades]
        min_date = min(all_dates)
        max_date = max(all_dates)

        print('  Date range: %s to %s' % (min_date.strftime('%Y-%m-%d'), max_date.strftime('%Y-%m-%d')))
        print('  Winning trade distribution by quarter:')

        # Generate all quarters in range
        quarters = sorted(set(list(quarter_profit.keys()) + list(all_quarter_count.keys())))

        for q in quarters:
            wp = quarter_profit.get(q, 0)
            wc = quarter_count.get(q, 0)
            ac = all_quarter_count.get(q, 0)
            ap = all_quarter_pnl.get(q, 0)
            bar = '#' * int(wp / max(total_profit, 1) * 40) if wp > 0 else ''
            print('    %s: %2d wins / %2d trades | profit: $%8.2f | net: $%8.2f %s' % (
                q, wc, ac, wp, ap, bar))

        # Check concentration: does any single quarter hold >40% of total profit?
        for q in quarters:
            wp = quarter_profit.get(q, 0)
            if total_profit > 0 and wp / total_profit > 0.40:
                print('  >>> FLAG: Quarter %s holds %.1f%% of total gross profit' % (
                    q, 100 * wp / total_profit))

        # Check: is there a 3-month window with >60% of profits?
        # Use monthly granularity
        month_profit = defaultdict(float)
        for t in winners:
            dt = parse_dt(t['entry_time'])
            m = '%d-%02d' % (dt.year, dt.month)
            month_profit[m] += t['pnl']

        months_sorted = sorted(month_profit.keys())
        if len(months_sorted) >= 3:
            max_3m_sum = 0
            max_3m_window = ''
            for i in range(len(months_sorted) - 2):
                s = sum(month_profit[months_sorted[j]] for j in range(i, i+3))
                if s > max_3m_sum:
                    max_3m_sum = s
                    max_3m_window = '%s to %s' % (months_sorted[i], months_sorted[i+2])

            if total_profit > 0:
                pct_3m = 100 * max_3m_sum / total_profit
                print('  Most concentrated 3-month window: %s = $%.2f (%.1f%% of gross profit)' % (
                    max_3m_window, max_3m_sum, pct_3m))
                if pct_3m > 60:
                    print('  >>> FLAG: 3-month window holds %.1f%% of gross profit (>60%%)' % pct_3m)

        # Consecutive losing streaks
        streak = 0
        max_streak = 0
        for t in trades:
            if t['pnl'] <= 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        print('  Max consecutive losing streak: %d trades' % max_streak)

    # ===== CHECK 3: REGIME CONCENTRATION =====
    print('\n--- CHECK 3: REGIME CONCENTRATION ---')

    regime_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'profit': 0.0, 'loss': 0.0})
    for t in trades:
        r = t.get('entry_regime', 'unknown')
        regime_stats[r]['count'] += 1
        if t['pnl'] > 0:
            regime_stats[r]['wins'] += 1
            regime_stats[r]['profit'] += t['pnl']
        else:
            regime_stats[r]['loss'] += abs(t['pnl'])

    for regime in ['trending', 'ranging', 'transitional']:
        s = regime_stats[regime]
        if s['count'] > 0:
            wr = 100 * s['wins'] / s['count']
            pf_r = s['profit'] / s['loss'] if s['loss'] > 0 else float('inf')
            net_r = s['profit'] - s['loss']
            print('  %-14s: %3d trades, %2d wins (%.1f%% WR), PF=%.3f, net=$%.2f' % (
                regime, s['count'], s['wins'], wr, pf_r, net_r))
        else:
            print('  %-14s: 0 trades' % regime)

    # Check: is one regime providing >80% of net profit?
    regime_net = {}
    for regime in ['trending', 'ranging', 'transitional']:
        s = regime_stats[regime]
        regime_net[regime] = s['profit'] - s['loss']

    total_positive_regime_net = sum(v for v in regime_net.values() if v > 0)
    if total_positive_regime_net > 0:
        for regime, net in regime_net.items():
            if net > 0:
                pct = 100 * net / total_positive_regime_net
                if pct > 80:
                    print('  >>> FLAG: %s regime provides %.1f%% of net profit from profitable regimes' % (
                        regime, pct))

    # Check: does any regime have PF < 1 (net negative)?
    for regime in ['trending', 'ranging', 'transitional']:
        s = regime_stats[regime]
        if s['count'] > 5 and s['loss'] > 0:
            pf_r = s['profit'] / s['loss']
            if pf_r < 1.0:
                print('  >>> NOTE: %s regime is net NEGATIVE (PF=%.3f, %d trades)' % (
                    regime, pf_r, s['count']))

    # ===== ADDITIONAL: Exit reason distribution =====
    print('\n--- EXIT REASON DISTRIBUTION ---')
    reason_stats = defaultdict(lambda: {'count': 0, 'pnl': 0.0})
    for t in trades:
        r = t.get('reason', 'unknown')
        reason_stats[r]['count'] += 1
        reason_stats[r]['pnl'] += t['pnl']

    for reason, s in sorted(reason_stats.items()):
        print('  %-10s: %3d trades, net=$%.2f' % (reason, s['count'], s['pnl']))

    # ===== ADDITIONAL: Long vs Short distribution =====
    print('\n--- LONG/SHORT DISTRIBUTION ---')
    side_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0.0})
    for t in trades:
        s = t['side']
        side_stats[s]['count'] += 1
        side_stats[s]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            side_stats[s]['wins'] += 1

    for side in ['long', 'short']:
        s = side_stats[side]
        if s['count'] > 0:
            wr = 100 * s['wins'] / s['count']
            print('  %-6s: %3d trades, %2d wins (%.1f%% WR), net=$%.2f' % (
                side, s['count'], s['wins'], wr, s['pnl']))

    print()


# ===== MAIN ANALYSIS =====

# Strategy 1: Vortex Transition v3a (PF=1.959)
trades1 = load_trades('artifacts/backtests/20260305/hl_20260305_d4ba7fc4.trade_list.json')
analyze_overfit('Vortex Transition v3a (hl_20260305_d4ba7fc4)', trades1, 1.959, 85, 15.37)

# Strategy 2: Vortex Transition v2c (PF=1.868)
trades2 = load_trades('artifacts/backtests/20260305/hl_20260305_42ec5123.trade_list.json')
analyze_overfit('Vortex Transition v2c (hl_20260305_42ec5123)', trades2, 1.868, 84, 12.44)

# Strategy 3: Vortex Transition v3b (PF=1.861)
trades3 = load_trades('artifacts/backtests/20260305/hl_20260305_da2d5191.trade_list.json')
analyze_overfit('Vortex Transition v3b (hl_20260305_da2d5191)', trades3, 1.861, 84, 11.86)

# ===== CROSS-STRATEGY COMPARISON =====
print('=' * 80)
print('CROSS-STRATEGY COMPARISON')
print('=' * 80)

# Are the same trades driving profitability across all 3?
print('\nComparing top winning trades across all 3 strategies:')
for name, trades in [('v3a', trades1), ('v2c', trades2), ('v3b', trades3)]:
    top_wins = sorted([t for t in trades if t['pnl'] > 0], key=lambda t: t['pnl'], reverse=True)[:5]
    print('\n  %s top 5 winners:' % name)
    for t in top_wins:
        print('    $%8.2f | %s -> %s | %s | %s' % (
            t['pnl'], t['entry_time'][:10], t['exit_time'][:10],
            t['side'], t['entry_regime']))

print('\n\nDo all 3 share the same top-profit trades (same entry dates)?')
def top_entries(trades):
    top = sorted([t for t in trades if t['pnl'] > 0], key=lambda t: t['pnl'], reverse=True)[:5]
    return set(t['entry_time'] for t in top)

t1 = top_entries(trades1)
t2 = top_entries(trades2)
t3 = top_entries(trades3)

shared = t1 & t2 & t3
print('  Shared top-5 entry times across ALL 3: %d / 5' % len(shared))
for s in sorted(shared):
    print('    %s' % s)
