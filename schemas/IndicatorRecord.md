# IndicatorRecord Schema

**Purpose:** Define a technical indicator (RSI, custom metric, etc.). Version-tracked, immutable spec, Git-tracked.

## Required Fields
- `id` (string): Use filename convention: `indicator-{name}-{version}` (e.g., `indicator-volatility-zscore-v1`)
- `name` (string): Human-readable name
- `version` (semantic): e.g., `1.0.0`
- `formula` (string): Plain English or pseudocode definition
- `parameters` (object): Tunable params with defaults (e.g., `{ "period": 14, "threshold": 2.0 }`)
- `code_path` (string): Relative path to implementation (e.g., `indicators/volatility_zscore.py`)
- `created_at` (ISO 8601)
- `tags` (array): `["volatility", "momentum", "custom"]`, etc.
- `source_url` (string): Where this came from (paper, package, personal design)
- `rights` (enum): `open`, `restricted`, `unknown`
- `attribution_required` (bool): Must credit original source?

## Optional Fields
- `description` (string): Detailed explanation (motivation, when to use, when NOT to use)
- `signal_timing` (string): When does it fire? `close`, `open-next`, `eod`, `adaptive`
- `research_source` (string): Link to research card that inspired this (e.g., `research/research-volatility-signal-20260221.json`)
- `test_results` (array): Backtest IDs that tested this indicator (e.g., `["backtest--a1b2c3d4e5f6"]`)
- `lineage_json` (JSON): Track evolution, dependencies
- `license` (string)

## File Naming
- Metadata: `indicators/specs/{id}.json` (e.g., `indicators/specs/indicator-volatility-zscore-v1.json`)
- Code: `indicators/{name}_{version}.py` (e.g., `indicators/volatility_zscore_v1.py`)
- Implementation can be referenced via `code_path`; no duplicate code in spec

## Minimal Example
```json
{
  "id": "indicator-volatility-zscore-v1",
  "name": "Volatility Z-Score",
  "version": "1.0.0",
  "formula": "z = (realized_vol - sma(realized_vol, period)) / std(realized_vol, period)",
  "parameters": {
    "period": 14,
    "threshold": 2.0
  },
  "code_path": "indicators/volatility_zscore_v1.py",
  "created_at": "2026-02-21T23:15:00Z",
  "tags": ["volatility", "custom", "binance", "zscore"],
  "source_url": "research/research-volatility-signal-20260221.json",
  "rights": "restricted",
  "attribution_required": false,
  "description": "Detects elevated volatility conditions using rolling z-score. Fires when volatility exceeds threshold (2σ default). Useful for signal generation and risk management; triggers entry signals in mean-reversion strategies.",
  "signal_timing": "close",
  "research_source": "research/research-volatility-signal-20260221.json",
  "test_results": [],
  "lineage_json": {
    "depends_on": ["research/research-volatility-signal-20260221.json"],
    "generated_by": "Ghosted",
    "notes": "Tested on Binance 15m bars; signal triggers on close"
  },
  "license": "internal"
}
```
