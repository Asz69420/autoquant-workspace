#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / 'data' / 'logs' / 'llm_calls.ndjson'
DEFAULT_OPENCLAW_CLI = r'C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd'
OPENCLAW_CLI = shutil.which('openclaw') or os.environ.get('OPENCLAW_CLI_PATH') or (DEFAULT_OPENCLAW_CLI if Path(DEFAULT_OPENCLAW_CLI).exists() else 'openclaw')


def _log_call(agent: str, prompt_len: int, response_len: int, latency_ms: int, success: bool, error: str | None):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        'timestamp': datetime.now(UTC).isoformat(),
        'agent': agent,
        'prompt_length_chars': int(prompt_len),
        'response_length_chars': int(response_len),
        'latency_ms': int(latency_ms),
        'success': bool(success),
        'error': error,
    }
    with open(LOG_PATH, 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def llm_complete(prompt: str, system: str = '', agent: str = 'reader', timeout: int = 120) -> str | None:
    """Call LLM through OpenClaw runtime. Returns text or None."""
    full_prompt = prompt
    if system:
        full_prompt = f"[SYSTEM]\n{system}\n[/SYSTEM]\n\n{prompt}"

    last_err: str | None = None

    for attempt in range(2):
        t0 = time.time()
        tmp_path = ''
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(full_prompt)
                tmp_path = f.name

            # 1) stdin path (no --message) to avoid Windows argv length limits
            cmd_stdin = [OPENCLAW_CLI, 'agent', '--agent', agent, '--json']
            try:
                p = subprocess.run(cmd_stdin, input=full_prompt, text=True, capture_output=True, check=True, timeout=timeout)
            except Exception:
                # 2) @file reference fallback via --message
                cmd_atfile = [OPENCLAW_CLI, 'agent', '--agent', agent, '--message', f'@{tmp_path}', '--json']
                p = subprocess.run(cmd_atfile, text=True, capture_output=True, check=True, timeout=timeout)

            obj = json.loads(p.stdout)
            text = obj['result']['payloads'][0]['text']
            latency_ms = int((time.time() - t0) * 1000)
            _log_call(agent, len(full_prompt), len(str(text or '')), latency_ms, True, None)
            return text
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            last_err = str(e)[:500]
            _log_call(agent, len(full_prompt), 0, latency_ms, False, last_err)
            if attempt == 0:
                time.sleep(5)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    return None


def parse_llm_json(raw: str) -> dict | None:
    """Strip markdown fences if present, parse JSON, return dict or None."""
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```json?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None
