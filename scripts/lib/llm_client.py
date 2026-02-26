#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import urllib.error
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / 'data' / 'logs' / 'llm_calls.ndjson'
DEFAULT_OPENCLAW_CLI = r'C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd'
OPENCLAW_CLI = shutil.which('openclaw') or os.environ.get('OPENCLAW_CLI_PATH') or (DEFAULT_OPENCLAW_CLI if Path(DEFAULT_OPENCLAW_CLI).exists() else 'openclaw')
GATEWAY_URL = 'http://127.0.0.1:18789'


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


def _call_gateway_http(prompt: str, system: str, agent: str, timeout: int) -> str | None:
    """Try calling Gateway via HTTP API instead of subprocess."""
    try:
        full_prompt = prompt
        if system:
            full_prompt = f"[SYSTEM]\n{system}\n[/SYSTEM]\n\n{prompt}"

        req_body = json.dumps({
            'agent': agent,
            'message': full_prompt,
            'json': True
        }).encode('utf-8')

        req = urllib.request.Request(
            f'{GATEWAY_URL}/api/agent',
            data=req_body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('result') and result['result'].get('payloads'):
                return result['result']['payloads'][0].get('text')
    except Exception:
        pass
    return None


def llm_complete(prompt: str, system: str = '', agent: str = 'main', timeout: int = 120) -> str | None:
    """Call LLM through OpenClaw runtime. Returns text or None."""
    full_prompt = prompt
    if system:
        full_prompt = f"[SYSTEM]\n{system}\n[/SYSTEM]\n\n{prompt}"

    last_err: str | None = None

    for attempt in range(2):
        t0 = time.time()
        try:
            # Try HTTP API first (preferred)
            text = _call_gateway_http(prompt, system, agent, timeout)
            if text:
                latency_ms = int((time.time() - t0) * 1000)
                _log_call(agent, len(full_prompt), len(str(text or '')), latency_ms, True, None)
                return text

            # Fallback to subprocess if HTTP fails
            if len(full_prompt) < 30000:
                cmd = [OPENCLAW_CLI, 'agent', '--agent', agent, '--message', full_prompt, '--json']
                p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
            else:
                cmd = [OPENCLAW_CLI, 'agent', '--agent', agent, '--json']
                p = subprocess.run(cmd, input=full_prompt, text=True, capture_output=True, timeout=timeout)

            if p.returncode != 0:
                err = (p.stderr or '').strip()
                out = (p.stdout or '').strip()
                error_detail = f"returncode={p.returncode}; stderr={err}; stdout={out}"
                raise RuntimeError(error_detail[:2000])

            obj = json.loads(p.stdout)
            text = obj['result']['payloads'][0]['text']
            latency_ms = int((time.time() - t0) * 1000)
            _log_call(agent, len(full_prompt), len(str(text or '')), latency_ms, True, None)
            return text
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            last_err = str(e)[:2000]
            _log_call(agent, len(full_prompt), 0, latency_ms, False, last_err)
            if attempt == 0:
                time.sleep(5)

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
