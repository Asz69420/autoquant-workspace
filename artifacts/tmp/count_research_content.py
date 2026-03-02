import os
import glob
import json

root = r"C:\Users\Clamps\.openclaw\workspace"
cards = []
for rp in glob.glob(root + "\\artifacts\\research\\*\\*.research_card.json"):
    try:
        with open(rp, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        continue
    raw_rel = d.get("raw_pointer")
    if not raw_rel:
        continue
    raw_path = os.path.join(root, raw_rel.replace('/', '\\'))
    if not os.path.exists(raw_path):
        continue
    try:
        with open(raw_path, encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except Exception:
        continue
    n = len(txt)
    if n > 500:
        cards.append({
            "card": rp,
            "raw": raw_path,
            "chars": n,
            "title": d.get("title") or "",
            "source_type": d.get("source_type") or "",
        })

print(f"COUNT {len(cards)}")
cards.sort(key=lambda x: x["chars"], reverse=True)
for i, c in enumerate(cards[:3], start=1):
    print(f"TOP{i}|{c['chars']}|{c['title']}|{c['source_type']}|{c['raw']}")
