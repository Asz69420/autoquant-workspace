# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-05
**Order ID:** QO-2026-03-05-CLAUDE-ONLY-02
**Intent:** Pipeline is KILLED. Full backtest capacity for Claude specs. Execute remaining 12 Claude specs, untested variants, kama_vortex_divergence template, and 1 new EMA200 Vortex iteration.

### Context
- Pipeline officially killed — Claude-only execution confirmed
- Supertrend CCI v4 4h = NEW ACCEPT #11 (PF=1.290, DD=11.63%, ranging/transitional specialist)
- EMA200 Vortex v3 tight = REJECT (PF=1.365, DD=40% — 0.75 ATR stop too tight for EMA200-filtered entries)
- 12 of 14 ordered specs from QO-FLUSH-01 remain unexecuted
- Untested Supertrend CCI v4 variants (8:1 and tight stop) never ran
- kama_vortex_divergence template still untested after 4 cycles
- At 22% ACCEPT rate on 12 specs, expecting 2-3 new ACCEPTs

### Execution Rules

1. **Claude specs ONLY.** No pipeline, no promotion, no refinement, no directive specs. If it doesn't have `claude` in the source or isn't defined below, skip it.

2. **Run ALL 12 remaining Claude specs on ETH 4h.** These were ordered in QO-FLUSH-01 but never backtested:
   - `claude-ikucloud` (Ichimoku cloud twist + KAMA)
   - `claude-vwapstk1` (VWAP + Stochastic pullback)
   - `claude-willr2e1` (Williams %R + EMA200 recovery)
   - `claude-chopsup1` (CHOP regime breakout + Supertrend)
   - `claude-t3suprt1` (T3 + Supertrend smooth transition)
   - `claude-kamasma1` (KAMA/SMA50 speed differential)
   - `claude-a7f3b1c2`, `claude-b7c2a9e6`, `claude-c9b0e2f7`
   - `claude-d4e1f8a3`, `claude-e5d8f4a9`, `claude-f3a8d5b1`

3. **Run untested Supertrend CCI v4 variants on ETH 4h:**

**Variant 2 (8:1 R:R) — highest priority, 8:1 is historically the sweet spot:**
name: supertrend_cci_v4_4h_8to1
template_name: spec_rules
entry_long:
- "SUPERTd_7_3.0 > 0"
- "CCI_20_0.015 > 0"
entry_short:
- "SUPERTd_7_3.0 < 0"
- "CCI_20_0.015 < 0"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

**Variant 3 (tight stop):**
name: supertrend_cci_v4_4h_tight
(same entry conditions as above)
risk_policy:
  stop_type: atr
  stop_atr_mult: 0.75
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

4. **Run kama_vortex_divergence template on ETH 4h** — built-in template, combines two proven families (KAMA + Vortex = 7/10 ACCEPTs), tests exhaustion-detection mechanism, never tested in 4 cycles. Use default template params with these risk variants:

**Variant 1 (default 8:1):**
name: kama_vortex_div_v1
template_name: kama_vortex_divergence
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

**Variant 2 (10:1):**
name: kama_vortex_div_v1_10to1
template_name: kama_vortex_divergence
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

5. **NEW: EMA200 Vortex v3b — moderate stop with compressed TP**

**Hypothesis:** v3 tight (0.75 ATR) FAILED because EMA200 entries cluster at high-volatility transition zones where tight stops get whipsawed. v2 (1.0 ATR, 12:1) had PF=1.969 but DD=30%. Solution: keep the 1.0 ATR stop that works, but compress TP from 12 to 8 ATR. More winners should convert to TP hits before reversing, reducing unrealized-gain drawdown. This is the v2c pattern that worked for pure Vortex.

name: ema200_vortex_v3b_8to1
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "close > EMA_200"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "close < EMA_200"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

**Variant 2 (moderate tightening):**
name: ema200_vortex_v3b_10to1
(same entry conditions)
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

Also run the **untested v3 8:1 variant** from QO-FLUSH-01:
name: ema200_vortex_v3_8to1
(same entry conditions)
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix
- **Asset:** ETH only
- **Timeframe:** 4h primary. Run 1h secondary ONLY for specs scoring PF > 1.2 on 4h.
- **Initial capital:** $10,000
- **Total runs expected:** ~24 (12 Claude specs + 2 CCI variants + 2 kama_vortex_div + 3 EMA200 Vortex + some multi-variant Claude specs)

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades per variant
- Regime breakdown (trending/ranging/transitional PF)
- **Rank ALL results by PF.** Flag any with PF > 1.2 AND DD < 20% as ACCEPT candidates.
- **Critical comparisons:**
  - Supertrend CCI v4 8:1 vs default 12:1 (PF=1.290): Does 8:1 R:R improve PF?
  - EMA200 Vortex v3b 8:1 vs v2 12:1 (PF=1.969, DD=30%): Does TP compression fix DD?
  - kama_vortex_divergence: Does exhaustion-detection work? Is it decorrelated from transition-detection?
  - Which of the 12 Claude specs produced highest PF?

### Risk Guardrails
- Do not disable Balrog or repo hygiene gates.
- `risk_per_trade_pct <= 0.01`
- Max drawdown cap: 20% (standard)
- If any run hits safety FAIL, halt only that spec and continue others.

---

## Previous Order (archived)

**Status:** COMPLETE
**Order ID:** QO-2026-03-05-CLAUDE-FLUSH-01
**Result:** 2 of 14 specs executed. Supertrend CCI v4 4h = NEW ACCEPT (PF=1.290, DD=11.63%). EMA200 Vortex v3 tight = REJECT (DD=40%). 12 specs remain unexecuted.

---

## Previous Order (archived)

**Status:** COMPLETE
**Order ID:** QO-2026-03-04-KICKSTART-01
**Result:** Pipeline ran 170 zero-trade backtests. Kickstart failed — pipeline cannot self-correct. Claude specs remain the only productive path.
