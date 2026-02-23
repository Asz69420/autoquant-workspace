# Build QC Gate (Significant Changes)

Purpose: add a fast second-pass quality check before final handoff on significant builds.

## Trigger condition (significant build)
Run QC gate when any of these are true:
- Automation/scheduler behavior changed
- Policy/contracts/runbooks changed
- Multi-file feature build
- Model routing/delegation behavior changed

Skip gate for tiny edits (typos/format-only/single-line non-functional docs). This trivial-edit carve-out is unaffected by the approval semantics rule.

### Lightweight mode (minor significant docs-only edits)
For minor significant docs-only edits, use lean proposal QC mode:
- one proposal QC pass
- one fix pass
- one recheck max
- then either PASS to approval or consolidated blockers to user decision

## Gate pattern
1. For significant builds, prepare proposal package first (plan + file list + preview/diff + acceptance criteria).
2. Spawn a second GPT-5.3 pass as independent reviewer (separate session) on the proposal package.
3. Reviewer checks:
   - requirement coverage
   - policy compliance (AutoQuant rules in USER.md)
   - explicit AutoQuant Operating Rules compliance:
     - no overwrite/delete without approval
     - plan → file list → diff/preview before write
     - no secrets in files
     - artifacts/data outputs are not Git-tracked
   - edge cases/regressions
   - docs/memory sync completeness
   - efficiency
   - effectiveness
   - future-proofing
   - project compatibility/alignment
4. If proposal QC fails: auto-revise bill and re-run proposal QC (max 2 loops).
5. If cap reached: emit one consolidated blocker list, require user decision, and stop auto-reruns.
6. Send verified bill to user for approval (`QC: PASS|FAIL | run_id: ...` + boxed stamp).
7. Wait for explicit standalone user approval (natural-language affirmative, case-insensitive, trimmed).
8. On approval, proceed directly to implementation (no additional proposal-stage QC rerun unless scope changes).
9. Implement/write + commit changes.
10. Run independent QC pass on implementation.
11. If implementation QC fails: revise once and re-run implementation QC once.
12. Return final summary + commit hash with QC stamp.

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
- Spawn QC reviewer in separate session using `sessions_spawn`.
- Pass: change summary, file list, acceptance criteria, and policy checks.
- If FAIL: revise once, re-run QC, then handoff with footer stamp.

## Enforcement guardrail (automation behavior)
- Treat missing QC stamp on significant-build handoff as a process failure.
- Auto-recovery: send an immediate correction message containing the correct boxed QC stamp.
- Do not continue to new topics until the correction stamp is sent.
- For major requested builds, do not request final user approval until proposal QC has completed (with auto-revise/recheck up to 2 loops on proposal FAIL).
- On reaching proposal-loop cap, provide one consolidated blocker list and pause for user decision (no further auto-reruns).
- Proposal approval request MUST include exactly one explicit status line: `STATUS | type:QC | label:<check-name> | result:<PASS|FAIL|WARN> | run_id:<id>` plus boxed QC stamp.
- Optional readability header allowed: one human-readable emoji line immediately above STATUS (no blank line), display-only (no machine fields).
- Proposal QC reports must use fixed checklist categories only: policy alignment, scope fit, mutation gate compliance, logging contract, verification visibility.
- Proposal QC reruns must deduplicate issues (repeat only when state changed).
- Pre-handoff checklist MUST verify terminal spawn outcomes for all `sessions_spawn` used in the build (`OK|WARN|FAIL` with run_id). If START exists, verify matching run_id and valid ordering.
- Valid approval is a standalone user message with clear affirmative intent (case-insensitive, trimmed), e.g. `approved`, `go ahead`, `commit it`, `approved go ahead and commit`.
- Standalone hold phrases (`wait`, `not yet`, `hold`, `stop`) must block execution and keep approval-wait state.
- Before approval, block all mutating actions (write/edit/create/delete, git add/commit/reset/rebase/cherry-pick, config mutations) and remain in approval-wait state.
- Do not send implementation handoff until post-implementation independent QC has completed.
- Default user-visible mode: report only one STATUS line + verification status + run_id + boxed stamp and final draft; provide full audit details only when explicitly requested.
- DM noise suppression: for routine proposal/implementation QC checks, prefer inline/local QC in main chat to avoid `sessions_spawn` auto-announcement noise; reserve `sessions_spawn` for long/multi-step or explicitly requested QC runs.

## Note
This is a **quick** gate, not full audit. Aim for 5-10 minutes.
