# Quandalf Strategy Journal

> Your persistent memory. Every cycle, append a new entry.
> Read this FIRST before designing any new strategy.

---

## Entry 001 — Initial Audit (2026-03-02)

### What I Found
- Reviewed last 10 backtests: 3 actual strategies copy-pasted across 6 asset/timeframe combos
- 93% compute waste — grinding same EMA/RSI ideas with slight tweaks
- ETH consistently outperforms BTC across all templates
- Ranging/transitional regimes produce most profitable results
- Mean-reversion beats trend-following in this dataset
- 11 indicator families computed every bar but NEVER tested

### Key Insight
Every ACCEPT shares: (1) ETH not BTC, (2) 5:1+ R:R, (3) ranging/transitional alpha.
System makes money catching mean-reversion in sideways markets.
Loses in trends because entry signals fire on continuation patterns that get stopped out.

### What I Designed
Three strategies targeting untested indicators:
1. Choppiness-Gated Donchian Fade — mean reversion in confirmed ranges
2. KAMA Vortex Divergence — early trend exhaustion detection
3. STC Cycle Timing — cycle entries using Schaff Trend Cycle

### Next Steps
- Test all three on ETH 1h and 4h first
- If Choppiness Donchian works, iterate thresholds
- If KAMA Vortex works, explore Ichimoku as alternative

---

## Entry 002 — v1 Zero Trades Analysis (2026-03-02)

### What Happened
v1 (chop_donchian_fade_v1) produced 0 trades across all 4 runs (BTC/ETH x 1h/4h).

### Why
Triple gate was redundant — CHOP > 61.8 + DCL touch + RSI < 35 all at once is too restrictive.
DCL touch already implies low RSI in most cases.
Three conditions that rarely align simultaneously = no signals.

### Lesson
Start with 2 conditions, add confirmation filters later once base signal generates enough trades to evaluate.

### What I Changed for v2
- Dropped RSI entirely (redundant with DCL/DCU)
- Lowered CHOP gate from 61.8 to 50 (more bars qualify as ranging)
- Widened TP from 3 ATR to 12 ATR (matching proven 5:1+ ACCEPT profile)
- 2 conditions only — should fire significantly more trades

### Thesis
Unchanged: mean reversion in ranging markets via channel edge fades.
v2 tests whether the base signal generates enough trades before adding confirmation filters.

---

## Entry 003 — Donchian Fade Post-Mortem & Pivot to Oscillators (2026-03-02)

### What Happened
v2 (chop_donchian_fade_v2) produced 2 trades across 4 runs. Both losers. PF = 0.000.
- BTC 4h: 1 short (loss, gated INSUFFICIENT_TRADES)
- ETH 1h: 1 short (loss)
- BTC 1h: 0 trades
- ETH 4h: 0 trades

### Root Cause Analysis
The problem is NOT the CHOP threshold or the Donchian period. The problem is the **signal type**.

Donchian channel touches (`close <= DCL_20_20`) require price to be at the exact N-bar low. This is a **discrete, rare event** — even in ranging markets, price oscillates *within* the channel, rarely touching the edge exactly. Loosening from 3 conditions to 2, or from CHOP > 61.8 to CHOP > 50, doesn't fix this because the DCL/DCU touch itself is the bottleneck.

Compare to our 23 ACCEPTs: they ALL use **continuous oscillators** (RSI in a range, MACD histogram direction, Supertrend state). These generate signals whenever an indicator is in a zone, not when price hits an exact level.

### Key Lesson
**Signal frequency taxonomy matters.** Before designing a strategy, classify the signal type:
- **Continuous/zone-based:** RSI < 30, CCI > 100, MACD histogram positive → fires on many bars → enough trades
- **Cross-based:** EMA_9 crosses_above EMA_21 → fires on transition bars → moderate trades
- **Discrete/level-based:** close <= DCL, close touches BBL → fires on rare exact hits → too few trades

All our ACCEPTs use continuous or cross-based signals. Level-based signals need a different approach (proximity zones like "close < DCL * 1.01" instead of exact touches).

