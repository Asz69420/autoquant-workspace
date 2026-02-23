# Build QC Gate (Significant Changes)

Purpose: add a fast second-pass quality check before final handoff on significant builds.

Canonical contract: `docs/CONTRACTS/verification-gate.md`.
If this runbook conflicts with that contract, the contract wins.

## Trigger condition (significant build)
Use the objective trigger matrix in `docs/CONTRACTS/verification-gate.md`.
Fail-closed rule applies: if significance is unknown/partial, treat as significant.

Skip gate only when clearly trivial under that contract.

### Proposal-stage loop rule (non-negotiable)
Proposal-stage QC is internal and continuous:
- FAIL -> revise -> re-audit (repeat) until PASS.
- No FAIL-stage pause-for-user is allowed.
- If a hard safety ceiling is configured and reached, transition to BLOCKED with explicit reason_code.

## Gate pattern
1. For significant builds, prepare proposal package first (plan + file list + preview/diff + acceptance criteria).
2. Run 🔰 Verifier proposal QC before any approval ask.
3. Require a valid proposal artifact at checkpoint `pre_implementation` with stage=`proposal`, status=`PASS`, and matching `scope_fingerprint`.
4. If proposal QC fails: auto-revise bill and re-run proposal QC until PASS.
5. Send one clean verified bill only after proposal PASS; wait for explicit standalone user approval.
6. Implement/write + commit only after approval token gate passes.
7. Run 🔰 Verifier implementation QC.
8. Require a valid implementation artifact at checkpoint `pre_handoff` with stage=`implementation`, status=`PASS|PARTIAL`.
9. If required artifact is missing/invalid at either checkpoint: mark `PROCESS_INVALID`, stop progression, correct, then continue.
10. Return final summary + commit hash with QC stamp.

## Verifier artifact contract (required)
Every required verifier checkpoint must produce a machine-checkable artifact containing:
- `artifact_version`
- `run_id`
- `stage`
- `status`
- `scope_fingerprint`
- `checkpoint` (`pre_implementation` | `pre_handoff`)
- `producer` (verifier sub-agent identity)
- `timestamp_utc`

Canonical location: `artifacts/verification/<run_id>/<stage>.json`
Fallback location: `docs/verification/<run_id>/<stage>.json`

## Verification Brief (required input to auditor)
For significant builds, auditor must receive this context pack:
- Project intent + long-term North Star
- Relevant USER.md hard rules and constraints
- Current architecture/agent-role context impacted by the change
- Proposed files + expected diffs + acceptance criteria
- Explicit audit lens: efficiency, effectiveness, future-proofing, compatibility, anti-drift

## Reviewer prompt template
"You are Build QC. Review this change independently for requirement fit, policy compliance, regressions, and missing docs/memory updates. Use AutoQuant constraints from USER.md (no destructive/unauthorized changes, spec vs artifact rules, logging policy). Assess efficiency, effectiveness, future-proofing, project compatibility/alignment, and drift risk against long-term goals. Return PASS/FAIL, top issues, and exact fixes. Keep it concise."

## Required output footer stamp (handoff to user)
On significant-build handoff, add this at the very bottom (mandatory):

Verified:
━━━━━━━━━━━━━━━━━━━━
**✅ QC VERIFIED — Independent GPT-5.3 review passed**
━━━━━━━━━━━━━━━━━━━━

Partial:
━━━━━━━━━━━━━━━━━━━━
**⚠️ QC PARTIAL**
**Issues found; revised once**
━━━━━━━━━━━━━━━━━━━━

Not verified:
━━━━━━━━━━━━━━━━━━━━
**❌ QC NOT VERIFIED**
**Gate failed or blocked**
━━━━━━━━━━━━━━━━━━━━

## Quick command pattern (operator)
- Spawn 🔰 Verifier in separate session using `sessions_spawn`.
- Pass: change summary, file list, acceptance criteria, and policy checks.
- If FAIL: keep proposal-stage loop internal (FAIL -> revise -> re-audit) until PASS; no FAIL-stage user approval ask.

## Enforcement guardrail (automation behavior)
- Treat missing QC stamp on significant-build handoff as a process failure.
- Auto-recovery: send an immediate correction message containing the correct boxed QC stamp.
- Do not continue to new topics until the correction stamp is sent.
- For major requested builds, do not request final user approval until proposal QC has completed with PASS (internal FAIL -> revise -> re-audit loop until PASS).
- Proposal FAIL-stage is internal; do not pause for user decision while in FAIL loop. Only legal pause states are WAIT_USER_APPROVAL or BLOCKED.
- Proposal approval request in chat should default to minimal human confirmation: `**✅ Verified**` (or `**⚠️ Partial**` / `**❌ Not Verified**`) plus boxed QC stamp.
- Structured STATUS lines are log-facing and should be sent in chat only on explicit request.
- Proposal QC reports must use fixed checklist categories only: policy alignment, scope fit, mutation gate compliance, logging contract, verification visibility.
- Proposal QC reruns must deduplicate issues (repeat only when state changed).
- Pre-handoff checklist MUST verify terminal spawn outcomes for all `sessions_spawn` used in the build (`OK|WARN|FAIL` with run_id). If START exists, verify matching run_id and valid ordering.
- Run `python scripts/spawn_lifecycle_reconcile.py --strict` before final handoff when spawn workflows were used; unresolved runs block handoff.
- Valid approval is a standalone user message with clear affirmative intent (case-insensitive, trimmed), e.g. `approved`, `go ahead`, `commit it`, `approved go ahead and commit`.
- Standalone hold phrases (`wait`, `not yet`, `hold`, `stop`) must block execution and keep approval-wait state.
- Before approval, block all mutating actions (write/edit/create/delete, git add/commit/reset/rebase/cherry-pick, config mutations) and remain in approval-wait state.
- If implementation occurs before standalone approval, treat it as process-invalid: stop, disclose, revert unauthorized commits, and restart from proposal QC.
- Do not send implementation handoff until post-implementation independent QC has completed.
- Default user-visible mode: report minimal verification confirmation (`**✅ Verified**` / `**⚠️ Partial**` / `**❌ Not Verified**`) + boxed stamp and final draft; keep structured status/run_id in logs and provide in chat only when explicitly requested.
- DM noise suppression: significant-build verifier stages remain mandatory, but should be orchestrated off-DM by default when platform supports it; DM should receive only the clean approval package and final handoff unless detailed audit output is explicitly requested.
- Enforce with `scripts/automation/spawn_gate.ps1` prior to any verifier spawn; blocked DM spawn must reroute to non-DM orchestration.
- Lifecycle logging gate: missing terminal `sessions_spawn` event evidence (`OK|WARN|FAIL`) is fail-closed and blocks progression until reconciled.

## Note
This is a **quick** gate, not full audit. Aim for 5-10 minutes.
