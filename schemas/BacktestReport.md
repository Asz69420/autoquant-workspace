# BacktestReport Schema

**Purpose:** Record results of a single backtest run. Immutable artifact (output only, never Git-tracked).

## Required Fields
- `id` (string): Hash-first ID convention: `backtest--{sha256_12}` (e.g., `backtest--a1b2c3d4e5f6`)
- `strategy_id` (string): Path to strategy spec (e.g., `strategies/specs/strategy-mean-revert-btc-v1.json`)
- `dataset_id` (string): Which market data (e.g., `data-binance-btc-2024`)
- `config_hash` (string): SHA256 of config.json; ensures reproducibility
- `execution_model` (string): How orders filled: `market`, `limit`, `twap`, `vwap`, `mock`
- `fees_model` (string): Fee structure: `binance-0.1%`, `hyperliquid-0.05%`, `none`, etc.
- `slippage_model` (string): Slippage assumption: `none`, `fixed-0.01%`, `empirical`, `adaptive`
- `fill_assumptions` (string): Order execution assumption: `full`, `partial-80%`, `aggressive`, `realistic`
- `signal_timing` (string): When does entry signal fire? `close`, `open-next`, `eod`, `adaptive`
- `start_date` (ISO date)
- `end_date` (ISO date)
- `metrics_json` (JSON object): Key results
  ```json
  {
    "total_return_pct": 15.3,
    "sharpe": 1.2,
    "max_drawdown_pct": -8.5,
    "win_rate": 0.55,
    "profit_factor": 1.8,
    "trades": 120,
    "avg_trade_pnl": 125.50,
    "best_trade": 500,
    "worst_trade": -250
  }
  ```
- `artifacts_path` (string): Path to folder with detailed results (e.g., `artifacts/backtests/backtest--a1b2c3d4e5f6/`)
- `created_at` (ISO 8601)
- `tags` (array)

## Optional Fields
- `source_url` (string): Where backtest was run (local machine, cloud service, etc.)
- `rights` (string): `open`, `restricted`, `unknown` (can results be shared?)
- `attribution_required` (bool)
- `notes` (string): Notable observations, caveats, next steps
- `lineage_json` (JSON): `{ "depends_on": [...strategy, dataset...], "generated_by": "backtrader_v2", ... }`
- `instrument` (string): e.g., `BTC/USDT`; de-normalized for fast queries

## File Naming
- Metadata: `artifacts/backtests/{id}.json` (e.g., `artifacts/backtests/backtest--a1b2c3d4e5f6.json`)
- Detailed outputs folder: `artifacts/backtests/{id}/`
  ```
  artifacts/backtests/backtest--a1b2c3d4e5f6/
  ├── config.json                 # Exact backtest config (for reproduction)
  ├── metrics.json                # Copy of the main metrics (for quick access)
  ├── equity_curve.csv            # Day-by-day cumulative returns
  ├── trades.csv                  # All trades: entry_time, entry_price, exit_time, exit_price, pnl
  ├── plots/
  │   ├── equity_curve.png
  │   ├── drawdown.png
  │   ├── monthly_returns.png
  │   └── correlation_heatmap.png
  └── log.txt                     # Full backtest run log
  ```

## Immutability & Deduplication
- Once written to `artifacts/backtests/{id}/`, never modify
- Content hash = immutability marker; same config + data = same hash, same backtest
- SQLite `config_hash` column prevents duplicate runs
- To reproduce: retrieve `config.json` from artifact, re-run with identical parameters

## Minimal Example
```json
{
  "id": "backtest--a1b2c3d4e5f6",
  "strategy_id": "strategies/specs/strategy-mean-revert-btc-v1.json",
  "dataset_id": "data-binance-btc-2024",
  "config_hash": "9f86d081884c7d6d9ffd60bb51d3378a812c6f8b",
  "execution_model": "market",
  "fees_model": "binance-0.1%",
  "slippage_model": "fixed-0.01%",
  "fill_assumptions": "full",
  "signal_timing": "close",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "metrics_json": {
    "total_return_pct": 15.3,
    "sharpe": 1.2,
    "max_drawdown_pct": -8.5,
    "win_rate": 0.55,
    "profit_factor": 1.8,
    "trades": 120,
    "avg_trade_pnl": 125.50,
    "best_trade": 500,
    "worst_trade": -250
  },
  "artifacts_path": "artifacts/backtests/backtest--a1b2c3d4e5f6/",
  "created_at": "2026-02-21T23:16:00Z",
  "tags": ["binance", "mean-reversion", "btc", "2024-data", "v1.0"],
  "source_url": "local machine (Ghosted)",
  "rights": "restricted",
  "attribution_required": false,
  "notes": "Strong Sharpe but max drawdown worrying in Q3 (market stress); needs risk adjustment. Ready for paper trading.",
  "lineage_json": {
    "depends_on": [
      "strategies/specs/strategy-mean-revert-btc-v1.json",
      "indicators/specs/indicator-volatility-zscore-v1.json",
      "data-binance-btc-2024"
    ],
    "generated_by": "backtrader_v4.1",
    "notes": "Ran on Binance 1m OHLC data; fees included; slippage 0.01%"
  },
  "instrument": "BTC/USDT",
  "license": "internal"
}
```

## Reproducibility Guarantee
1. Every backtest stores its `config.json` in the artifact folder
2. `config_hash` = SHA256 of config.json; use to find reproducible backtests
3. To reproduce exactly:
   ```bash
   # Fetch config
   cat artifacts/backtests/backtest--a1b2c3d4e5f6/config.json
   # Re-run
   python run_backtest.py --config artifacts/backtests/backtest--a1b2c3d4e5f6/config.json
   # New backtest should have same config_hash and metrics (within rounding)
   ```
