# Quandalf Latest Response

**Timestamp:** 2026-03-03 14:39:14 AEST
**Prompt:** No, I will work that out. You don’t have to worry. You just do your job. I just wanted your opinion now. I am thinking we will forward test it just how we have built now but then we will promote the w...
**Status:** COMPLETE

---

That's a solid promotion pipeline. Three stages of increasing commitment:

**Forward test (backtester)** â†’ **Paper trade (HyperLiquid agent)** â†’ **Live capital**

Each stage filters differently:
- Forward testing catches **curve-fitting** â€” does the edge hold on unseen data?
- Paper trading catches **execution reality** â€” slippage, fill rates, timing gaps that backtests assume away
- Live capital is the final filter â€” **psychology and risk** under real P&L

A few things worth thinking about as you build it:

**Graduation criteria matter most.** Without clear thresholds at each gate, you'll either promote too early (losing money) or too late (missing edge decay). Minimum trade count, PF drift tolerance, max drawdown â€” these need to be defined before the first promotion, not after.

**Position sizing should scale with confidence.** Paper trade at full size, but when a strategy first gets real capital, start it at a fraction (say 25%) and scale up as it proves itself live. That's a fourth implicit stage.

**Regime awareness carries through.** A strategy that passes forward testing during a ranging market and then gets paper-traded during a trending market might look like it failed â€” but it didn't. The regime context needs to travel with the strategy through every stage.

The architecture is right. Graduated trust with hard gates between stages is exactly how fund managers do it. The details of those gates are what separate "we have a process" from "we have edge."