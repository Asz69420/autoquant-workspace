from pathlib import Path
import re
p=Path(r'C:\Users\Clamps\.openclaw\workspace\scripts\automation\route_request.ps1')
text=p.read_text(encoding='utf-8')
pat=re.compile(r"  if \(\$intentAction -eq 'show_leaderboard'.*?\n  \}\n\n  if \(\$intentAction -eq 'show_report'", re.S)
rep="""  if ($intentAction -eq 'show_leaderboard' -or $m -like 'leaderboard*') {
    $assetArg = ''
    if ($m -match '^leaderboard\\s+(.+)$') { $assetArg = [string]$matches[1] }
    if ([string]::IsNullOrWhiteSpace($assetArg)) {
      python scripts/pipeline/render_leaderboard.py
    } else {
      python scripts/pipeline/render_leaderboard.py --assets $assetArg
    }
    exit 0
  }

  if ($intentAction -eq 'show_report'"""
new, n = pat.subn(lambda m: rep, text, count=1)
if n!=1:
    raise SystemExit('pattern not found')
p.write_text(new, encoding='utf-8')
print('ok')
