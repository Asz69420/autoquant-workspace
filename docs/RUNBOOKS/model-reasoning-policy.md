# Runbook: Model & Reasoning Policy (Enforced)

## Purpose

Provide a single enforced source of truth for task buckets:

- `system` → no LLM required
- `low` → cheap LLM path
- `medium` → default strategy-quality path
- `high` → deep synthesis/risk path

This avoids per-session/manual model-thinking setup.

## Source of truth

- Policy file: `config/model_reasoning_policy.json`
- Resolver: `scripts/automation/resolve_model_policy.py`
- Drift guard: `scripts/tests/test_model_policy.py`

## Bucket contract

- **system**
  - `llm_required=false`
  - deterministic script execution only
- **low**
  - `model=haiku`
  - `reasoning=off`
- **medium**
  - `model=gpt-5.3`
  - `reasoning=medium`
- **high**
  - `model=gpt-5.3`
  - `reasoning=high`

## Resolve examples

```bash
python scripts/automation/resolve_model_policy.py --task analyser_thesis
python scripts/automation/resolve_model_policy.py --task claude_strategy_researcher
python scripts/automation/resolve_model_policy.py --agent claude --action strategy_research
```

Returns JSON with:

- `bucket`
- `llm_required`
- `model`
- `reasoning`

## Drift guard test

```bash
python scripts/tests/test_model_policy.py
```

The test fails on:

- missing required buckets
- invalid bucket references
- missing required key mappings
- invalid `unknown_task_policy`

## Enforcement mode

Current policy uses:

- `unknown_task_policy: "error"`

Meaning unmapped tasks are blocked until explicitly mapped (prevents silent drift).

## Phase status

- **Phase 1 (complete):** policy file + resolver + drift guard + docs
- **Phase 2 (next):** wire individual scripts one-by-one, test each, commit separately
