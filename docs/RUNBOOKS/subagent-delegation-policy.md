# Sub-Agent Delegation Policy (BUILD_PATH)

## Rules

1. **FAST_PATH**: never spawn sub-agents
   - Read-only queries, toggles, approvals
   - Respond inline to main chat
   - No artifacts, no logging gates

2. **BUILD_PATH**: always delegate coding implementation via sub-agent
   - `route_request.ps1` routes to `run_work.ps1`
   - `run_work.ps1` shall spawn a coding sub-agent (implementer) first
   - Verifier runs automatically as part of BUILD_PATH loop (bounded by MaxAttempts)
   - Sub-agent lifecycle logged to action events (START/OK/WARN/FAIL)

3. **Main Chat Output: Strict Short Form**
   - Commit hash (e.g., `a1b2c3d`)
   - 1-line summary (e.g., `feat: short feature summary`)
   - Up to 3 bullets (status, risk level, user impact)
   - **NEVER** include diffs, full logs, or verifier details unless user says "show diff" or "show debug"

4. **Logging Artifacts: Full Detail**
   - Full verifier output → `artifacts/verifier/`
   - Full coding sub-agent output → `artifacts/coding/`
   - Build session ledger → `build_session_ledger.jsonl`
   - Task ledger → `task_ledger.jsonl`
   - Action events → `data/logs/actions.ndjson`

5. **Output Filtering: `Write-MainChatFiltered`**
   - Filter function suppresses:
     - JSON objects / arrays
     - Internal run_ids, reason_codes, route decisions
     - Artifact paths (`artifacts/verifier/`, `artifacts/coding/`)
     - Verifier-run IDs
   - Limit output to first 5 lines (user-facing summary only)

## Current Implementation Status

- ✅ Output filtering: `route_request.ps1` uses `Write-MainChatFiltered` (lines 120–130)
- ✅ Verifier integration: `run_work.ps1` invokes verifier via `openclaw agent --agent verifier`
- ✅ Ledger-based state machine: task_ledger.jsonl and build_session_ledger.jsonl track all state
- ⏳ Coding sub-agent spawning: placeholder for future (verifier role already in place)
- ✅ Action event logging: emit-LogEvent used throughout for audit trail

## Smoke Test Results

**Input:** `build smoke short response check`

**Main Chat Output (Filtered):**
```
Working on it - I will verify it and then ask for approval.
Build ready for your review
- What changed: requested updates implemented and verified
- Risk summary: PASS
- User impact: no immediate live impact
Apply these changes?
```

**Logs (Full Detail in artifacts/):**
- `artifacts/verifier/build-*.txt` — complete verifier feedback
- `build_session_ledger.jsonl` — full session state history
- `task_ledger.jsonl` — full task state trace
- `data/logs/actions.ndjson` — all action events (routing, verifier attempts, state transitions)

## Summary

Main chat remains concise (< 10 lines) while full execution detail is preserved in logs and artifacts. This satisfies operator DM noise suppression while maintaining full audit trail.
