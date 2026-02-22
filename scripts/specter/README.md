# Specter Build 1 (Mock-Only)

Build 1 provides a contract-valid scaffold for Specter.

## Scope
- Parse request JSON
- Minimal validation (stdlib only)
- Return schema-shaped mock response
- Emit ActionEvents via `scripts/log_event.py`

## Non-Goals (Build 1)
- No browser automation
- No external side effects
- No real provider execution

If request `intent` is `execute`, runner returns `blocked` with `NEEDS_APPROVAL`.

## Usage
```bash
python scripts/specter/runner.py --request path/to/request.json
```

## Expected Event Emissions
- `START` at run begin
- `OK` on successful mock response
- `BLOCKED` when intent=execute
- `FAIL` on parse/validation/runtime errors
