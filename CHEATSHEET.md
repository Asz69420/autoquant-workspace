# AutoQuant Quick Reference Cheat Sheet

## 3-Layer Architecture

```
Repo Memory (Git)              Artifact Store (Immutable)     Retrieval Index (SQLite)
────────────────────────       ──────────────────────────     ────────────────────
MEMORY.md (project brain)      artifacts/backtests/           artifacts.db (queries)
docs/ (decisions)              artifacts/videos/              Fast lookups
schemas/ (specs)               artifacts/datasets/            Deduplication
research/                      (all hash-based IDs)           Lineage tracking
indicators/specs/              (never modify)
strategies/specs/
```

## File Structure

| What | Where | Git-Track? | Why |
|------|-------|------------|-----|
| Research cards | `research/research-{name}-{date}.json` | ✅ Yes | Source of truth |
| Indicator specs | `indicators/specs/indicator-{name}-v{N}.json` | ✅ Yes | Source of truth |
| Indicator code | `indicators/{name}_{version}.py` | ✅ Yes | Implementation |
| Strategy specs | `strategies/specs/strategy-{name}-v{N}.json` | ✅ Yes | Source of truth |
| Strategy code | `strategies/{name}_{version}.py` | ✅ Yes | Implementation |
| Backtest results | `artifacts/backtests/backtest--{hash}/` | ❌ No | Immutable output |
| Video/transcripts | `artifacts/videos/video--{hash}/` | ❌ No | Large files |
| Config for reproducibility | `artifacts/backtests/{id}/config.json` | ❌ No | Immutable |

## ID Conventions

- **Specs (Git-tracked):** Use filename convention
  - `research-volatility-signal-20260221.json`
  - `indicator-volatility-zscore-v1.json`
  - `strategy-mean-revert-btc-v1.json`

- **Artifacts (Immutable):** Hash-first
  - `backtest--a1b2c3d4e5f6` (SHA256 first 12 chars)
  - `video--x9y8z7w6v5u4`
  - Optional date suffix: `backtest--a1b2c3d4e5f6_20260221`

## Core Workflow

### 1. Add Research Finding
```json
research/research-signal-name-20260221.json
{
  "id": "research-signal-name-20260221",
  "title": "...",
  "hypothesis": "...",
  "findings": "...",
  "confidence": "medium",
  "tags": ["tag1", "tag2"],
  "source_url": "...",
  "rights": "restricted",
  "artifact_ids": []  // Fill after creating related artifacts
}
```

### 2. Design Indicator
```json
indicators/specs/indicator-my-signal-v1.json
{
  "id": "indicator-my-signal-v1",
  "name": "My Signal",
  "formula": "...",
  "parameters": { "period": 14, ... },
  "code_path": "indicators/my_signal_v1.py",
  "research_source": "research/research-signal-name-20260221.json"
}
```
Then implement: `indicators/my_signal_v1.py`

### 3. Design Strategy
```json
strategies/specs/strategy-example-v1.json
{
  "id": "strategy-example-v1",
  "entry_rules": "...",
  "exit_rules": "...",
  "indicators": ["indicators/specs/indicator-my-signal-v1.json"],
  "research_references": ["research/research-signal-name-20260221.json"]
}
```
Then implement: `strategies/example_v1.py`

### 4. Run Backtest
```bash
python run_backtest.py --strategy strategies/specs/strategy-example-v1.json --dataset data-binance-btc-2024
# Output: data/cache/backtest--{hash}/
```

### 5. Index Result
```bash
python scripts/index_backtest.py data/cache/backtest--{hash}/metrics.json
# Moves to artifacts/backtests/backtest--{hash}/
# Updates SQLite artifacts table
```

### 6. Query Results
```bash
# Top strategies
python scripts/query_index.py --strategy-ranking sharpe

# Find all backtests for one strategy
python scripts/query_index.py --strategy strategies/specs/strategy-example-v1.json

# Deduplicate (find duplicate runs)
python scripts/query_index.py --dedup-hash
```

## Required Fields Summary

### ResearchCard
`id`, `title`, `author`, `created_at`, `hypothesis`, `findings`, `confidence`, `tags`, `source_url`, `rights`, `attribution_required`

### IndicatorRecord
`id`, `name`, `version`, `formula`, `parameters`, `code_path`, `created_at`, `tags`, `source_url`, `rights`, `attribution_required`

### StrategySpec
`id`, `name`, `version`, `instrument`, `timeframe`, `entry_rules`, `exit_rules`, `risk_params`, `indicators`, `created_at`, `status`, `tags`, `source_url`, `rights`, `attribution_required`

### BacktestReport
`id`, `strategy_id`, `dataset_id`, `config_hash`, `execution_model`, `fees_model`, `slippage_model`, `fill_assumptions`, `signal_timing`, `start_date`, `end_date`, `metrics_json`, `artifacts_path`, `created_at`, `tags`

## SQLite Queries (Fast!)

```sql
-- Top strategies by Sharpe
SELECT s.id, s.status, b.metrics_json->>'$.sharpe' AS sharpe
FROM strategies s
LEFT JOIN backtests b ON b.id = s.last_eval_id
ORDER BY sharpe DESC LIMIT 10;

-- All backtests for a strategy
SELECT id, created_at, metrics_json->>'$.total_return_pct' AS return
FROM backtests
WHERE strategy_id = 'strategies/specs/strategy-example-v1.json'
ORDER BY created_at DESC;

-- Deduplicate by hash
SELECT hash, COUNT(*) as count FROM artifacts
GROUP BY hash HAVING count > 1;
```

## Common Mistakes to Avoid

❌ **Don't:**
- Store backtest results in Git (use artifacts/)
- Commit API keys to .env
- Overwrite artifacts (immutable = create new ID)
- Modify a spec after it's been backtested without versioning
- Use raw file paths without ".json" in strategy/indicator references

✅ **Do:**
- Create new indicator version (`v2.0`) if formula changes
- Link research → indicator → strategy with `source_url` + `research_references`
- Store `config.json` with every backtest (for reproducibility)
- Update MEMORY.md when you add major new research/indicators
- Use SQLite queries instead of grepping files

## First Commit

```bash
git add MEMORY.md USER.md docs/ schemas/ research/ indicators/specs/ strategies/specs/ CHEATSHEET.md .gitignore
git commit -m "feat: initialize AutoQuant three-layer memory system

- Repo Memory (small, Git-tracked): MEMORY.md, docs/, schemas/, specs/
- Artifact Store (large, immutable): artifacts/ (not Git-tracked)
- Retrieval Index: SQLite artifacts.db schema documented
- Specs vs Artifacts: clear separation (research/, indicators/specs/, strategies/specs/ are Git-tracked source of truth)
- ID conventions: specs use filenames, artifacts use hash-first (type--sha256_12)
- Added ResearchCard, IndicatorRecord, StrategySpec, BacktestReport schemas with required fields
- Constitution: goals, non-goals, memory rules, decision process
- ADR 0001: three-layer design rationale
- Runbook 00: how to run pipeline, index backtests, query results
"
```

---

**Last Updated:** 2026-02-21  
**Owner:** Ghosted
