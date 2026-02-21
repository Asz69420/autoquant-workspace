# SQLite Retrieval Index Schema

**Database:** `artifacts.db` (created on first backtest run; in .gitignore)

## Tables

### `artifacts` — Central artifact registry
```sql
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,            -- hash-first ID: type--sha256_12
  type TEXT NOT NULL,             -- 'research', 'video', 'backtest', 'dataset'
  source_url TEXT,                -- Where it came from (GitHub URL, paper, etc.)
  created_at TIMESTAMP NOT NULL,  -- ISO 8601
  hash TEXT NOT NULL UNIQUE,      -- SHA256 (full); immutability marker
  path TEXT NOT NULL,             -- Relative path: artifacts/{type}/{id}/
  title TEXT,                     -- One-liner
  summary TEXT,                   -- 100–300 words
  tags TEXT,                      -- JSON array: ["tag1", "tag2"]
  rights TEXT,                    -- 'open', 'restricted', 'unknown'
  attribution_required INTEGER,   -- 0 or 1 (bool)
  license TEXT,                   -- 'MIT', 'CC-BY-4.0', 'internal', etc.
  lineage_json TEXT,              -- {"depends_on": [...], "generated_by": "...", "notes": "..."}
  metadata_json TEXT              -- Type-specific extra fields (flexible)
);

CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_artifacts_created ON artifacts(created_at);
CREATE INDEX idx_artifacts_hash ON artifacts(hash);
CREATE INDEX idx_artifacts_rights ON artifacts(rights);
```

### `strategies` — Strategy specification index
```sql
CREATE TABLE strategies (
  id TEXT PRIMARY KEY,             -- path-based: strategies/specs/strategy-{name}-{version}.json
  spec_path TEXT NOT NULL,         -- Full path to spec file (Git-tracked)
  status TEXT,                     -- 'draft', 'backtested', 'paper-trading', 'live', 'retired'
  score REAL,                      -- Aggregate score (e.g., Sharpe from best backtest)
  last_eval_id TEXT,               -- Most recent backtest artifact ID
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  tags TEXT,                       -- JSON array: ["tag1", "tag2"]
  notes TEXT,
  metadata_json TEXT               -- Strategy-specific fields
);

CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_score ON strategies(score DESC);
```

### `backtests` — Backtest result index
```sql
CREATE TABLE backtests (
  id TEXT PRIMARY KEY,             -- hash-first: backtest--sha256_12
  artifact_id TEXT NOT NULL,       -- Foreign key to artifacts.id
  strategy_id TEXT NOT NULL,       -- Foreign key to strategies.id (or path to spec)
  dataset_id TEXT,                 -- e.g., 'data-binance-btc-2024'
  config_hash TEXT NOT NULL,       -- Config immutability; SHA256 of config.json
  execution_model TEXT,            -- 'market', 'limit', 'twap', etc.
  fees_model TEXT,                 -- 'binance-0.1%', 'hyperliquid-0.05%', etc.
  slippage_model TEXT,             -- 'none', 'fixed-0.01%', 'empirical', etc.
  fill_assumptions TEXT,           -- 'full', 'partial-80%', 'aggressive', etc.
  signal_timing TEXT,              -- 'close', 'open-next', 'eod', 'adaptive'
  start_date DATE,
  end_date DATE,
  metrics_json TEXT NOT NULL,      -- {"total_return_pct": ..., "sharpe": ..., "max_dd": ...}
  artifacts_path TEXT NOT NULL,    -- Path to detailed results (CSVs, plots)
  created_at TIMESTAMP,
  tags TEXT,                       -- JSON array: ["tag1", "tag2"]
  notes TEXT,
  lineage_json TEXT,
  FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);
CREATE INDEX idx_backtests_created ON backtests(created_at);
CREATE INDEX idx_backtests_config_hash ON backtests(config_hash);
CREATE INDEX idx_backtests_artifact ON backtests(artifact_id);
```

