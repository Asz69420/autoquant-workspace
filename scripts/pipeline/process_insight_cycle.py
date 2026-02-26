#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
REVISIT_STATE_PATH = ROOT / 'data' / 'state' / 'insight_revisit_state.json'


def run(cmd: list[str], extra_env: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True, env=env)
    return p.stdout.strip()


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def get_today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def short_err(exc: Exception) -> str:
    msg = f"{type(exc).__name__}: {str(exc)}".strip()
    return (msg or type(exc).__name__)[:220]


def emit_insight_fail(insight_id: str, step: str, err: str) -> None:
    run_id = f"insight-fail-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    summary = f"Insight fail: insight_id={insight_id} step={step} error={err}"[:400]
    cmd = [
        PY,
        'scripts/log_event.py',
        '--run-id', run_id,
        '--agent', 'oQ',
        '--model-id', 'openai-codex/gpt-5.3-codex',
        '--action', 'insight_cycle',
        '--status-word', 'WARN',
        '--status-emoji', 'WARN',
        '--reason-code', 'INSIGHT_FAIL',
        '--summary', summary,
        '--inputs', f'insight_id={insight_id}', f'step={step}',
        '--outputs', f'error={err}',
    ]
    try:
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


def run_pipeline_for_card(card: dict, max_refinements: int, mode: str) -> None:
    insight_id = str(card.get('id') or 'unknown')
    title = str(card.get('title') or '').strip()[:120]
    concept = str(card.get('concept') or '').strip()[:2000]
    tags = card.get('tags') or []

    if not title:
        raise ValueError('missing title')
    if not concept:
        raise ValueError('missing concept')

    try:
        rc_cmd = [
            PY,
            'scripts/pipeline/emit_research_card.py',
            '--source-ref', f"manual_insight:{insight_id}:{mode.lower()}",
            '--source-type', 'manual_insight',
            '--raw-text', concept,
            '--title', title,
        ]
        if tags:
            rc_cmd += ['--tags', json.dumps(tags)]
        rc = json.loads(run(rc_cmd))
    except Exception as e:
        raise RuntimeError(f'emit_research_card failed: {short_err(e)}') from e

    reasoning_env = {
        'OPENCLAW_MODEL_ID': 'openai-codex/gpt-5.3-codex',
        'OPENCLAW_REASONING_EFFORT': 'high',
    }

    try:
        an = json.loads(run([PY, 'scripts/pipeline/run_analyser.py', '--research-card-path', rc['research_card_path'], '--linkmap-path', ''], extra_env=reasoning_env))
    except Exception as e:
        raise RuntimeError(f'run_analyser failed: {short_err(e)}') from e

    try:
        run([PY, 'scripts/pipeline/verify_pipeline_stage2.py', '--thesis', an['thesis_path']])
    except Exception as e:
        raise RuntimeError(f'verify_stage2 failed: {short_err(e)}') from e

    try:
        sp = json.loads(run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', an['thesis_path']], extra_env=reasoning_env))
    except Exception as e:
        raise RuntimeError(f'emit_strategy_spec failed: {short_err(e)}') from e

    if int(sp.get('variants') or 0) > 0 and sp.get('strategy_spec_path'):
        try:
            run([PY, 'scripts/pipeline/run_batch_backtests.py', '--strategy-spec', sp['strategy_spec_path'], '--variant', 'all'])
        except Exception as e:
            raise RuntimeError(f'run_batch_backtests failed: {short_err(e)}') from e

        if max_refinements > 0:
            try:
                promo_id = Path(sp['strategy_spec_path']).stem
                promo_path = ROOT / 'artifacts' / 'promotions' / datetime.now().strftime('%Y%m%d') / f'promo_{promo_id}.promotion_run.json'
                promo_obj = {
                    'schema_version': '1.0',
                    'id': f'promo_{promo_id}',
                    'created_at': now_iso(),
                    'status': 'OK',
                    'input_linkmap_path': '',
                    'thesis_artifact_path': an['thesis_path'],
                    'strategy_spec_artifact_path': sp['strategy_spec_path'],
                    'batch_backtest_artifact_path': '',
                    'experiment_plan_artifact_path': '',
                }
                write_json(promo_path, promo_obj)
                run([PY, 'scripts/pipeline/run_refinement_loop.py', '--promotion-run', str(promo_path).replace('\\', '/'), '--max-iters', '1'])
            except Exception as e:
                raise RuntimeError(f'run_refinement_loop failed: {short_err(e)}') from e


def update_card(path: Path, card: dict, *, status: str | None = None, touch_review: bool = False, increment_times_used: bool = False, last_error: str | None = None) -> None:
    if status is not None:
        card['status'] = status
    if touch_review:
        card['last_reviewed_at'] = now_iso()
    if increment_times_used:
        card['times_used'] = int(card.get('times_used') or 0) + 1
    else:
        card['times_used'] = int(card.get('times_used') or 0)
    if 'last_reviewed_at' not in card:
        card['last_reviewed_at'] = None
    card['last_error'] = last_error
    write_json(path, card)


def process_card(target: Path, card: dict, *, max_refinements: int, mode: str) -> tuple[bool, str]:
    try:
        run_pipeline_for_card(card, max_refinements=max_refinements, mode=mode)
        update_card(target, card, status='PROCESSED', touch_review=True, increment_times_used=True, last_error=None)
        return True, ''
    except Exception as e:
        err = short_err(e)
        if ' failed:' in err:
            step = err.split(' failed:')[0]
        elif err.startswith('ValueError:'):
            step = 'precheck'
        else:
            step = 'unknown_step'
        update_card(target, card, status='FAILED', touch_review=True, increment_times_used=False, last_error=err)
        emit_insight_fail(str(card.get('id') or target.stem), step, err)
        return False, err


def main() -> int:
    max_refinements = 1
    max_insights = 1

    if '--max-refinements' in sys.argv:
        i = sys.argv.index('--max-refinements')
        max_refinements = int(sys.argv[i + 1])
    if '--max-insights' in sys.argv:
        i = sys.argv.index('--max-insights')
        max_insights = int(sys.argv[i + 1])

    idx_path = ROOT / 'artifacts' / 'insights' / 'INDEX.json'
    idx = read_json(idx_path, [])
    if not isinstance(idx, list):
        idx = []

    paths = sorted([ROOT / str(p) for p in idx if (ROOT / str(p)).exists()], key=lambda p: str(p).lower())

    new_paths: list[Path] = []
    revisit_candidates: list[Path] = []
    for p in paths:
        c = read_json(p, {})
        if not isinstance(c, dict):
            continue
        status = c.get('status')
        times_used = int(c.get('times_used') or 0)
        if status == 'NEW':
            new_paths.append(p)
        elif status == 'PROCESSED' and times_used == 0:
            revisit_candidates.append(p)

    out = {'new_processed': 0, 'revisited': 0, 'failed': 0}
    if max_insights <= 0:
        print(json.dumps(out))
        return 0

    processed_this_run = 0

    if new_paths and processed_this_run < max_insights:
        target = new_paths[0]
        card = read_json(target, {})
        ok, _ = process_card(target, card, max_refinements=max_refinements, mode='NEW')
        if ok:
            out['new_processed'] += 1
            processed_this_run += 1
        else:
            out['failed'] += 1

    if processed_this_run < max_insights:
        state = read_json(REVISIT_STATE_PATH, {'last_revisit_date': ''})
        last_revisit_date = str(state.get('last_revisit_date') or '')
        today = get_today()
        can_revisit_today = last_revisit_date != today

        if can_revisit_today and revisit_candidates:
            target = revisit_candidates[0]
            card = read_json(target, {})
            ok, _ = process_card(target, card, max_refinements=max_refinements, mode='REVISIT')
            if ok:
                out['revisited'] += 1
                processed_this_run += 1
                state['last_revisit_date'] = today
                write_json(REVISIT_STATE_PATH, state)
            else:
                out['failed'] += 1

    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
