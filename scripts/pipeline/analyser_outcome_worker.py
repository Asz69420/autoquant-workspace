#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
DIRECTIVE_TYPES = {
    'ROLE_SWAP', 'THRESHOLD_SWEEP', 'PARAM_SWEEP', 'ENTRY_TIGHTEN', 'ENTRY_RELAX', 'EXIT_CHANGE', 'GATE_ADJUST', 'TEMPLATE_SWITCH'
}


def _j(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _log(status_word: str, reason: str, summary: str):
    cmd = [
        PY, 'scripts/log_event.py',
        '--run-id', f"analyser-outcome-{int(datetime.now(UTC).timestamp())}",
        '--agent', 'Analyser',
        '--model-id', 'openai-codex/gpt-5.3-codex',
        '--action', 'ANALYSER_OUTCOME_SUMMARY',
        '--status-word', status_word,
        '--status-emoji', ('OK' if status_word == 'OK' else ('WARN' if status_word == 'WARN' else 'FAIL')),
        '--reason-code', reason,
        '--summary', summary,
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def latest_file(pattern: str) -> Path | None:
    files = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _extract_metrics(batch: dict) -> tuple[float, float, int, dict, str, str]:
    runs = batch.get('runs') or []
    summary = batch.get('summary') or {}
    best = runs[0] if runs else {}
    if runs:
        # deterministic: choose run with highest PF then lowest DD then highest trades
        best = sorted(
            runs,
            key=lambda r: (
                float(r.get('profit_factor', 0.0) or 0.0),
                -float(r.get('max_drawdown', 1.0) or 1.0),
                int(r.get('trades', 0) or 0),
            ),
            reverse=True,
        )[0]
    pf = float(best.get('profit_factor', summary.get('profit_factor', 0.0)) or 0.0)
    dd = float(best.get('max_drawdown', summary.get('max_drawdown', 1.0)) or 1.0)
    trades = int(best.get('trades', summary.get('trades', 0)) or 0)
    strategy_path = str(batch.get('strategy_spec_path') or '')
    strategy_family = Path(strategy_path).stem if strategy_path else 'unknown_strategy'
    template = str(best.get('variant_name') or batch.get('variant') or 'unknown_template')
    return pf, dd, trades, best, strategy_family, template


def _classify_verdict(pf_after_costs: float, max_drawdown: float, trades: int) -> str:
    # deterministic hard gates
    if trades < 20 or pf_after_costs < 1.0 or max_drawdown > 0.30:
        return 'REJECT'
    if pf_after_costs < 1.2 or max_drawdown > 0.20:
        return 'REVISE'
    return 'ACCEPT'


def _failure_reasons(pf: float, dd: float, trades: int, evidence: str, refinement: dict) -> list[dict]:
    out: list[dict] = []
    if trades < 20:
        out.append({'code': 'LOW_TRADE_COUNT', 'short': f'Trade count below gate: {trades} < 20', 'evidence_pointer': evidence})
    if dd > 0.30:
        out.append({'code': 'HIGH_DRAWDOWN', 'short': f'Max drawdown too high: {dd:.3f} > 0.30', 'evidence_pointer': evidence})
    if pf < 1.0:
        out.append({'code': 'PF_BELOW_1', 'short': f'Profit factor after costs below 1.0: {pf:.3f}', 'evidence_pointer': evidence})
    rec = str(refinement.get('final_recommendation') or '')
    if rec == 'NO_IMPROVEMENT':
        out.append({'code': 'NO_IMPROVEMENT', 'short': 'Refinement reported no improvement', 'evidence_pointer': 'refinement_cycle.final_recommendation'})
    if not out:
        out.append({'code': 'MARGIN_RISK', 'short': 'No hard fail; tune thresholds to improve margin of safety', 'evidence_pointer': evidence})
    return out[:5]


def _directives_from_failures(failures: list[dict], verdict: str) -> list[dict]:
    directives: list[dict] = []
    idx = 1
    for f in failures:
        code = f['code']
        if code == 'LOW_TRADE_COUNT':
            directives.append({'id': f'd{idx}', 'type': 'ENTRY_RELAX', 'params': {'confidence_threshold_delta': -0.05}, 'rationale': 'Increase participation to clear minimum trade gate.', 'priority': 1})
            idx += 1
            directives.append({'id': f'd{idx}', 'type': 'THRESHOLD_SWEEP', 'params': {'parameter': 'confidence_threshold', 'range': [0.5, 0.7], 'step': 0.05}, 'rationale': 'Sweep entry threshold to recover trade frequency.', 'priority': 2})
            idx += 1
        elif code == 'HIGH_DRAWDOWN':
            directives.append({'id': f'd{idx}', 'type': 'ENTRY_TIGHTEN', 'params': {'confidence_threshold_delta': 0.05}, 'rationale': 'Tighten entry quality to reduce adverse excursions.', 'priority': 1})
            idx += 1
            directives.append({'id': f'd{idx}', 'type': 'EXIT_CHANGE', 'params': {'stop_atr_mult': 1.2, 'tp_atr_mult': 1.8}, 'rationale': 'Adjust exits to cap drawdown.', 'priority': 2})
            idx += 1
        elif code == 'PF_BELOW_1':
            directives.append({'id': f'd{idx}', 'type': 'PARAM_SWEEP', 'params': {'parameter': 'risk_r', 'range': [0.5, 1.5], 'step': 0.25}, 'rationale': 'Re-balance payoff profile to improve PF.', 'priority': 1})
            idx += 1
            directives.append({'id': f'd{idx}', 'type': 'ROLE_SWAP', 'params': {'swap': 'entry<->confirmation'}, 'rationale': 'Test alternate component role assignment for better edge.', 'priority': 3})
            idx += 1
        elif code == 'NO_IMPROVEMENT':
            directives.append({'id': f'd{idx}', 'type': 'TEMPLATE_SWITCH', 'params': {'target': 'FALLBACK_TEMPLATE_CONFIRMATION'}, 'rationale': 'Switch template when local refinement stalls.', 'priority': 2})
            idx += 1
        elif code == 'MARGIN_RISK':
            directives.append({'id': f'd{idx}', 'type': 'GATE_ADJUST', 'params': {'min_trades_required': 25}, 'rationale': 'Raise reliability gate under acceptable baseline.', 'priority': 3})
            idx += 1
    if verdict == 'REJECT' and len(directives) < 2:
        directives.append({'id': f'd{idx}', 'type': 'GATE_ADJUST', 'params': {'max_drawdown_cap': 0.25}, 'rationale': 'Enforce stricter DD cap before promotion.', 'priority': 1})
    out = []
    for d in directives:
        if d['type'] in DIRECTIVE_TYPES and d not in out:
            out.append(d)
        if len(out) >= 5:
            break
    return out[:5] if out else [{'id': 'd1', 'type': 'GATE_ADJUST', 'params': {'min_trades_required': 20}, 'rationale': 'Default deterministic gate hygiene.', 'priority': 3}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--batch-artifact', default='')
    ap.add_argument('--refinement-artifact', default='')
    args = ap.parse_args()

    batch_path = Path(args.batch_artifact) if args.batch_artifact else latest_file('artifacts/batches/**/batch_*.batch_backtest.json')
    ref_path = Path(args.refinement_artifact) if args.refinement_artifact else latest_file('artifacts/refinement/**/*.refinement_cycle.json')
    lessons_path = ROOT / 'artifacts' / 'library' / 'LESSONS_INDEX.json'

    batch = _j(batch_path, {}) if batch_path else {}
    refinement = _j(ref_path, {}) if ref_path else {}
    _ = _j(lessons_path, [])

    sources_used: list[str] = []
    if batch_path and batch_path.exists():
        sources_used.append(str(batch_path).replace('\\', '/'))
    if ref_path and ref_path.exists():
        sources_used.append(str(ref_path).replace('\\', '/'))
    if lessons_path.exists():
        sources_used.append(str(lessons_path).replace('\\', '/'))

    pf, dd, trades, best_run, strategy_family, template = _extract_metrics(batch)
    verdict = _classify_verdict(pf, dd, trades)
    evidence = (best_run.get('backtest_result_path') or (sources_used[0] if sources_used else 'artifacts/backtests/unknown'))

    failures = _failure_reasons(pf, dd, trades, str(evidence), refinement)
    directives = _directives_from_failures(failures, verdict)

    next_experiments = [
        f"Apply {d['type']} with params={json.dumps(d['params'], sort_keys=True)}"
        for d in directives[:5]
    ]

    day = datetime.now(UTC).strftime('%Y%m%d')
    out_dir = ROOT / 'artifacts' / 'outcomes' / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'outcome_notes_{args.run_id}.json'
    payload = {
        'schema_version': '2.0',
        'id': f'outcome-notes-{args.run_id}',
        'run_id': args.run_id,
        'created_at': datetime.now(UTC).isoformat(),
        'verdict': verdict,
        'strategy_family': strategy_family,
        'template': template,
        'failure_reasons': failures[:5],
        'directives': directives[:5],
        'next_experiments': next_experiments[:5],
        'sources_used': sources_used[:10],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    summary_line = f'ANALYSER_OUTCOME_SUMMARY — processed=1 verdict={verdict} directives={len(directives[:5])}'
    _log('OK' if verdict == 'ACCEPT' else 'WARN', 'ANALYSER_OUTCOME_SUMMARY', summary_line)
    print(summary_line)
    print(json.dumps({'processed': 1, 'verdict': verdict, 'directives': len(directives[:5]), 'outcome_notes_path': str(out_path).replace('\\', '/')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
