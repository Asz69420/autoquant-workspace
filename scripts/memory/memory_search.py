#!/usr/bin/env python3
"""
Fast unified memory search across MEMORY.md, HANDOFFS, and DAILY logs.
Returns ranked results with file paths, line ranges, and context snippets.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Repo root
REPO_ROOT = Path(__file__).parent.parent.parent
MEMORY_FILE = REPO_ROOT / "MEMORY.md"
HANDOFFS_DIR = REPO_ROOT / "docs" / "HANDOFFS"
DAILY_DIR = REPO_ROOT / "docs" / "DAILY"

def read_file_safe(file_path):
    """Read file with UTF-8 tolerance; skip on failure."""
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return f.read()
    except Exception as e:
        print(f"WARN: Could not read {file_path}: {e}", file=sys.stderr)
        return None

def get_file_mtime(file_path):
    """Get file modification time for recency boost."""
    try:
        return os.path.getmtime(file_path)
    except:
        return 0

def score_result(query, line, line_num, file_path, mtime, file_priority):
    """
    Rank result based on:
    - Exact match (high)
    - Word matches (medium)
    - Proximity (slight boost)
    - Recency (slight boost)
    - File priority: MEMORY.md > HANDOFFS > DAILY
    """
    query_lower = query.lower()
    line_lower = line.lower()
    
    score = 0
    
    # Exact match
    if query_lower in line_lower:
        score += 100
    
    # Word-by-word matches
    query_words = query_lower.split()
    word_matches = sum(1 for word in query_words if word in line_lower)
    score += word_matches * 20
    
    # Recency boost (files modified today: +10)
    now = datetime.now().timestamp()
    if (now - mtime) < 86400:  # Within 24h
        score += 10
    
    # File priority
    score += file_priority * 50
    
    return score

def search_file(query, file_path, file_priority):
    """Search single file, return ranked results."""
    content = read_file_safe(file_path)
    if not content:
        return []
    
    lines = content.split('\n')
    mtime = get_file_mtime(file_path)
    results = []
    
    for i, line in enumerate(lines, start=1):
        if query.lower() in line.lower():
            score = score_result(query, line, i, file_path, mtime, file_priority)
            results.append({
                'file': str(file_path.relative_to(REPO_ROOT)),
                'line': i,
                'text': line.strip()[:120],  # Truncate to 120 chars for display
                'score': score
            })
    
    return results

def get_context(file_path, line_num, context_lines=2):
    """Get snippet of lines around match."""
    content = read_file_safe(file_path)
    if not content:
        return []
    
    lines = content.split('\n')
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    
    return lines[start:end]

def main():
    if len(sys.argv) < 2:
        print("Usage: python memory_search.py '<query>' [--limit N]", file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    limit = 10
    
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    
    results = []
    
    # Search MEMORY.md (priority 3, highest)
    if MEMORY_FILE.exists():
        results.extend(search_file(query, MEMORY_FILE, file_priority=3))
    
    # Search HANDOFFS (priority 2)
    if HANDOFFS_DIR.exists():
        for handoff_file in sorted(HANDOFFS_DIR.glob("handoff-*.md"), reverse=True):
            results.extend(search_file(query, handoff_file, file_priority=2))
    
    # Search DAILY (priority 1)
    if DAILY_DIR.exists():
        for daily_file in sorted(DAILY_DIR.glob("*.md"), reverse=True):
            results.extend(search_file(query, daily_file, file_priority=1))
    
    # Sort by score (descending)
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    results = results[:limit]
    
    if not results:
        print(f"No results for: {query}", file=sys.stdout)
        sys.exit(0)
    
    # Print results
    print(f"\nResults for: '{query}' ({len(results)} found)\n", file=sys.stdout)
    
    for i, res in enumerate(results, start=1):
        file_path = REPO_ROOT / res['file']
        line_num = res['line']
        
        # Pointer line
        print(f"{i}. {res['file']}:L{line_num} (score: {res['score']})", file=sys.stdout)
        print(f"   {res['text']}", file=sys.stdout)
        
        # Context snippet (next 1-2 lines)
        context = get_context(file_path, line_num, context_lines=1)
        if context:
            for ctx_line in context[1:]:  # Skip the match line itself
                if ctx_line.strip():
                    print(f"   > {ctx_line.strip()[:100]}", file=sys.stdout)
        
        print()
    
    sys.exit(0)

if __name__ == '__main__':
    main()
