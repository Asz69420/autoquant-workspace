#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / "artifacts" / "library" / "RUN_INDEX.json"
OUT_PATH = ROOT / "artifacts" / "reports" / "leaderboard.txt"

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"  # exactly 32
HEADER = "TF   P&L      PF    WR    TC     DD"

TF_W = 4
PNL_W = 8
PF_W = 5
WR_W = 4
TC_W = 6
DD_W = 9

ASSET_EMOJI = {"BTC": "🟠", "ETH": "🔵", "SOL": "🟣"}
ASSET_PRIORITY = ["BTC", "ETH", "SOL"]
TF_ORDER = ["15m", "1h", "4h"]

PLACEHOLDER_RE = re.compile(r"999\.9|\+X\.X|need|no data|<pre>|</pre>", re.IGNORECASE)


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(v):
    try:
        return float(v)
    except Exception:
        return None


def as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def extract_wr_dd(backtest_path: str) -> tuple[float | None, float | None]:
    p = Path(backtest_path)
    if not backtest_path or not p.exists():
        return None, None
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        results = j.get("results", {})
        wr = as_float(results.get("win_rate"))
        dd = as_float(results.get("max_drawdown"))
        if wr is None or dd is None:
            return None, None
        wr_pct = wr * 100.0
        dd_pct = dd * 100.0 if abs(dd) <= 1.0 else dd
        return wr_pct, dd_pct
    except Exception:
        return None, None


def valid_metrics(pnl, pf, wr, tc, dd) -> bool:
    if any(v is None for v in (pnl, pf, wr, tc, dd)):
        return False
    if not all(isinstance(v, (int, float)) for v in (pnl, pf, wr, dd)):
        return False
    if not isinstance(tc, int):
        return False
    if tc <= 0:
        return False
    if round(dd, 1) == 999.9:
        return False
    return True


def fmt_row(tf: str, pnl: float, pf: float, wr: float, tc: int, dd: float) -> str:
    tf_s = str(tf)[:TF_W].ljust(TF_W)
    pnl_s = f"{pnl:+.1f}".rjust(PNL_W)
    pf_s = f"{pf:.2f}".rjust(PF_W)
    wr_s = f"{int(round(wr))}%".rjust(WR_W)
    tc_s = str(tc).rjust(TC_W)
    dd_s = f"{dd:.1f}".rjust(DD_W)
    return f"{tf_s}{pnl_s} {pf_s} {wr_s} {tc_s} {dd_s}"


def asset_sort_key(asset: str):
    if asset in ASSET_PRIORITY:
        return (0, ASSET_PRIORITY.index(asset), asset)
    return (1, 999, asset)


def tf_sort_key(tf: str):
    if tf in TF_ORDER:
        return (0, TF_ORDER.index(tf), tf)
    return (1, 999, tf)


def emit_fail(reason_code: str, summary: str) -> None:
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/log_event.py",
                "--run-id",
                f"leaderboard-{reason_code.lower()}",
                "--agent",
                "oQ",
                "--model-id",
                "openai-codex/gpt-5.3-codex",
                "--action",
                "leaderboard_txt",
                "--status-word",
                "FAIL",
                "--status-emoji",
                "❌",
                "--reason-code",
                reason_code,
                "--summary",
                summary,
            ],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def send_file_to_telegram(path: Path) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CMD_CHAT_ID") or os.getenv("TELEGRAM_LOG_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CMD_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with path.open("rb") as f:
        files = {"document": (path.name, f, "text/plain")}
        data = {"chat_id": chat_id, "caption": "leaderboard.txt"}
        r = requests.post(url, data=data, files=files, timeout=20)
        r.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    runs = load_json(RUN_INDEX)

    grouped: dict[str, dict[str, list[tuple]]] = defaultdict(lambda: defaultdict(list))

    for r in runs:
        ds_list = r.get("datasets_tested") or []
        if not ds_list:
            continue
        ds = ds_list[0] if isinstance(ds_list, list) else ds_list
        asset = str(ds.get("symbol", "")).upper().strip()
        tf = str(ds.get("timeframe", "")).lower().strip()
        if not asset or not tf:
            continue

        net = as_float(r.get("net_profit"))
        pf = as_float(r.get("profit_factor"))
        tc = as_int(r.get("trades"))
        bt = str((r.get("pointers") or {}).get("backtest_result") or "")
        wr, dd = extract_wr_dd(bt)

        if net is None:
            continue
        pnl = (net / 10000.0) * 100.0

        if not valid_metrics(pnl, pf, wr, tc, dd):
            continue

        grouped[asset][tf].append((pnl, pf, wr, tc, dd))

    lines: list[str] = []
    assets_included = 0
    rows_included = 0

    for asset in sorted(grouped.keys(), key=asset_sort_key):
        tf_rows = grouped[asset]
        rendered_rows: list[str] = []

        for tf in sorted(tf_rows.keys(), key=tf_sort_key):
            rows = sorted(tf_rows[tf], key=lambda x: (x[0], x[1]), reverse=True)
            unique = []
            seen = set()
            for row in rows:
                key = (round(row[0], 1), round(row[1], 2), int(round(row[2])), row[3], round(row[4], 1))
                if key in seen:
                    continue
                seen.add(key)
                unique.append(row)
                if len(unique) >= 3:
                    break

            for pnl, pf, wr, tc, dd in unique:
                rendered_rows.append(fmt_row(tf, pnl, pf, wr, tc, dd))

        if not rendered_rows:
            continue

        assets_included += 1
        lines.append(f"{ASSET_EMOJI.get(asset, '⚪')} {asset}")
        lines.append(HEADER)
        lines.append(DIVIDER)
        lines.extend(rendered_rows)
        lines.append("")
        rows_included += len(rendered_rows)

    text = "\n".join(lines).rstrip() + "\n"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")

    placeholders_found = bool(PLACEHOLDER_RE.search(text))
    if placeholders_found:
        emit_fail("LEADERBOARD_PLACEHOLDER_DETECTED", "Placeholder token found in leaderboard.txt")
        print(json.dumps({
            "ok": False,
            "reason_code": "LEADERBOARD_PLACEHOLDER_DETECTED",
            "assets_included": assets_included,
            "rows_included": rows_included,
            "placeholders_found": True,
            "path": str(OUT_PATH).replace("\\", "/"),
        }))
        return 2

    if args.send_telegram:
        send_file_to_telegram(OUT_PATH)

    print(json.dumps({
        "ok": True,
        "assets_included": assets_included,
        "rows_included": rows_included,
        "placeholders_found": False,
        "path": str(OUT_PATH).replace("\\", "/"),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
