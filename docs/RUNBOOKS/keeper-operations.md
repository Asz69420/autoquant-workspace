# Runbook: Keeper Operations

## Goal
Automate memory upkeep and compatibility checks with minimal user intervention.

## Cadence
- **Daily light pass:** retrieval health + handoff scan + low-risk promotions.
- **Weekly deep pass:** compatibility drift audit + compaction review.
- **On-demand:** run Keeper immediately.

## Daily Light Pass
1. Scan latest `docs/HANDOFFS/handoff-*.md` files.
2. Run retrieval smoke test: `python scripts/tests/test_memory_retrieval.py`.
3. Promote safe memory bullets to `MEMORY.md` (idempotent markers required).
4. Emit ActionEvents to outbox.

## Weekly Deep Pass
1. Run compatibility check: `python scripts/keeper/check_compatibility.py`.
2. Run retrieval smoke test.
3. Review MEMORY size/duplicates and trim low-value repetition.
4. Emit summary ActionEvent.

## Safe Auto-Apply Scope (Allowed)
- Formatting/typo cleanup.
- Link/path fix-ups.
- Duplicate cleanup.
- MEMORY size trimming (non-meaning-changing).
- Add concise bullet summaries with source pointers.

## Escalate (Do Not Auto-Apply)
- Any meaning-changing rewrite.
- Deletions with semantic impact.
- Security rule/policy changes.
- Contract restructuring across agents/docs.

## Status Vocabulary
Use only:
- START ▶️
- OK ✅
- WARN ⚠️
- BLOCKED ⛔
- FAIL ❌

`WARN`, `BLOCKED`, `FAIL` must include `reason_code`.

## Logging Contract
- Emit ActionEvents to `data/logs/outbox/` only.
- Do not send Telegram directly.
- Logger (`scripts/tg_reporter.py`) handles Telegram + NDJSON.