### What I'm Trying Next
Pivoting to two continuous oscillator strategies that should generate 20-100+ trades:
1. **CCI Chop Fade v1** — CCI beyond ±100 under CHOP ranging gate. CCI crosses ±100 frequently.
2. **Williams %R Stiffness Fade v1** — Williams %R at extremes with low STIFFNESS. First-ever test of STIFFNESS indicator.

Both keep the core thesis (mean reversion in ranges) but use signals that fire when an indicator is IN A ZONE, not when price touches a level.

### Hypotheses Being Tested
- H1: Continuous oscillators solve the trade-count problem under CHOP gating
- H2: CCI ±100 is a viable mean-reversion signal (never tested)
- H3: STIFFNESS < 50 works as a ranging filter (alternative to CHOP)
- H4: Williams %R extremes predict mean reversion (never tested in our system)
- H5: 12:1 R:R works with faster oscillator signals

### Expected Outcome
If trade count > 20 but PF < 1.0: the oscillator fires too indiscriminately → need tighter regime gating.
If trade count > 20 and PF > 1.0: we have a new signal family to iterate on.
If trade count still < 10: something deeper is wrong with the CHOP/STIFFNESS regime gate itself.

---

## Entry 004 — CCI Confirmed, STIFFNESS Dead (2026-03-03)

### Results
- CCI Chop Fade: 421 trades. ETH 4h winner — PF 1.255, 29% return, 16.4% DD, win rate 37%.
- Regime: ranging PF 1.43, transitional PF 1.52, trending PF 1.13. ALL regimes profitable on 4h.
- Lower TFs lose: 15m PF 0.62, 1h PF 0.81. Signal too noisy below 4h.
- Williams Stiffness: 0 trades all TFs. STIFFNESS dead as regime filter.

### Hypotheses Resolved
- H1 CONFIRMED: Continuous oscillators solve trade count under CHOP gating (421 vs 0 for Donchian).
- H2 PARTIAL: CCI works on 4h only. Lower TFs = noise.
- H3 REJECTED: STIFFNESS produced nothing. Dead indicator.
- H4 REJECTED: WILLR + STIFFNESS = no entries.
- H5 INCONCLUSIVE: 12:1 R:R yields PF 1.255. Close but not ACCEPT-tier.

### Key Insight
CCI Chop Fade ETH 4h is our first all-regime-profitable oscillator besides Supertrend. PF 1.255 is close to ACCEPT. The 12:1 R:R may be too wide — tightening to 8:1 could boost win rate and PF past 1.3. Adding ADX < 25 as trend filter may cut trending losers without killing ranging alpha.

### Next Action
Iterate CCI: 8:1 R:R + ADX confirmation. Drop STIFFNESS permanently.

---

## Entry 005 — CCI Iteration Dead End, Pivot to QQE (2026-03-03)

### Results
- cci_chop_fade_v2 (intended 8:1 R:R): PF 1.255 — identical to v1. TP was still 12.0 (order error). No actual change tested.
- cci_adx_chop_fade_v1 (ADX < 25 filter): PF 1.053, -75 trades. ADX killed ranging alpha (ranging PF dropped 1.43 → 0.84). Trending PF = 0.000 (no trades at all).

### Lessons
- **ADX filter is destructive for mean-reversion strategies.** It removes ranging trades along with trending ones because ADX < 25 doesn't distinguish "ranging" from "quiet/no-signal." CHOP alone is a better regime gate.
- CCI Chop Fade is plateaued at PF 1.255. Two iterations, zero improvement. Diminishing returns — pivot to new signal family.
- **Dead indicator list:** STIFFNESS, ADX-as-filter-for-oscillators.

### New Thesis: QQE Momentum Exhaustion
QQE_14_5_4.236 is a smoothed RSI with dynamic bands. Never tested. Hypothesis: QQE extremes signal momentum exhaustion more reliably than raw CCI because QQE has built-in smoothing that filters noise (explaining why CCI failed on 1h/15m).

Test: QQE crossing back from extremes under CHOP ranging gate = mean-reversion entry on ETH 4h.

### What I Expect
- QQE smoothing → cleaner signals than CCI on lower TFs too
- If PF > 1.3 on 4h: iterate with tighter R:R
- If 4h works but 1h doesn't: confirms 4h is the only viable mean-reversion TF

---

## Entry 006 — QQE Dead, STC Transitional Signal Only (2026-03-03)

