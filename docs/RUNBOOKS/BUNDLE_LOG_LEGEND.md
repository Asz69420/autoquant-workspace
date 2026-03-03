# Bundle Log Legend (Frodex)

This file is the canonical meaning of the compact activity labels used in `scripts/automation/bundle-run-log.ps1` for `-Pipeline frodex`.

## Activity Labels

- **Ingested**
  - New inputs pulled into the lab pipeline in the reporting window.
  - Primary source: `LAB_SUMMARY` (`ingested=N`).

- **Submitted**
  - Candidates submitted into validation/backtest flow.
  - Computation order in logger:
    1) `bundlesSelected` (preferred), else
    2) `bundleStarts`, else
    3) total specs observed (`specOk + specBlocked + specReview`).

- **Passed**
  - Specs that passed validation gates.
  - Primary source: `BUNDLE_SPEC_RESULT` with `spec_status=OK`.

- **Backtests**
  - Backtests actually executed in the window.
  - Primary source: `BATCH_BACKTEST_SUMMARY` (`executed=N`).

- **Promoted**
  - Variants promoted/advanced by promotion gates.
  - Primary source: `PROMOTION_SUMMARY` with `status=OK` and promotion counters.

- **Queue lag**
  - Number of unsent events waiting in `data/logs/outbox`.
  - `0` is healthy.

- **Tested**
  - Forward-testing checks/runs executed in the window.
  - Primary source: `data/forward/FORWARD_LOG.ndjson` (`RUN_OK`).

## Notes

- The Telegram bundle log should stay compact: activity counts + short human note.
- Legend details live here in repo (not in the log payload).
- If labels or sourcing logic change, update this file and `bundle-run-log.ps1` in the same commit.
