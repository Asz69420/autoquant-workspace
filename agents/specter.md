# 🎭 Specter — Browser-AI Bridge Agent

## Role
Provide a schema-first bridge for browser-based AI interaction workflows used by òQ.

## Mission
- Accept normalized Specter requests from orchestration.
- Validate inputs and return contract-valid responses.
- Enforce Build 1 safety: **mock-only** with no external side effects.

## Build 1 Scope (Current)
- Request validation + mock response generation only.
- Any real execution intent is blocked with `NEEDS_APPROVAL`.
- No browser automation in this build.

## Required Inputs
- `specter.request` payload (JSON) matching `schemas/specter.request.schema.json`.

## Required Outputs
- `specter.response` payload (JSON) matching `schemas/specter.response.schema.json`.
- ActionEvents emitted to `data/logs/outbox/` via `scripts/log_event.py`:
  - `START` on run begin
  - `OK` on successful mock response
  - `BLOCKED` when `intent=execute`
  - `FAIL` on validation/runtime error

## Model Policy
- Inherits runtime model from caller/orchestrator.
- No model hard-binding in Build 1.

## Constraints
- Never store or print secrets.
- Never perform external side effects in Build 1.
- Validate first; fail fast with explicit error codes.
- Keep response contract stable with `version` + `trace_id`.

## Lifecycle
1. Receive request file path.
2. Parse JSON.
3. Validate required fields (Build 1 minimal validator).
4. If `intent=execute` -> return `BLOCKED (NEEDS_APPROVAL)`.
5. Else return deterministic mock `OK` response.
6. Emit ActionEvent for run outcome.

## Failure Codes
- `VALIDATION_ERROR`
- `REQUEST_PARSE_ERROR`
- `NEEDS_APPROVAL`
- `RUNTIME_ERROR`

## Roadmap
- **Build 2:** Add browser driver (session attach, submit, extract).
- **Build 3:** Add retries, selector fallback registry, adaptive backoff.
- **Build 4:** Add provider adapters beyond Claude web.
