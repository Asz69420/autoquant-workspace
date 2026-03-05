#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORDERS_FILE="$ROOT_DIR/docs/shared/QUANDALF_ORDERS.md"
RESULTS_FILE="$ROOT_DIR/docs/shared/LAST_CYCLE_RESULTS.md"

if [[ ! -f "$ORDERS_FILE" ]]; then
  echo "Orders file not found: $ORDERS_FILE"
  exit 1
fi

PY_BIN="python"
if command -v python3 >/dev/null 2>&1; then
  PY_BIN="python3"
fi

STATE_DIR="$ROOT_DIR/data/state"
STATE_FILE="$STATE_DIR/quandalf_handoff_state.json"
REFLECTION_STATE_FILE="$STATE_DIR/quandalf_reflection_state.json"
LOCK_DIR="$STATE_DIR/locks/quandalf_pipeline.lockdir"
ACTIONS_FILE="$ROOT_DIR/data/logs/actions.ndjson"
RUNTIME_FLAGS_FILE="$ROOT_DIR/config/runtime_flags.json"

mkdir -p "$STATE_DIR" "$ROOT_DIR/data/state/locks"

HYPER_MODE="0"
if [[ -f "$RUNTIME_FLAGS_FILE" ]]; then
  HYPER_MODE=$("$PY_BIN" - "$RUNTIME_FLAGS_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    obj = json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
except Exception:
    obj = {}
print('1' if bool(obj.get('hyperMode')) else '0')
PY
)
fi

cleanup_lock() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}

trigger_frodex_chain() {
  if [[ "$HYPER_MODE" != "1" ]]; then
    return 0
  fi
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File "$ROOT_DIR/scripts/automation/trigger_frodex_chain.ps1" || true
}

if ! mkdir "$LOCK_DIR" >/dev/null 2>&1; then
  echo "SKIP: quandalf-auto-execute already running (lock held)."
  exit 0
fi
trap cleanup_lock EXIT

readarray -t GATE_INFO < <("$PY_BIN" - "$ACTIONS_FILE" "$STATE_FILE" <<'PY'
import json
import re
import sys
from pathlib import Path

actions_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])

def base_run_id(run_id: str) -> str | None:
    m = re.match(r'^(autopilot-\d+)', run_id or '')
    return m.group(1) if m else None

last_processed = ''
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        last_processed = str(state.get('last_processed_run_id') or '')
    except Exception:
        last_processed = ''

latest = ''
latest_ts = ''
if actions_path.exists():
    for raw in actions_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        t = raw.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except Exception:
            continue
        if str(obj.get('action') or '') != 'LAB_SUMMARY':
            continue
        rid = base_run_id(str(obj.get('run_id') or ''))
        if not rid:
            continue
        ts = str(obj.get('ts_iso') or '')
        if not latest or ts > latest_ts:
            latest = rid
            latest_ts = ts

print(f"LATEST_RUN_ID={latest}")
print(f"LAST_PROCESSED_RUN_ID={last_processed}")
print(f"SHOULD_RUN={1 if latest and latest != last_processed else 0}")
PY
)

LATEST_RUN_ID=""
LAST_PROCESSED_RUN_ID=""
SHOULD_RUN="0"
for line in "${GATE_INFO[@]}"; do
  line="${line%$'\r'}"
  case "$line" in
    LATEST_RUN_ID=*) LATEST_RUN_ID="${line#LATEST_RUN_ID=}" ;;
    LAST_PROCESSED_RUN_ID=*) LAST_PROCESSED_RUN_ID="${line#LAST_PROCESSED_RUN_ID=}" ;;
    SHOULD_RUN=*) SHOULD_RUN="${line#SHOULD_RUN=}" ;;
  esac
done

if [[ "$SHOULD_RUN" != "1" ]]; then
  echo "No new completed Frodex run. last=$LAST_PROCESSED_RUN_ID latest=$LATEST_RUN_ID"
  exit 0
fi

# Claude Code reflection first (Opus via run_claude_skill); non-fatal fallback to executor path.
echo "Quandalf reflection: trying Claude Code (Opus)..."
set +e
timeout 45s powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File "$ROOT_DIR/scripts/automation/run_claude_skill.ps1" \
  -Mode research -RetryCount 1 >/dev/null 2>&1
