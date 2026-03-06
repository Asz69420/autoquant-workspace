---
id: fact-rr-architecture-dependent
type: fact
title: Optimal R:R ratio depends on strategy architecture — transition-detection 8:1, confirmation 12:1
status: active
confidence: 0.75
evidence_paths:
  - docs/shared/LAST_CYCLE_RESULTS.md
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - risk-reward
  - architecture
  - transition-detection
  - confirmation
  - regime-tradeoff
supporting_ids:
  - fact-supertrend-cci-1h-allregime
  - rule-minimum-rr-5to1
  - fact-vortex-transition-edge
contradictory_ids: []
validated_at: "2026-03-06T08:00:00Z"
updated_at: "2026-03-06T08:00:00Z"
---

The optimal reward-to-risk ratio is NOT universal — it depends on when the strategy enters relative to the move.

**Evidence:**

Transition-detection strategies (early entry):
- Vortex v3a: 8:1 R:R → PF=2.034, DD=15.2% (CHAMPION)
- Vortex v2c: 8:1 → PF=1.892, DD=12.3%
- All 6 Vortex ACCEPTs use 8:1 or similar
- Early entry = catches the full move → moderate TP (8 ATR) captures most of the opportunity

Confirmation strategies (late entry):
- Supertrend CCI v4 default 12:1 → PF=1.290, DD=11.63% (ACCEPT)
- Supertrend CCI v4 8:1 → PF=1.358, DD=25.36% (REJECT — DD doubled)
- Late entry = enters AFTER momentum confirmed → needs wider TP (12 ATR) because initial impulse already spent

Mean-reversion strategies:
- CCI Chop Fade 12:1 → PF=1.255, DD=16.4% (ACCEPT)
- Historical pattern: mean-reversion also benefits from wider TP

**Mechanism:**
- Early-entry strategies capture moves from the START → 8 ATR TP captures most profitable transitions
- Late-entry strategies enter MID-MOVE → 8 ATR TP exits before the move completes OR gets stopped by the same volatility that triggered the signal
- The 8:1 "sweet spot" applies to transition-detection. Confirmation and mean-reversion strategies need 10-12:1.

**Regime-level evidence (Supertrend CCI v4):**
- 8:1 transitional PF=3.291 (+18% vs 12:1) — narrower TP CAPTURES medium transitions
- 8:1 ranging PF=1.548 (-22% vs 12:1) — narrower TP loses ranging alpha
- Net effect: higher PF but catastrophic DD increase

**Minimum 5:1 rule still holds universally.** This fact refines the OPTIMAL R:R, not the minimum.

Confidence 0.75: based on one confirmation architecture (Supertrend CCI). Would rise to 0.90 with a second confirmation strategy showing same pattern.
