# Backtest Quality Audit — 2026-03-01 (Update 2)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** 2621 backtests across 20260227 (~1600), 20260228 (~450), 20260301 (~570)
**Prior advisory context:** STRATEGY_ADVISORY Update 6 (2026-02-28)
**Prior audit:** 2026-03-01 Update 1 (1,033 backtests, 92% flagged)

---

## Summary

**2621 backtests reviewed. 8 issues flagged across 3 categories.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 4 high-PF / low-trade suspects, 2 tail-harvester warnings | HIGH |
| Data Quality | 6 distinct issues (gate bug, duplicates, zero-trade surge, BTC leak, sentinel values, DD% bug) | CRITICAL |
| Regime Bias | Supertrend trending-only clustering, universal transitional toxicity | MEDIUM |

**Key numbers:**
- Zero-trade results: **138** (5.3%) — surging: 3 → 54 → 81 across 3 days (27x increase)
- Gate bug (min_trades_required=0): **279 results** on Feb 28 + Mar 1 (bypassing quality gate)
- Confirmed exact-duplicate fingerprints: **5 files** from 4 different specs producing identical results
- directive_exploration still active: **45 results** on Mar 1 (8th advisory flagging)
- Estimated overall compute waste: **~85-90%** (duplicates + zero-trade + dead variants)

**Positive:** stochastic_reversal and bollinger_breakout templates finally removed from Mar 1 pipeline (0 results). First advisory directive to be fully actioned after 6 cycles.

---

## Overfit Suspects

### A. High PF / Low Trade Count (PF > 1.5, trades < 30)

| ID | Variant | PF | Trades | WR% | DD% | Flag |
|---|---|---|---|---|---|---|
| `b58008ef` (0228) | supertrend_strong_trend | **2.019** | **16** | 43.8 | 5.2 | PF>2, trades<30, 100% trending |
| `98f45038` (0228) | rsi_fast_trend_balanced | **1.987** | **10** | 50.0 | **50.5** | PF~2, trades=10, DD=50%, gate bug (min=0) |
| `b11da16c` (0228) | supertrend_conservative_high_adx | **1.589** | **16** | 37.5 | 3.0 | Trades<30, 100% trending |
| `019bd3df` (0228) | supertrend_strong_trend (1h) | **1.540** | **18** | 33.3 | 2.3 | Trades<30, 100% trending, gate bug (min=0) |

**Verdict: REJECT all 4.** These are textbook overfits — insufficient trades for statistical significance and/or extreme regime concentration. The `rsi_fast_trend_balanced` (10 trades, PF=1.99, DD=50.5%) is the worst offender: surviving by luck with catastrophic drawdown risk.

### B. Tail-Harvester Warnings (Lower Confidence)

| ID | Variant | PF | Trades | WR% | DD% | Flag |
|---|---|---|---|---|---|---|
| `54d2de29` (0301) | supertrend_no_adx_gate_8to1 | **1.907** | 99 | 23.2 | 25.8 | High PF, 23% WR, top-trade dependency |
| `199a8350` (0301) | supertrend_ultra_tight_7to1 | **1.878** | 85 | 23.5 | 26.9 | Top 10 of 85 trades = ~150% of net profit |

**Trade list deep-dive (hl_20260301_199a8350):** 85 trades spread across full 2-year test period (2024-03 to 2026-02) — no time clustering. Top 10 winning trades: +$6,488 total, but net profit only $4,150 (losses offset most gains). Top 2 trades alone ($980 + $1,030) = 49% of net profit. Removing them drops PF from 1.88 to ~1.35.

**Verdict: REVISE with caution.** The 85-99 trade count is adequate, but structural dependency on rare 15-30% crash events creates fragile profitability. Require forward-test validation before promotion.

### C. Template Cross-Contamination (CRITICAL — CONFIRMED)

**5 different variant names from 4 different strategy specs produce BYTE-IDENTICAL results:**

