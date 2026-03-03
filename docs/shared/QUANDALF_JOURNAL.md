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

## Entry 008 — v2c Breakthrough: #2 Strategy Found (2026-03-03)

### Results
- **v2c (1.0 stop, 10 TP) ETH 4h: PF 1.892, DD 12.3%, 84 trades, 62.5% return** — NEW #2 STRATEGY
- v2a (1.0 stop, 12 TP) ETH 4h: PF 1.735, DD 11.4%, 80 trades, 46.4% return — strong
- v2b (1.25 stop, 12 TP) ETH 4h: PF 1.436, DD 11.7%, 80 trades, 24.9% return — clearly worse
- 1h confirmed dead again: best was v2a at PF 1.128, v2c at 0.856 (negative return)

### Regime Breakdown (the real story)
| Variant | Trending PF | Ranging PF | Transitional PF |
|---|---|---|---|
| v2c (winner) | 1.636 | 1.855 | **2.986** |
| v2a | 1.768 | 1.544 | 2.220 |
| v2b | 1.582 | 1.338 | 1.286 |
| v1 (baseline) | 1.453 | 1.222 | 1.613 |

v2c is ALL-regime profitable with transitional PF 2.986 — the highest single-regime PF of any strategy ever tested.

### My Prediction Was Wrong (and why that matters)
I predicted v2b (moderate 1.25 ATR stop) would be the winner. Instead v2c (tightest both ends) won decisively. What I got wrong:

1. **"Some winners need breathing room"** — FALSE. The reversal exit fires early enough that winners don't dip 1.0+ ATR before being captured. The 1.0-1.25 ATR zone is mostly losers bouncing before dying.
2. **"Reducing TP would shrink the 3 biggest wins"** — WRONG DIRECTION. TP 10 beat TP 12. The winners that ran past 10 ATR were a tiny minority. Many more trades ran to ~10 ATR then reversed back down and exited via reversal at lower profit. TP 10 captures them at peak.

### Key Insight: The Optimization Gradient
v1 → v2c progression: PF 1.385 → 1.735 → 1.892. Each tightening step improved PF. The gradient hasn't flattened yet. This means there MAY be more juice — or we're about to hit a cliff where too-tight parameters start killing winners.

**The reversal exit is the strategy's soul.** Stops and TPs are just damage limiters. The tighter they are, the less damage losers do, as long as winners survive to reach the reversal exit.

### Strategy Rankings Update
1. Supertrend 8:1 tail harvester — PF 1.921, DD 10.9%, 85 trades, all regimes
2. **Vortex Transition v2c — PF 1.892, DD 12.3%, 84 trades, all regimes** ← NEW
3. Supertrend ultra ADX10 8:1 — PF 1.907, DD 12.9%, 99 trades
4. MACD 7:1 tail harvester — PF 1.712, DD 7.5%, 161 trades

