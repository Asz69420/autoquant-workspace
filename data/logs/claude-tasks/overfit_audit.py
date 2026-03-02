"""
Overfitting audit for 20260228 trade lists.
Analyzes trade concentration, time clustering, and zero-trade variants.
"""
import json
import os
import glob
from datetime import datetime
from collections import defaultdict

base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228'

# Step 1: Parse all backtest results
print("=" * 80)
print("STEP 1: BACKTEST RESULT OVERVIEW")
print("=" * 80)

bt_files = glob.glob(os.path.join(base, '*.backtest_result.json'))
bt_data = {}
for f in bt_files:
    try:
        d = json.load(open(f))
        r = d.get('results', d)
        h = os.path.basename(f).replace('.backtest_result.json', '')
        bt_data[h] = {
            'pf': r.get('profit_factor', 0),
            'trades': r.get('total_trades', 0),
            'net_profit': r.get('net_profit', 0),
            'win_rate': r.get('win_rate', 0),
            'max_dd': r.get('max_drawdown', 0),
        }
    except Exception as e:
        pass

sorted_by_pf = sorted(bt_data.items(), key=lambda x: x[1]['pf'], reverse=True)

print(f"\nTotal backtest result files: {len(bt_data)}")
print(f"\nTOP 30 by Profit Factor:")
for h, d in sorted_by_pf[:30]:
    print(f"  {h}  PF={d['pf']:.5f}  Trades={d['trades']}  WR={d['win_rate']:.3f}  NetP={d['net_profit']:.2f}")

# Zero trade variants
zeros = [(h, d) for h, d in bt_data.items() if d['trades'] == 0]
print(f"\nZERO-TRADE VARIANTS: {len(zeros)}")
for h, d in zeros:
    print(f"  {h}")

# Very low trade variants (1-5)
low = [(h, d) for h, d in sorted_by_pf if 0 < d['trades'] <= 5]
print(f"\nVERY LOW TRADE VARIANTS (1-5 trades): {len(low)}")
for h, d in low:
    print(f"  {h}  PF={d['pf']:.5f}  Trades={d['trades']}")

# Low trade variants (6-15)
med_low = [(h, d) for h, d in sorted_by_pf if 5 < d['trades'] <= 15]
print(f"\nLOW TRADE VARIANTS (6-15 trades): {len(med_low)}")

# Step 2: Analyze trade lists for top PF variants and a sample of others
print("\n" + "=" * 80)
print("STEP 2: TRADE LIST DEEP ANALYSIS")
print("=" * 80)

# Pick top 15 by PF + 5 random from middle
to_analyze = [h for h, d in sorted_by_pf[:15]]
mid = len(sorted_by_pf) // 2
to_analyze += [h for h, d in sorted_by_pf[mid:mid+5]]