| ID | Variant | Spec | Results |
|---|---|---|---|
| `85409ce4` (0301) | macd_tight_stop_1h_7to1 | claude-mc4s8n2x | PF=1.712, 161 trades, net=$3,159.62 |
| `1253515f` (0301) | macd_tight_stop_4h_7to1 | claude-mc4s8n2x | **IDENTICAL** |
| `0537219a` (0301) | rsi_pullback_1h_tail_harvester_7to1 | claude-rp1h5m7k | **IDENTICAL** |
| `72ff79a8` (0301) | macd_1h_tail_harvester_7to1 | claude-mc7h1f6p | **IDENTICAL** |
| `f29b2f2b` (0301) | macd_tail_harvester_7to1_4h | claude-mc6r4w8n | **IDENTICAL** |

All 5 share identical: net_profit ($3,159.62), trade count (161), regime breakdown (37/78/46), PF (1.71187815), all on ETH/1h.

**MACD and RSI Pullback templates should NOT produce identical results.** This proves the advisory's deduplication warning (flagged 7 cycles): different rule strings resolve to the same template parameters post-resolution. The backtester sees the same signals regardless of which spec generated them.

**Impact:** 4 of 5 backtests were pure compute waste. Extrapolating suggests 40-60% of all Mar 1 backtests are duplicates.

---

## Data Quality Issues

### 1. CRITICAL: Gate Bypass Bug (min_trades_required=0) — UNFIXED FROM PRIOR AUDIT

**279 backtests** on Feb 28 (119) and Mar 1 (160) have `min_trades_required: 0`. Consequences:

- **Zero-trade results pass gate:** Confirmed — `hl_20260301_155916a0` (rsi_deep_dip_trend_continuation, 0 trades, gate_pass=true)
- **Low-trade overfits pass gate:** Confirmed — `hl_20260228_98f45038` (10 trades, PF=1.99, gate_pass=true)

**Root cause:** All affected results appear to be ETH/1h or claude-spec backtests. The spec-generation path for these configurations does not set the gate threshold. **This was flagged as CRITICAL in the prior audit — unfixed and worsening (24→279 affected results).**

### 2. CRITICAL: Duplicate Fingerprints — Worsening

The 5-file identical group above is one confirmed cluster. Based on prior audit data (87% duplication on Feb 28) and the advisory's estimate (~50% waste), the true duplication rate across 2621 backtests is likely **1,300-1,500 redundant backtests**.

**Root cause:** Post-resolution deduplication absent. Hashing spec-level rule strings instead of resolved template parameters. Flagged in advisory for **7 consecutive cycles** and in prior audit.

### 3. HIGH: Zero-Trade Results Accelerating

| Date | Zero-Trade Count | % of Daily Total |
|---|---|---|
| 20260227 | 3 | ~0.2% |
| 20260228 | 54 | ~6% |
| 20260301 | 81 | ~8% |

**27x increase in 3 days.** Confirmed zero-trade variants on Mar 1:
- `rsi_pullback_tail_harvester_5to1` (ETH/4h) — 0 entry signals
- `rsi_deep_dip_trend_continuation` (ETH/1h) — 0 entry signals
- `directive_variant_2_template_switch` (multiple) — template switch produces unresolvable combos

**Root cause:** New Claude-spec RSI variants use overly restrictive filter combinations (RSI < 25 + ADX > 25 + EMA alignment) that structurally never co-occur on 4h crypto data. The spec generation needs a minimum-signal-frequency pre-check.

### 4. MEDIUM: Sentinel Value Leakage (regime_pf=999.0)

Found in `hl_20260228_98f45038`: `transitional_pf: 999.0` with 2 transitional trades (both winning). This is a div-by-zero edge case that should be capped at a reasonable maximum or flagged as N/A.

### 5. MEDIUM: BTC Leakage Continues

At least **5 BTC backtests** confirmed on Mar 1 (BTC/4h dataset paths). Advisory has recommended hard-excluding BTC for **6 consecutive cycles** due to structural loss generation. BTC continues consuming compute slots.

