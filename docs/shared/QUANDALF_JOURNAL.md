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

---

## Entry 002 — v1 Zero Trades Analysis (2026-03-02)

### Results
chop_donchian_fade_v1: **0 trades on ETH 1h** (confirmed on 4,014 bars)

### Why
Triple gate (CHOP > 61.8 AND DCL touch AND RSI < 35) is too restrictive. Each condition individually has reasonable frequency, but combining all three means they almost never align at the same bar. The Donchian touch especially — it's a discrete event at specific prices, not a zone.

### Lesson
Start with 2 conditions, add filters only if overtrading. A strategy with 0 trades teaches nothing about market dynamics.

---

## Entry 003 — Donchian Fade Post-Mortem & Pivot to Oscillators (2026-03-02)

### Results
chop_donchian_fade_v2 (relaxed RSI gate removed): 2 trades, both losers. PF=0.000.

### Post-Mortem
Discrete/level-based signals (DCL touch) are too rare for reliable backtesting. Found a signal frequency taxonomy:
1. **Continuous/zone-based:** RSI > 50, close > EMA_200 — fires every bar in a zone (too frequent alone)
2. **Cross-based:** EMA_9 crosses EMA_21, VTXP crosses VTXM — moderate frequency, good for signals
3. **Discrete/level-based:** price touches DCL_20, close == BBU — very rare, poor as primary signals

### Key Finding
ALL 23 prior ACCEPTs use continuous or cross-based signals. NONE use discrete/level-based.

### Pivot
Abandoning Donchian fade entirely. Pivoting to:
1. **CCI Chop Fade** — CCI oscillator with CHOP range confirmation (both continuous/zone)
2. **Williams %R Stiffness Fade** — WILLR with STIFFNESS range filter (both continuous/zone)

---

## Entry 004 — CCI Confirmed, STIFFNESS Dead (2026-03-03)

### Results
CCI Chop Fade: 421 trades total.
- **ETH 4h: PF 1.255, 29% return, 16.4% DD, 37% win rate** — PROFITABLE ALL REGIMES
  - Ranging PF 1.43, Transitional PF 1.52, Trending PF 1.13
- ETH 1h: PF 0.816, -31% return — signal too noisy below 4h
- ETH 15m: PF 0.618 — dead
- BTC 4h: PF 0.955 — BTC loses again (ranging PF 1.12 only profitable slice)

Williams Stiffness Fade: **0 TRADES** on ETH 4h (and all combos). STIFFNESS indicator never transitions below 50 simultaneously with WILLR at extremes.

### Key Insights
1. **CCI works as mean-reversion on 4h.** Not spectacular (PF 1.255) but ALL regimes profitable.
2. **STIFFNESS is dead.** The indicator design doesn't match our signals. Permanently blacklisted.
3. **4h confirms as THE timeframe.** CCI 15m→1h→4h: PF 0.618→0.816→1.255. Signal clarity improves monotonically.

### Next
Iterate CCI with 8:1 R:R and ADX confirmation filter.

---

## Entry 005 — CCI Iteration Dead End, Pivot to QQE (2026-03-03)

### Results
- cci_chop_fade_v2: PF 1.255 (identical to v1 — TP was still 12:1 despite orders saying 8:1. Execution error.)
- cci_adx_chop_fade_v1: PF 1.053, -75 trades. ADX filter was destructive.

### Why ADX Failed
ADX > 20 as an entry filter eliminates the BEST mean-reversion trades (which occur when ADX is LOW = range-bound). CCI Chop Fade's ranging PF dropped from 1.43 to 0.84 with ADX filter.

### Lesson
**ADX-as-filter kills mean-reversion edge.** ADX measures trend STRENGTH. Adding a strength filter to a mean-reversion strategy removes exactly the conditions where the strategy profits. This is obvious in hindsight.

### Dead Indicator List (updated)
- STIFFNESS: 0 trades, dead signal
- ADX-as-filter: actively destructive for mean-reversion
- Donchian touches: too rare, discrete events

### Pivot to QQE
QQE (Quantitative Qualitative Estimation) is a smoothed RSI with dynamic bands. Hypothesis: QQE's smoothing might work better on lower timeframes than raw CCI.

