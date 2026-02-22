# Memory & Retrieval Standard (AutoQuant)

**Purpose:** Keep memory durable, searchable, and model-agnostic without bloating instructions.

## 1) Canonical Memory Tiers

1. **Short-term journal:** `memory/YYYY-MM-DD.md`
   - Raw session notes, temporary context, unresolved items.
2. **Long-term curated memory:** `MEMORY.md`
   - Stable decisions, architecture truths, persistent preferences.
3. **Specs (source of truth):** `research/`, `indicators/specs/`, `strategies/specs/`, `schemas/`
   - Versioned definitions and contracts.
4. **Artifacts (large outputs):** `artifacts/` (not git-tracked)
   - Backtests, bulky outputs, media.

## 2) Retrieval Contract (Must Hold)

- Retrieval must prioritize compact summaries first, then expand on demand.
- Any durable fact should be traceable to a path and (where useful) line/citation.
- Do not duplicate bulky content in memory files; store pointers + hashes.
- Long-term memory entries must be concise and decision-oriented.

## 3) What Gets Promoted to MEMORY.md

Promote only if at least one is true:
- Architecture decision with ongoing impact.
- Policy/rule that changes agent behavior.
- Durable user preference relevant across sessions.
- Critical lesson from failure/incident.

Do **not** promote:
- Temporary debugging chatter.
- One-off outputs with no repeated value.
- Large raw logs (keep in artifacts/logs).

## 4) Indexing & Search Expectations

- Paths and IDs must be stable and machine-friendly.
- Prefer hash-based artifact identities when available.
- Retrieval queries should return references, not just prose.
- If retrieval confidence is low, report low confidence and request/perform a targeted check.

## 5) Anti-Bloat Rules

- Keep `MEMORY.md` compact (target: <10KB unless explicitly justified).
- Weekly compaction: summarize recent daily notes into durable points.
- Replace repeated paragraphs with one canonical rule + pointers.
- Never copy the same policy text across multiple docs; reference this standard.

## 6) Change Control

When memory/retrieval behavior changes:
1. Update this standard or linked runbook.
2. Add brief ADR note in `docs/DECISIONS/` if behavior/contract changed materially.
3. Add/adjust smoke test in `scripts/tests/test_memory_retrieval.py`.

## 7) OpenClaw Alignment

This standard is designed for OpenClaw conventions:
- schema-first outputs,
- logger/outbox workflow,
- model-agnostic operation,
- durable file-based continuity across sessions.

It extends existing guidance in `USER.md` and `MEMORY.md` without replacing them.
