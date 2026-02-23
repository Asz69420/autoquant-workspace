#!/usr/bin/env python3
import argparse, json
from datetime import datetime, UTC
from pathlib import Path

LEDGER = Path("build_session_ledger.jsonl")
STATE_ACTIVE = "ACTIVE"
VALID_STATES = {"ACTIVE", "SESSION_READY_FOR_APPROVAL", "SESSION_APPLIED", "SUPERSEDED", "BLOCKED", "CLOSED"}

def now():
    return datetime.now(UTC).isoformat().replace('+00:00','Z')

def rid():
    t = datetime.now(UTC).strftime('%Y%m%d-%H%M%S')
    return f"build-{t}"

def read_rows():
    if not LEDGER.exists():
        return []
    return [json.loads(x) for x in LEDGER.read_text(encoding='utf-8').splitlines() if x.strip()]

def write_row(row):
    with LEDGER.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False)+"\n")

def latest_sessions(rows):
    m={}
    for r in rows:
        m[r['build_session_id']] = r
    return m

def cmd_start(args):
    rows = read_rows()
    latest = latest_sessions(rows)
    active = [r for r in latest.values() if r.get('state')==STATE_ACTIVE]
    if active and not args.force_new:
        print(json.dumps(active[-1]))
        return
    sid = rid()
    row = {
        'build_session_id': sid,
        'created_at': now(),
        'last_update_at': now(),
        'description': args.description or '',
        'state': STATE_ACTIVE,
        'tasks': [],
        'artifacts': [],
        'verifier_run_ids': [],
        'apply_evidence': None,
        'blocker_trace': None,
    }
    write_row(row)
    print(json.dumps(row))

def cmd_add_task(args):
    rows = read_rows(); latest = latest_sessions(rows)
    if args.build_session_id not in latest:
        raise SystemExit('build_session_id not found')
    cur = latest[args.build_session_id]
    tasks = list(cur.get('tasks', [])); tasks.append(args.task_id)
    artifacts = list(cur.get('artifacts', []))
    if args.artifact: artifacts.append(args.artifact)
    vids = list(cur.get('verifier_run_ids', []))
    if args.verifier_run_id: vids.append(args.verifier_run_id)
    row = dict(cur)
    row.update({'tasks': tasks, 'artifacts': artifacts, 'verifier_run_ids': vids, 'last_update_at': now()})
    write_row(row)
    print(json.dumps(row))

def cmd_set_state(args):
    rows = read_rows(); latest = latest_sessions(rows)
    if args.build_session_id not in latest:
        raise SystemExit('build_session_id not found')
    if args.state not in VALID_STATES:
        raise SystemExit('invalid state')
    cur = latest[args.build_session_id]
    row = dict(cur)
    row['state']=args.state
    row['last_update_at']=now()
    if args.apply_evidence is not None: row['apply_evidence']=args.apply_evidence
    if args.blocker_trace is not None: row['blocker_trace']=args.blocker_trace
    write_row(row)
    print(json.dumps(row))

def cmd_show(args):
    rows = read_rows(); latest = latest_sessions(rows)
    if args.build_session_id:
        if args.build_session_id not in latest: raise SystemExit('build_session_id not found')
        print(json.dumps(latest[args.build_session_id], indent=2))
        return
    arr = sorted(latest.values(), key=lambda x:x.get('last_update_at',''), reverse=True)
    print(json.dumps(arr[:args.limit], indent=2))

p=argparse.ArgumentParser()
sub=p.add_subparsers(dest='cmd', required=True)

s=sub.add_parser('start'); s.add_argument('--description'); s.add_argument('--force-new', action='store_true'); s.set_defaults(func=cmd_start)
a=sub.add_parser('add-task'); a.add_argument('--build-session-id', required=True); a.add_argument('--task-id', required=True); a.add_argument('--artifact'); a.add_argument('--verifier-run-id'); a.set_defaults(func=cmd_add_task)
ss=sub.add_parser('set-state'); ss.add_argument('--build-session-id', required=True); ss.add_argument('--state', required=True); ss.add_argument('--apply-evidence'); ss.add_argument('--blocker-trace'); ss.set_defaults(func=cmd_set_state)
sh=sub.add_parser('show'); sh.add_argument('--build-session-id'); sh.add_argument('--limit', type=int, default=5); sh.set_defaults(func=cmd_show)

ns=p.parse_args(); ns.func(ns)
