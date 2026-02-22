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
2. Spawn a second GPT-5.3 pass as independent reviewer.
3. Reviewer checks:
   - requirement coverage
   - policy compliance
   - edge cases/regressions
   - docs/memory sync completeness
4. If issues found: revise once.
5. Return final summary + commit hash.

## Reviewer prompt template
"You are Build QC. Review this change independently for requirement fit, policy compliance, regressions, and missing docs/memory updates. Return PASS/FAIL, top issues, and exact fixes. Keep it concise."

## Note
This is a **quick** gate, not full audit. Aim for 5-10 minutes.
