from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'BASELINE_MANIFEST.json').read_text(encoding='utf-8'))


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

rows = []
total_chars = 0
for rel in manifest.get('default_load', []):
    p = ROOT / rel
    if p.exists():
        txt = p.read_text(encoding='utf-8')
        chars = len(txt)
        toks = estimate_tokens(txt)
        total_chars += chars
        rows.append((rel, chars, toks))

payload = {
    'ts': datetime.now().isoformat(),
    'default_load': [{'path': r, 'chars': c, 'tokens_est': t} for r, c, t in rows],
    'baseline_tokens_est': sum(t for _, _, t in rows),
    'baseline_chars': total_chars,
    'target_tokens_max': manifest.get('target_tokens_max', 8000)
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
