$ErrorActionPreference = 'Stop'

$QueuePath = 'data/state/build_queue.json'
$LockPath = 'data/state/build_queue.lock'
$QueueCap = 20
$LockStaleSeconds = 300

function Get-NowIso {
  return ([DateTimeOffset]::UtcNow.ToString('o'))
}

function Initialize-QueueState {
  $dir = Split-Path -Parent $QueuePath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  if (-not (Test-Path $QueuePath)) {
    $init = @{ active = $null; queue = @(); history = @() }
    Save-QueueState -State $init
  }
}

function Load-QueueState {
  Initialize-QueueState
  try {
    $raw = Get-Content -Path $QueuePath -Raw -Encoding utf8
    if ([string]::IsNullOrWhiteSpace($raw)) { return @{ active = $null; queue = @(); history = @() } }
    $obj = $raw | ConvertFrom-Json
    if ($null -eq $obj.active) { $obj | Add-Member -NotePropertyName active -NotePropertyValue $null -Force }
    if ($null -eq $obj.queue) { $obj | Add-Member -NotePropertyName queue -NotePropertyValue @() -Force }
    if ($null -eq $obj.history) { $obj | Add-Member -NotePropertyName history -NotePropertyValue @() -Force }
    return $obj
  } catch {
    throw "Queue state unreadable: $QueuePath"
  }
}

function Save-QueueState {
  param([Parameter(Mandatory = $true)]$State)
  $dir = Split-Path -Parent $QueuePath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $tmp = "$QueuePath.tmp"
  $json = ($State | ConvertTo-Json -Depth 20)
  Set-Content -Path $tmp -Value $json -Encoding utf8
  Move-Item -Path $tmp -Destination $QueuePath -Force
}

function Acquire-QueueLock {
  param([switch]$AllowStaleBreak)
  $dir = Split-Path -Parent $LockPath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

  $pidVal = $PID
  $now = [DateTimeOffset]::UtcNow
  $lockData = @{ pid = "$pidVal"; started_at = (Get-NowIso); heartbeat = (Get-NowIso) }

  if (-not (Test-Path $LockPath)) {
    Set-Content -Path $LockPath -Value ($lockData | ConvertTo-Json -Depth 5) -Encoding utf8
    return @{ Acquired = $true; Stale = $false; Reason = 'LOCK_ACQUIRED' }
  }

  try {
    $existing = (Get-Content -Path $LockPath -Raw -Encoding utf8 | ConvertFrom-Json)
    $hb = [DateTimeOffset]::Parse($existing.heartbeat)
    $age = ($now - $hb).TotalSeconds
    if ($age -gt $LockStaleSeconds) {
      if ($AllowStaleBreak) {
        Remove-Item -Path $LockPath -Force -ErrorAction SilentlyContinue
        Set-Content -Path $LockPath -Value ($lockData | ConvertTo-Json -Depth 5) -Encoding utf8
        return @{ Acquired = $true; Stale = $true; Reason = 'STALE_LOCK_REPLACED' }
      }
      return @{ Acquired = $false; Stale = $true; Reason = 'STALE_LOCK_PRESENT'; Existing = $existing }
    }
    return @{ Acquired = $false; Stale = $false; Reason = 'LOCK_ACTIVE'; Existing = $existing }
  } catch {
    if ($AllowStaleBreak) {
      Remove-Item -Path $LockPath -Force -ErrorAction SilentlyContinue
      Set-Content -Path $LockPath -Value ($lockData | ConvertTo-Json -Depth 5) -Encoding utf8
      return @{ Acquired = $true; Stale = $true; Reason = 'CORRUPT_LOCK_REPLACED' }
    }
    return @{ Acquired = $false; Stale = $true; Reason = 'LOCK_UNREADABLE' }
  }
}

function Update-QueueLockHeartbeat {
  if (-not (Test-Path $LockPath)) { return }
  try {
    $obj = Get-Content -Path $LockPath -Raw -Encoding utf8 | ConvertFrom-Json
  } catch {
    $obj = @{}
  }
  $obj.pid = "$PID"
  if (-not $obj.started_at) { $obj.started_at = (Get-NowIso) }
  $obj.heartbeat = (Get-NowIso)
  Set-Content -Path $LockPath -Value ($obj | ConvertTo-Json -Depth 5) -Encoding utf8
}

function Release-QueueLock {
  if (Test-Path $LockPath) { Remove-Item -Path $LockPath -Force -ErrorAction SilentlyContinue }
}

function New-QueueJobId {
  return ('job-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
}

function Enqueue-BuildJob {
  param(
    [Parameter(Mandatory = $true)][string]$Question,
    [string]$ChatId,
    [string]$MessageId,
    [string]$UpdateId,
    [Parameter(Mandatory = $true)][string]$IdemKey
  )
  $state = Load-QueueState

  if ($state.active -and $state.active.idem_key -eq $IdemKey) {
    return @{ Enqueued = $false; Duplicate = $true; Position = 1; Job = $state.active }
  }
  foreach ($j in @($state.queue)) {
    if ($j.idem_key -eq $IdemKey) { return @{ Enqueued = $false; Duplicate = $true; Position = 2; Job = $j } }
  }

  if (@($state.queue).Count -ge $QueueCap) {
    return @{ Enqueued = $false; QueueFull = $true; Cap = $QueueCap }
  }

  $job = [ordered]@{
    job_id = (New-QueueJobId)
    question = $Question
    created_at = (Get-NowIso)
    chat_id = $ChatId
    message_id = $MessageId
    update_id = $UpdateId
    idem_key = $IdemKey
  }
  $q = @($state.queue)
  $q += $job
  $state.queue = $q
  Save-QueueState -State $state

  $pos = @($state.queue).Count
  return @{ Enqueued = $true; Position = $pos; Job = $job }
}

function Dequeue-NextJob {
  $state = Load-QueueState
  $q = @($state.queue)
  if ($q.Count -eq 0) { return @{ Job = $null; State = $state } }
  $job = $q[0]
  if ($q.Count -gt 1) { $state.queue = @($q[1..($q.Count - 1)]) } else { $state.queue = @() }
  Save-QueueState -State $state
  return @{ Job = $job; State = $state }
}

function Cancel-NextJob {
  $state = Load-QueueState
  $q = @($state.queue)
  if ($q.Count -eq 0) { return @{ Cancelled = $false; Job = $null } }
  $job = $q[0]
  if ($q.Count -gt 1) { $state.queue = @($q[1..($q.Count - 1)]) } else { $state.queue = @() }
  $hist = @($state.history)
  $hist += [ordered]@{ job_id = $job.job_id; result = 'CANCELLED'; ended_at = (Get-NowIso) }
  $state.history = $hist | Select-Object -Last 100
  Save-QueueState -State $state
  return @{ Cancelled = $true; Job = $job }
}

function Clear-Queue {
  $state = Load-QueueState
  $q = @($state.queue)
  $count = $q.Count
  $hist = @($state.history)
  foreach ($job in $q) {
    $hist += [ordered]@{ job_id = $job.job_id; result = 'CANCELLED'; ended_at = (Get-NowIso) }
  }
  $state.queue = @()
  $state.history = $hist | Select-Object -Last 100
  Save-QueueState -State $state
  return @{ Cleared = $count }
}

function Get-QueueStatus {
  $state = Load-QueueState
  $active = $state.active
  $queue = @($state.queue)
  return @{ Active = $active; Queue = $queue; QueueCount = $queue.Count }
}
