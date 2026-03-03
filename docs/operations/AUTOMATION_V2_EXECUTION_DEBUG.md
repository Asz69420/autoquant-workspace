# AUTOMATION V2 — Execution + Debug Playbook

Purpose: a deterministic, repeatable checklist for migration and fast recovery if automation degrades.

## 0) Ground Rules

1. One owner per function (Task or Cron, never both).
2. No live edits without snapshot + rollback path.
3. Keep output parity (same channel, same format) before disabling legacy jobs.
4. All commands run from Admin PowerShell unless noted.

---

## 1) Pre-Cutover Snapshot (Mandatory)

```powershell
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$root = 'C:\Users\Clamps\.openclaw\workspace'
$arc = Join-Path $root ("data\archive\automation-pre-v2-" + $ts)
New-Item -ItemType Directory -Force -Path $arc | Out-Null

Get-ScheduledTask | Where-Object {$_.TaskName -like 'AutoQuant-*'} | Sort-Object TaskName |
  ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $arc 'scheduled_tasks.json')

openclaw cron list | Out-String | Set-Content -Encoding UTF8 (Join-Path $arc 'openclaw_cron_list.txt')

git rev-parse HEAD | Set-Content -Encoding UTF8 (Join-Path $arc 'git_head.txt')
git status --short | Set-Content -Encoding UTF8 (Join-Path $arc 'git_status.txt')
```

---

## 2) V2 Install (Manifest-Driven)

Dry run first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\automation\install_v2_tasks.ps1" -DryRun
```

Apply:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\automation\install_v2_tasks.ps1" -Apply -NoStart
```

Verify:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\automation\verify_v2_tasks.ps1"
```

Expected: `FAIL=0` before disabling any legacy jobs.

---

## 3) Critical Path Smoke Tests (Must Pass)

### 3.1 Frodex ops + bundle
```powershell
Start-ScheduledTask -TaskName "frodex-ops-loop-15m"
Start-Sleep -Seconds 10
Start-ScheduledTask -TaskName "frodex-bundle-log-15m"
```

### 3.2 Quandalf journal path
```powershell
Start-ScheduledTask -TaskName "quandalf-research-4h"
```
Check DM receives expected journal format (no directives dump, no duplicate unchanged entry).

### 3.3 Forward lane
```powershell
Start-ScheduledTask -TaskName "frodex-forward-runner-4h"
Start-Sleep -Seconds 10
Start-ScheduledTask -TaskName "frodex-forward-health-4h"
```

---

## 4) Legacy Cutover (Only after smoke passes)

Disable old jobs that overlap with V2 equivalents:

```powershell
@(
  'AutoQuant-autopilot-user',
  'AutoQuant-bundle-run-log-user',
  'AutoQuant-bundle-run-log-quandalf-user',
  'AutoQuant-youtube-watch-user',
  'AutoQuant-Claude-Researcher',
  'AutoQuant-Claude-Generator',
  'AutoQuant-Claude-Doctrine',
  'AutoQuant-Claude-Auditor',
  'AutoQuant-daily-intel-user',
  'AutoQuant-transcript-ingest-user',
  'AutoQuant-Forward-Runner',
  'AutoQuant-Forward-Health',
  'AutoQuant-Forward-Weekly',
  'AutoQuant-Oragorn-ContextSync'
) | ForEach-Object {
  if (Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue) {
    Disable-ScheduledTask -TaskName $_ | Out-Null
  }
}
```

Keep non-overlap maintenance as-is unless explicitly migrated.

---

## 5) Monitoring/SLO Checks

Run every check window:

```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like '*frodex*' -or $_.TaskName -like '*quandalf*' -or $_.TaskName -like '*oragorn*'} |
  Sort-Object TaskName |
  ForEach-Object {
    $i = Get-ScheduledTaskInfo -TaskName $_.TaskName
    [pscustomobject]@{Task=$_.TaskName;State=$_.State;LastResult=$i.LastTaskResult;LastRun=$i.LastRunTime;NextRun=$i.NextRunTime}
  } | Format-Table -AutoSize
```

Pass criteria:
- LastResult = 0 on core jobs
- Expected logs/files update on schedule
- No duplicate sender noise

---

## 6) Fast Debug Matrix

### Symptom: Bundle missing
Check:
1) Task `LastRunTime` moved?
2) `data/logs/bundle-run-log.last.txt` timestamp changed?
3) `actions.ndjson` has events in bundle window?

Quick test:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\automation\bundle-run-log.ps1" -Pipeline frodex -WindowMinutes 120
```

### Symptom: Journal not received
Check:
1) `quandalf-research-4h` last run result
2) `docs/shared/QUANDALF_JOURNAL.md` updated?
3) duplicate hash suppression file (`data/logs/claude-tasks/last-journal-dm.sha256`)

### Symptom: Forward alerts stale
Check:
1) `data/forward/FORWARD_LOG.ndjson` moving
2) `frodex-forward-runner-4h` and health task result

---

## 7) Rollback (Immediate)

If V2 degrades output, revert to pre-cutover state:

1) Re-enable legacy tasks from snapshot list.
2) Disable V2 renamed tasks.
3) Confirm core legacy tasks are `Ready` and firing.

Emergency re-enable template:

```powershell
Get-Content "data\archive\<snapshot>\scheduled_tasks_table.txt"
# Re-enable required legacy names manually or from stored list.
```

---

## 8) Change Log Discipline

For every migration change:
- Record commit hash
- Record tasks added/disabled
- Record exact verify output (`PASS/WARN/FAIL` counts)
- Record rollback command used

This file is the canonical step-by-step debug reference.
