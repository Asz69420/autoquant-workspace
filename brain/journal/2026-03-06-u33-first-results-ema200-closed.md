---
id: journal-2026-03-06-u33-first-results-ema200-closed
ts: "2026-03-06T01:30:00Z"
pointers:
  - fact-kama-vortex-template-untested
  - failure-ema200-dd-barrier
  - fact-claude-specs-sole-progress
  - fact-supertrend-cci-1h-allregime
  - failure-pipeline-structural-death
  - docs/shared/LAST_CYCLE_RESULTS.md
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-t3vtx01.strategy_spec.json
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-mchtrn01.strategy_spec.json
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-almcci01.strategy_spec.json
---

U33: First Claude spec execution since U31 — 7 specs backtested (all ETH 4h). kama_vortex_div generated 9 trades (1 short of 10 minimum gate), confirming exhaustion-detection mechanism works but needs parameter tuning. EMA200 Vortex family CLOSED after 3 generations (v2 DD=30%, v3 DD=40%, v3b DD=25-32%) — EMA200 entries cluster at high-volatility transition points making DD structurally unfixable. Supertrend CCI 8:1 variant PF=1.358 (up) but DD=25.36% (up) — default variant confirmed optimal. 3 new Claude specs written: T3 Vortex Transition, MACDh CHOP Transition, ALMA CCI Exhaustion (8 variants total). Pipeline waste continues: 30 outcomes ALL 0-trade REJECT. Brain: 32→33 objects (+1 failure: ema200-dd-barrier; 3 updated). 11 ACCEPTs unchanged.
