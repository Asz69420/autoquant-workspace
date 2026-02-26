# Daily Intel Spec (Locked)

## Schedule
- Task name: `AutoQuant-daily-intel-user`
- Run time: `05:30` Australia/Brisbane (AEST)
- Launcher: PowerShell hidden window

## Manual Triggers
The following chat triggers must generate+send immediately:
- `intel`
- `brief`
- `leaderboard`
- `report`

## Output Contract
- Filename: `daily_intel.txt`
- Delivery: Telegram document attachment
- Header:
  - `📊 DAILY INTEL — <date> 5:30 AEST`
- Assets:
  - `🟠 BTC`
  - `🔵 ETH`
- Table header appears once per asset above timeframe sections.
- Timeframe separators:
  - `○── 4h ─────...`
  - `○── 1h ─────...`
  - `○── 15m ─────...`
  - Must fill to table width.
- Rows:
  - top 3 per timeframe per asset
  - no rank numbers
  - dedup by strategy best result only
- Strategy names:
  - max 12 chars
  - source order: thesis title/description → strategy family → spec stem fallback
- Percent fields only: WR%, DD%, P&L%
- Trend arrows:
  - `↑` improving
  - `↓` declining
  - `→` flat
  - `○` new
- Alignment string (locked):
  - `f"{arrow:<1} {name:<12} {pf:>4} {wr:>4} {tc:>3} {dd:>4} {pnl:>5}"`
  - Header must use same format string.
- Max width: 42 chars per line

## Required Sections
- `⚡ 24H ACTIVITY`
  - `Cycles:X Backtests:X Specs:X Errors:X`
- `🎯 MILESTONES`
- `⚠️ ATTENTION`
  - FAIL errors only, or `System healthy ✅`