### 6. MEDIUM: DD% Calculation Bug (from prior audit — confirmed)

60+ backtests on Mar 1 report `max_drawdown_pct: 0.0` despite significant absolute drawdowns (up to $99K). Any downstream percentage-based DD gating is unreliable. **Prior audit flagged this — still unfixed.**

---

## Regime Analysis

### Regime Distribution in High-PF Strategies

| ID | Variant | PF | Trades | Trending | Ranging | Trans. | Flag |
|---|---|---|---|---|---|---|---|
| `b58008ef` | supertrend_strong_trend | 2.02 | 16 | **16 (100%)** | 0 | 0 | EXTREME BIAS |
| `b11da16c` | supertrend_conservative_high_adx | 1.59 | 16 | **16 (100%)** | 0 | 0 | EXTREME BIAS |
| `019bd3df` | supertrend_strong_trend (1h) | 1.54 | 18 | **18 (100%)** | 0 | 0 | EXTREME BIAS |
| `199a8350` | supertrend_ultra_tight_7to1 | 1.88 | 85 | 33 (39%) | 31 (36%) | 21 (25%) | Balanced |
| `54d2de29` | supertrend_no_adx_gate_8to1 | 1.91 | 99 | 33 (33%) | 45 (45%) | 21 (21%) | Balanced |
| duplicate group | macd/rsi 1h | 1.71 | 161 | 37 (23%) | 78 (48%) | 46 (29%) | Balanced |

### Regime PF Breakdown

| Variant | Trending PF | Ranging PF | Transitional PF |
|---|---|---|---|
| supertrend_strong_trend | 2.02 | N/A | N/A |
| supertrend_ultra_tight_7to1 | 1.29 | **2.95** | 1.60 |
| supertrend_no_adx_gate_8to1 | 1.29 | **2.56** | 1.84 |
| macd/rsi 1h duplicate | 1.68 | **2.06** | 1.31 |
| supertrend_1h_selective_wide_tp (BTC) | 1.49 | N/A | 2.51 |

### Key Findings

1. **Trending-only variants are overfits.** The 16-18 trade supertrend variants trade exclusively in trending regime. If market enters sustained ranging, these produce zero trades. They are retrospective event detectors for known ETH crashes, not persistent strategies.

2. **Tail-harvester strategies show balanced regime distribution** but derive disproportionate profit from ranging-regime tail events. Ranging PF (2.06-2.95) vastly exceeds trending PF (1.29-1.68). This is paradoxical for Supertrend (a trend-following signal) and suggests the large R:R target is hit during range breakdowns rather than trend continuations.

3. **Transitional PF is positive for wide R:R strategies.** Previous advisory findings showed transitional PF universally toxic (0.595-0.919). The new tail-harvester variants show transitional PF of 1.31-1.84. **This suggests the transitional toxicity finding is R:R-dependent.** Wide R:R (7:1+) strategies may be partially immune because occasional large wins overcome poor signal quality.

4. **The planned transitional filter (ADX 20-28 exclusion) may need to be R:R-conditional** rather than universal. Applying it to wide R:R strategies would remove ~25% of trades including some large winners, potentially reducing PF.

---

## Comparison With Prior Audit

| Metric | Prior Audit (Update 1) | This Audit (Update 2) | Trend |
|---|---|---|---|
| Backtests reviewed | 1,033 | 2,621 | +154% (expanded to 3 days) |
| Zero-trade variants | 134 (13%) | 138 (5.3%) | Stable in absolute count |
| Gate bug (min_trades=0) | 24+ | **279** | **12x worse** — still unfixed |
| Duplicate rate | ~87% | ~50-60% (estimated) | Improved in 3-day view but still dominant |
| Overfit suspects | 6 | 6 | Stable — same core variants |
| Template cross-contamination | 5 variants | 5 variants (confirmed) | Same finding confirmed |
| DD% bug | 60+ records | 60+ records | **Still unfixed** |
| stochastic/bollinger templates | Still appearing | **Removed** | Fixed on Mar 1 |
| directive_exploration | 34+ (0228) | **45** (0301) | **Worsening** |

