$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

New-Item -ItemType Directory -Force -Path "$ROOT\docs\claude-reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\logs\claude-tasks" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\state\locks" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "$ROOT\data\logs\claude-tasks\doctrine_$timestamp.log"
$sharedLockDir = "$ROOT\data\state\locks\quandalf_pipeline.lockdir"

$gov = & "$ROOT\scripts\claude-tasks\resolve-quandalf-governor.ps1" -Mode "doctrine_synthesizer" -Root $ROOT
$maxOutcomeNotes = [int]$gov.max_outcome_notes
$governorTier = [string]$gov.tier

if (Test-Path -LiteralPath $sharedLockDir) {
  try { python scripts/log_event.py --agent "claude-advisor" --action "doctrine_synthesis" --status WARN --summary "Skipped: shared Quandalf pipeline lock is held by another task." | Out-Null } catch {}
  Write-Output "[$timestamp] Skipped: shared Quandalf pipeline lock held" | Tee-Object -FilePath $logFile -Append
  exit 0
}

New-Item -ItemType Directory -Path $sharedLockDir | Out-Null

try {

$prompt = @"
MODE: DOCTRINE_SYNTHESIZER

You are the Doctrine Curator for AutoQuant.
Keep the Analyser doctrine clean, actionable, and free of noise.

READ these files (governor tier: $governorTier):
1. docs/DOCTRINE/analyser-doctrine.md (current doctrine)
2. Latest $maxOutcomeNotes outcome notes in artifacts/outcomes/
3. docs/claude-reports/STRATEGY_ADVISORY.md (if exists)

TASKS:
1. REMOVE entries that are opaque YouTube video IDs with no actionable content, duplicate rules saying the same thing, or contradicted by newer evidence
2. CONSOLIDATE entries that express the same principle into one clear rule
3. ADD new principles derived from recent outcome patterns not yet captured
4. REWRITE unclear entries into actionable format like:
   [date|conf:X] Clear actionable rule with evidence basis

IMPORTANT:
Write the cleaned doctrine to docs/claude-reports/DOCTRINE_PROPOSED.md (NOT the original file).
The original should only be updated by the pipeline update_analyser_doctrine.py script.

After writing, emit notification:
python scripts/log_event.py --agent "claude-advisor" --action "doctrine_synthesis" --status OK --summary "Doctrine cleaned: removed N, consolidated N, added N"
"@

Write-Output "[$timestamp] Starting Doctrine Synthesizer..." | Tee-Object -FilePath $logFile -Append
Write-Output "[$timestamp] Governor tier=$governorTier outcome_notes=$maxOutcomeNotes" | Tee-Object -FilePath $logFile -Append
claude -p $prompt --allowedTools "Read,Write,Bash(python scripts/log_event.py*)" 2>&1 | Tee-Object -FilePath $logFile -Append
Write-Output "[$timestamp] Completed: $LASTEXITCODE" | Tee-Object -FilePath $logFile -Append

$proposedDoctrine = "$ROOT\docs\claude-reports\DOCTRINE_PROPOSED.md"
if (Test-Path $proposedDoctrine) {
  powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
    -TaskLabel "doctrine cycle" `
    -SourceFile $proposedDoctrine | Out-Null
}
}
finally {
  Remove-Item -LiteralPath $sharedLockDir -Recurse -Force -ErrorAction SilentlyContinue
}