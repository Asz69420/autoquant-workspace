# Council Single-Path Reliability Proof (2026-02-23)

## Scope
Implemented and verified `scripts/automation/council.ps1` for reliable single-path execution when user asks council mode.

## Code proof (single canonical path)
- `scripts/automation/council.ps1:271` → `# Canonical preflight probes (informational only; no path split)`
- `scripts/automation/council.ps1:299` → `# Round 1: both lanes (canonical path)`
- `scripts/automation/council.ps1:308` → `# Round 2: critiques (canonical path)`
- `scripts/automation/council.ps1:338` → `# Round 3: revisions (canonical path)`
- `scripts/automation/council.ps1:372` → `for ($r = 4; $r -le $rounds -and $material; $r++) {`
- Prior split branches (`single-model degraded path` / `both unavailable` path blocks) removed.

## Verification run
- Date: 2026-02-23 22:57 AEST
- Run command (mocked provider for deterministic verification):
  - `$env:OPENROUTER_API_KEY='mock-key'; $env:OPENROUTER_BASE_URL='http://127.0.0.1:18080'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/council.ps1 --question "Should we enable feature flag X for 5% of traffic this week?" --rounds 3 --name "Council Reliability Smoke"`

### Exact run_id
- `council-1771851460-0eabf7`

### Required lifecycle logs (same run_id)
- START file: `data/logs/outbox/20260223T125740Z___council-1771851460-0eabf7___oQ___START.json`
  - `"status_word": "START"`
  - `"run_id": "council-1771851460-0eabf7"`
  - `"reason_code": "COUNCIL_START"`
- Terminal file: `data/logs/outbox/20260223T125741Z___council-1771851460-0eabf7___oQ___OK.json`
  - `"status_word": "OK"`
  - `"run_id": "council-1771851460-0eabf7"`
  - `"reason_code": "COUNCIL_OK"`

### Both council lanes returned
- `[Round 1][GPT-5.3]` emitted with structured response.
- `[Round 1][MiniMax M2.5]` emitted with structured response.
- `[Round 3][GPT-5.3 revised]` and `[Round 3][MiniMax M2.5 revised]` both emitted.
- Execution summary: `Execution mode: normal` and `Failure reason: NONE`.

### Final merged result (exact)
- Recommended action: Roll out to 5% behind guardrails and rollback trigger.
- Confidence: Medium.
- Key risks: Latency regression under edge traffic.
- What would change decision: Error budget burn >20% baseline in canary.
- Immediate next test: 24h canary with automated rollback threshold.

## Future operator command (production)
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/automation/council.ps1 --question "<your decision question>" --rounds 5 --name "Council Decision"`
