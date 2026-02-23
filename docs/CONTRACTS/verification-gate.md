# Verification Gate Contract (Canonical)

Purpose: make verifier audits objective, fail-closed, and non-negotiable for significant builds.

## Precedence (hard rule)
This file is the canonical source for verification gating.
If any wording in `USER.md` or runbooks conflicts, this contract wins.

## Significant Build Trigger Matrix (objective)
A change is **Significant** if **ANY** condition is true:
1. Touches policy/contract/runbook memory governance files:
   - `USER.md`, `MEMORY.md`, `docs/RUNBOOKS/*`, `docs/CONTRACTS/*`
2. Touches orchestration/enforcement logic:
   - `scripts/automation/*` or approval/spawn/lifecycle enforcement logic
3. Changes model routing/default/fallback behavior
4. Changes logging/enforcement policy
5. Planned files changed `>= 5`
6. Planned LOC delta `>= 150`

**Fail-closed classification:** if trigger evaluation is unknown/partial, classify as Significant.

## Mandatory Stages
For Significant builds, both verifier stages are required:
1. **Proposal stage** (before user approval ask)
2. **Implementation stage** (before final handoff)

### Allowed statuses
- Proposal stage: `PASS | FAIL`
- Implementation stage: `PASS | PARTIAL | FAIL`

## Required Verifier Artifact (machine-checkable)
Required fields:
- `artifact_version`
- `run_id`
- `stage`
- `status`
- `scope_fingerprint`
- `checkpoint` (`pre_implementation` or `pre_handoff`)
- `producer` (must identify verifier sub-agent)
- `timestamp_utc`

Canonical artifact location:
- `artifacts/verification/<run_id>/<stage>.json`
- Fallback when artifacts path is unavailable: `docs/verification/<run_id>/<stage>.json`

## Scope Drift Invalidation
If `scope_fingerprint` changes after proposal `PASS` and before implementation start,
proposal verification is invalid and proposal verifier QC must be rerun.

## Hard Blocking Behavior
Missing/invalid required verifier artifact at a required checkpoint = `PROCESS_INVALID`.
Block mutating progression and handoff until corrected.

## Override Semantics (strict)
Verifier bypass is allowed only when user sends the standalone exact normalized phrase:
`skip verifier for this change`

Parsing constraints:
- user-authored
- standalone message only
- non-quoted
- non-codeblock
- no additional text

## Non-Waiver Clause
Verifier override does **not** bypass:
- standalone user approval token gate
- mutation safety controls
- other policy/safety controls

## Verification Visibility
For Significant builds, both are mandatory:
- minimal chat badge: `✅ Verified` / `⚠️ Partial` / `❌ Not Verified`
- boxed QC stamp in approval package and final handoff

## Logger/Lifecycle Invariants (non-negotiable)
- Telegram Reporter is always-on with self-healing watchdog automation.
- Every `sessions_spawn` completion must produce terminal lifecycle status (`OK|WARN|FAIL`).
- Missing terminal lifecycle evidence is fail-closed and blocks progression/handoff until reconciled.
