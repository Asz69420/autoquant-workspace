Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'
# Quandalf-only strategy generation mode:
# keep Frodex operational tasks, but disable pipeline bundle-driven spec creation.
& '.\scripts\pipeline\autopilot_worker.ps1' -RunTVCatalogWorker -RepoHygieneMode FAIL -MaxBundlesPerRun 0
