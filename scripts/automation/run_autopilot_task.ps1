Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'
# Quandalf-only strategy generation mode:
# keep Frodex operational tasks, disable bundle-driven spec creation,
# and keep TV/catalog strategy routing out of the 15m Frodex autopilot loop.
& '.\scripts\pipeline\autopilot_worker.ps1' -RepoHygieneMode FAIL -MaxBundlesPerRun 0
