# Runbook: Memory Maintenance (Weekly)

## Goal
Keep memory retrieval fast, accurate, and low-noise as AutoQuant scales.

## Cadence
- Weekly (or after major milestone): 15-30 minutes.

## Checklist

1. **Review daily notes**
   - Read last 7 days in `memory/YYYY-MM-DD.md`.
   - Mark durable decisions/preferences/incidents.

2. **Promote durable items**
   - Add concise entries to `MEMORY.md`.
   - Prefer bullet points with references to specs/artifacts.

3. **Prune noise**
   - Remove stale/duplicated content in `MEMORY.md`.
   - Keep one canonical phrasing per durable rule.

4. **Verify retrieval health**
   - Run: `python scripts/tests/test_memory_retrieval.py`
   - If failing, fix retrieval assumptions before adding more memory docs.

5. **Record major changes**
   - If behavior/contract changed materially, add short ADR in `docs/DECISIONS/`.

## Promotion Template (Recommended)

- **Decision/Insight:** <1 line>
- **Why it matters:** <1 line>
- **Pointer:** <path or artifact id>

## Guardrails

- No secrets in memory files.
- No large raw artifacts in memory files.
- Use pointers/hashes instead of pasted blobs.
- Keep `MEMORY.md` compact and readable.
