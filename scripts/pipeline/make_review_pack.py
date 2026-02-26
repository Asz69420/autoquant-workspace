#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:64] or "review-pack"


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return p.stdout.strip()


def _commit_summary(commit: str | None) -> list[str]:
    if not commit:
      return ["- no code changes"]
    out = _run(["git", "show", "--stat", "--oneline", "-1", commit])
    lines = [x for x in out.splitlines() if x.strip()]
    if not lines:
      return ["- no code changes"]
    bullets = [f"- commit: {lines[0]}"]
    for ln in lines[1:6]:
      bullets.append(f"- {ln.strip()}")
    return bullets


def _artifact_evidence(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths[:10]:
      pp = (ROOT / p).resolve() if not Path(p).is_absolute() else Path(p)
      if not pp.exists():
        out.append(f"- {p} (missing)")
        continue
      try:
        if pp.suffix == ".json":
          j = json.loads(pp.read_text(encoding="utf-8-sig"))
          if isinstance(j, dict):
            if "summary" in j and isinstance(j["summary"], dict):
              s = j["summary"]
              out.append(f"- {p}: runs={s.get('total_runs')} failed={s.get('failed_runs')} PF={s.get('profit_factor')} DD={s.get('max_drawdown')}")
              continue
            if "top_count" in j or "promotions_processed" in j:
              out.append(f"- {p}: promotions={j.get('promotions_processed')} refinements={j.get('refinements_run')} new_candidates={j.get('new_candidates_count')} errors={j.get('errors_count')}")
              continue
            if "winner" in j and isinstance(j.get("winner"), dict):
              w = j["winner"]
              out.append(f"- {p}: winner={w.get('variant_name')} PF={w.get('summary',{}).get('profit_factor',w.get('profit_factor'))} DD={w.get('summary',{}).get('max_drawdown',w.get('max_drawdown'))}")
              continue
          out.append(f"- {p}: json artifact")
        else:
          out.append(f"- {p}: file")
      except Exception:
        out.append(f"- {p}: file")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--commit", default="")
    ap.add_argument("--artifacts", default="")
    ap.add_argument("--questions", default="")
    args = ap.parse_args()

    now = datetime.now(UTC)
    day = now.strftime("%Y%m%d")
    out_dir = ROOT / "artifacts" / "review_packs" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = [x.strip() for x in args.artifacts.split(",") if x.strip()]
    questions = [q.strip() for q in re.split(r"[\n|;]", args.questions) if q.strip()][:5]

    lines: list[str] = []
    lines.append(f"# Review Pack: {args.title.strip()[:120]}")
    lines.append(f"Generated: {now.isoformat()}")
    lines.append("")
    lines.append("## Goal")
    lines.append(args.scope.strip()[:240])
    lines.append("")
    lines.append("## Constraints")
    lines.extend([
      "- Deterministic summary only",
      "- No strategy mutation",
      "- No backtest semantics changes",
      "- Bounded packet (no raw logs)",
    ])
    lines.append("")
    lines.append("## What changed")
    lines.extend(_commit_summary(args.commit.strip() or None)[:6])
    lines.append("")
    lines.append("## Evidence")
    ev = _artifact_evidence(artifact_paths)
    lines.extend(ev if ev else ["- no artifacts provided"])
    lines.append("")
    lines.append("## Open questions for Opus")
    if questions:
      lines.extend([f"- {q[:180]}" for q in questions])
    else:
      lines.extend([
        "- Is the current winner selection criterion robust enough?",
        "- Which single constraint should be relaxed first?",
      ])
    lines.append("")
    lines.append("## Safety note")
    lines.append("No secrets included")

    if len(lines) > 250:
      lines = lines[:250]

    slug = _slug(args.title)
    md_path = out_dir / f"{slug}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"review_pack_path": str(md_path), "lines": len(lines)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
