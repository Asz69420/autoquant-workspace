# ADR 0001: Three-Layer Memory System (Repo Memory + Artifact Store + SQLite Index)

**Date:** 2026-02-21  
**Status:** APPROVED  
**Deciders:** Ghosted

## Context
Earlier iterations of AutoQuant became bloated: large monolithic memory files, duplicate artifacts, manual tracking of research/backtests, unclear which files were specs vs. outputs. Needed a system that:
- Avoids context explosion in main MEMORY.md
- Prevents accidental file corruption (immutability)
- Clearly separates specs (Git-tracked source of truth) from artifacts (immutable bulky outputs)
- Enables multi-agent coordination (agents read summaries, not raw data)
- Stays Git-friendly (small, textual core)

## Decision
Implement a **three-layer memory architecture with strict specs vs. artifacts separation:**

### Layer 1: Repo Memory (Small, Git-tracked)
- `MEMORY.md` (index, North Star, conventions)
- `USER.md` (preferences)
- `docs/` (decisions, runbooks)
- `schemas/` (immutable specs for data structures)
- **Specs (source of truth):**
  - `research/` (research card specs)
  - `strategies/specs/` (strategy specification files)
  - `indicators/specs/` (indicator specification files)

### Layer 2: Artifact Store (Large, Immutable, NOT Git-tracked)
- `artifacts/{type}/` folders (backtests, videos, transcripts, datasets)
- Content-hashed filenames; never overwrite
- Metadata (paths, hashes, summaries) in SQLite
- **Only bulky outputs here, never specs**

### Layer 3: Retrieval Index (SQLite, Queryable)
- Fast metadata lookups (find top strategies, related artifacts, dedup by hash)
- Lineage tracking (depends_on, generated_by relationships)
- Agents query for metadata without loading large files

## Consequences

**Advantages:**
- MEMORY.md stays <10KB; humans read it in seconds
- Specs are Git-tracked, versioned, auditable
- Artifacts are immutable; backtest results can never be accidentally corrupted
- Clear distinction: edit specs in Git; output artifacts to immutable store
- Agents can query SQLite for metadata without parsing JSON
- Deduplication by hash prevents duplicate research/backtests
- Git history is clean; only decision + spec changes are tracked

**Trade-offs:**
- Requires SQLite schema + queries (minimal overhead)
- Agents must retrieve artifacts separately from metadata
- Manual discipline: must not commit large files to Git; .gitignore enforces this
- Specs and artifacts must be consciously separated during authoring

**Risk Mitigation:**
- .gitignore enforces artifact separation
- Content hash (SHA256, 12 chars in IDs) ensures immutability
- Lineage tracking makes dependencies and errors traceable
- Proposal-first workflow for schema changes
- SQLite provides fast queries; no need to load MEMORY.md for every lookup

## Alternatives Considered

### A. Monolithic MEMORY.md (Old Approach)
- ❌ Grows to 50KB+ in months
- ❌ Context explosion in agent retrievals
- ❌ Accidental overwrites + file corruption
- ❌ Manual deduplication
- ❌ Unclear what's a spec vs. an output

### B. Full Embedding Store (Weaviate, Qdrant)
- ✅ Semantic search
- ❌ Overkill for this scale
- ❌ External infrastructure dependency
- ❌ Harder to audit decisions

### C. Git Submodules + External Artifact Repo
- ✅ Separate artifacts from code
- ❌ Complexity; harder for casual users
- ❌ Version management overhead

### D. Everything in artifacts/ (no specs Git-tracked)
- ❌ Lost version history for specs
- ❌ Harder to track strategy evolution
- ❌ No clear source of truth for what's current

**Winner:** Three-layer with specs vs. artifacts (Layer 1 + Layer 2 + Layer 3)

## Implementation
- [x] Create folder structure
- [x] Define schemas (ResearchCard, IndicatorRecord, StrategySpec, BacktestReport)
- [x] Set up .gitignore (enforce separation)
- [x] Propose SQLite schema
- [ ] Create artifacts.db on first backtest run
- [ ] Write agents to populate index + fetch specs
- [ ] Build agent-facing queries

---

**Follow-up:** ADR 0002 (Scheduling backtests across multi-agent pipeline)
