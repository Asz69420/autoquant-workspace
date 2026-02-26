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

RANK_CAP = 2
TF_CAP = 4
PNL_CAP = 9
PF_CAP = 6
WR_CAP = 4
TC_CAP = 6
DD_CAP = 11

ASSET_EMOJI = {"BTC": "🟠", "ETH": "🔵", "SOL": "🟣"}
ASSET_PRIORITY = ["BTC", "ETH", "SOL"]
TF_ORDER = ["15m", "1h", "4h"]

PLACEHOLDER_RE = re.compile(r"999\.9|\+X\.X|need|no data|<pre>|</pre>", re.IGNORECASE)
SEP = "  "


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        j = json.loads(p.read_text(encoding="utf-8-sig"))
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
    # Drawdown must be a realistic percentage for display.
    if dd < 0 or dd > 100:
        return False
    return True


def truncate_to_width(value: str, width: int) -> str:
    return value if len(value) <= width else value[:width]


def compute_widths(rows: list[tuple[str, str, str, str, str, str, str]]) -> tuple[int, int, int, int, int, int, int]:
    rank_w = min(max([len("#")] + [len(r[0]) for r in rows]), RANK_CAP)
    tf_w = min(max([len("TF")] + [len(r[1]) for r in rows]), TF_CAP)
    pnl_w = min(max([len("P&L")] + [len(r[2]) for r in rows]), PNL_CAP)
    pf_w = min(max([len("PF")] + [len(r[3]) for r in rows]), PF_CAP)
    wr_w = min(max([len("WR")] + [len(r[4]) for r in rows]), WR_CAP)
    tc_w = min(max([len("TC")] + [len(r[5]) for r in rows]), TC_CAP)
    dd_w = min(max([len("DD")] + [len(r[6]) for r in rows]), DD_CAP)
    return rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w


def format_header(rank_w: int, tf_w: int, pnl_w: int, pf_w: int, wr_w: int, tc_w: int, dd_w: int) -> str:
    return (
        f"{'#'.ljust(rank_w)}{SEP}"
        f"{'TF'.ljust(tf_w)}{SEP}"
        f"{'P&L'.rjust(pnl_w)}{SEP}"
        f"{'PF'.rjust(pf_w)}{SEP}"
        f"{'WR'.rjust(wr_w)}{SEP}"
        f"{'TC'.rjust(tc_w)}{SEP}"
        f"{'DD'.rjust(dd_w)}"
    )


def format_row(row: tuple[str, str, str, str, str, str, str], rank_w: int, tf_w: int, pnl_w: int, pf_w: int, wr_w: int, tc_w: int, dd_w: int) -> str:
    rank, tf, pnl, pf, wr, tc, dd = row
    return (
        f"{truncate_to_width(rank, rank_w).ljust(rank_w)}{SEP}"
        f"{truncate_to_width(tf, tf_w).ljust(tf_w)}{SEP}"
        f"{truncate_to_width(pnl, pnl_w).rjust(pnl_w)}{SEP}"
        f"{truncate_to_width(pf, pf_w).rjust(pf_w)}{SEP}"
        f"{truncate_to_width(wr, wr_w).rjust(wr_w)}{SEP}"
        f"{truncate_to_width(tc, tc_w).rjust(tc_w)}{SEP}"
        f"{truncate_to_width(dd, dd_w).rjust(dd_w)}"
    )


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
    tested_assets: set[str] = set()

    for r in runs:
        ds_list = r.get("datasets_tested") or []
        if not ds_list:
            continue
        ds = ds_list[0] if isinstance(ds_list, list) else ds_list
        asset = str(ds.get("symbol", "")).upper().strip()
        tf = str(ds.get("timeframe", "")).lower().strip()
        if not asset or not tf:
            continue
        tested_assets.add(asset)

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

    selected_by_asset: dict[str, list[tuple[str, str, str, str, str, str, str]]] = defaultdict(list)

    for asset in sorted(grouped.keys(), key=asset_sort_key):
        tf_rows = grouped[asset]
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
                selected_by_asset[asset].append((
                    "",
                    tf,
                    f"{pnl:+.1f}",
                    f"{pf:.2f}",
                    f"{int(round(wr))}%",
                    str(tc),
                    f"{dd:.1f}%",
                ))

    ranked_rows_by_asset: dict[str, list[tuple[str, str, str, str, str, str, str]]] = defaultdict(list)
    for asset, rows in selected_by_asset.items():
        for i, row in enumerate(rows, 1):
            ranked_rows_by_asset[asset].append((str(i), row[1], row[2], row[3], row[4], row[5], row[6]))

    all_rows = [row for rows in ranked_rows_by_asset.values() for row in rows]

    lines: list[str] = []
    assets_included = 0
    rows_included = 0

    if all_rows:
        rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w = compute_widths(all_rows)
        header = format_header(rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w)
        divider = "━" * len(header)

        for asset in sorted(ranked_rows_by_asset.keys(), key=asset_sort_key):
            asset_rows = ranked_rows_by_asset.get(asset, [])
            if not asset_rows:
                continue
            assets_included += 1
            lines.append(f"{ASSET_EMOJI.get(asset, '⚪')} {asset}")
            lines.append(header)
            lines.append(divider)
            for row in asset_rows:
                lines.append(format_row(row, rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w))
            lines.append("")
            rows_included += len(asset_rows)
    else:
        rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w = compute_widths([("#", "TF", "P&L", "PF", "WR", "TC", "DD")])
        header = format_header(rank_w, tf_w, pnl_w, pf_w, wr_w, tc_w, dd_w)
        divider = "━" * len(header)
        for asset in sorted(tested_assets, key=asset_sort_key):
            lines.append(f"{ASSET_EMOJI.get(asset, '⚪')} {asset}")
            lines.append(header)
            lines.append(divider)
            lines.append("")

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
