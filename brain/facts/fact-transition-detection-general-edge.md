---
id: fact-transition-detection-general-edge
type: fact
title: Transition-detection is a general market mechanism enabling all-regime profitability
status: active
confidence: 0.88
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/outcomes/20260304/
  - artifacts/research/20260304/
tags:
  - regime
  - transition
  - mechanism
  - ichimoku
  - vortex
  - trex
  - tasc-dm
supporting_ids:
  - fact-vortex-transition-edge
  - fact-transitional-highest-alpha
validated_at: "2026-03-05T12:00:00Z"
updated_at: "2026-03-05T12:00:00Z"
---

Transition-detection is a GENERAL market mechanism, not a Vortex-specific artifact. Multiple indicator families that detect the MOMENT markets shift between regime states achieve all-regime profitability on ETH 4h.

Evidence from two independent implementations:
- Vortex crossover (VTXP/VTXM): PF=2.034, all-regime, trans PF=3.886
- Ichimoku Tenkan-Kijun cross (ITS_9/IKS_26): PF=1.604, all-regime, 111 trades — NEW ACCEPT U24

Both use structurally different calculations (directional movement vs median-price smoothing) but share the common property: they detect regime TRANSITIONS at boundaries, not regime STATES.

Hypothesis validated from Entry 012: "If Ichimoku TK works, transition-detection is a general market mechanism." It worked.

Implications:
- Any indicator that detects change-of-direction (slope change, crossover, momentum flip) is a candidate for transition-detection strategy
- Next to test: KAMA slope change, T3 direction flip, TRIX zero-cross
- The underlying edge is timing: entering at regime boundaries captures moves in BOTH directions

Research card candidates (U26):
- TREX histogram (SoheilPKO): triple exponentially smoothed MA turned histogram. Detects trend reversals via zero-cross. Mathematically fits transition-detection model.
- TASC Directional Movement (SoheilPKO): uses Hilbert transform for phase detection. Mathematical regime transition detection at signal level.
- Both require new indicator columns before testing. Requested in U26 advisory.
