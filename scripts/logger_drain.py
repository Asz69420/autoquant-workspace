#!/usr/bin/env python3
"""Deprecated: logger_drain.py is now tg_reporter.py. Forwarding for backward compatibility."""
import subprocess
import sys

print("⚠️  logger_drain.py is deprecated; use scripts/tg_reporter.py", file=sys.stderr)
result = subprocess.run([sys.executable, "scripts/tg_reporter.py"] + sys.argv[1:])
sys.exit(result.returncode)
