# Claude Skill Adapter (V2 Phase 2)

## Purpose

This adapter defines how OpenClaw agents call Claude Code as a **skill backend** without handing over agent identity, memory ownership, or orchestration control.

In this pattern:

- OpenClaw agents (e.g., Oragorn, Quandalf) remain the owners of:
  - identity and role
  - memory files and continuity
  - task routing and operational decisions
- Claude Code is used as a **callable execution backend** for bounded work units.

This is a strict adapter boundary, not an agent replacement.

---

## Ownership Boundary

### OpenClaw agent owns

- Session context and memory contracts
- Prompt framing and task intent
- Validation, gating, and promotion logic
- Final decision on whether outputs are accepted
- Event telemetry and run lifecycle tracking

### Claude skill backend provides

- Prompt-scoped execution for a selected mode
- Generated artifacts and analysis output
- Exit status and raw execution logs

---

## Adapter Components

- Policy: `config/claude_skill_policy.json`
- Runtime wrapper: `scripts/automation/run_claude_skill.ps1`
- Task-facing helper: `scripts/claude-tasks/invoke-claude-skill.ps1`

### Supported modes (phase 2)

- `research`
- `generate`
- `doctrine`
- `audit`

Mode permissions and defaults are policy-driven.

---

## Execution Flow

1. OpenClaw task invokes `invoke-claude-skill.ps1`.
2. Helper delegates to `run_claude_skill.ps1`.
3. Wrapper loads policy, validates mode, runs Claude CLI, handles retry/backoff on rate-limit conditions, and emits structured ActionEvents.
4. Wrapper returns standardized output (JSON + stable key-value lines) for upstream task scripts.
5. Calling task decides downstream actions (notify, persist, gate, promote).

---

## Safety and Change Scope

Phase 2 introduces adapter plumbing only.

- No live scheduled task rewiring in this phase.
- Existing task schedules and triggers remain unchanged.
- Adapter can be adopted incrementally by individual task scripts.

---

## Telemetry

`run_claude_skill.ps1` emits structured events via `scripts/log_event.py` with run metadata:

- run id
- mode/action
- status progression (`START`, `THROTTLED`, `RETRY`, `OK`, `FAIL`)
- summary and optional reason code
- input/output artifact references

This keeps Claude skill invocations observable inside the same event stream used by other automation components.
