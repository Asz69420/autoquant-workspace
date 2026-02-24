#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def main() -> int:
    transcript = (
        "Today we used Supertrend indicator by Kivanc and RSI divergence on BTC 1h and ETH 4h.\n"
        "Rule: wait for trend flip and volume confirmation."
    )

    rc_out = run([
        PY,
        "scripts/pipeline/emit_research_card.py",
        "--source-ref", "fixture://sample-transcript",
        "--source-type", "transcript",
        "--raw-text", transcript,
        "--title", "Fixture Transcript",
        "--tags", "[\"smoke\",\"pipeline-stage1\"]",
    ])
    rc_paths = json.loads(rc_out)
    rc_path = rc_paths["research_card_path"]

    ir_out = run([
        PY,
        "scripts/pipeline/emit_indicator_record.py",
        "--tv-ref", "tv://supertrend-kivanc",
        "--url", "https://tradingview.com/script/example",
        "--name", "Supertrend",
        "--author", "KivancOzbilgic",
        "--source-code", "//@version=5\nindicator('x')\nplot(close)",
        "--key-inputs", "[\"atr_period\",\"multiplier\"]",
        "--signals", "[\"trend flip\",\"buy/sell\"]",
        "--notes", "[\"fixture\"]",
    ])
    ir_paths = json.loads(ir_out)
    ir_path = ir_paths["indicator_record_path"]

    lm_out = run([
        PY,
        "scripts/pipeline/link_research_indicators.py",
        "--research-card-path", rc_path,
        "--indicator-record-paths", json.dumps([ir_path]),
    ])
    linkmap_path = json.loads(lm_out)["linkmap_path"]

    # index cap prune test (>200) without deleting artifacts
    r_index = ROOT / "artifacts/research/INDEX.json"
    i_index = ROOT / "artifacts/indicators/INDEX.json"
    r_index.parent.mkdir(parents=True, exist_ok=True)
    i_index.parent.mkdir(parents=True, exist_ok=True)
    oversized = [f"fake/{i}.json" for i in range(250)]
    r_index.write_text(json.dumps(oversized), encoding="utf-8")
    i_index.write_text(json.dumps(oversized), encoding="utf-8")

    run([
        PY,
        "scripts/pipeline/emit_research_card.py",
        "--source-ref", "fixture://cap-test",
        "--raw-text", "indicator MACD mentioned",
    ])
    run([
        PY,
        "scripts/pipeline/emit_indicator_record.py",
        "--tv-ref", "tv://cap-test",
        "--name", "MACD",
    ])

    run([
        PY,
        "scripts/pipeline/verify_pipeline_stage1.py",
        "--research-card", rc_path,
        "--indicator-record", ir_path,
        "--linkmap", linkmap_path,
    ])

    r_len = len(json.loads(r_index.read_text(encoding="utf-8")))
    i_len = len(json.loads(i_index.read_text(encoding="utf-8")))
    assert r_len <= 200 and i_len <= 200

    print(json.dumps({
        "research_card_path": rc_path,
        "indicator_record_path": ir_path,
        "linkmap_path": linkmap_path,
        "research_index_len": r_len,
        "indicator_index_len": i_len,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
