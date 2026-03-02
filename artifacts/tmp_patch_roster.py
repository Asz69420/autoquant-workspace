from pathlib import Path

p = Path(r"C:\Users\Clamps\.openclaw\workspace\scripts\automation\route_request.ps1")
text = p.read_text(encoding="utf-8")
needle = "  if ($intentAction -eq 'show_roster' -or $m -eq 'roster' -or $m -eq 'show roster' -or $m -eq 'agent roster' -or $m -eq 'roster details') {"
start = text.find(needle)
if start < 0:
    raise SystemExit("start not found")
end = text.find("    exit 0\n  }", start)
if end < 0:
    raise SystemExit("end not found")
end += len("    exit 0\n  }")

new_block = '''  if ($intentAction -eq 'show_roster' -or $m -eq 'roster' -or $m -eq 'show roster' -or $m -eq 'agent roster' -or $m -eq 'roster details') {
    Write-Output "✅ Active Agents (LLM)"
    Write-Output "🤖 oQ - Main orchestrator and delegation control."
    Write-Output "🔰 Verifier - Independent QC gate for policy and compatibility checks."
    Write-Output "🗃️ Keeper - Artifact indexing, dedup, and memory curation authority."
    Write-Output "🧾 Logger - Outbox drain + NDJSON action/error logging authority."
    Write-Output "🛡️ Firewall - Spec/security guard and write-allowlist enforcement."
    Write-Output "⏱️ Scheduler - Timing, cron orchestration, recurring task control."
    Write-Output "🔗 Reader - Source ingestion into ResearchCards."
    Write-Output "🧲 Grabber - TradingView indicator harvesting into IndicatorRecords."
    Write-Output "🕵️ Specter - Browser-AI bridge for schema-validated interactions (partial)."
    Write-Output "🧠 Analyser - Falsifiable thesis generation from research inputs."
    Write-Output "📊 Strategist - Thesis-to-StrategySpec translation."
    Write-Output "📈 Backtester - Batch backtest execution and report output."

    Write-Output "✅ Active Systems (Scripts)"
    Write-Output "🧵 Build Queue Worker - Single-flight queued BUILD_PATH execution."
    Write-Output "📣 TG Reporter - High-signal Telegram reporting and filters."
    Write-Output "🗄️ HL Data Ingest - Hyperliquid OHLCV ingestion + validation."
    Write-Output "🧪 HL Backtest Engine - Core hl_backtest_engine.py runner."
    Write-Output "📦 Batch Backtest Runner - Batch runs + experiment-plan emission."
    Write-Output "🔁 Refinement Loop Runner - run_refinement_loop.py bounded refinement loop."
    Write-Output "📚 Librarian v1 - run_librarian.py + dedup + archive management."
    Write-Output "🧾 Stage Verifiers - Stage1/2/3 verifiers + stage4 gates."
    Write-Output "📤 TV Exporter - WIP; blocked on reliable real-download capture."
    Write-Output "🧪 TV Parity Harness - WIP parity validation against TV trade outputs."

    Write-Output "🛠️ Planned"
    Write-Output "🏁 Ranker - Planned ranking across regimes and constraints."
    Write-Output "📚 Librarian (agent form) - Planned persona wrapper over active Librarian v1 system."
    Write-Output "🔁 Refiner (agent form) - Planned persona wrapper over active refinement loop system."
    Write-Output "🧑‍💻 Coder - Planned Pine/Python conversion and adapter maintainer."
    Write-Output "⚡ Executor-HL - Planned live Hyperliquid executor under guardrails."
    Write-Output "🛑 Risk Manager - Planned live risk and circuit-breaker enforcement."
    exit 0
  }'''

text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("updated")
