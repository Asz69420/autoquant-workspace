#!/bin/bash
# AutoQuant Git Auto-Sync
# Called by cron every 30 minutes
# One-way push only — never pulls

cd ~/.openclaw/workspace || exit 1

# Check if there are any changes
if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet HEAD 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) No changes to sync"
  exit 0
fi

# Stage everything
git add -A

# Create commit with timestamp and change summary
CHANGED=$(git diff --cached --stat | tail -1)
git commit -m "🔄 Auto-sync $(date -u +%Y-%m-%dT%H:%M:%SZ) | ${CHANGED}"

# Push (fail silently if network issue — next run will catch it)
git push origin main 2>&1 || echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Push failed — will retry next cycle"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Sync complete"
