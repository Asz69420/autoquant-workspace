#!/usr/bin/env python3
"""One-shot script to append Entry 023 to QUANDALF_JOURNAL.md"""
import pathlib

journal_path = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "shared" / "QUANDALF_JOURNAL.md"

entry = """

## Entry 023 \u2014 R:R Is Architecture-Dependent, HMM Adds 6th Framework (2026-03-06)

### Results
- **0 new ACCEPTs.** 11 unchanged since U31. No new backtest data since U33.
- Pipeline waste continues: 20+ more zero-trade directive outcomes today (300+ since kill)
- **15 Claude specs still blocked** \u2014 12 flush specs (5 cycles) + 3 U33 specs (3 cycles). Zero results.
- Supertrend CCI v4 variants (8:1, tight) both REJECT (DD=25-27%). Default 12:1 confirmed only viable config. Variants CLOSED.
- EMA200 family comprehensively dead: v3b 8:1 = v3 8:1 (identical results). Total 7 tests, all DD>20%. Confidence 0.97.
- Brain: 33 objects (+1 new fact: rr-architecture-dependent, 3 updated). 11 ACCEPTs unchanged.

### Key Insights
- **R:R optimization is architecture-dependent (NEW).** Supertrend CCI v4 at 8:1 improved PF (1.290 to 1.358) but DOUBLED DD (11.63% to 25.36%). The 8:1 sweet spot applies to transition-detection strategies (early entry) but NOT confirmation strategies (late entry). Confirmation enters after momentum is confirmed and needs wider TP (12:1) because the initial impulse is already spent.
- **Regime-level tradeoff:** 8:1 R:R shifts alpha from ranging (PF 1.989 to 1.548, -22%) to transitional (PF 2.777 to 3.291, +18%). Narrower TP captures medium transitions but loses ranging alpha.
- **HMM regime detection = 6th convergence framework.** Two new research cards (Baum-Welch HMM, HMM Reversal Finder) classify markets into Bull/Balance/Bear states probabilistically. Most mathematically rigorous of all 6 frameworks. Convergence confidence raised to 0.92.
- **kama_vortex_div still needs parameter redesign.** Template threshold (0.001 normalized) generates 0.18% fire rate. Needs widening to 0.003-0.005.

### What I am Testing Next
- **P0: Execute 15 blocked Claude specs** \u2014 12 flush + 3 U33 specs. 3-5 cycles overdue. Expected 3 ACCEPTs.
- **P1: kama_vortex_div parameter tuning** \u2014 widen kama_slope_threshold from 0.001 to 0.003
- **P2: Forward-test enrollment** \u2014 KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4
- **P3: Add TRIX_14** \u2014 12th cycle requesting

### Suggestions For Asz
- **URGENT: Confirm Claude spec execution status.** 15 specs, 0 results across 3-5 cycles. If queue cannot be fixed, run manually.
- **Tune kama_vortex_div threshold** \u2014 change default from 0.001 to 0.003 in signal_templates.py line 251
- **Add TRIX_14** \u2014 12th cycle. pandas_ta.trix(close, length=14).
- **Define forward-test graduation** \u2014 16th cycle requesting. 3 ACCEPTs waiting.

---
"""

with open(journal_path, "a", encoding="utf-8") as f:
    f.write(entry)

print(f"Entry 023 appended to {journal_path}")
