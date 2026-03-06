# Cycle Contract (Universal Multi-Agent Sync Pattern)

## Purpose
Provide a reusable, backward-compatible synchronization contract for multi-agent pipelines where one stage hands off to another (e.g., Frodex ➜ Quandalf).

This avoids out-of-order cards, duplicate posts, and cross-run metric mixing.

---

## Canonical Rules

1. **Canonical cycle identity**
   - Use one cycle key (`cycle_id`) per upstream run.
   - In current implementation, `cycle_id` = Frodex `run_id` (e.g., `autopilot-1772748902`).

2. **Deterministic handoff order**
   - Upstream cycle card must emit first.
   - Downstream reflection/execution card emits only after upstream cycle is settled and handoff is accepted.

3. **Run-scoped accounting**
   - Queue/generation/backtest metrics are computed only from events that belong to the same cycle key.
   - Never mix window-aggregate metrics across different cycles in one card.

4. **Idempotent emission**
   - Card posting must be deduped by cycle identity and phase.
   - Re-runs/retries must not create duplicate cards for the same cycle.

5. **Backward compatibility**
   - Existing `run_id`, event names, summaries, and files remain valid.
   - New behavior is additive (hints, pairing, ordering), not destructive.

---

## Current Implementation (Automation V2)

### Components
- `scripts/automation/bundle-run-log.ps1`
  - Supports optional `-RunIdHint` to pin the Frodex card to an exact cycle.
  - Supports `-EmitReason handoff` so handoff-paired Frodex card emission is not suppressed by scheduled dedupe state.
- `scripts/automation/check_quandalf_handoff.ps1`
  - Waits for upstream settle.
  - Emits Frodex card for the exact cycle (`-RunIdHint <cycle> -EmitReason handoff`).
  - Triggers Quandalf run.
  - Emits Quandalf card with matching cycle reference.

### Visible Pairing
- Frodex card header includes compact run identity:
  - `... | 🆔 <last-6-digits>`
- Quandalf card header includes compact run identity:
  - `... | 🆔 <last-6-digits>`
- This keeps cards visually paired while reducing header length.

---

## Reuse in Other Applications
This contract is intentionally generic and can be reused for any orchestrator:
- ingest ➜ analysis
- analysis ➜ execution
- build ➜ deploy
- queue producer ➜ queue consumer

Porting checklist:
1. Pick canonical `cycle_id`.
2. Ensure upstream emits final handoff event.
3. Scope downstream metrics strictly by that `cycle_id`.
4. Add idempotent state for each phase.
5. Keep all old fields/events intact while adding the new contract.

---

## Rollback
If needed, disable cycle pinning/ordered emission path and fall back to prior window-based behavior.
No schema/data migration rollback is required because changes are additive.