claude_rc=$?
set -e
if [[ $claude_rc -eq 124 ]]; then
  echo "WARN: Claude reflection timed out; continuing with fallback executor path."
elif [[ $claude_rc -ne 0 ]]; then
  echo "WARN: Claude reflection unavailable; continuing with fallback executor path."
fi

"$PY_BIN" - "$REFLECTION_STATE_FILE" "$LATEST_RUN_ID" "$claude_rc" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

state_path = Path(sys.argv[1])
run_id = str(sys.argv[2] or '').strip()
rc = int(sys.argv[3]) if len(sys.argv) > 3 else 1
state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
state['last_run_id'] = run_id
state['last_claude_rc'] = rc
state['last_reflection_status'] = 'ok' if rc == 0 else 'fallback_gpt'
state['last_reflection_at'] = datetime.now(timezone.utc).isoformat()
state['last_note'] = 'Claude reflection ok.' if rc == 0 else 'Claude reflection failed; used GPT fallback executor path.'
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
PY

set +e
"$PY_BIN" - "$ROOT_DIR" "$ORDERS_FILE" "$RESULTS_FILE" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(sys.argv[1])
orders_path = Path(sys.argv[2])
results_path = Path(sys.argv[3])
text = orders_path.read_text(encoding='utf-8', errors='ignore')

status_match = re.search(r"\*\*Status:\*\*\s*(\w+)", text)
if not status_match:
    print("ERROR: status_line_missing")
    sys.exit(2)

status = status_match.group(1).upper()
if status not in {"PENDING", "NEW"}:
    print("NO_PENDING")
    sys.exit(10)


def _grab_block(src: str, start_header: str, end_header_regex: str) -> str:
    pat = re.compile(start_header + r"\n\n(.*?)\n" + end_header_regex, re.S)
    m = pat.search(src)
    return m.group(1) if m else ""


def parse_strategies(src: str):
    blocks = re.findall(r"###\s+(?:New\s+)?Strategy[^\n]*\n\n(.*?)(?=\n###\s+(?:New\s+)?Strategy|\n###\s+Test Matrix|\n##\s+Test Matrix|\Z)", src, re.S)
    out = []
    for blk in blocks:
        name_m = re.search(r"^name:\s*([\w_\-]+)\s*$", blk, re.M)
        if not name_m:
            continue
        name = name_m.group(1).strip()

        def parse_list(label: str):
            m = re.search(rf"^{label}:\s*\n((?:-\s*\".*\"\s*\n?)+)", blk, re.M)
            if not m:
                return []
            lines = [ln.strip() for ln in m.group(1).strip().splitlines() if ln.strip().startswith('-')]
            vals = []
            for ln in lines:
                v = ln[1:].strip()
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                vals.append(v)
            return vals

        entry_long = parse_list('entry_long')
        entry_short = parse_list('entry_short')

        risk_block_m = re.search(r"^risk_policy:\s*\n((?:\s{2}[^\n]+\n?)+)", blk, re.M)
        risk = {
            "stop_type": "atr",
            "stop_atr_mult": 1.5,
            "tp_type": "atr",
            "tp_atr_mult": 12.0,
            "risk_per_trade_pct": 0.01,
        }
        if risk_block_m:
            for ln in risk_block_m.group(1).splitlines():
                if ':' not in ln:
                    continue
                k, v = ln.strip().split(':', 1)
                v = v.strip()
                if v in ('atr', 'none'):
                    risk[k] = v
                else:
                    try:
                        risk[k] = float(v)
                    except ValueError:
                        risk[k] = v

        out.append({
            'name': name,
            'entry_long': entry_long,
            'entry_short': entry_short,
            'risk_policy': risk,
        })
    return out


strategies = parse_strategies(text)
if not strategies:
    print("ERROR: no_strategy_blocks_parsed")
    sys.exit(3)

assets = ['ETH']
timeframes = ['4h']
assets_m = re.search(r"-\s*Assets:\s*(.+)", text)
if assets_m:
    aval = assets_m.group(1)
    found = re.findall(r"\b(BTC|ETH|SOL)\b", aval, re.I)
    if found:
        assets = [x.upper() for x in found]