for h in to_analyze:
    tl_file = os.path.join(base, h + '.trade_list.json')
    if not os.path.exists(tl_file):
        print(f"\n--- {h}: TRADE LIST FILE MISSING ---")
        continue

    try:
        trades = json.load(open(tl_file))
    except:
        print(f"\n--- {h}: PARSE ERROR ---")
        continue

    if not trades or len(trades) == 0:
        print(f"\n--- {h}: EMPTY TRADE LIST (0 trades) ---")
        continue

    bt_info = bt_data.get(h, {})
    pf = bt_info.get('pf', 'N/A')

    print(f"\n--- {h} (PF={pf}, Trades={len(trades)}) ---")

    # Extract PnL per trade
    pnls = []
    timestamps = []
    for t in trades:
        pnl = t.get('pnl', t.get('profit', t.get('net_pnl', 0)))
        pnls.append(pnl)
        ts = t.get('entry_time', t.get('entry_ts', t.get('open_time', '')))
        timestamps.append(ts)

    total_pnl = sum(pnls)
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]

    # Trade concentration: top 2 trades vs total
    sorted_pnls = sorted(pnls, reverse=True)
    top2_pnl = sum(sorted_pnls[:2]) if len(sorted_pnls) >= 2 else sum(sorted_pnls)

    if total_pnl != 0:
        top2_pct = (top2_pnl / total_pnl * 100) if total_pnl > 0 else 0
    else:
        top2_pct = 0

    # For concentration: also check gross profit
    gross_profit = sum(winners)
    if gross_profit > 0:
        top2_of_gross = top2_pnl / gross_profit * 100
    else:
        top2_of_gross = 0

    print(f"  Total PnL: {total_pnl:.2f}")
    print(f"  Winners: {len(winners)}, Losers: {len(losers)}")
    print(f"  Top 2 trades PnL: {top2_pnl:.2f}")
    if total_pnl > 0:
        print(f"  Top 2 as % of net profit: {top2_pct:.1f}%")
    print(f"  Top 2 as % of gross profit: {top2_of_gross:.1f}%")

    if top2_pct > 100 and total_pnl > 0:
        print(f"  ** CONCENTRATION FLAG: Top 2 trades exceed total net profit!")
    elif top2_pct > 50 and total_pnl > 0:
        print(f"  ** CONCENTRATION FLAG: >50% of net profit from top 2 trades!")

    # Time clustering analysis
    if timestamps and timestamps[0]:
        try:
            # Parse timestamps - try multiple formats
            parsed_ts = []
            for ts in timestamps:
                if not ts:
                    continue
                try:
                    if 'T' in str(ts):
                        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromtimestamp(float(ts))
                    parsed_ts.append(dt)
                except:
                    pass

            if parsed_ts:
                # Monthly distribution
                monthly = defaultdict(int)
                for dt in parsed_ts:
                    monthly[f"{dt.year}-{dt.month:02d}"] = monthly.get(f"{dt.year}-{dt.month:02d}", 0) + 1

                # Weekly distribution
                weekly = defaultdict(int)
                for dt in parsed_ts:
                    wk = dt.isocalendar()
                    weekly[f"{wk[0]}-W{wk[1]:02d}"] = weekly.get(f"{wk[0]}-W{wk[1]:02d}", 0) + 1

                sorted_months = sorted(monthly.items())
                total_months = len(sorted_months)
                max_month_trades = max(monthly.values()) if monthly else 0

                # Check if winning trades cluster
                winner_months = defaultdict(float)
                for i, pnl in enumerate(pnls):
                    if pnl > 0 and i < len(parsed_ts):
                        dt = parsed_ts[i]
                        key = f"{dt.year}-{dt.month:02d}"
                        winner_months[key] += pnl

                if winner_months:
                    top_winner_month = max(winner_months.items(), key=lambda x: x[1])
                    if gross_profit > 0:
                        top_month_pct = top_winner_month[1] / gross_profit * 100
                        if top_month_pct > 50:
                            print(f"  ** TIME CLUSTER FLAG: {top_month_pct:.1f}% of gross profit from month {top_winner_month[0]}")

                # Time span
                time_span = (max(parsed_ts) - min(parsed_ts)).days
                print(f"  Time span: {time_span} days ({min(parsed_ts).strftime('%Y-%m-%d')} to {max(parsed_ts).strftime('%Y-%m-%d')})")
                print(f"  Monthly distribution: {dict(sorted_months)}")

                # Check if trades cluster in narrow window
                if time_span > 0:
                    # Check if >50% of trades in <25% of the time span
                    quarter_span = time_span / 4
                    parsed_sorted = sorted(parsed_ts)
                    max_in_quarter = 0
                    for i in range(len(parsed_sorted)):
                        end_window = parsed_sorted[i].timestamp() + quarter_span * 86400
                        count = sum(1 for t in parsed_sorted if t.timestamp() >= parsed_sorted[i].timestamp() and t.timestamp() <= end_window)
                        max_in_quarter = max(max_in_quarter, count)

                    cluster_pct = max_in_quarter / len(parsed_sorted) * 100
                    if cluster_pct > 60:
                        print(f"  ** TIME CLUSTER FLAG: {cluster_pct:.1f}% of trades in 25% of time window")
        except Exception as e:
            print(f"  Time analysis error: {e}")

# Step 3: Bulk zero-check across ALL trade lists
print("\n" + "=" * 80)
print("STEP 3: BULK TRADE LIST SCAN (all files)")
print("=" * 80)

tl_files = glob.glob(os.path.join(base, '*.trade_list.json'))
empty_lists = []
tiny_lists = []  # 1-3 trades
concentration_flags = []

for f in tl_files:
    h = os.path.basename(f).replace('.trade_list.json', '')
    try:
        trades = json.load(open(f))
        n = len(trades) if trades else 0

        if n == 0:
            empty_lists.append(h)
            continue

        if n <= 3:
            tiny_lists.append((h, n))

        # Quick concentration check
        pnls = [t.get('pnl', t.get('profit', t.get('net_pnl', 0))) for t in trades]
        total = sum(pnls)
        if total > 0 and n >= 2:
            top2 = sum(sorted(pnls, reverse=True)[:2])
            pct = top2 / total * 100
            if pct > 200:
                concentration_flags.append((h, n, pct))
    except:
        pass

print(f"\nTotal trade list files: {len(tl_files)}")
print(f"Empty trade lists (0 trades): {len(empty_lists)}")
print(f"Tiny trade lists (1-3 trades): {len(tiny_lists)}")
print(f"High concentration flags (top2 > 200% of net): {len(concentration_flags)}")

if empty_lists:
    print(f"\nEmpty lists:")
    for h in empty_lists[:30]:
        print(f"  {h}")

if tiny_lists:
    print(f"\nTiny lists:")
    for h, n in tiny_lists:
        print(f"  {h}  trades={n}")

if concentration_flags:
    print(f"\nConcentration flags:")
    for h, n, pct in sorted(concentration_flags, key=lambda x: x[2], reverse=True)[:20]:
        print(f"  {h}  trades={n}  top2_pct={pct:.1f}%")

print("\nDONE")