---

## Entry 006 — QQE Dead, STC Transitional Signal Only (2026-03-03)

### Results
QQE Chop Fade: 33 trades, ETH 4h PF 0.116 (catastrophic), 1h PF 0.993.
STC Cycle Fade: 475 trades, ETH 4h PF 1.012, DD 33.8%.
- STC regime breakdown: transitional PF 1.28 (4h) and 1.246 (1h). ONLY profitable regime.
  - Ranging: breakeven (1.00-1.02)
  - Trending: loses (-0.71 to -0.94)

### Key Insights
1. **QQE is dead for mean-reversion.** The smoothed RSI+bands fires almost exclusively during TRENDING regime, which is exactly wrong for a fade strategy.
2. **STC shows a transition signal** — its only alpha is in transitional regime. But DD=33.8% and PF=1.012 overall make it impractical.
3. **Transitional regime is the untapped alpha.** STC transitional PF=1.28, CCI transitional PF=1.52. Both strategies find their best edge in regime transitions.

### Dead Indicator List (updated)
STIFFNESS, ADX-as-filter, QQE (for mean-reversion), Donchian touches

### Pivot: Transition Detection
If transitional is where alpha lives, I should build a strategy that TARGETS transitions. Which indicators detect regime transitions?
- **Vortex** (VTXP/VTXM crossover) — directional movement crossover
- **CHOP going below 50** — end of range-bound period
- **ADX rising from low** — trend beginning

New hypothesis: Vortex crossover + falling CHOP = transition entry.

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
- Signal taxonomy: cross-based (VTXP crosses VTXM) — moderate frequency, good for 4h
- Entries balanced: 45 long, 42 short

### Key Insight
**The reversal exit IS the strategy's edge.** Vortex cross-back acts as a natural trailing exit — lets winners run but cuts them when momentum dies. The fixed TP only matters for the 3 biggest tail events. This means the STOP is the only tunable lever:
- Tighter stop — each of 57 losses costs less
- Winners still exit via reversal (unaffected by stop)
- 3 TP winners ran far enough that even a tighter stop wouldn't have killed them early
- Reducing TP would shrink the 3 biggest wins — wrong direction

### What I'm Testing (v2a/v2b/v2c)
Three stop variants, same entry logic:
- v2a: stop 1.0 ATR, TP 12 (12:1) — aggressive tightening
- v2b: stop 1.25 ATR, TP 12 (9.6:1) — moderate tightening
- v2c: stop 1.0 ATR, TP 10 (10:1) — tight both ends (control)

### Hypothesis
If PF increases with tighter stop: the marginal trades between 1.0-1.25 ATR drawdown were mostly losers (they recovered but lost again). Tighter stop cuts them off sooner.
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
2. **Vortex Transition v2c — PF 1.892, DD 12.3%, 84 trades, all regimes** — NEW
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
1. Backtest — ACCEPT (PF > 1.2, DD < 25%)
2. Forward-test — validate live PF matches backtest PF within drift tolerance
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
- If forward PF tracks backtest PF within +/-30% after 10+ trades: we have a validated live strategy
- If forward PF diverges significantly: the backtest was overfit and we need to investigate why

---

## Entry 010 — Consolidation: Pipeline Death & Forward-Test Patience (2026-03-03)

### What Happened
No new ACCEPTs this cycle. This is the first pure consolidation cycle — no new strategy breakthroughs, but important system-level findings.

### The Pipeline Is Dead
The autopilot summary reveals catastrophic pipeline starvation:
- **215 starvation cycles** — no accepted work in 215 consecutive cycles
- **31 drought cycles** — no candidates passing gate for 31 cycles
- **22 directive stall cycles** — directive system producing nothing for 22 cycles
- **1/100 candidates ingested** — 99% rejection at ingestion
- **0 candidates passing gate** — even the 1% that gets through doesn't survive

This isn't a temporary drought. The pipeline's spec generation is fundamentally broken. Every ACCEPT in the system came from Claude specs (8/8). The pipeline produced exactly 1 ACCEPT ever (template_div, PF=1.419). Pipeline compute is pure waste at this point.

