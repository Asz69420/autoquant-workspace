#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / 'data' / 'logs' / 'llm_calls.ndjson'
OPENCLAW_CLI = shutil.which("openclaw") or r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.cmd"
GATEWAY_URL = 'http://127.0.0.1:18789'


def _log_call(agent: str, prompt_len: int, response_len: int, latency_ms: int, success: bool, error: str | None, source: str = 'openclaw'):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        'timestamp': datetime.now(UTC).isoformat(),
        'agent': agent,
        'source': source,
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


def llm_complete_direct(prompt: str, system: str = '', model: str = 'openai/gpt-4.1', timeout: int = 120) -> str | None:
    api_key = os.environ.get('OPENROUTER_API_KEY', '')
    base_url = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    if not api_key:
        return None

    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    body = json.dumps({
        'model': model,
        'messages': messages,
        'temperature': 0.3,
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{base_url}/chat/completions',
        data=body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data['choices'][0]['message']['content']
    except Exception:
        return None


def llm_complete(prompt: str, system: str = '', agent: str = 'main', timeout: int = 120) -> str | None:
    """Call LLM through embedded OpenClaw runtime (--local), bypassing gateway."""
    if system:
        full_prompt = f"{system}\n\n{prompt}"
    else:
        full_prompt = prompt

    for attempt in range(2):
        t0 = time.time()
        try:
            kwargs = dict(text=True, capture_output=True, timeout=timeout)
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            # Flatten for CLI compatibility (newlines break Windows args)
            cli_prompt = full_prompt.replace('\n', ' ').replace('\r', ' ')
            cmd = [OPENCLAW_CLI, 'agent', '--agent', agent, '--local', '--session-id', 'analyser-brain', '-m', cli_prompt, '--json', '--timeout', str(timeout)]
            p = subprocess.run(cmd, **kwargs)

            if p.returncode != 0:
                err = (p.stderr or '').strip()
                out = (p.stdout or '').strip()
                error_detail = f"returncode={p.returncode}; stderr={err}; stdout={out}"
                raise RuntimeError(error_detail[:2000])

            obj = json.loads(p.stdout)
            payloads = obj.get('payloads') or obj.get('result', {}).get('payloads') or []
            text = payloads[0].get('text') if payloads and isinstance(payloads[0], dict) else None
            if not isinstance(text, str):
                raise RuntimeError('missing text payload in openclaw agent response')

            latency_ms = int((time.time() - t0) * 1000)
            _log_call(agent, len(full_prompt), len(str(text or '')), latency_ms, True, None, source='openclaw-local')
            return text
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            last_err = str(e)[:2000]
            _log_call(agent, len(full_prompt), 0, latency_ms, False, last_err, source='openclaw-local')
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
