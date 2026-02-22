#!/usr/bin/env python3
"""
Validate and normalize handoff files.
Ensures UTF-8 encoding, validates against schema, fills optional defaults.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def load_handoff(file_path):
    """Load handoff with UTF-8 tolerance (utf-8-sig for BOM)."""
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except UnicodeDecodeError:
        print(f"ERROR: {file_path} is not valid UTF-8. Please re-encode.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: {file_path} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

def normalize_handoff(data):
    """Fill optional fields with sensible defaults."""
    if 'ts_created' not in data:
        data['ts_created'] = datetime.utcnow().isoformat() + 'Z'
    if 'blockers' not in data:
        data['blockers'] = []
    if 'completed' not in data:
        data['completed'] = []
    if 'pointers' not in data:
        data['pointers'] = {}
    if 'notes' not in data:
        data['notes'] = ""
    if 'session_id' not in data:
        data['session_id'] = None
    return data

def validate_required_fields(data):
    """Check required fields only."""
    required = ['ts_created', 'status', 'next_tasks']
    missing = [f for f in required if f not in data]
    if missing:
        print(f"ERROR: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        return False
    if not isinstance(data['next_tasks'], list) or len(data['next_tasks']) == 0:
        print(f"ERROR: next_tasks must be a non-empty array", file=sys.stderr)
        return False
    return True

def write_handoff(file_path, data):
    """Write handoff with UTF-8 + LF newlines."""
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        print(f"ERROR: Failed to write {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_handoff.py <handoff_file> [--fix]", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    fix_mode = '--fix' in sys.argv
    
    if not Path(file_path).exists():
        print(f"ERROR: {file_path} not found", file=sys.stderr)
        sys.exit(1)
    
    # Load
    data = load_handoff(file_path)
    
    # Normalize
    data = normalize_handoff(data)
    
    # Validate required
    if not validate_required_fields(data):
        sys.exit(1)
    
    # Write back (or to .normalized)
    if fix_mode:
        write_handoff(file_path, data)
        print(f"OK: {file_path} normalized and written", file=sys.stdout)
    else:
        normalized_path = file_path.replace('.md', '.normalized.json').replace('.json', '.normalized.json')
        write_handoff(normalized_path, data)
        print(f"OK: Normalized copy written to {normalized_path}", file=sys.stdout)
    
    sys.exit(0)

if __name__ == '__main__':
    main()
