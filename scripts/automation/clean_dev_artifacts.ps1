param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$protected = @(
  'BASELINE_MANIFEST.json',
  'USER.md','USER-EXTENDED.md',
  'AGENTS-CORE.md','AGENTS-FULL.md',
  'SOUL-DIGEST.md','SOUL-FULL.md',
  'MEMORY-INDEX.md'
)

function Is-ProtectedPath([string]$rel) {
  $n = $rel.Replace('\\','/').TrimStart('./')
  if ($protected -contains $n) { return $true }
  if ($n -like 'memory/MEMORY-FULL-*.md') { return $true }
  if ($n -like 'data/*') { return $true }
  if ($n -like '*ledger*.jsonl') { return $true }
  return $false
}

$repoRoot = (Resolve-Path '.').Path
$tracked = @{}
(git ls-files) | ForEach-Object { if($_){ $tracked[$_.Replace('/','\')] = $true } }

$targets = @()

if (Test-Path 'tmp') {
  $targets += Get-ChildItem 'tmp' -Recurse -Force -File | ForEach-Object { $_.FullName }
}

$targets += Get-ChildItem 'docs/DAILY' -Filter '*-summary.md' -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
$targets += Get-ChildItem 'docs/HANDOFFS' -Filter 'handoff-*.md' -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
$targets += Get-ChildItem 'memory' -Filter '*-route-spam.md' -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }

$targets = $targets | Sort-Object -Unique

$deletable = @()
foreach ($path in $targets) {
  $full = (Resolve-Path -LiteralPath $path).Path
  $rel = $full.Substring($repoRoot.Length).TrimStart('\')
  $relNorm = $rel.Replace('/','\')
  if ($tracked.ContainsKey($relNorm)) { continue }
  if (-not (Is-ProtectedPath $rel)) {
    $deletable += [pscustomobject]@{ FullPath=$full; RelPath=$rel }
  }
}

if ($deletable.Count -eq 0) {
  Write-Output 'No dev artifacts matched cleanup rules.'
  exit 0
}

Write-Output ("Artifacts matched: " + $deletable.Count)
$deletable | ForEach-Object { Write-Output ("- " + $_.RelPath) }

if ($DryRun) {
  Write-Output 'Dry run only. No files deleted.'
  exit 0
}

foreach ($item in $deletable) {
  Remove-Item -LiteralPath $item.FullPath -Force -ErrorAction SilentlyContinue
}

if (Test-Path 'tmp') {
  $remaining = Get-ChildItem 'tmp' -Recurse -Force -ErrorAction SilentlyContinue
  if (-not $remaining) {
    Remove-Item 'tmp' -Force -ErrorAction SilentlyContinue
  }
}

Write-Output ("Deleted: " + $deletable.Count)
