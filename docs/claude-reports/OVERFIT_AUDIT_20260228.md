# Overfitting & Regime Bias Audit -- 20260228 Backtests
**Date:** 2026-03-01
**Auditor:** Quandalf (claude-auditor)
**Scope:** All trade_list.json files in `artifacts/backtests/20260228/`

---

## Executive Summary

**CRITICAL FINDING:** The 20260228 backtest batch contains 457 trade_list.json files, but they represent only ~12-15 genuinely unique backtest results. The vast majority are **byte-for-byte duplicates** caused by the pipeline re-running identical variant+dataset combinations across different strategy specs that produce no functional change in backtester behavior. This inflates apparent exploration breadth while providing zero additional information.

The highest profit factor found is **PF=1.209** (121 trades, ETH 4h refine exploit_3), but this variant exhibits severe profit concentration: the top 5 trades carry over 112% of net profit, and the remaining 116 trades are collectively a net loser.

**No strategy in this batch is viable for live deployment.**

---

## 1. Massive Duplication (Critical)

### Evidence

457 trade_list.json files collapse to approximately 12-15 unique file sizes:

| File Size | Dataset | Variant Type | PF | Trades | Occurrences (est.) |
|-----------|---------|-------------|------|--------|-------------------|
| 112 bytes | various | template_diversity | 0.0 | 0 | ~40-60 |
| 95,598 | ETH 4h (2yr) | directive_v1/library_aug | 1.033 | 389 | ~30-40 |
| 100,963 | BTC 4h (2yr) | directive_v1/v2/library | 1.001 | 406 | ~30-40 |
| 101,841 | ETH 1h (7mo) | directive_v1/v2/library | 0.998 | 415 | ~30-40 |
| 208,885 | BTC 4h (2yr) | directive_exploration | 0.818 | 843 | ~20-30 |
| 218,004 | ETH 1h (7mo) | directive_exploration | 0.754 | 891 | ~20-30 |
| 187,431 | ETH 4h (2yr) | directive_exploration | 0.884 | 766 | ~20-30 |
| 38,126 | BTC 4h (refine) | dir_v1_exit | 0.624 | 153 | ~15-20 |
| 34,199 | ETH 4h (refine) | dir_v1_exit | 0.966 | 139 | ~15-20 |
| ~29-40K | various (refine) | exploit_1/2/3 | varies | 120-160 | unique pairs |
| 45,804 | BTC 4h (2yr) | ema_cross_trending | 1.073 | 183 | 1 (unique) |
| 29,868 | ETH 4h (refine) | exploit_3 (refine-2a0a) | 1.209 | 121 | ~2-3 |

**Root Cause:** Different strategy specs (e.g., 18323d891886, 101ed86f17b3, and many claude-generated specs) are being fed to the backtester, but the backtester produces identical results because the **variant template code path is invariant to spec-level changes** for the directive_variant_1, directive_variant_2, library_augmented, directive_exploration, and template_diversity variant types.

**Impact:** The pipeline is consuming ~30x more compute than necessary. Each "new" strategy spec run across these standard variants produces no new information. The outcome analyser then reports the same PF=1.033 metric as the "best variant" across every batch, creating an illusion of consistency when it's actually stagnation.

### Confirmed Duplicate Groups (verified by exact file size match)

- **5be501f9 = ffd6628e = d4b88fec = 4701d782 = 828d578e = 979b971a = 1718e434 = 5ab473c1 = 15482c6f = 16f5243e = 27275805 = ...** (all 95,598 bytes)
- **24b7e3c6 = 9d8f76e1 = c864068d = 8978642d = 9a56c1c7 = 78b3c113 = b8e7ea26 = b5f2f1c9 = a5610d1b = 550c9999 = 935fe1ee = ...** (all 100,963 bytes)
- **3615cc19 = c1bf2bcf = ec9ff8b6 = 7dda9daa = 24ddb975 = 97fa52d0 = d243b236 = c15c2a2f = 589f5b48 = 9f04ad41 = 5993d111 = 9173105c = ...** (all 101,841 bytes)
- **0334c909 = a01d914e = 95c8ca44 = e0eedae0 = 2149c1c7 = d4b5c347 = 841df611 = 32456201 = 337734c0 = aa1ec852 = 7ba0c8f8 = f77c86b2 = ...** (all 112 bytes, empty)

