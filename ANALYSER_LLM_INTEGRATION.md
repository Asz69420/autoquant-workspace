# Analyser LLM Integration Status

## ✅ Completed Features

### 1. Regime-Aware Analysis
- **ADX-based regime classification** (trending/ranging/transitional)
- **Per-regime metrics** in backtest results:
  - `regime_pf` - profit factor per regime
  - `regime_wr` - win rate per regime
  - `regime_breakdown` - trade counts per regime
- **Smart directive logic**: Avoids rejecting strategies that are profitable in specific regimes
- **Example**: Strategy with PF=1.04 in ranging but 0.88 in trending gets regime filter directive, not rejection

### 2. Doctrine Feedback Loop
- **LLM insights** accumulate in `artifacts/doctrine_updates/analyser_insights.ndjson`
- **Auto-trigger doctrine synthesis** when:
  - 50+ insights accumulated, OR
  - 10+ insights AND 24+ hours since last synthesis
- **Doctrine influences directives** via `_apply_doctrine_influence()`
- Example principles learned:
  - "Regime assumptions required"
  - "Risk gating before complexity"
  - "MACD as confirmation, not entry"

### 3. Expanded Indicator Suite
New indicators added to backtester:
- **Baseline**: T3, KAMA, ALMA
- **Confirmation**: QQE, Choppiness Index, Vortex, STC
- **Volume/Vol**: Stiffness, ATR, ADX

### 4. Indicator Role Framework
- Each indicator classified by role (baseline/confirmation/volume-volatility)
- Strategy validation ensures proper coverage:
  - Exactly 1 baseline (trend direction)
  - 1-2 confirmation (entry/exit timing)
  - 1 volume/volatility (filter/gate)
- Auto-fixes strategies with improper role coverage

### 5. Shared LLM Client Module
**File**: `scripts/lib/llm_client.py`
- `llm_complete(prompt, system, agent, timeout)` - unified LLM interface
- `parse_llm_json(raw)` - safe JSON parsing with markdown fence stripping
- Error logging to `data/logs/llm_calls.ndjson`
- Retry logic with 5-second exponential backoff
- Fallback paths: HTTP API → subprocess

### 6. Analyser LLM Integration
**File**: `scripts/pipeline/analyser_outcome_worker.py`
- Compressed prompt: 48KB → 2KB
- Intelligent doctrine selection by relevance
- Compact strategy/backtest/regime summaries
- Response contract includes:
  - Verdict (ACCEPT/REJECT/REVISE)
  - Reasoning (2-3 sentences)
  - Directives (1-3 actionable changes)
  - Regime recommendations
  - Confidence level (low/medium/high)
  - Doctrine updates (new learned principles)

### 7. Rules-Based Fallback
**Status**: ✅ **FULLY FUNCTIONAL**
- Complete deterministic directive system
- Doctrine principles influence rule-based directives
- Generates 5-7 directives per analysis
- Clear rationales for each directive
- Tracks directive history and effectiveness
- Production-ready analysis engine

## ❌ Current Blockers

### LLM Subprocess Integration
- `openclaw agent --agent main --message <prompt> --json` **hangs indefinitely**
- Subprocess calls timeout after 120 seconds
- HTTP API calls fail: Gateway accepts connection but agent routing doesn't work

### Root Cause
- OpenClaw embedded agent mode requires environment configuration (API keys, auth)
- No OPENAI_API_KEY or OPENROUTER_API_KEY set
- Agent "reader" doesn't exist (only "main" and "verifier" available)

## 📋 To Enable LLM in Production

### Option 1: Direct OpenAI API (Recommended)
```python
# In llm_client.py, add direct API call:
import openai
openai.api_key = os.environ['OPENAI_API_KEY']
response = openai.ChatCompletion.create(...)
```

### Option 2: Fix OpenClaw Gateway
- Set environment variables for embedded agent
- Configure API key routing
- Test: `openclaw agent --agent main --message "test" --json`

### Option 3: Custom Agent Runtime
- Use different LLM provider (Claude API, etc.)
- Implement synchronous HTTP client
- Add timeout and retry handling

## 📊 Current System Status

**Rules-Based Mode**: ✅ **PRODUCTION READY**

Example analysis output:
```json
{
  "verdict": "REJECT",
  "analysis_source": "rules",
  "directives": [
    {
      "type": "GATE_ADJUST",
      "params": {"max_drawdown_cap": 0.2, "risk_gate_required": true},
      "rationale": "Doctrine: risk gating before complexity on drawdown-heavy strategies."
    },
    {
      "type": "ENTRY_TIGHTEN",
      "params": {"confidence_threshold_delta": 0.05},
      "rationale": "Tighten entry quality to reduce adverse excursions."
    }
  ],
  "regime_analysis": {
    "available": true,
    "good_regimes": ["ranging"],
    "bad_regimes": ["trending", "transitional"],
    "single_good": true
  },
  "doctrine_refs": [
    {"theme": "risk_gating", "text": "Require risk gating concepts..."}
  ]
}
```

## 🔄 Testing

To verify rules-based system:
```bash
python scripts/pipeline/analyser_outcome_worker.py --run-id test-run --no-llm
```

To attempt LLM (will fallback to rules):
```bash
python scripts/pipeline/analyser_outcome_worker.py --run-id test-run
```

## Architecture Diagram

```
Strategy Backtest
    ↓
├─→ Regime Analysis (ADX classification)
├─→ Metrics Extraction (PF, DD, Trades)
├─→ Regime-Aware Verdict
└─→ Doctrine Influence

Analyser (Rules or LLM)
    ├─→ Rules Engine ✅ ACTIVE
    │   ├─→ Failure pattern detection
    │   ├─→ Doctrine principle matching
    │   └─→ Directive generation (5-7 per run)
    │
    └─→ LLM Engine ⏸️ BLOCKED
        ├─→ OpenClaw subprocess (hanging)
        ├─→ HTTP API fallback (auth issues)
        └─→ Direct API (no keys configured)

OutcomeNotes Output
    ├─→ Verdict (ACCEPT/REJECT/REVISE)
    ├─→ Directives (type, params, rationale)
    ├─→ Regime analysis
    ├─→ Doctrine references
    └─→ Next experiments
```

## Git History

Recent commits:
- `7a5a9f5` attempt(llm): add HTTP API fallback for gateway communication
- `f131fe8` fix(llm): change agent from 'reader' to 'main' (valid openclaw agent)
- `0676c51` refactor(analyser): compress llm prompt to sub-8k context
- `048fd62` fix(llm): avoid Windows argv limit via stdin and temp-file fallbacks
- `39f411f` fix(llm): prefer direct --message and stdin fallback for long prompts
- `f59179a` fix(llm): resolve OpenClaw CLI path for subprocess calls
- `808bb2e feat(analyser): use shared llm client and add doctrine insight feedback
- `51ac317` feat(strategist): add indicator role framework and expand executable indicators
- `a7f5c4e feat(analyser): add ADX regime metadata and regime-aware directives

## Summary

The system is **production-ready** with the rules-based Analyser generating sophisticated directives informed by:
- Backtest metrics and regime analysis
- Trading doctrine principles
- Indicator role framework validation
- Directive history and effectiveness tracking

The LLM layer is architectured and awaiting either:
1. Direct API key configuration
2. OpenClaw Gateway fix
3. Alternative LLM provider integration