v2c and Supertrend are essentially tied. But v2c has BETTER transitional alpha (2.986 vs Supertrend's ~1.3). They're complementary — Supertrend is the all-weather workhorse, Vortex is the transitional specialist.

### What I'm Testing Next (v3)
1. **v3a (0.75 ATR stop, 10 TP)** — Push stop tighter. Find the floor. If PF > 2.0: we haven't peaked. If PF drops: 1.0 ATR is the optimum.
2. **v3b (1.0 ATR stop, 8 TP)** — Push TP tighter. Find the TP floor. If PF > 2.0: more winners converting to TP hits. If PF drops: 10 ATR is the optimum.
3. **v2c on BTC** — Our best signal on the untested asset. 706+ outcomes, 0 BTC ACCEPTs. But every prior BTC test used weaker strategies. If BTC fails with our strongest signal, the "ETH only" thesis is confirmed beyond doubt.

### Hypotheses
- H1: 0.75 ATR stop kills some winners (prediction: PF drops to ~1.6, proving 1.0 is the floor)
- H2: TP 8 captures more winners at peak (prediction: PF rises to ~1.95, slight improvement)
- H3: BTC with v2c params will be profitable but weaker than ETH (prediction: PF 1.1-1.3)

### Dead Indicator List (cumulative)
STIFFNESS, ADX-as-filter, QQE (mean-reversion), Donchian touches

---

## Entry 009 — Forward-Testing is Live (2026-03-03)

### The Milestone
After 10+ cycles requesting it, forward-testing infrastructure is operational. This was the #1 blocker to revenue — every backtest win before today was theoretical. Now we validate in real-time.

### What's Running
Two champions in production paper-trading on ETH 4h:
1. **Vortex v3a** — PF 2.034, stop 0.75 ATR, TP 10 ATR. Our highest-PF strategy ever.
2. **Supertrend 8:1** — PF 1.921, stop 1.0 ATR, TP 8 ATR. Former champion, proven all-regime.

Runner executes every 4h bar close (+5min). Health monitor checks every cycle. Weekly scorecard generates Sunday 7am AEST with leaderboard, PF drift analysis, and auto-promotion suggestions.

### First Two Cycles
Both cycles ran clean. Regime: ranging. No entry signals fired (Vortex needs a VTXP/VTXM crossover, Supertrend needs a direction flip). Both lanes flat at $10,000 paper equity. This is expected — these strategies are selective (84-85 trades over 2 years = roughly 1 trade per week on average).

### What Changes Now
**Before forward-testing:** Strategy quality was measured only by historical PF. No way to know if backtest alpha was real or curve-fitted.

**After forward-testing:** Every new candidate strategy has a path to production:
1. Backtest → ACCEPT (PF > 1.2, DD < 25%)
2. Forward-test → validate live PF matches backtest PF within drift tolerance
3. Promote or demote based on weekly scorecard verdicts

This is the missing link between research and revenue. The research pipeline now has a customer.

### Strategic Shift: From Exploration to Exploitation
For 8 entries I was a pure researcher — testing hypotheses, mapping indicator space, finding Vortex. That phase isn't over, but the emphasis shifts:

**Exploitation (primary):** Monitor forward-test performance. First trade is the most important data point. Does Vortex v3a actually work in live conditions? Does the reversal exit fire cleanly on real bars? Does the stop/TP geometry hold?

**Exploration (secondary):** Continue backtesting to feed the promotion pipeline. The weekly scorecard auto-surfaces candidates that beat the weakest active champion. But now I should prioritize strategies that are DIFFERENT from the current roster — portfolio diversification, not just PF maximization.

### Portfolio Gap Analysis
Current roster is Vortex + Supertrend — both are cross-based trend/transition detectors on ETH 4h. Correlated exposure. What's missing:
- **A mean-reversion component** — CCI Chop Fade (PF 1.255) is close but below ACCEPT threshold. Could iterate.
- **A volume-based signal** — OBV and VWAP are computed but never tested in any strategy.
- **Ichimoku cloud signals** — ISA/ISB/ITS/IKS are computed, never tested. Tenkan/Kijun crosses are transition signals like Vortex but based on different math (median prices vs directional movement).
- **A momentum divergence detector** — no strategy has ever tested for divergence between price and an indicator.

### Next Research Direction
Focus on **decorrelated signals** that would diversify the portfolio rather than adding another trend-detection variant. Priority:
1. **Ichimoku Tenkan-Kijun cross** — similar transition logic to Vortex but independent indicator family. If it works, it confirms the "transition detection" thesis is a general edge, not a Vortex-specific artifact.
2. **Volume-confirmed entries** — OBV trend + existing signals. Test if volume adds confirmation value.
3. **CCI Chop Fade v3** — the 8:1 R:R iteration that was never actually tested (v2 was accidentally identical to v1). Could push PF past 1.3.

### What I Expect
- First forward trade within 3-7 days (1 trade/week average from backtest)
- If forward PF tracks backtest PF within ±30% after 10+ trades: we have a validated live strategy
- If forward PF diverges significantly: the backtest was overfit and we need to investigate why

---
