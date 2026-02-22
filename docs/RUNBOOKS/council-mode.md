# Council Mode (v1)

Use Council mode for tough decisions where you want two model viewpoints to challenge each other before acting.

## Intent-based trigger guidance

You do **not** need an exact phrase in code. Any intent-equivalent request is valid, for example:
- "ask the council"
- "run council"
- "get council take"
- "council this decision"

The workflow is intent-based: if the request clearly asks for a two-model council pass, use this runbook.

## Runner

- Script: `scripts/automation/council.ps1`
- Models:
  - Main: `openai-codex/gpt-5.3-codex`
  - Peer: `opencode/minimax-m2.5`
- Inputs:
  - `--question` (required)
  - `--rounds` (optional, default `5`, allowed `3..5`)
  - `--name` (optional)
  - `--reasoning` (`adaptive|low|medium|high`, default `adaptive`)
  - `--verbosity` (`short|medium`, default `short`)
  - `--timeoutSec` (optional HTTP timeout, default `60`)

## Protocol

1. **Round 1:** independent answers from both models
2. **Round 2:** cross-critique
3. **Round 3:** revised answers
4. **Rounds 4-5:** only if materially disagree
5. **Early stop:** when convergence/consensus is reached
6. **Degraded mode:** if one model fails/timeouts, continue with warning + best synthesis (no hard crash)

Final output always includes:
- Recommended action
- Confidence
- Key risks
- What would change decision
- Immediate next test

## Usage examples

```powershell
# Help
./scripts/automation/council.ps1 --help

# Basic
./scripts/automation/council.ps1 --question "Should we deploy Strategy A this week?"

# Named decision, force max 4 rounds
./scripts/automation/council.ps1 --question "Cut over to Binance-only data for this sprint?" --rounds 4 --name "Data Feed Cutover"

# Use high reasoning for hard calls
./scripts/automation/council.ps1 --question "Should we productionize strategy X now?" --reasoning high
```

## Requirements

Set model API key in environment (either one):

```powershell
$env:OPENROUTER_API_KEY="<your_key>"
# or
$env:OPENCODE_API_KEY="<your_key>"
```

The runner also auto-loads from `.env` (workspace root) and `C:\Users\Clamps\.openclaw\.env` when present.

Optional:

```powershell
$env:OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
```
