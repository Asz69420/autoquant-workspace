#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def process_one(insight_path: Path, max_refinements: int) -> tuple[bool, bool]:
    card = read_json(insight_path, {})
    if not isinstance(card, dict):
        return False, False

    card['status'] = 'PROCESSED'
    write_json(insight_path, card)

    title = str(card.get('title') or 'Manual insight')[:120]
    concept = str(card.get('concept') or '')[:2000]
    tags = card.get('tags') or []

    rc_cmd = [
        PY, 'scripts/pipeline/emit_research_card.py',
        '--source-ref', f"manual_insight:{card.get('id','unknown')}",
        '--source-type', 'manual_insight',
        '--raw-text', concept,
        '--title', title,
    ]
    if tags:
        rc_cmd += ['--tags', json.dumps(tags)]

    rc = json.loads(run(rc_cmd))
    an = json.loads(run([PY, 'scripts/pipeline/run_analyser.py', '--research-card-path', rc['research_card_path'], '--linkmap-path', '']))
    run([PY, 'scripts/pipeline/verify_pipeline_stage2.py', '--thesis', an['thesis_path']])
    sp = json.loads(run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', an['thesis_path']]))

    ran_batch = False
    if int(sp.get('variants') or 0) > 0 and sp.get('strategy_spec_path'):
        ran_batch = True
        run([PY, 'scripts/pipeline/run_batch_backtests.py', '--strategy-spec', sp['strategy_spec_path'], '--variant', 'all'])

        if max_refinements > 0:
            promo_id = Path(sp['strategy_spec_path']).stem
            promo_path = ROOT / 'artifacts' / 'promotions' / datetime.now().strftime('%Y%m%d') / f'promo_{promo_id}.promotion_run.json'
            promo_obj = {
                'schema_version': '1.0',
                'id': f'promo_{promo_id}',
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'status': 'OK',
                'input_linkmap_path': '',
                'thesis_artifact_path': an['thesis_path'],
                'strategy_spec_artifact_path': sp['strategy_spec_path'],
                'batch_backtest_artifact_path': '',
                'experiment_plan_artifact_path': '',
            }
            write_json(promo_path, promo_obj)
            run([PY, 'scripts/pipeline/run_refinement_loop.py', '--promotion-run', str(promo_path).replace('\\', '/'), '--max-iters', '1'])
    return True, ran_batch


def main() -> int:
    max_refinements = 1
    if '--max-refinements' in sys.argv:
        i = sys.argv.index('--max-refinements')
        max_refinements = int(sys.argv[i + 1])

    idx_path = ROOT / 'artifacts' / 'insights' / 'INDEX.json'
    idx = read_json(idx_path, [])
    if not isinstance(idx, list):
        idx = []

    existing = [ROOT / str(p) for p in idx if (ROOT / str(p)).exists()]
    new_cards = []
    for p in existing:
        c = read_json(p, {})
        if isinstance(c, dict) and c.get('status') == 'NEW':
            new_cards.append(p)

    out = {'new': len(new_cards), 'processed': 0, 'failed': 0}
    if not new_cards:
        print(json.dumps(out))
        return 0

    target = new_cards[0]
    try:
        ok, _ = process_one(target, max_refinements=max_refinements)
        out['processed'] = 1 if ok else 0
    except Exception:
        out['failed'] = 1

    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
