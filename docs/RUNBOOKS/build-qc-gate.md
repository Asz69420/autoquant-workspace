# Build QC Gate (Significant Changes)

Purpose: add a fast second-pass quality check before final handoff on significant builds.

## Trigger condition (significant build)
Run QC gate when any of these are true:
- Automation/scheduler behavior changed
- Policy/contracts/runbooks changed
- Multi-file feature build
- Model routing/delegation behavior changed

Skip gate for tiny edits (typos/format-only/single-line non-functional docs).

## Gate pattern
1. Primary implementation completes.
2. Spawn a second GPT-5.3 pass as independent reviewer (separate session).
3. Reviewer checks:
   - requirement coverage
   - policy compliance (AutoQuant rules in USER.md)
   - edge cases/regressions
   - docs/memory sync completeness
4. If issues found: revise once.
5. Re-run QC once after revision.
6. Return final summary + commit hash with QC badge.

## Reviewer prompt template
"You are Build QC. Review this change independently for requirement fit, policy compliance, regressions, and missing docs/memory updates. Use AutoQuant constraints from USER.md (no destructive/unauthorized changes, spec vs artifact rules, logging policy). Return PASS/FAIL, top issues, and exact fixes. Keep it concise."

## Required output footer (handoff to user)
Add one line at the end of significant-build handoff:
- `QC: ✅ VERIFIED (independent GPT-5.3)`
- `QC: ⚠️ PARTIAL (issues found, revised once)`
- `QC: ❌ NOT VERIFIED (gate failed/blocked)`

## Quick command pattern (operator)
- Spawn QC reviewer in separate session using `sessions_spawn`.
- Pass: change summary, file list, acceptance criteria, and policy checks.
- If FAIL: revise once, re-run QC, then handoff with footer.

## Note
This is a **quick** gate, not full audit. Aim for 5-10 minutes.
