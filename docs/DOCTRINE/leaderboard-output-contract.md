# Leaderboard Output Contract

## Purpose
When the operator asks for leaderboard-style outputs (examples: `leaderboard`, `top performers`, `top strategies`, `top`), responses must use the Daily Intel strategy table format.

## Required Format
Use the same fixed-width table style as Daily Intel:

```text
🟠 BTC
△ Strategy       PF  WR%  TC  DD%  P&L%
○── 4h ────────────────────────────────
○ Example_Name  1.23 45.6 120 12.3 +10.1

🔵 ETH
△ Strategy       PF  WR%  TC  DD%  P&L%
○── 1h ────────────────────────────────
↑ Example_Name  1.45 39.1 180 18.2 +22.4
```

## Timeframe Slot Rule (Dynamic)
- Include a section for **every timeframe that has results**.
- If `15m` results exist, render a `○── 15m ...` section.
- Do not hard-code only `1h` and `4h`.
- Preferred order when present: `4h`, `1h`, `15m`, then any additional timeframes alphabetically.

## Metrics Columns
- `PF`: Profit Factor
- `WR%`: Win Rate (%)
- `TC`: Trade Count
- `DD%`: Drawdown (%)
- `P&L%`: Net P&L (%)

## Consistency Rules
- Keep alignment and headers identical to Daily Intel formatter.
- Use monospace-compatible plain text output.
- Prefer top 3 entries per asset/timeframe bucket unless user asks otherwise.