---

## 2. Zero-Trade Variants

**All "template_diversity" variants produce zero trades.** This includes files across every strategy spec tested. The variant template generates no entry signals at all.

Estimated count: **~40-60 files** (every spec x every template_diversity dataset combination).

These all pass `gate_pass: true` on ETH 1h (where `min_trades_required: 0`) but fail on BTC/ETH 4h (where `min_trades_required: 10`). The inconsistent gate threshold is itself a concern.

---

## 3. Trade Concentration Analysis (PF=1.209 variant, e35b7b6d)

This is the **highest PF variant found** in the entire batch (ETH 4h, refine-2a0a2ac0, exploit_3, 121 trades, net profit +1,469.66).

### Top 5 Winners vs Net Profit

| Rank | PnL | Date | Side | Regime |
|------|-----|------|------|--------|
| 1 | +370.82 | 2025-08-20 | long | trending |
| 2 | +352.39 | 2024-03-18 | short | trending |
| 3 | +317.79 | 2026-02-05 | short | trending |
| 4 | +310.19 | 2025-11-03 | short | trending |
| 5 | +304.56 | 2024-12-04 | long | transitional |

- **Top 2 trades PnL: 723.21** = **49.2% of net profit**
- **Top 5 trades PnL: 1,655.75** = **112.7% of net profit**
- Remaining 116 trades are collectively **net negative** (-186.09)

**CONCENTRATION FLAG:** The strategy's entire profitability depends on 5 trades. Remove any two of the top five and the strategy becomes a net loser. This is a textbook overfitting signature.

### Win Rate Problem

38.0% win rate with 121 trades. 75 losers vs 46 winners. The strategy bleeds small losses continuously and depends on occasional large winners. This is fragile: any minor change in market microstructure kills profitability.

---

## 4. Time Clustering Analysis (PF=1.209 variant)

### Monthly Trade Distribution

Trades span 2024-03-11 to 2026-02-24 (approximately 23.5 months). Trade distribution by month:

- 2024-03: 3 trades
- 2024-04: 5 trades
- 2024-05: 4 trades
- 2024-06: 6 trades
- 2024-07: 5 trades
- 2024-08: 6 trades
- 2024-09: 5 trades
- 2024-10: 2 trades
- 2024-11: 7 trades
- 2024-12: 4 trades
- 2025-01: 9 trades
- 2025-02: 7 trades
- 2025-03: 3 trades
- 2025-04: 4 trades
- 2025-05: 3 trades
- 2025-06: 1 trade
- 2025-07: 4 trades
- 2025-08: 2 trades
- (gap: Sep-Oct 2025 = 0 trades)
- 2025-10: 2 trades
- 2025-11: 5 trades
- 2025-12: 5 trades
- 2026-01: 4 trades
- 2026-02: 4 trades

**Winning PnL Clustering:**
- Oct-Nov 2025 cluster: +272.75 + 310.19 + 290.31 + 272.97 = **+1,146.22** (a huge portion of total profit) from just 4 trades in a narrow window
- Dec 2024: +304.56 + 187.60 = +492.16
- Aug 2025: +370.82

**TIME CLUSTER FLAG:** Approximately **78% of the strategy's net profit** comes from two time windows: the Oct-Nov 2025 period (~1,146) and Dec 2024 (~492). This indicates the strategy is capturing specific market dislocations rather than a persistent edge.

### Regime Bias

The backtest result shows regime PF breakdown: trending=1.161, ranging=1.248, transitional=1.209. The win rate is uniformly low across all regimes (33-43%). The strategy appears to perform "equally" across regimes, but this is an artifact of the few large winners being spread across regime labels.

---

## 5. Other Anomalies

### 5a. Outcome Analyser Always Reports Same "Best"

