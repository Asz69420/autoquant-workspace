# AutoQuant — User Preferences & Context

## AutoQuant Operating Rules (FOLLOW THESE)

1. **Durable memory lives in:** MEMORY.md, docs/, schemas/, research/, indicators/specs/, strategies/specs/
2. **Big outputs live in:** artifacts/ or data/ (never Git-track)
3. **Never store secrets** (keys/tokens/wallets/credentials) in any file
4. **Never overwrite or delete files without asking first**
5. **When creating specs:** Follow the schema files in /schemas
6. **Before writing any files:** Show (a) plan, (b) file list, (c) preview/diff, then wait for approval

## Your Identity
- **Name:** Ghosted
- **Timezone:** Australia/Brisbane
- **Role:** Project lead, R&D strategy, execution oversight

## Working Style
1. **Propose risky changes first** — Draft ADR or design doc before implementing breaking changes
2. **Concise + actionable** — Get to the point; include next steps
3. **No destructive actions without approval** — Never delete, overwrite, or reset without explicit go-ahead
4. **Specs before artifacts** — When documenting research/indicators/strategies, Git-track the spec; artifacts go to immutable store
5. **Summary-driven** — Fetch summaries first; expand on demand

## Current Goals (AutoQuant Phase 1)
- Build trading automation pipeline R&D loop: Research → Indicator → Strategy → Backtest → (execution later)
- Fresh architecture from ground up; avoid bloat
- Systematically reintroduce existing code with fresh audits
- Multi-agent coordination: agents read summaries, fetch artifacts on demand
- Backtest framework decision: Binance perps proxy first, later cross-check Hyperliquid

## Integration Points (No Secrets Here)
- **Market data feed:** TBD (Binance perps API proxy initially; Hyperliquid API later)
- **Backtesting framework:** TBD (candidate: Backtrader, VectorBT, custom)
- **Execution layer:** Phase 2; Hyperliquid API integration (no secrets in specs)

## Existing Artifacts
- None to import yet; clean slate

## Notes
- Avoid context explosion; keep MEMORY.md <10KB
- Use SQLite queries to find strategy/backtest results, not large file reads
- When adding a new research finding, create a ResearchCard spec first (Git-track), then link to artifacts
