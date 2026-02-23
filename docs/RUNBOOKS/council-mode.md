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

## Protocol (deterministic)

0. **Preflight (required):** probe both model routes before Round 1.
1. **Round 1:** independent answers from both models (if both available)
2. **Round 2:** cross-critique
3. **Round 3:** revised answers
4. **Rounds 4-5:** only if materially disagree
5. **Early stop:** when convergence/consensus is reached

Deterministic branch behavior:
- **Both models available** → full council rounds (`Execution mode: normal`)
- **One model unavailable** → single-model path + degraded local synthesis (`Execution mode: degraded`)
- **Both models unavailable** → immediate degraded local synthesis (`Execution mode: degraded`)
- **Final synthesis call fails** → always fallback to degraded local synthesis

Reason codes and precedence:
- `NONE`
- `AUTH_FAIL`
- `MODEL_UNAVAILABLE`
- `TOOL_PATH_FAIL`

Precedence (highest wins):
`AUTH_FAIL > MODEL_UNAVAILABLE > TOOL_PATH_FAIL > NONE`

Final output contract is preserved with required sections:
- Recommended action
- Confidence
- Key risks
- What would change decision
- Immediate next test

Metadata lines are emitted outside those sections:
- `Execution mode: normal|degraded`
- `Failure reason: NONE|AUTH_FAIL|MODEL_UNAVAILABLE|TOOL_PATH_FAIL`

Council lifecycle logging (mandatory):
- Emit `START` ActionEvent when council begins.
- Emit terminal `OK|WARN|FAIL` ActionEvent on completion.
- Reuse the same `run_id` for start + terminal pair.
- Emit via `scripts/log_event.py` to outbox (logger handles channel delivery).

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

## Troubleshooting matrix

| Symptom | Reason code | Detection rule | Expected execution mode | Operator action |
|---|---|---|---|---|
| 401/403 or auth rejection | AUTH_FAIL | HTTP status 401/403 or auth error pattern | degraded | Rotate/fix API key, verify env load, rerun |
| Model route timeout/unavailable/provider disabled | MODEL_UNAVAILABLE | Probe timeout/unavailable/not-found/provider-disabled patterns | degraded | Check provider/model availability and base URL |
| Local script/runtime/path failure | TOOL_PATH_FAIL | Non-auth, non-model-route local execution errors | degraded | Fix script path/runtime issue and rerun |
| Synthesis call fails after rounds | MODEL_UNAVAILABLE or TOOL_PATH_FAIL | Final synthesis call returns failure | degraded | Review failure reason, keep degraded output, rerun after fix |

## Safety and log hygiene

- Do not print tokens, auth headers, or raw credential-bearing payloads.
- User-facing output should include normalized reason codes only.