tf_m = re.search(r"-\s*Timeframes:\s*(.+)", text)
if tf_m:
    tval = tf_m.group(1).lower()
    tfs = re.findall(r"\b(15m|1h|4h)\b", tval)
    if tfs:
        timeframes = [x for x in tfs]


def latest_meta(asset: str, timeframe: str) -> Path:
    d = root / 'artifacts' / 'data' / 'hyperliquid' / asset / timeframe
    metas = sorted(d.glob('*.meta.json'))
    if not metas:
        raise FileNotFoundError(f'No dataset meta found for {asset} {timeframe}')
    return metas[-1]


def run_backtest(spec_path: Path, variant_name: str, dataset_meta: Path):
    cmd = [
        sys.executable,
        str(root / 'scripts' / 'backtester' / 'hl_backtest_engine.py'),
        '--dataset-meta', str(dataset_meta),
        '--strategy-spec', str(spec_path),
        '--variant', variant_name,
        '--initial-capital', '10000',
    ]
    p = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    o = json.loads(p.stdout.strip())
    bt = json.loads(Path(o['backtest_result']).read_text(encoding='utf-8'))
    r = bt['results']
    g = bt.get('gate', {})
    return {
        'backtest_result_path': o.get('backtest_result'),
        'trade_list_path': o.get('trade_list'),
        'profit_factor': float(r.get('profit_factor', 0.0) or 0.0),
        'win_rate': float(r.get('win_rate', 0.0) or 0.0),
        'max_drawdown_pct': float(r.get('max_drawdown_pct', 0.0) or 0.0),
        'net_profit_pct': float(r.get('net_profit_pct', 0.0) or 0.0),
        'total_trades': int(r.get('total_trades', 0) or 0),
        'total_return_on_capital_pct': float(r.get('total_return_on_capital_pct', 0.0) or 0.0),
        'regime_pf': r.get('regime_pf', {'trending': 0.0, 'ranging': 0.0, 'transitional': 0.0}),
        'gate_pass': bool(g.get('gate_pass', True)),
        'gate_reason': str(g.get('gate_reason', 'OK')),
        'min_trades_required': int(g.get('min_trades_required', 0) or 0),
    }


tmp_dir = root / 'artifacts' / 'tmp'
tmp_dir.mkdir(parents=True, exist_ok=True)

