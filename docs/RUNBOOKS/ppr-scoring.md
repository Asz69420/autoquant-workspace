# Runbook: PPR Scoring System (PASS / PROMOTE)

## Purpose
PPR (Pipeline Performance Rating) is the canonical quality score for strategy runs.

- Scale: **0.0 to 10.0**
- Decisions:
  - **FAIL**: score < 1.0
  - **PASS**: score >= 1.0
  - **PROMOTE**: score >= 3.0
  - **SUSPECT**: high-PF/low-sample guardrail

PPR is used to standardize quality gating and pass-library inclusion.

---

## Formula
`PPR = 10 * Edge * Resilience * Grade`

Components (all clamped to [0,1]):

1) **Edge**
- `Edge = (min(PF, 2.5) - 1.0) / (2.5 - 1.0)`

2) **Resilience**
- `Resilience = 1 - (MaxDD_pct / 40)`

3) **Grade**
- `Grade = trade_count / 30`

### Hard Guards
- If `trade_count < 10` => `FAIL` (`LOW_SAMPLE_HARD_FAIL`)
- If `PF > 4.0` and `trade_count < 25` => `SUSPECT` (`HIGH_PF_LOW_SAMPLE`)

---

## Canonical Implementation
- `scripts/pipeline/ppr_score.py`
  - `compute_ppr(...)`
  - Thresholds: `pass_min=1.0`, `promote_min=3.0`

---

## Data Contract

### Backtest artifact
Each backtest result includes:
- `ppr.name`
- `ppr.version`
- `ppr.score`
- `ppr.decision`
- `ppr.components.edge|resilience|grade`
- `ppr.inputs.profit_factor|max_drawdown_pct|trade_count`
- `ppr.thresholds.pass_min|promote_min`
- `ppr.flags[]`

Producer:
- `scripts/backtester/hl_backtest_engine.py`

### Batch artifact summary
Each batch summary includes:
- `ppr_pass_count`
- `ppr_promote_count`
- `ppr_fail_count`
- `ppr_suspect_count`

Producer:
- `scripts/pipeline/run_batch_backtests.py`

### Autopilot logs
Batch summary lines now emit PPR counts alongside gate counts.

Producer:
- `scripts/pipeline/autopilot_worker.ps1`

---

## Libraries (Scalable)
PASS/PROMOTE strategies are stored in a scalable multi-tier library:

- **Hot (7d):** `artifacts/library/PASSED_HOT_7D.json`
- **Warm (14d):** `artifacts/library/PASSED_WARM_14D.json`
- **Alias (compat):** `artifacts/library/PASSED_INDEX.json` (points to hot)
- **Archive (uncapped):** `artifacts/library/passed/YYYY-MM.passed.ndjson`
- **Summary metadata:** `artifacts/library/PASSED_INDEX_SUMMARY.json`

Builder:
- `scripts/pipeline/run_librarian.py`

Notes:
- Inclusion is PPR-driven (`PASS` or `PROMOTE`), not legacy gate-only.
- Summary includes `score_system` metadata and hot/warm decision counts.

---

## Leaderboard
Leaderboard prioritizes PPR ranking.

Renderer:
- `scripts/pipeline/render_leaderboard.py`

Display includes PPR, PF, WR, TC, DD.

---

## Operational Commands

Rebuild library windows and summary:
```powershell
python scripts/pipeline/run_librarian.py --hot-days 7 --warm-days 14
```

Render leaderboard JSON:
```powershell
python scripts/pipeline/render_leaderboard.py --json
```

---

## Future Extension
- cPPR (combined robustness score) can be added post-promotion.
- PPR remains the pass/promote gate unless policy is revised.