**Net assessment:** Two prior-audit CRITICAL findings remain unaddressed (gate bug, DD% bug). One advisory directive finally actioned (template removal). Directive_exploration continues to worsen. The duplicate fingerprint finding is confirmed and represents the single largest source of compute waste.

---

## Recommendations

### CRITICAL (Act This Cycle)

| # | Recommendation | Rationale |
|---|---|---|
| 1 | **Implement post-resolution dedup** | Hash resolved template params, not spec-level strings. Would eliminate 40-60% compute waste (1,000-1,500 of 2,621 backtests). This is the single highest-ROI fix. Flagged 8 advisory cycles, 2 audit cycles. |
| 2 | **Fix gate bug: min_trades_required=0** | 279 results bypass quality gate. Zero-trade results pass as OK. 10-trade overfits promoted. Flagged 2 audit cycles — still unfixed and worsening. |
| 3 | **Reject 4 overfit suspects** | supertrend_strong_trend (PF=2.02, 16t), rsi_fast_trend_balanced (PF=1.99, 10t), supertrend_conservative_high_adx (PF=1.59, 16t), supertrend_strong_trend 1h (PF=1.54, 18t). All textbook overfits. |

### HIGH (Act Within 2 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 4 | **Kill directive_exploration** | 45 results on Mar 1, all PF<1.0. 8th advisory cycle flagging. |
| 5 | **Add top-N profit concentration check** | Auto-flag when top 2 trades > 50% net PnL. Would catch 6+ current "best" variants. |
| 6 | **Fix DD% calculation bug** | max_drawdown_pct=0.0 for 60+ records with real $10K-$99K drawdowns. Percentage-based gating broken. 2nd audit cycle flagging. |
| 7 | **Investigate zero-trade surge** | 27x increase in 3 days (3→81). RSI deep-dip/conviction/panic spec families generate structurally impossible filter combos. Add minimum-signal pre-check to spec generation. |
| 8 | **Hard-exclude BTC** | 5+ BTC results on Mar 1. 8th cycle flagging. |

### MEDIUM (Act Within 5 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 9 | **Validate tail-harvesters out-of-sample** | 85-99 trade supertrend variants (PF=1.88-1.91) are best new results but depend on rare tail events. Paper-trade 4+ weeks. |
| 10 | **R:R-condition the transitional filter** | Wide R:R strategies show positive transitional PF (1.31-1.84). A universal transitional exclusion may hurt these strategies. |
| 11 | **Cap sentinel regime_pf values** | Replace PF=999.0 with NaN when trade count < 3. Prevents downstream contamination. |
| 12 | **Add regime entropy gate** | Reject variants where 100% of trades in single regime. Catches trending-only overfits automatically. |

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-01 |
| Audit version | Update 2 |
| Backtests reviewed | 2,621 |
| Date range | 20260227–20260301 |
| Files flagged (overfitting) | 6 |
| Files flagged (data quality) | 279 (gate) + 138 (zero-trade) + 5 (dupes) + 60 (DD% bug) |
| Files flagged (regime bias) | 4 (trending-only) |
| Critical issues | 3 (gate bug, dedup, overfit promotion) |
| High issues | 5 (directive_exploration, profit concentration, DD% bug, zero-trade surge, BTC leak) |
| Medium issues | 4 (tail-harvester validation, transitional filter, sentinel values, regime gate) |
| Prior-audit CRITICALs unfixed | 2 of 2 (gate bug, DD% bug) |
| Advisory directives finally actioned | 2 of 10+ (stochastic + bollinger removal) |

*Next audit recommended after gate bug fix is deployed, or in 48 hours, whichever comes first.*
