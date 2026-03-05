# Automation V2 Runbook

## Scope
Phase 1 introduces manifest-driven Task Scheduler management scripts only:

- `scripts/automation/install_v2_tasks.ps1`
- `scripts/automation/verify_v2_tasks.ps1`
- Manifest source: `config/automation_v2_manifest.json`

No automatic task starts/stops are performed by this phase.

---

## Prerequisites

- Windows PowerShell 5.1
- Access to Scheduled Tasks on the host
- Repository root: `C:\Users\Clamps\.openclaw\workspace`

---

## Install / Update Tasks

### Dry run (recommended first)

```powershell
cd C:\Users\Clamps\.openclaw\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/install_v2_tasks.ps1 -DryRun
```

### Apply manifest changes

```powershell
cd C:\Users\Clamps\.openclaw\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/install_v2_tasks.ps1 -Apply -NoStart
```

Notes:
- Installer only creates/updates tasks listed in manifest (`tasks[]` where `type=task`).
- Hidden/no-popup defaults are enforced via hidden PowerShell task actions.
- `-NoStart` is accepted for explicit safety signalling; this phase does not start tasks.

---

## Verify Live Tasks vs Manifest

```powershell
cd C:\Users\Clamps\.openclaw\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/verify_v2_tasks.ps1
```

Verifier compares, per task:
- task presence by name
- schedule shape (`daily`, `weekly`, `interval`)
- command execution arguments
- owner metadata (if present in task description)

Output lines are tagged `PASS`, `WARN`, or `FAIL` and end with a summary.

---

## Rollback

### Option A: Re-apply legacy per-task scripts

Use legacy setup scripts to restore prior definitions (examples):

```powershell
cd C:\Users\Clamps\.openclaw\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/setup_autopilot_task.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/setup_oragorn_context_sync_task.ps1
# ...run other legacy setup_* scripts as needed
```

### Option B: Restore from git revision

```powershell
cd C:\Users\Clamps\.openclaw\workspace
git checkout <known-good-commit> -- config/automation_v2_manifest.json scripts/automation/
```

Then apply installer again in dry-run/apply sequence.

---

## Operational Sequence

1. `install_v2_tasks.ps1 -DryRun`
2. `install_v2_tasks.ps1 -Apply -NoStart`
3. `verify_v2_tasks.ps1`
4. Investigate any `FAIL` before production promotion

---

## Quandalf Governor

Scheduled Quandalf Claude tasks now run under a context/token governor.

- Config: `config/quandalf_governor.json`
- Resolver: `scripts/claude-tasks/resolve-quandalf-governor.ps1`
- Guide: `docs/operations/QUANDALF_GOVERNOR.md`

This keeps runs efficient by default and escalates scope only when needed (e.g., pending strategy orders).
