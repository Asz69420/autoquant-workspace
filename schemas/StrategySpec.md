# StrategySpec Schema

**Purpose:** Define a trading strategy: entry/exit rules, risk, position sizing. Single source of truth for backtesting + execution.

## Required Fields
- `id` (string): Use filename convention: `strategy-{name}-{version}` (e.g., `strategy-mean-revert-btc-v1`)
- `name` (string): Human-readable name
- `version` (semantic)
- `instrument` (string): e.g., `BTC/USDT` (Binance) or `BTC/USD-PERP` (Hyperliquid)
- `timeframe` (string): `1m`, `5m`, `15m`, `1h`, etc.
- `entry_rules` (string): Plain English or pseudocode; must be deterministic
- `exit_rules` (string): When to close position
- `risk_params` (object): `{ "max_loss_pct": 2.0, "max_position_usd": 5000, "leverage": 2.0 }`
- `indicators` (array): List of indicator spec paths used (e.g., `["indicators/specs/indicator-volatility-zscore-v1.json"]`)
- `created_at` (ISO 8601)
- `status` (enum): `draft`, `backtested`, `paper-trading`, `live`, `retired`
- `tags` (array)
- `source_url` (string): Where this came from (research, paper, personal design)
- `rights` (enum): `open`, `restricted`, `unknown`
- `attribution_required` (bool)

## Optional Fields
- `description` (string): Detailed explanation (when/why to use, market conditions)
- `research_references` (array): Links to research cards that motivated this (e.g., `["research/research-volatility-signal-20260221.json"]`)
- `backtest_results` (array): Backtest artifact IDs (e.g., `["backtest--a1b2c3d4e5f6"]`)
- `lineage_json` (JSON)
- `code_path` (string): Implementation path
- `license` (string)

## File Naming
- Metadata: `strategies/specs/{id}.json` (e.g., `strategies/specs/strategy-mean-revert-btc-v1.json`)
- Code: `strategies/{name}_{version}.py` (e.g., `strategies/mean_revert_btc_v1.py`)

## Minimal Example
```json
{
  "id": "strategy-mean-revert-btc-v1",
  "name": "Mean Revert BTC 15m",
  "version": "1.0.0",
  "instrument": "BTC/USDT",
  "timeframe": "15m",
  "entry_rules": "When volatility_zscore > 2.0 AND price is above 20-period SMA, go short. Position size = min(5000 / leverage, account_equity * 0.05).",
  "exit_rules": "Close when volatility_zscore < 1.0 OR position loss > 2% OR time_in_trade > 4 hours.",
  "risk_params": {
    "max_loss_pct": 2.0,
    "max_position_usd": 5000,
    "leverage": 2.0
  },
  "indicators": ["indicators/specs/indicator-volatility-zscore-v1.json"],
  "created_at": "2026-02-21T23:15:00Z",
  "status": "draft",
  "tags": ["binance", "mean-reversion", "btc", "15m"],
  "source_url": "personal design",
  "rights": "restricted",
  "attribution_required": false,
  "description": "Short-term mean-reversion strategy on BTC when volatility spikes. Entry on z-score > 2.0 (elevated vol); exit when volatility normalizes or max loss hit. Target: capture reversion within 4-hour window.",
  "research_references": ["research/research-volatility-signal-20260221.json"],
  "backtest_results": [],
  "lineage_json": {
    "depends_on": ["research/research-volatility-signal-20260221.json", "indicators/specs/indicator-volatility-zscore-v1.json"],
    "generated_by": "Ghosted",
    "notes": "Waiting for full backtest on Binance 2024 data"
  },
  "license": "internal"
}
```
