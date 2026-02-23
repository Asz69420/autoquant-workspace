# ActionEvent Schema

**Purpose:** Structured log of every action (start, completion, error, retry, etc.). 
All agents emit ActionEvents locally to `data/logs/outbox/` (primary; `spool/` is legacy read-compat only); only Logger sends to Telegram.

## Required Fields
- `ts_iso` (ISO 8601 UTC): "2026-02-22T15:01:00Z"
- `ts_local` (Brisbane 12h AM/PM AEST): "22 Feb 10:01 AM AEST"
- `run_id` (string): Unique run identifier (e.g., "backtest--a1b2c3d4e5f6")
- `agent` (string): Agent name (e.g., "BacktestRunner", "Logger", "ResearchAgent")
- `model_id` (string): Model used (e.g., "haiku", "sonnet", "n/a")
- `action` (string): What the agent did (e.g., "run_backtest", "index_backtest", "send_telegram")
- `status_word` (enum): START, OK, WARN, FAIL, BLOCKED, SKIP, PAUSE, QUEUED, RETRY, THROTTLED, CANCELLED, ARCHIVED, TESTING, PROMOTED, REJECTED, INFO
- `status_emoji` (string): Corresponding emoji (▶️, ✅, ⚠️, ❌, ⛔, ⏭️, ⏸️, ⏳, 🔁, 🐢, 🛑, 🧊, 🧪, 🏆, 🗑️, ℹ️)
- `summary` (string): One-liner describing what happened
- `inputs` (array): List of input paths/URLs (e.g., ["strategies/specs/strategy-mean-revert-btc-v1.json"])
- `outputs` (array): List of output paths/artifact IDs (e.g., ["backtest--a1b2c3d4e5f6"])

## Optional Fields
- `reason_code` (string): Short code if status is WARN/FAIL/BLOCKED/SKIP/REJECTED (e.g., "OVERFIT", "TIMEOUT", "NEEDS_APPROVAL")
- `attempt` (string): Retry attempt count (e.g., "2/5")
- `error` (object): 
  ```json
  {
    "message": "Connection timeout",
    "type": "TimeoutError",
    "stack_short": "line 42: tg_notify.py: requests.post() timeout"
  }
  ```
- `tags` (array): Searchable tags (e.g., ["hyperliquid", "backtest", "critical"])
- `lineage_json` (object): `{ "depends_on": [...], "generated_by": "...", "notes": "..." }`

## File Naming
- Primary path: `data/logs/outbox/{ts_file}___{run_id}___{agent}___{status_word}.json`
- Legacy compat path (read-only fallback in reporter): `data/logs/spool/{ts_file}___{run_id}___{agent}___{status_word}.json`
- `ts_file` format: `YYYYMMDDTHHMMSSZ` (filename-safe, no colons)
- Example: `20260222T150100Z___backtest--a1b2c3d4e5f6___BacktestRunner___OK.json`
- Spool files are deleted after Logger successfully processes + sends to Telegram

## Minimal Example: OK (Successful)
```json
{
  "ts_iso": "2026-02-22T15:01:00Z",
  "ts_local": "22 Feb 10:01 AM AEST",
  "run_id": "backtest--a1b2c3d4e5f6",
  "agent": "BacktestRunner",
  "model_id": "n/a",
  "action": "run_backtest",
  "status_word": "OK",
  "status_emoji": "✅",
  "summary": "Backtest completed: 2024-01-01 to 2024-12-31, Sharpe 1.2",
  "inputs": ["strategies/specs/strategy-mean-revert-btc-v1.json", "data-binance-btc-2024"],
  "outputs": ["backtest--a1b2c3d4e5f6"],
  "tags": ["binance", "mean-reversion", "completed"]
}
```

