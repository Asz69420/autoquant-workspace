# Quandalf Latest Response

**Timestamp:** 2026-03-03 11:25:52 AEST
**Prompt:** What do you imagine for our forward testing how should it look? we are planning to build the system but how frequent should the Ford testing be on the champions? Only is there something we just check ...
**Status:** COMPLETE

---

Here's my thinking â€” two tiers:

**Tier 1: Live signal tracking (continuous)**
Every 4h bar close (since 4h is our edge timeframe), run the top 3-5 champions against the latest candle data. Log whether they fire entry/exit signals. No real capital â€” just paper tracking. This is cheap and gives us the most important thing: **does the strategy actually fire in live conditions, and do those signals match backtest behavior?**

**Tier 2: Weekly scorecard (every Sunday)**
Roll up the week's paper signals into a report:
- How many signals fired per strategy?
- What would P&L have been?
- Profit factor vs backtest PF â€” is it degrading?
- Regime distribution that week vs backtest training set

**Why continuous + weekly, not just weekly:**
- 4h bars = 42 bars/week. Weekly-only means you're reviewing stale signals with no context on *when* they fired relative to market moves.
- Continuous tracking catches "strategy went silent for 3 days" immediately â€” that's a regime mismatch signal.
- Weekly scorecard is where you make decisions (promote, demote, kill).

**What I'd start with (MVP):**
1. Cron job every 4h â€” pull latest HyperLiquid candles, compute indicators, evaluate champion rule sets, log signals to a file
2. TG alert on any entry signal (so we can watch it play out)
3. Sunday script that aggregates the week and compares to backtest expectations

**Graduation criteria to real capital:**
- 4 weeks of paper trading
- Live PF within 30% of backtest PF
- At least 15 paper trades logged
- No silent weeks (proves strategy fires in current market)

Start with Vortex v3a and Supertrend 8:1 only. Adding all 5 champions day one just creates noise before we trust the plumbing.

Want me to spec out the MVP pipeline in detail?