rows = []
for strat in strategies:
    spec = {
        'schema_version': '1.0',
        'id': strat['name'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_thesis_path': 'docs/shared/QUANDALF_ORDERS.md',
        'variants': [{
            'name': strat['name'],
            'template_name': 'spec_rules',
            'entry_long': strat['entry_long'],
            'entry_short': strat['entry_short'],
            'risk_policy': strat['risk_policy'],
            'execution_policy': {
                'entry_fill': 'bar_close',
                'tie_break': 'worst_case',
                'allow_reverse': True,
            },
            'parameters': [],
            'filters': [],
            'exit_rules': [],
            'risk_rules': [],
            'constraints': ['bar_close_execution', 'no_pyramiding'],
        }],
    }
    spec_path = tmp_dir / f"{strat['name']}.auto.json"
    spec_path.write_text(json.dumps(spec), encoding='utf-8')

    for asset in assets:
        for tf in timeframes:
            meta_path = latest_meta(asset, tf)
            m = run_backtest(spec_path, strat['name'], meta_path)
            rows.append({
                'strategy': strat['name'],
                'asset': asset,
                'timeframe': tf,
                **m,
            })


def pct(v: float) -> str:
    return f"{v*100:.2f}%"


def render_md(results):
    order_names = ' + '.join(f"`{s['name']}`" for s in strategies)
    md = []
    md.append('# Last Cycle Results\n')
    md.append('> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.\n')
    md.append('## Cycle Summary')
    md.append(f"- Order: {order_names}")
    md.append('- Status: COMPLETE')
    md.append(f"- Assets tested: {', '.join(sorted(set(r['asset'] for r in results)))}")
    md.append(f"- Timeframes tested: {', '.join(sorted(set(r['timeframe'] for r in results), key=lambda x: ['15m','1h','4h'].index(x) if x in ['15m','1h','4h'] else 9))}")
    md.append('- Initial capital: $10,000\n')

    md.append('## Backtest Results (per strategy/timeframe)\n')
    md.append('| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |')
    md.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for r in results:
        gate = 'PASS' if r['gate_pass'] else f"FAIL (`{r['gate_reason']}`)"
        md.append(
            f"| {r['strategy']} | {r['asset']} | {r['timeframe']} | {r['profit_factor']:.3f} | {r['win_rate']*100:.2f}% | {r['max_drawdown_pct']:.4f}% | {r['net_profit_pct']:.4f}% | {r['total_trades']} | {r['total_return_on_capital_pct']:.4f}% | {gate} |"
        )

    md.append('\n## Regime Breakdown (PF)\n')
    md.append('| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |')
    md.append('|---|---|---:|---:|---:|---:|')
    for r in results:
        rg = r.get('regime_pf', {}) or {}
        md.append(f"| {r['strategy']} | {r['asset']} | {r['timeframe']} | {float(rg.get('trending',0.0)):.3f} | {float(rg.get('ranging',0.0)):.3f} | {float(rg.get('transitional',0.0)):.3f} |")

    fails = [r for r in results if not r['gate_pass']]
    md.append('\n## Gate Failures')
    if not fails:
        md.append('- None.')
    else:
        for f in fails:
            md.append(f"- {f['strategy']} {f['asset']} {f['timeframe']}: `{f['gate_reason']}` (min required: {f['min_trades_required']}, observed: {f['total_trades']})")

    if len(strategies) >= 2:
        a = [r for r in results if r['strategy'] == strategies[0]['name']]
        b = [r for r in results if r['strategy'] == strategies[1]['name']]
        trades_a = sum(x['total_trades'] for x in a)
        trades_b = sum(x['total_trades'] for x in b)
        avg_pf_a = sum(x['profit_factor'] for x in a) / len(a) if a else 0.0
        avg_pf_b = sum(x['profit_factor'] for x in b) / len(b) if b else 0.0
        md.append('\n## Critical Comparison')
        md.append(f"- `{strategies[0]['name']}` trades: **{trades_a}** | avg PF: **{avg_pf_a:.3f}**")
        md.append(f"- `{strategies[1]['name']}` trades: **{trades_b}** | avg PF: **{avg_pf_b:.3f}**")
        md.append(f"- Trade count difference: **{trades_a - trades_b:+d}**")

    return '\n'.join(md).rstrip() + '\n'


results_path.write_text(render_md(rows), encoding='utf-8')
updated = re.sub(r"(\*\*Status:\*\*\s*)(?:PENDING|NEW)", r"\1COMPLETE", text, count=1)
orders_path.write_text(updated, encoding='utf-8')
print(f"EXECUTED {len(rows)} RUNS")
PY
py_rc=$?
set -e

mark_processed_run() {
  "$PY_BIN" - "$STATE_FILE" "$LATEST_RUN_ID" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

state_path = Path(sys.argv[1])
run_id = str(sys.argv[2] or '').strip()
if not run_id:
    raise SystemExit(0)
state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
state['last_processed_run_id'] = run_id
state['updated_at'] = datetime.now(timezone.utc).isoformat()
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
PY
}

if [[ $py_rc -eq 10 ]]; then
  mark_processed_run
  trigger_frodex_chain
  echo "No pending Quandalf order for completed run $LATEST_RUN_ID."
  exit 0
elif [[ $py_rc -ne 0 ]]; then
  echo "Quandalf execution failed."
  exit $py_rc
fi

cd "$ROOT_DIR"
if ! git diff --quiet -- docs/shared/QUANDALF_ORDERS.md docs/shared/LAST_CYCLE_RESULTS.md; then
  git add docs/shared/QUANDALF_ORDERS.md docs/shared/LAST_CYCLE_RESULTS.md
  git commit -m "docs(quandalf): auto-execute pending order"
fi

# Optional notification skipped due to timeout risk
# powershell.exe -NoProfile -ExecutionPolicy Bypass \
#   -File "$ROOT_DIR/scripts/claude-tasks/send-quandalf-cycle-summary.ps1" \
#   -TaskLabel "Strategy Cycle" \
#   -SourceFile "$ROOT_DIR/docs/shared/QUANDALF_JOURNAL.md"

mark_processed_run
trigger_frodex_chain

echo "Quandalf pending order processed for run $LATEST_RUN_ID."