### Forward-Test Is Healthy
18 signal evaluations across 6 runs, all clean. Every bar shows `regime: "ranging"`. Both Vortex v3a and Supertrend 8:1 are correctly waiting for their respective signals — neither fires in ranging (Vortex needs a crossover, Supertrend needs a direction flip). This is exactly what selective strategies should do. Patience.

### What Changed In My Thinking
1. **Encoded a meta-rule.** After 46 backtests, the strongest pattern isn't about any specific indicator — it's about indicator *architecture*. Adaptive indicators (KAMA's self-adjusting speed, Vortex's transition detection) are the only path to all-regime profitability. Static indicators (CCI, RSI, MACD) top out at PF=1.712 and need regime gates. This is now brain rule `rule-adaptive-over-static`.

2. **Pipeline death changes the research model.** If the pipeline can't generate specs, the research agenda is 100% Claude-driven. This is fine — Claude specs have a 22.2% ACCEPT rate vs pipeline's ~0%. But it means research velocity is bounded by Claude advisory cycles, not by compute.

3. **Research card quality is a missed opportunity.** 9/10 TradingView catalog cards extracted nothing useful. The TV catalog sees hundreds of indicators with specific entry/exit logic, but the extraction pipeline only captures titles and authors. Fixing this would seed Claude spec generation with concrete ideas.

### What I'm Testing Next
Same as Entry 009 — the 3 pending orders remain unexecuted:
1. Ichimoku TK Transition v1 — transition detection via different math than Vortex
2. CCI Chop Fade v3 — the 8:1 R:R iteration
3. Supertrend OBV Confirm v1 — first volume-based signal

### Suggestions For Asz
- Deploy KAMA Stoch v1 as third forward-test lane (no code changes needed)
- Decide pipeline fate: kill it, rebuild it, or accept it's dead
- Define forward-test graduation criteria before the first trade fires
- Fix TV catalog extraction — it's a research pipeline that produces empty cards

---

## Entry 011 — BALROG Unblocked: The YAML Bug That Ate 53 Cycles (2026-03-04)

### What Happened
Zero new ACCEPTs, but I found and fixed the root cause of a critical system failure. The BALROG pre-backtest gate had been blocking every single backtest since I initialized the brain knowledge base in U18. Drought counter surged from 31 to 53. Directive stalls from 22 to 44.

### Root Cause
The brain's `validate_brain.py` uses a simple YAML parser that can't handle inline array syntax. When I wrote `tags: [asset, timeframe, eth, 4h]`, the parser tried `json.loads("[asset, timeframe, eth, 4h]")` which fails because JSON needs quoted strings. It silently fell back to returning the raw string, which the schema then rejected as "expected array."

17 FAILs across 14 brain objects. Every backtest blocked. 36+ failed attempts across 6+ autopilot cycles.

### The Fix
Converted all inline arrays to multi-line YAML syntax (`- item` per line) and added `validated_at` timestamps. Created a new brain rule (`rule-yaml-multiline-only`) to prevent recurrence.

### What Changed In My Thinking
1. **System bugs > strategy research.** The best strategy spec is worthless if the pipeline can't run it. I had 3 Claude specs (Ichimoku, ALMA, T3) sitting unexecuted because a serialization format bug prevented any backtests. Infrastructure quality directly bounds research velocity.

2. **The pipeline is structurally dead, not just stalled.** 53 drought cycles. 44 directive stalls. 0 backtests this cycle. Even after the BALROG fix, the pipeline's spec-generation and refinement loops have 0% improvement rate. The question isn't "how do we fix the pipeline" — it's "should we maintain it at all?"

3. **New brain objects encode system failures, not just market knowledge.** Added `failure-balrog-yaml-parse-block` and `failure-pipeline-structural-death` as first-class brain objects. The brain should track system risks alongside market insights.

### New Brain Objects Added (4)
- `failure-balrog-yaml-parse-block` — YAML parsing bug documentation
- `failure-pipeline-structural-death` — Pipeline 53-drought structural failure
- `fact-claude-specs-sole-progress` — Claude 22.2% ACCEPT rate vs pipeline ~0%
- `rule-yaml-multiline-only` — Multi-line YAML arrays mandatory

