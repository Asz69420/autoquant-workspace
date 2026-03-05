# Runbook 00: How to Run the AutoQuant Pipeline

## Quick Start

### 1. Set Up Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env (template provided)
cp .env.template .env
# Edit .env: add your Binance/Hyperliquid API keys (no secrets in Git)
```

### 2. Run a Backtest
```bash
# Single strategy, single dataset
python run_backtest.py --strategy strategies/specs/strategy-mean-revert-btc-v1.json --dataset data-binance-btc-2024

# Output structure:
data/cache/backtest--a1b2c3d4e5f6/
├── metrics.json                # BacktestReport schema (immutable once indexed)
├── equity_curve.csv            # Day-by-day returns
├── trades.csv                  # All trades: entry, exit, P&L
├── config.json                 # Exact config (for reproducibility)
├── plots/
│   ├── equity_curve.png
│   └── drawdown.png
└── log.txt                     # Full run log
```

### 3. Index the Result
```bash
# Index the backtest; moves to artifacts/, computes hash
python scripts/index_backtest.py data/cache/backtest--a1b2c3d4e5f6/metrics.json

# Updates SQLite: artifacts(id, type, hash, path, summary, ...)
# Output: artifacts/backtests/backtest--a1b2c3d4e5f6/
```

### 4. Query Results
```bash
# Find top strategies by Sharpe
python scripts/query_index.py --strategy-ranking sharpe

# Find all backtests for a strategy
python scripts/query_index.py --strategy strategies/specs/strategy-mean-revert-btc-v1.json

# Deduplicate by hash (check for duplicate runs)
python scripts/query_index.py --dedup-hash
```

## Detailed: Adding a New Indicator

1. **Research** (ResearchCard spec, Git-tracked)
   - Create `research/research-volatility-signal-20260221.json`
   - Document hypothesis, findings, confidence

2. **Implement Spec** (IndicatorRecord, Git-tracked)
   - Create `indicators/specs/indicator-volatility-zscore-v1.json`
   - Define formula, parameters, dependencies

3. **Implement Code** (Git-tracked source)
   - Create `indicators/volatility_zscore.py`
   - Reference from spec

4. **Test in Backtest**
   - Add to StrategySpec: `"indicators": ["indicators/specs/indicator-volatility-zscore-v1.json"]`
   - Run backtest
   - Index results

## Detailed: Running a Full Backtest

```bash
# Single strategy, single dataset, multiple workers
python run_backtest.py \
  --strategy strategies/specs/strategy-mean-revert-btc-v1.json \
  --dataset data-binance-btc-2024 \
  --workers 4 \
  --output data/cache/

# Output structure:
data/cache/backtest--a1b2c3d4e5f6/
├── metrics.json                # Matches BacktestReport schema
├── equity_curve.csv            # Daily returns
├── trades.csv                  # Entry/exit/P&L
├── config.json                 # config_hash reproducibility
├── plots/
│   ├── equity_curve.png
│   ├── drawdown.png
│   └── correlation_heatmap.png
└── log.txt                     # Debug info

# Index it (moves to artifacts/, computes SHA256)
python scripts/index_backtest.py data/cache/backtest--a1b2c3d4e5f6/metrics.json

# Updates SQLite + symlinks to artifacts/backtests/backtest--a1b2c3d4e5f6/
```

## Understanding the File Layout

| Directory | Purpose | Git-Tracked? | Mutable? |
|-----------|---------|--------------|----------|
| `research/` | Research card specs (hypotheses, findings) | ✅ Yes | ❌ No (specs) |
| `indicators/specs/` | Indicator definition specs | ✅ Yes | ❌ No (specs) |
| `indicators/` | Indicator implementations (.py) | ✅ Yes | ✅ Yes (code) |
| `strategies/specs/` | Strategy definition specs | ✅ Yes | ❌ No (specs) |
| `strategies/` | Strategy implementations (.py) | ✅ Yes | ✅ Yes (code) |
| `artifacts/backtests/` | Backtest results (immutable) | ❌ No | ❌ No (immutable) |
| `artifacts/videos/` | Research videos, etc. | ❌ No | ❌ No (immutable) |
| `data/cache/` | Temporary backtest outputs (before indexing) | ❌ No | ✅ Yes (temp) |
| `data/feeds/` | Market data (if cached locally) | ❌ No | ✅ Yes (data) |

## Troubleshooting

### Q: Backtest failed with "strategy {file} not found"
**A:** Verify the strategy spec file exists:
```bash
ls -la strategies/specs/strategy-*.json
```

### Q: SQLite index grows too large
**A:** Archive old artifacts:
```bash
python scripts/archive_backtest.py --before 2025-12-31 --dest archive/
```

### Q: How do I reproduce a backtest exactly?
**A:** Every backtest has a `config_hash` in BacktestReport. Configuration is stored in the artifact:
```bash
cat artifacts/backtests/backtest--a1b2c3d4e5f6/config.json
```
Re-run with:
```bash
python run_backtest.py --config artifacts/backtests/backtest--a1b2c3d4e5f6/config.json
```

### Q: What's the difference between `data/cache/` and `artifacts/backtests/`?
**A:**
- `data/cache/` is temporary (before indexing); you can delete it
- `artifacts/backtests/` is permanent + immutable (content-hashed); never delete

---

## Scheduling (Clock-Aligned, No Overlap)

Task Scheduler cadence (Australia/Brisbane):

- `\AutoQuant-autopilot` → every **2 hours on the hour** (`00:00, 02:00, 04:00, ...`)
- `\AutoQuant-youtube-watch` → every **2 hours at +10 minutes** (`00:10, 02:10, 04:10, ...`)
- `\AutoQuant-tv-catalog` → every **12 hours** at `01:00` and `13:00`
- `\AutoQuant-keeper-30m` → every **30 minutes** aligned to `:00` and `:30`
- `\AutoQuant-tg_reporter` → existing cadence retained

Collision rules:

- Keep **single-instance / no-overlap** (`MultipleInstances=IgnoreNew`) on automation tasks.
- Keep unattended execution model (S4U/background) and highest-privilege posture as configured.
- Keep task working directory and command action unchanged unless explicitly re-approved.

See also: `docs/RUNBOOKS/01-adding-indicators.md`, `docs/RUNBOOKS/02-running-backtest.md`, `docs/RUNBOOKS/ppr-scoring.md`, `docs/SCHEMA-sqlite.md`
