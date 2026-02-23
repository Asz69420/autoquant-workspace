# Autopilot Loop (Verifier-First State Machine)

Canonical references:
- `docs/CONTRACTS/verification-gate.md`
- `docs/RUNBOOKS/build-qc-gate.md`
- `docs/RUNBOOKS/delegation-policy.md`

## States
- `PROPOSAL_QC`
- `REVISING`
- `WAIT_USER_APPROVAL`
- `IMPLEMENTATION_QC`
- `BLOCKED`
- `DONE`

## Legal transitions
- Proposal FAIL: `PROPOSAL_QC -> REVISING -> PROPOSAL_QC` (repeat until PASS)
- Proposal PASS: `PROPOSAL_QC -> WAIT_USER_APPROVAL`
- Approval received: `WAIT_USER_APPROVAL -> IMPLEMENTATION_QC`
- Implementation PASS|PARTIAL: `IMPLEMENTATION_QC -> DONE`
- Any unrecoverable condition: `* -> BLOCKED`

## Non-negotiable pause rule
Only legal pause states are:
- `WAIT_USER_APPROVAL`
- `BLOCKED`

Explicitly prohibited:
- FAIL-stage idle wait
- pause-for-user while proposal is FAIL

## Approval package rule
Emit exactly one clean verified approval package, and only after proposal PASS.