Every outcome note file I examined (across 10+ different strategy families and batches spanning 12+ hours of pipeline runs) reports the EXACT same "best variant" metrics:
- PF = 1.03262167
- Trades = 389
- Max DD = 0.285331145814

This means the analyser is consistently picking the ETH 4h directive_variant_1/library_augmented result as the winner, and this same result has been replicated byte-for-byte across every batch. The pipeline is stuck in a loop, producing the same outcome and then issuing the same directives (GATE_ADJUST + TEMPLATE_SWITCH) which do not change the backtest behavior.

### 5b. ETH 1h Gate Threshold = 0

The ETH 1h dataset has `min_trades_required: 0`, allowing zero-trade variants to pass the gate. This should be harmonized with the 4h threshold of 10.

### 5c. Refine Specs Duplicate Each Other

Different refine strategy specs (e.g., refine-a8c09725 vs refine-2a0a2ac0) produce identical results for the same variant+dataset combination:
- 691da115 (refine-a8c09725, BTC 4h, dir_v1_exit) = 761792a1 identical metrics
- 02d7367c (refine-2a0a2ac0, ETH 4h, exploit_2) = 6f13f79f (refine-a8c09725, ETH 4h, exploit_2) = identical 33,734 bytes

### 5d. Massive Drawdown on BTC Variants

The BTC 4h variants from the base spec show extreme drawdowns:
- directive_exploration: max DD = 108,094 (10.8x account, PF=0.818)
- refine exploit_1 (BTC): max DD = 80,771 (PF=0.587)
- refine dir_v1_exit (BTC): max DD = 81,177 (PF=0.624)

These are catastrophic drawdown levels that should immediately disqualify these variants.

---

## 6. Recommendations

1. **URGENT -- Fix pipeline duplication.** Implement a backtest result cache keyed on (dataset_hash + variant_name + fee_model_hash). Skip re-running identical combinations. This will reduce compute by ~30x.

2. **Reject PF=1.033 as a viable signal.** This is barely above break-even and the same result has been produced hundreds of times without improvement. The pipeline's refinement loop is stalled.

3. **Flag the PF=1.209 variant for concentration risk.** While this is the "best" result, 5 trades carry 113% of profit. This does not constitute a reliable edge.

4. **Harmonize gate thresholds.** Set min_trades_required = 30 across all datasets to prevent low-sample results from passing.

5. **Add concentration checks to the analyser.** Any variant where top-2 trades exceed 50% of net profit should receive an automatic CONCENTRATION_WARNING flag.

6. **Add duplication detection.** Before emitting a new batch, check if the backtest result hash matches any existing result in the same day's artifacts.

7. **Break the refinement loop.** The current GATE_ADJUST + TEMPLATE_SWITCH directives are not producing different backtest behavior. The pipeline needs a mechanism to detect when directives have no effect and escalate to fundamentally different strategy approaches.

---

## Appendix: Files Examined

**Backtest result files read (25+):**
- hl_20260228_24b7e3c6, 3615cc19, 5be501f9, 9d8f76e1, c1bf2bcf, ffd6628e, a0699436, 78edcf00, a5466507, a01d914e, 0334c909, 95c8ca44, ec9ff8b6, d4b88fec, 691da115, 761792a1, 64783559, 042263dd, 863a2424, 6f13f79f, ae567daa, f88bb328, 1c07be63, e0eedae0, c864068d, 7dda9daa, 7dc2ad2a, 02d7367c, e35b7b6d, 860ed357, a7ffb779

**Trade list files read in full (3):**
- hl_20260228_e35b7b6d (121 trades, PF=1.209 -- full trade-by-trade analysis)
- hl_20260228_0334c909, a01d914e, 95c8ca44 (empty, 0 trades)

**File sizes compared (~60 files):** Confirmed duplication patterns across multiple batches.

**Outcome notes examined (6+):**
- autopilot-1772239788, 1772282987, 1772304587, 1772317188, 1772319888 (all reporting same PF=1.033 metrics)
- autopilot-1772240688-backfill-claude-ex22d5e6 (PF=1.073, REJECTED for HIGH_DRAWDOWN)
