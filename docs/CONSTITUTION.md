# AutoQuant Constitution

## Mission & North Star
**Mission:** Build a durable, scalable trading automation pipeline for Hyperliquid perps, with a project brain that survives context explosion and multi-agent handoffs.

**North Star:** Avoid bloat. Keep memory small and queryable. Specs Git-tracked. Artifacts immutable. Decisions recorded. Code auditable.

## Goals
1. **Reliable R&D loop:** Research → Indicator → Strategy → Backtest → Live execution
2. **Durable memory:** Project survives agent restarts, model changes, human context switches
3. **Auditability:** Every backtest result, strategy change, and decision is traceable
4. **Scalability:** Add new agents without breaking the system; parallelize backtests
5. **No bloat:** Fresh architecture; systematically reintroduce audited code

## Non-Goals
- Real-time market data streaming (separate infrastructure)
- Live execution engine (Phase 2)
- End-to-end UI dashboard (tooling only)
- Historical price database (rely on Hyperliquid API or external feed)

## Constraints
- Windows filesystem; use "/" path convention everywhere, relative to repo root
- No secrets in MEMORY.md, specs, or Git-tracked files; use .env / encrypted store
- Artifacts are immutable; create new versions with new IDs + hashes
- SQLite index is source of truth for artifact metadata
- Backtest framework TBD (Binance perps proxy → Hyperliquid cross-check)

## Repo Layout Rules
```
docs/                   → Decisions, constitution, runbooks (Git-tracked)
docs/DECISIONS/         → ADRs: each one a dated, numbered decision
docs/RUNBOOKS/          → "How to..." guides
schemas/                → Schema definitions (immutable specs, Git-tracked)
research/               → Research card specs (Git-tracked source of truth)
strategies/specs/       → Strategy spec files (Git-tracked source of truth)
indicators/specs/       → Indicator spec files (Git-tracked source of truth)
artifacts/              → Large immutable outputs ONLY: videos, backtests (NOT tracked)
data/                   → Runtime outputs, caches, logs (NOT tracked)
.gitignore              → Enforce specs vs artifacts separation
MEMORY.md               → Project brain index (Git-tracked, compact)
USER.md                 → Your preferences (Git-tracked)
```

## Decision Process
1. **Proposal:** Draft ADR in `docs/DECISIONS/NNNN-{slug}.md`
2. **Review:** Explain context, decision, consequences, alternatives
3. **Record:** Commit ADR + related changes atomically
4. **Announce:** Update MEMORY.md with summary + status

## Memory Rules (Critical)
1. **Files are truth; memory is search layer** — Specs live in Git; artifacts live in `artifacts/`; MEMORY.md has summaries + paths
2. **Specs vs Artifacts distinction:**
   - **Git-track specs:** `research/`, `strategies/specs/`, `indicators/specs/` (source of truth)
   - **Artifact store:** `artifacts/` = bulky immutable outputs only (videos, transcripts, backtest results, datasets)
3. **Never store raw bulky artifacts in memory** — Only summaries, pointers, hashes, lineage
4. **Immutability by default** — Once an artifact is hashed, never overwrite. New version = new ID
5. **No secrets** — API keys, tokens, private URLs must NOT appear in MEMORY.md, specs, or Git-tracked files
6. **Summary-first retrieval** — Always fetch compact metadata first; expand to full artifacts on demand
7. **Deduplication** — Content hash = identity; SQLite index prevents duplicate work

## Risky Changes (Require Approval)
- Modifying backtest framework or architecture
- Changing artifact storage structure or ID scheme
- Altering schema definitions (breaking changes)
- Introducing new dependencies
- Deleting or overwriting any existing files

---

**Last Updated:** 2026-02-21  
**Owner:** Ghosted