### `indicators` — Indicator definition index
```sql
CREATE TABLE indicators (
  id TEXT PRIMARY KEY,             -- path-based: indicators/specs/indicator-{name}-{version}.json
  spec_path TEXT NOT NULL,         -- Full path to spec file (Git-tracked)
  name TEXT NOT NULL,
  version TEXT,
  code_path TEXT,                  -- Relative path to implementation
  formula TEXT,
  parameters TEXT,                 -- JSON object
  source_url TEXT,                 -- Where this came from
  rights TEXT,                     -- 'open', 'restricted', 'unknown'
  attribution_required INTEGER,    -- 0 or 1
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  tags TEXT,                       -- JSON array
  metadata_json TEXT
);

CREATE INDEX idx_indicators_name ON indicators(name, version);
CREATE INDEX idx_indicators_path ON indicators(spec_path);
```

### `research` — Research card index
```sql
CREATE TABLE research (
  id TEXT PRIMARY KEY,             -- path-based: research/research-{name}-{date}.json
  spec_path TEXT NOT NULL,         -- Full path to spec file (Git-tracked)
  title TEXT,
  hypothesis TEXT,
  confidence TEXT,                 -- 'high', 'medium', 'low', 'uncertain'
  source_url TEXT,
  rights TEXT,                     -- 'open', 'restricted', 'unknown'
  created_at TIMESTAMP,
  tags TEXT,                       -- JSON array
  artifact_ids TEXT,               -- JSON array of artifact IDs this research references
  lineage_json TEXT,
  metadata_json TEXT
);

CREATE INDEX idx_research_title ON research(title);
CREATE INDEX idx_research_confidence ON research(confidence);
CREATE INDEX idx_research_created ON research(created_at);
```

## Key Queries

### Find top strategies by Sharpe ratio
```sql
SELECT s.id, s.status, b.metrics_json->>'$.sharpe' AS sharpe, b.created_at
FROM strategies s
LEFT JOIN backtests b ON b.id = s.last_eval_id
ORDER BY sharpe DESC
LIMIT 10;
```

### Find all backtests for a strategy
```sql
SELECT id, created_at, 
       metrics_json->>'$.total_return_pct' AS return_pct,
       metrics_json->>'$.sharpe' AS sharpe
FROM backtests
WHERE strategy_id = 'strategies/specs/strategy-mean-revert-btc-v1.json'
ORDER BY created_at DESC;
```

### Deduplicate artifacts by hash (find duplicate runs)
```sql
SELECT hash, COUNT(*) as count, GROUP_CONCAT(id) as ids
FROM artifacts
GROUP BY hash
HAVING count > 1;
```

### Find related artifacts (by tag)
```sql
SELECT id, type, title, tags, created_at
FROM artifacts
WHERE tags LIKE '%hyperliquid%'
  AND type IN ('research', 'backtest')
ORDER BY created_at DESC
LIMIT 20;
```

### Trace lineage: what depends on this artifact/spec?
```sql
SELECT id, type, lineage_json
FROM artifacts
WHERE lineage_json LIKE '%depends_on%'
  AND lineage_json LIKE '%research/research-volatility-signal%'
LIMIT 10;
```

### Find research cards that motivated a strategy
```sql
SELECT r.id, r.title, r.confidence
FROM research r
WHERE r.artifact_ids LIKE '%strategy-mean-revert%'
ORDER BY r.created_at DESC;
```

### Check for reproducibility: find config by hash
```sql
SELECT id, artifacts_path, config_hash
FROM backtests
WHERE config_hash = '9f86d081884c7d6d9ffd60bb51d3378a812c6f8b';
```

## Notes
- JSON fields use SQLite's `->>` operator for extraction (JSON1 extension)
- All timestamps are ISO 8601 (UTC)
- Hashes are SHA256 hex strings; IDs truncate to 12 chars (`type--abc123def456`)
- tags/metadata/lineage are stored as JSON strings; parse on retrieval
- Specs (research/, indicators/specs/, strategies/specs/) are Git-tracked; use file paths as IDs
- Artifacts (backtests, videos, etc.) are immutable; use hash-based IDs
- Config reproducibility: every backtest's config.json is stored in artifacts/ with its config_hash
