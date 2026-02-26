#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

DOCTRINE_PATH = Path('docs/DOCTRINE/analyser-doctrine.md')
MAX_BULLETS = 40
MAX_WORDS = 2000
MAX_DELTAS = 10

SECTION_TITLES = {
    'research': '## 1) Research heuristics',
    'strategy': '## 2) Strategy hypothesis heuristics',
    'automation': '## 3) Automation/system heuristics',
}

BULLET_RE = re.compile(r'^- \[(?P<id>[^|\]]+)\|conf:(?P<conf>[0-9.]+)\] (?P<text>.+)$')


@dataclass
class Bullet:
    section: str
    bullet_id: str
    confidence: float
    text: str


def words_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def normalize(text: str) -> List[str]:
    return re.findall(r'[a-z0-9]+', text.lower())


def jaccard(a: str, b: str) -> float:
    sa, sb = set(normalize(a)), set(normalize(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def parse_doctrine(path: Path) -> List[Bullet]:
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    current = None
    out: List[Bullet] = []
    for line in lines:
        st = line.strip()
        if st == SECTION_TITLES['research']:
            current = 'research'
            continue
        if st == SECTION_TITLES['strategy']:
            current = 'strategy'
            continue
        if st == SECTION_TITLES['automation']:
            current = 'automation'
            continue
        m = BULLET_RE.match(st)
        if m and current:
            out.append(Bullet(current, m.group('id'), float(m.group('conf')), m.group('text')))
    return out


def render_doctrine(path: Path, bullets: List[Bullet]) -> str:
    by_section = {'research': [], 'strategy': [], 'automation': []}
    for b in bullets:
        by_section[b.section].append(b)

    lines = ['# Analyser Doctrine', '']
    for key in ('research', 'strategy', 'automation'):
        lines.append(SECTION_TITLES[key])
        section_items = sorted(by_section[key], key=lambda x: x.bullet_id)
        for b in section_items:
            lines.append(f'- [{b.bullet_id}|conf:{b.confidence:.2f}] {b.text}')
        lines.append('')

    text = '\n'.join(lines).rstrip() + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return text


def load_thesis(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def collect_deltas(thesis: dict, date_prefix: str, start_idx: int) -> List[Bullet]:
    out: List[Bullet] = []

    def add(section: str, text: str, conf: float) -> None:
        idx = start_idx + len(out) + 1
        out.append(Bullet(section, f'{date_prefix}-{idx:02d}', conf, text.strip().rstrip('.')))

    for x in thesis.get('key_ideas', [])[:4]:
        add('research', f'Promote recurring concept signal: {x}', 0.68)

    for x in thesis.get('trading_relevant_concept_hooks', [])[:3]:
        add('strategy', f'Embed concept hook into testable hypothesis design: {x}', 0.72)

    for x in thesis.get('proposed_automation_improvements_for_autoquant', [])[:3]:
        add('automation', f'Prioritize system improvement candidate: {x}', 0.75)

    return out[:MAX_DELTAS]


def dedupe_bullets(bullets: List[Bullet], threshold: float = 0.72) -> Tuple[List[Bullet], int]:
    kept: List[Bullet] = []
    dropped = 0
    for b in sorted(bullets, key=lambda x: (-x.confidence, x.bullet_id)):
        if any(jaccard(b.text, k.text) >= threshold for k in kept):
            dropped += 1
            continue
        kept.append(b)
    return kept, dropped


def prune_caps(bullets: List[Bullet]) -> Tuple[List[Bullet], int]:
    # Prefer higher confidence and newer IDs; pruning drops oldest/lowest confidence deterministically.
    kept = sorted(bullets, key=lambda x: (x.confidence, x.bullet_id), reverse=True)
    pruned = 0

    def total_words(items: List[Bullet]) -> int:
        rendered = ['# Analyser Doctrine', '', SECTION_TITLES['research'], SECTION_TITLES['strategy'], SECTION_TITLES['automation']]
        rendered.extend([b.text for b in items])
        return sum(words_count(x) for x in rendered)

    while len(kept) > MAX_BULLETS or total_words(kept) > MAX_WORDS:
        kept = sorted(kept, key=lambda x: (x.confidence, x.bullet_id))
        kept.pop(0)
        pruned += 1
    kept = sorted(kept, key=lambda x: x.bullet_id)
    return kept, pruned


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--thesis-pack', required=True)
    args = ap.parse_args()

    thesis_path = Path(args.thesis_pack)
    thesis = load_thesis(thesis_path)

    today = datetime.now().strftime('%Y%m%d')
    existing = parse_doctrine(DOCTRINE_PATH)
    todays_ids = [b.bullet_id for b in existing if b.bullet_id.startswith(f'{today}-')]
    max_idx = 0
    for bid in todays_ids:
        try:
            max_idx = max(max_idx, int(bid.split('-')[-1]))
        except Exception:
            pass
    deltas = collect_deltas(thesis, today, max_idx)

    merged = existing + deltas
    deduped, deduped_count = dedupe_bullets(merged)
    pruned, pruned_count = prune_caps(deduped)

    rendered = render_doctrine(DOCTRINE_PATH, pruned)

    update = {
        'id': f'doctrine-update-{today}-{thesis_path.stem}',
        'date': today,
        'thesis_pack': str(thesis_path).replace('\\\\', '/'),
        'added_candidates': len(deltas),
        'deduped': deduped_count,
        'pruned': pruned_count,
        'final_bullets': len(pruned),
        'final_words': words_count(rendered),
        'doctrine_path': str(DOCTRINE_PATH).replace('\\\\', '/'),
    }

    out_dir = Path('artifacts/doctrine_updates') / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{thesis_path.stem}.doctrine_update.json'
    out_path.write_text(json.dumps(update, indent=2), encoding='utf-8')

    print(
        'DOCTRINE_UPDATE_SUMMARY '
        f"status=OK added={update['added_candidates']} deduped={update['deduped']} pruned={update['pruned']} "
        f"final_bullets={update['final_bullets']} final_words={update['final_words']}"
    )
    print(str(out_path).replace('\\\\', '/'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
