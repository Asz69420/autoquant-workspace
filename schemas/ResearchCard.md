# ResearchCard Schema

**Purpose:** Document a hypothesis, finding, or exploratory result. Immutable spec, Git-tracked.

## Required Fields
- `id` (string): Unique ID, use filename convention: `research-{topic}-{YYYYMMDD}` (e.g., `research-volatility-signal-20260221`)
- `title` (string): One-line summary of research question or finding
- `author` (string): Who did this research
- `created_at` (ISO 8601 timestamp): When added to repo
- `hypothesis` (string): What you tested or explored (50–200 words)
- `findings` (string): What you learned; main results (100–500 words)
- `confidence` (enum): `high`, `medium`, `low`, `uncertain`
- `tags` (array): e.g., `["hyperliquid", "volatility", "signal-design"]`
- `source_url` (string): Where this came from (paper, blog, personal observation)
- `rights` (enum): `open`, `restricted`, `unknown` (can this be shared/published?)
- `attribution_required` (bool): Must credit original source?

## Optional Fields
- `next_steps` (string): Proposed follow-up work
- `artifact_ids` (array): References to related artifacts (e.g., `["backtest--a1b2c3d4e5f6"]`)
- `lineage_json` (JSON): `{ "depends_on": [...], "generated_by": "...", "notes": "..." }`
- `license` (string): `MIT`, `CC-BY-4.0`, `internal`, etc.
- `related_specs` (array): Links to indicator/strategy specs that use this research

## File Naming Convention
- Path: `research/{id}.json` (e.g., `research/research-volatility-signal-20260221.json`)
- Store only one research card per file
- Immutable once committed to Git

## Links to Artifact Store
- Embed artifact references as array of IDs: `"artifact_ids": ["backtest--a1b2c3d4e5f6", "video--b2c3d4e5f6g7"]`
- The artifact's path and details are in the SQLite `artifacts` table; fetch from there

## Minimal Example Instance
```json
{
  "id": "research-volatility-signal-20260221",
  "title": "Volatility clustering on Binance BTC/USDT 15m bars",
  "author": "Ghosted",
  "created_at": "2026-02-21T23:15:00Z",
  "hypothesis": "Realized volatility on Binance hourly BTC/USDT shows strong mean-reversion after spikes; potential entry signal for pairs/mean-reversion strategies.",
  "findings": "Analyzed 90 days of 1m OHLC data from Binance. Found that 15m rolling volatility mean-reverts in 2–4 hours with 0.72 autocorrelation at lag-12. Daily spikes (>2σ) reverse within 4 hours 68% of the time. Tested on both live + backtest data; consistent pattern.",
  "confidence": "medium",
  "tags": ["binance", "volatility", "signal-design", "mean-reversion", "15m-timeframe"],
  "source_url": "personal observation + Binance API analysis",
  "rights": "restricted",
  "attribution_required": false,
  "next_steps": "Design volatility z-score indicator; backtest on Hyperliquid; verify signal timing (close vs. open-next).",
  "artifact_ids": [],
  "lineage_json": {
    "depends_on": [],
    "generated_by": "manual research + Python analysis",
    "notes": "Handwritten notes in OneNote; Python notebook in local machine"
  },
  "license": "internal",
  "related_specs": ["indicators/specs/indicator-volatility-zscore-v1.json"]
}
```
