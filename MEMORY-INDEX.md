# MEMORY-INDEX.md

last_updated: 2026-02-24T10:00:00+10:00

## Memory Stores
- Curated index: `MEMORY.md` (this index-only mode)
- Full historical snapshot: `memory/MEMORY-FULL-2026-02-24.md`
- Daily logs: `memory/YYYY-MM-DD.md`
- Handoffs: `docs/HANDOFFS/handoff-*.md`
- Rolling status: `docs/STATUS.md`
- Daily summaries: `docs/DAILY/YYYY-MM-DD-summary.md`

## Current State (compact)
- Mission: build durable project brain for multi-agent trading R&D.
- Separation principle: specs in repo, large artifacts out of Git.
- Hash-first artifact identity and immutability remain core.
- Retrieval-first behavior via search/index over long raw context.
- Telegram logging pipeline is live (reporter daemon + outbox drain).
- Focus loop automation exists (`scripts/automation/focus_loop.ps1`).
- Council mode exists (`scripts/automation/council.ps1`).
- Build QC gate workflow is active in runbooks/contracts.
- Verifier role is integrated for proposal/implementation QC.
- Keeper periodic sync cadence set via scheduled task.
- Model policy: Codex primary, Haiku fallback, MiniMax manual-only.
- No secrets should live in tracked files.
