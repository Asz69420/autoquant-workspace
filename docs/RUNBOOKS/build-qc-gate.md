# Build QC Gate (Significant Changes)

Purpose: add a fast second-pass quality check before final handoff on significant builds.

## Trigger condition (significant build)
Run QC gate when any of these are true:
- Automation/scheduler behavior changed
- Policy/contracts/runbooks changed
- Multi-file feature build
- Model routing/delegation behavior changed

Skip gate for tiny edits (typos/format-only/single-line non-functional docs). This trivial-edit carve-out is unaffected by the `APPROVE BILL` token rule.

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
5. Send verified bill to user for approval (`QC: PASS|FAIL | run_id: ...` + boxed stamp).
6. Wait for explicit standalone approval token: `APPROVE BILL` (case-insensitive, trimmed exact match).
7. Implement/write + commit changes.
8. Run independent QC pass on implementation.
9. If implementation QC fails: revise once and re-run implementation QC once.
10. Return final summary + commit hash with QC stamp.

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
- Proposal approval request MUST include one-line verifier summary (`QC: PASS|FAIL | run_id: ...`) plus boxed QC stamp.
- Valid approval token is a standalone user message equal to `APPROVE BILL` (case-insensitive, trimmed exact match).
- Before approval token, block all mutating actions (write/edit/create/delete, git add/commit/reset/rebase/cherry-pick, config mutations) and remain in approval-wait state.
- Do not send implementation handoff until post-implementation independent QC has completed.
- Default user-visible mode: report only verification status + run_id + boxed stamp and final draft; provide full audit details only when explicitly requested.

## Note
This is a **quick** gate, not full audit. Aim for 5-10 minutes.