## Minimal Example: FAIL (Error)
```json
{
  "ts_iso": "2026-02-22T15:05:30Z",
  "ts_local": "22 Feb 10:05 AM AEST",
  "run_id": "backtest--x9y8z7w6v5u4",
  "agent": "BacktestRunner",
  "model_id": "n/a",
  "action": "run_backtest",
  "status_word": "FAIL",
  "status_emoji": "❌",
  "reason_code": "TIMEOUT",
  "summary": "Backtest timeout after 10 minutes",
  "inputs": ["strategies/specs/strategy-example-v2.json"],
  "outputs": [],
  "error": {
    "message": "Backtest execution exceeded 600 seconds",
    "type": "TimeoutError",
    "stack_short": "run_backtest.py:142 -> executor.run(timeout=600)"
  },
  "tags": ["timeout", "alert"]
}
```

## Minimal Example: BLOCKED (Needs Approval)
```json
{
  "ts_iso": "2026-02-22T15:10:00Z",
  "ts_local": "22 Feb 10:10 AM AEST",
  "run_id": "add-indicator--vol-zscore-v2",
  "agent": "SpecValidator",
  "model_id": "haiku",
  "action": "validate_spec",
  "status_word": "BLOCKED",
  "status_emoji": "⛔",
  "reason_code": "NEEDS_APPROVAL",
  "summary": "New indicator spec requires approval before deployment",
  "inputs": ["indicators/specs/indicator-volatility-zscore-v2.json"],
  "outputs": [],
  "tags": ["approval-required"]
}
```

## Minimal Example: RETRY (Attempting Again)
```json
{
  "ts_iso": "2026-02-22T15:15:45Z",
  "ts_local": "22 Feb 10:15 AM AEST",
  "run_id": "index-backtest--b2c3d4e5f6g7",
  "agent": "Logger",
  "model_id": "n/a",
  "action": "send_telegram",
  "status_word": "RETRY",
  "status_emoji": "🔁",
  "attempt": "2/5",
  "summary": "Retrying Telegram send (connection unstable)",
  "inputs": [],
  "outputs": [],
  "error": {
    "message": "Connection refused; retrying in 5s",
    "type": "ConnectionError",
    "stack_short": "tg_notify.py:58 -> requests.post(timeout=5)"
  },
  "tags": ["network-issue"]
}
```

## Minimal Example: THROTTLED (Rate-Limited)
```json
{
  "ts_iso": "2026-02-22T15:20:00Z",
  "ts_local": "22 Feb 10:20 AM AEST",
  "run_id": "batch-research--01",
  "agent": "ResearchAgent",
  "model_id": "sonnet",
  "action": "fetch_external_data",
  "status_word": "THROTTLED",
  "status_emoji": "🐢",
  "summary": "Rate-limited by API; backing off 30s",
  "inputs": ["https://api.example.com/data"],
  "outputs": [],
  "tags": ["rate-limit", "backoff"]
}
```

## Minimal Example: PROMOTED (Status Upgrade)
```json
{
  "ts_iso": "2026-02-22T15:25:00Z",
  "ts_local": "22 Feb 10:25 AM AEST",
  "run_id": "strategy--mean-revert-btc",
  "agent": "StrategyEvaluator",
  "model_id": "haiku",
  "action": "promote_strategy",
  "status_word": "PROMOTED",
  "status_emoji": "🏆",
  "summary": "Strategy promoted: draft → backtested (Sharpe > 1.0)",
  "inputs": ["strategies/specs/strategy-mean-revert-btc-v1.json"],
  "outputs": ["strategies/specs/strategy-mean-revert-btc-v1.json"],
  "tags": ["promotion", "success"]
}
```

## Validation Rules
- All required fields must be present
- `status_word` must match one of the 16 allowed values
- `ts_local` format: "DD MMM HH:MM AM|PM AEST"
- If `status_word` ∈ {WARN, FAIL, BLOCKED, SKIP, REJECTED}, `reason_code` is recommended
- If `status_word` = RETRY, `attempt` is required
- `inputs` and `outputs` should be relative paths (from repo root) or artifact IDs
- No secrets in any field (ever)