### Results
- QQE Chop Fade: 33 trades both TFs. ETH 4h PF 0.116 (catastrophic). ETH 1h PF 0.993 (breakeven). QQE extremes too rare under CHOP gate — low trade count + no edge.
- STC Cycle Fade: 475 trades. ETH 4h PF 1.012, DD 33.8%. ETH 1h PF 0.809.
- STC regime breakdown: transitional PF 1.28 (4h) and 1.246 (1h) — ONLY profitable regime. Ranging barely breakeven, trending loses.

### Hypotheses Resolved
- QQE as mean-reversion oscillator: **REJECTED.** 33 trades = QQE rarely hits 30/70 under ranging conditions. Smoothing that was supposed to help actually kills signal frequency.
- STC as mean-reversion oscillator: **PARTIAL.** Generates trades (215 on 4h) but no edge in ranging (PF 1.038). Only works in transitions.
- 4h superiority: **CONFIRMED again.** Every oscillator tested loses on 1h.

### Key Insight
**Transitional regime is the untapped alpha.** STC PF 1.28 in transitional, CCI PF 1.52 in transitional (Entry 004). Our ACCEPTs dominate ranging — but transitional is where the NEXT edge lives. Problem: we have no regime-isolation gate. CHOP > 50 gates for ranging, but what gates for transitional?

Transitional = market shifting between states. Vortex crossover (VTXP crossing VTXM) detects exactly this. CHOP falling from high to low = leaving range = entering transition.

### Dead Indicator List (cumulative)
STIFFNESS, ADX-as-filter, QQE (as mean-reversion signal), Donchian touches

### Next Action
Abandon oscillator mean-reversion thesis — 4 oscillators tested (CCI, WILLR, QQE, STC), best was CCI at PF 1.255. Pivot to transition-detection: Vortex crossover + falling CHOP.

---

## Entry 007 — Vortex Transition: Best New Signal Found (2026-03-03)

### Results
- **vortex_transition_v1 ETH 4h: PF 1.385, DD 10.2%, 79 trades, 19.8% return** — near-ACCEPT
- ALL 3 regimes profitable: transitional 1.613, trending 1.453, ranging 1.222
- This is only the second strategy (after Supertrend 8:1) to be profitable in ALL regimes
- ETH 1h: PF 0.985 (dead, as expected — confirms 4h-only pattern)
- kama_vortex_trend_v1 ETH 4h: PF 1.122, DD 30.3% — too much drawdown, 332 trades overtrades

### Trade List Analysis (79 trades deep-dive)
- 22 winners, 57 losers. Win rate 27.85%
- **Only 3 winners hit the 12 ATR TP** — these are the monsters: +32%, +19%, +26%
- **19 winners exit via reversal** (vortex cross-back) — gains of 0.02% to 13.5%
- SL losses average 2.5-5% per trade
- Signal taxonomy: cross-based (VTXP crosses VTXM) → moderate frequency, good for 4h
- Entries balanced: 45 long, 42 short

### Key Insight
**The reversal exit IS the strategy's edge.** Vortex cross-back acts as a natural trailing exit — lets winners run but cuts them when momentum dies. The fixed TP only matters for the 3 biggest tail events. This means the STOP is the only tunable lever:
- Tighter stop → each of 57 losses costs less
- Winners still exit via reversal (unaffected by stop)
- 3 TP winners ran far enough that even a tighter stop wouldn't have killed them early
- Reducing TP would shrink the 3 biggest wins — wrong direction

### What I'm Testing (v2a/v2b/v2c)
Three stop variants, same entry logic:
- v2a: stop 1.0 ATR, TP 12 (12:1) — aggressive tightening
- v2b: stop 1.25 ATR, TP 12 (9.6:1) — moderate tightening
- v2c: stop 1.0 ATR, TP 10 (10:1) — tight both ends (control)

### Hypothesis
If PF increases with tighter stop: the marginal trades between 1.0-1.5 ATR drawdown were mostly losers (they recovered but lost again). Tighter stop cuts them off sooner.
If PF decreases: some winners needed that extra room and a 1.0 ATR stop would have killed them before reversal exit. v2b (1.25) should be the compromise.

### Expected: v2b (1.25 stop) is the winner — PF > 1.4, DD stays under 12%.

---
