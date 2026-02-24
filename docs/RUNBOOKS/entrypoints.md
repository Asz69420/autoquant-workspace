# Production Entrypoints Map

## Canonical (active)
- Request router: `scripts/automation/route_request.ps1`
- Build runner: `scripts/automation/run_work.ps1`
- Approval resolver: `scripts/automation/resolve_approval_intent.ps1`
- Build-session approval applier: `scripts/automation/approve_build_session.ps1`
- Keeper runner (scheduled): `scripts/keeper/runner_v2.py`

## Legacy / compatibility (not canonical)
- Legacy keeper runner (archived): `scripts/keeper/legacy/runner.py`
  - **Deprecated**: not scheduled; do not use.
- Task-level approval script: `scripts/automation/approve_work.ps1`
  - **Legacy compatibility**: prefer build-session approvals via `approve_build_session.ps1`.

## Notes
- `scripts/automation/fresh_session_replay.ps1` is a replay harness for audits/testing.
- Canonical approval path is build-session based.
