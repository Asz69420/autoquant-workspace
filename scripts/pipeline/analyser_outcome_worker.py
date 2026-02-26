#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--batch-artifact', default='')
    ap.add_argument('--refinement-artifact', default='')
    args = ap.parse_args()

    batch_path = Path(args.batch_artifact) if args.batch_artifact else latest_file('artifacts/backtests/**/batch-*.json')
    ref_path = Path(args.refinement_artifact) if args.refinement_artifact else latest_file('artifacts/refinements/**/*.json')
    lessons_path = ROOT / 'artifacts' / 'library' / 'LESSONS_INDEX.json'

    worked = []
    failed = []
    hypotheses = []
    evidence = []

    if batch_path and batch_path.exists():
      batch = _j(batch_path, {})
      evidence.append(str(batch_path).replace('\\', '/'))
      for r in (batch.get('runs') or [])[:10]:
          if r.get('gate_pass') is True and len(worked) < 5:
              worked.append(f"{r.get('variant_name','variant')}: gate_pass=true")
          if (r.get('gate_pass') is False or r.get('skip_reason')) and len(failed) < 5:
              failed.append(f"{r.get('variant_name','variant')}: {r.get('skip_reason') or 'gate_fail'}")

    if ref_path and ref_path.exists():
      ref = _j(ref_path, {})
      evidence.append(str(ref_path).replace('\\', '/'))
      rec = str(ref.get('final_recommendation') or '')
      if rec and len(worked) < 5:
          worked.append(f'refinement recommendation: {rec}')
      if rec == 'NO_IMPROVEMENT' and len(failed) < 5:
          failed.append('refinement: no improvement found')

    lessons = _j(lessons_path, [])
    if isinstance(lessons, list):
        evidence.append(str(lessons_path).replace('\\', '/'))
        for l in lessons[:5]:
            pat = (l.get('pattern') if isinstance(l, dict) else None) or 'lesson_pattern'
            sug = (l.get('suggestion') if isinstance(l, dict) else None) or 'test narrower hypothesis'
            if len(hypotheses) < 5:
                hypotheses.append(f"{pat}: {sug}")

    while len(worked) < 5:
        worked.append('insufficient recent signal: maintain conservative baseline')
    while len(failed) < 5:
        failed.append('insufficient recent failure detail: keep current guardrails')
    while len(hypotheses) < 5:
        hypotheses.append('derive one additional falsifiable entry filter from latest losses')

    day = datetime.now(UTC).strftime('%Y%m%d')
    out_dir = ROOT / 'artifacts' / 'outcomes' / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'outcome_notes_{args.run_id}.json'
    payload = {
        'id': f'outcome-notes-{args.run_id}',
        'run_id': args.run_id,
        'created_at': datetime.now(UTC).isoformat(),
        'what_worked': worked[:5],
        'what_failed': failed[:5],
        'next_hypotheses': hypotheses[:5],
        'evidence_pointers': evidence[:10],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    _log('OK', 'ANALYSER_OUTCOME_SUMMARY', 'Analyser outcome: processed=1 status=OK')
    print(json.dumps({'processed': 1, 'status': 'OK', 'outcome_notes_path': str(out_path).replace('\\', '/')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
