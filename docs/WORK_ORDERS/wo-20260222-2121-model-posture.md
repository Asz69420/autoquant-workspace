# Keeper Work Order — Model Posture Sync (Locked)

## Intent
Sync curated memory + status to match the current model policy and agent mapping. No runtime config edits. No secrets.

## Evidence (read-only pointers)
- memory/2026-02-22.md (raw trace entry)
- USER.md (if updated)
- openclaw.json (runtime snapshot; read-only)
- git commit(s): 96f6101, b672c57

## Allowlist (Keeper may edit ONLY these)
- MEMORY.md (ONLY section: "Model Policy (Locked)")
- docs/STATUS.md (ONLY section: "Current model posture")
- docs/HANDOFFS/handoff-20260222-2121.md (new file only)

## Curated changes (exact bullets to apply)
### MEMORY.md → Model Policy (Locked)
ADD bullets:
- Primary model: Codex 5.3
- Fallback model: Haiku
- Manual-only: MiniMax (excluded from automatic fallback)
- Active agents on Codex: Specter, Keeper, Strategist, Firewall, òQ
- Haiku-primary agents: Reader, Grabber
REMOVE bullets:
- Sonnet (removed from active model list)
- Opus (removed from active model list)
Reason (1–2 lines):
- Cross-provider fallback preferred; MiniMax excluded from automatic fallback due to reliability/rate-limit concerns.

### docs/STATUS.md → Current model posture
Replace snapshot lines with:
- Primary: Codex 5.3
- Fallback: Haiku
- Manual-only: MiniMax
- Agents: (same mapping as above)

### docs/HANDOFFS/handoff-20260222-2121.md
Create a short pointer-only checkpoint containing:
- What changed (model posture)
- Where it’s recorded (memory log + MEMORY.md section)
- Any operational notes (restart gateway after validation)

## Safety
- Do not include secrets (tokens, API keys, auth blobs, private URLs).
- Do not modify schemas/strategies/indicators.
- Do not touch runtime configs.

## Validation checklist (must PASS before commit)
- USER.md consistent with MEMORY.md
- MEMORY.md consistent with docs/STATUS.md
- Latest HANDOFF exists and points to evidence
- openclaw.json posture matches the curated docs (read-only check)
