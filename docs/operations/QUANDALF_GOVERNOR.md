# Quandalf Governor (Token + Context Control)

## Purpose
Keep Quandalf tasks efficient long-term without blinding strategy quality.

## Files
- Config: `config/quandalf_governor.json`
- Resolver: `scripts/claude-tasks/resolve-quandalf-governor.ps1`
- Applied in:
  - `scripts/claude-tasks/run-strategy-generator.ps1`
  - `scripts/claude-tasks/run-strategy-researcher.ps1`
  - `scripts/claude-tasks/run-doctrine-synthesizer.ps1`
  - `scripts/claude-tasks/run-backtest-auditor.ps1`

## How it works
1. Each task resolves a governor tier (`lite|standard|deep`) at start.
2. Tier sets hard scope caps (outcome notes, backtest horizon/count, research cards, spec count, library rows).
3. The prompt uses those caps explicitly.
4. Task log includes governor line (tier + limits) for auditability.

## Escalation logic
- Default tier is mode-based (`mode_defaults` in config).
- If `QUANDALF_ORDERS.md` has `Status: PENDING|NEW` and mode is generator/researcher, tier escalates to `deep`.
- If recent mode log shows model limit/rate-limit signal, tier downgrades to `lite`.

## Tuning
Edit `config/quandalf_governor.json`:
- `tiers` for budget sizes
- `mode_defaults` for per-task baseline
- `escalation` toggles

## Verification
- Check latest `data/logs/claude-tasks/*.log` for:
  - `Governor tier=...`
- Confirm tasks still complete and outputs are produced in:
  - `docs/claude-reports/`
  - `docs/shared/`
  - `brain/`

## Notes
- This controls scheduled Claude-task workload, not Frodex backtesting.
- `quandalf-auto-execute` remains on `quandalf-lite` for low-burn orchestration.
