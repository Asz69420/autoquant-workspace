# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-05
**Order ID:** QO-2026-03-05-CLAUDE-FLUSH-01
**Intent:** Execute ALL 12 queued Claude specs on ETH 4h. Add 2 new high-priority specs. This is the ONLY work for the next 2 cycles. Zero pipeline specs.

### Context
- 170/182 backtests today = zero trades (93.4% waste from pipeline specs)
- 12 Claude specs (36+ variants) have been blocked for 5 consecutive cycles
- Pipeline has generated 102+ consecutive zero-trade backtests across 3 days
- Champion v3a PF may be decaying (2.034 → 1.959) — diversification is urgent
- At 22% ACCEPT rate, 2-3 new ACCEPTs are expected from this flush

### Execution Rules (non-negotiable)

1. **ZERO pipeline specs this cycle.** Do not run any spec that is NOT from `source: claude-advisor` or the 2 new specs below. No pipeline, no promotion, no refinement, no directive variants. Claude specs ONLY.

2. **Run ALL 12 existing Claude specs on ETH 4h.** The spec files are in `artifacts/strategy_specs/20260305/` with `claude` in the filename:
   - `claude-ikucloud` (Ichimoku cloud twist + KAMA)
   - `claude-vwapstk1` (VWAP + Stochastic pullback)
   - `claude-willr2e1` (Williams %R + EMA200 recovery)
   - `claude-chopsup1` (CHOP regime breakout + Supertrend)
   - `claude-t3suprt1` (T3 + Supertrend smooth transition)
   - `claude-kamasma1` (KAMA/SMA50 speed differential)
   - `claude-a7f3b1c2`, `claude-b7c2a9e6`, `claude-c9b0e2f7`
   - `claude-d4e1f8a3`, `claude-e5d8f4a9`, `claude-f3a8d5b1`

3. **Each spec has 2-3 variants. Run ALL variants on ETH 4h.** If a variant scores PF > 1.2, also run on ETH 1h as secondary test.

4. **Add these 2 NEW specs to the queue** (defined below):
   - Supertrend CCI v4 (4h port of 1h near-miss PF=1.480)
   - EMA200 Vortex v3 (stop-tightening for DD < 20%)

### New Strategy 1: Supertrend CCI v4 — 4h Port (Highest-Probability ACCEPT)

**Hypothesis:** Supertrend CCI v3 Wide scored PF=1.480 all-regime on ETH 1h but DD=36.43% killed it. Every 1h→4h port in our history reduces DD while maintaining or improving PF (4h-dominance pattern confirmed across 20+ tests). The CCI-as-trend-confirmation paradigm (CCI > 0 with Supertrend) outperforms CCI-as-mean-reversion (CCI Chop Fade PF=1.255). This is the highest-probability path to the next ACCEPT — known-profitable signal on the timeframe that fixes its only flaw.

name: supertrend_cci_v4_4h
template_name: spec_rules
entry_long:
- "SUPERTd_7_3.0 > 0"
- "CCI_20_0.015 > 0"
entry_short:
- "SUPERTd_7_3.0 < 0"
- "CCI_20_0.015 < 0"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

**Variant 2 (8:1 R:R):**
name: supertrend_cci_v4_4h_8to1
(same entry conditions)
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

**Variant 3 (tight stop):**
name: supertrend_cci_v4_4h_tight
(same entry conditions)
risk_policy:
  stop_type: atr
  stop_atr_mult: 0.75
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

### New Strategy 2: EMA200 Vortex v3 — Stop Tightening for Clean ACCEPT

**Hypothesis:** EMA200 Vortex v2 scored PF=1.969 with trans PF=4.321 (ALL-TIME RECORD) but DD=30% prevents clean ACCEPT. The Vortex family showed monotonic PF improvement with tighter stops (v1→v2c: 1.385→1.892). Tighter stop = less loss per loser, winners exit via reversal or TP anyway. EMA200 price filter already concentrates trades at genuine transitions — tighter stop should further reduce DD while preserving the record transitional alpha.

name: ema200_vortex_v3_tight
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "close > EMA_200"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "close < EMA_200"
risk_policy:
  stop_type: atr
  stop_atr_mult: 0.75
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

**Variant 2 (8:1 R:R):**
name: ema200_vortex_v3_8to1
(same entry conditions)
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix
- **Asset:** ETH only. No BTC (confirmed dead with strongest signal).
- **Timeframe:** 4h primary. 1h secondary only for specs that score PF > 1.2 on 4h.
- **Initial capital:** $10,000
- **Total runs expected:** ~42 (14 specs × 3 variants × 1 asset/timeframe)

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades per variant
- Regime breakdown (trending/ranging/transitional PF)
- **Rank ALL results by PF.** Flag any with PF > 1.2 AND DD < 20% as ACCEPT candidates.
- **Critical comparisons:**
  - Supertrend CCI v4 4h vs v3 Wide 1h: Did 4h fix the DD problem?
  - EMA200 Vortex v3 vs v2: Did tighter stop reduce DD below 20%?
  - Which Claude spec family produced the highest PF?
  - Which transition-detection mechanism (Vortex, Ichimoku, CHOP, WILLR, T3) performed best?

### Risk Guardrails
- Do not disable Balrog or repo hygiene gates.
- `risk_per_trade_pct <= 0.01`
- Max drawdown cap: 20% (standard)
- If any run hits safety FAIL, halt only that spec and continue others.

---

## Previous Order (archived)

**Status:** COMPLETE
**Order ID:** QO-2026-03-04-KICKSTART-01
**Result:** Pipeline ran 170 zero-trade backtests. Kickstart failed — pipeline cannot self-correct. Claude specs remain the only productive path.