### What's Pending Execution
Three Claude specs ready for backtest (if BALROG now passes):
1. **ALMA MACDh Momentum Flip** — First ALMA_9_6.0_0.85 test. Gaussian MA + MACDh zero-cross timing.
2. **Ichimoku TK Cloud CCI Gate** — First Ichimoku (ITS_9/IKS_26/ISA_9/ISB_26) test. Tests whether transition-detection is a general mechanism or Vortex-specific.
3. **T3 Vortex Pullback Confluence** — First T3_10_0.7 test. Triple-smoothed deep pullback + Vortex direction confirm.

### Suggestions For Asz
- Run `python scripts/quandalf/validate_brain.py` — verify 0 FAILs before next autopilot cycle
- Add YAML formatting rule to brain contract doc
- Consider killing the automated pipeline — 53 drought cycles, 0 useful output
- The dual-MACD system from the Red K Pressure Index video (SoheilPKO) deserves a spec: fast MACD 34/144/9 + slow MACD 100/200/50 — requires new indicator columns

---

## Entry 012 — Spec Backlog Crisis: 10 Claude Specs Queued, Zero Backtested (2026-03-04)

### Results
- 0 new ACCEPTs. 24 backtests this cycle, ALL zero trades
- 55 promotions ran (research to thesis to spec) — all produced 0-trade specs
- 150+ batch files today, estimated 95%+ dedup rate
- 10 new Claude-designed strategy specs created but NONE backtested yet
- Total consecutive zero-trade backtests: 34+ (since U18)
- Promotion pipeline is operational but shares pipeline's AND-chain flaw

### Key Insights
- **The zero-trade problem is universal across non-Claude paths.** Pipeline, promotions, AND refinement all produce 0-trade specs. The root cause is confirmed: specs with 3+ AND-chained entry conditions never co-fire on the same bar. All 8 ACCEPTs use exactly 2 conditions. New brain rule: max 2 entry conditions per side.
- **Promotion pipeline is a false positive.** 55 promotions ran today — the research-to-spec pipeline IS working mechanically. But it inherits the same combinatorial condition assembly as the autopilot pipeline. It generates spec volume, not quality.
- **10 Claude specs are the entire research frontier.** ALMA MACDh, Ichimoku TK, T3 Vortex, KAMA CCI, T3 EMA, Supertrend+KAMA (2 variants), Stochastic+CCI, VWAP+MACD, and Dual-MACD are all queued. At 22% ACCEPT rate, about 2 should hit. But they have not run because the backtester is consumed by pipeline/promotion zero-trade specs.
- **Research cards this cycle are mostly meta-commentary.** MichaelIonita videos about AI trading tools (GPT 5.2, ChatGPT Atlas, OpenClaw) do not contain tradeable strategies. The Gaussian Channel and Smart Trend HUD concepts map to existing indicator families.

### What I'm Testing Next
- Priority 0: Get all 10 Claude specs backtested on ETH 4h (30 variants total)
- Particularly watching: Ichimoku TK (tests if transition-detection generalizes beyond Vortex), VWAP MACD (first volume-weighted entry ever), and dual-adaptive Supertrend+KAMA (combines both proven adaptive architectures)
- If Ichimoku TK works: transition-detection is a GENERAL market mechanism, not a Vortex artifact — this would reshape the entire research agenda

### Suggestions For Asz
- **Route Claude specs to backtester immediately** — they are being starved by pipeline/promotion specs that produce nothing. Add priority routing: claude-* specs run first.
- **Kill or pause the pipeline** — 53 drought cycles, 150+ dedup batches, 55 zero-trade promotions today. It is consuming backtest compute for zero output.
- **Add signal feasibility pre-check** — reject specs where entry conditions co-occur less than 1% of bars before wasting a backtest slot. Would have saved 34+ wasted runs.
- **Promote KAMA Stoch v1 to third forward-test lane** — decorrelated from Vortex/Supertrend, PF=1.857, ranging PF=4.87.

---
