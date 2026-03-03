#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

import sys
sys.path.insert(0, str((ROOT / "scripts" / "backtester").resolve()))
from hl_backtest_engine import build_indicator_frame, _classify_regime_from_adx  # type: ignore
from signal_templates import get_signals  # type: ignore


def _jload(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _append_ndjson(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _notify(msg: str) -> None:
    ps = ROOT / "scripts" / "claude-tasks" / "notify-asz.ps1"
    subprocess.run([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps), "-Message", msg
    ], cwd=ROOT, check=False)


def _latest_meta(symbol: str, tf: str) -> Path:
    d = ROOT / "artifacts" / "data" / "hyperliquid" / symbol / tf
    metas = sorted(d.glob("*.meta.json"))
    if not metas:
        raise FileNotFoundError(f"No dataset meta for {symbol} {tf}")
    return metas[-1]


def _ingest(symbol: str, tf: str, lookback_days: int = 730) -> tuple[bool, str]:
    cmd = [
        "python", "scripts/data/ingest_hyperliquid_ohlcv.py",
        "--symbol", symbol,
        "--timeframe", tf,
        "--lookback-days", str(lookback_days),
    ]
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if p.returncode == 0:
        return True, (p.stdout or "").strip()
    return False, ((p.stderr or p.stdout or "").strip())


def _load_bars(meta_path: Path) -> list[dict]:
    csv_path = Path(str(meta_path).replace(".meta.json", ".csv"))
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig", newline="")))
    bars = []
    for r in rows:
        bars.append({
            "time": r["time"],
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r.get("volume", 1.0) or 1.0),
        })
    return bars


def _position_qty(equity: float, risk_pct: float, entry: float, stop: float) -> float:
    risk_amount = equity * max(0.0, risk_pct)
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return max(1.0 / max(entry, 1e-9), 0.0)
    qty = risk_amount / stop_dist
    max_qty = (equity * 0.95) / max(entry, 1e-9)
    qty = min(qty, max_qty)
    if qty * entry < 1.0:
        qty = 1.0 / max(entry, 1e-9)
    return round(qty, 8)


def _trade_key(ch: dict) -> str:
    return f"{ch['id']}::{ch['asset']}::{ch['timeframe']}"


def _ensure_state(path: Path, champions: list[dict]) -> dict:
    st = _jload(path, {})
    if not isinstance(st, dict):
        st = {}
    st.setdefault("schema_version", "1.0")
    st.setdefault("updated_at", "")
    st.setdefault("lanes", {})
    lanes = st["lanes"]

    for ch in champions:
        key = _trade_key(ch)
        if key not in lanes:
            lanes[key] = {
                "champion_id": ch["id"],
                "asset": ch["asset"],
                "timeframe": ch["timeframe"],
                "status": "flat",
                "equity": 10000.0,
                "open_position": None,
                "watch_weeks": 0,
                "stats": {"entries": 0, "closes": 0, "wins": 0, "losses": 0, "gross_win": 0.0, "gross_loss": 0.0, "realized_pnl": 0.0},
            }

    return st


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--champions", default="docs/shared/CHAMPIONS.json")
    ap.add_argument("--log", default="data/forward/FORWARD_LOG.ndjson")
    ap.add_argument("--state", default="data/forward/PAPER_POSITIONS.json")
    ap.add_argument("--retry-once", action="store_true", default=True)
    args = ap.parse_args()

    ts = datetime.now(UTC).isoformat()
    cfg = _jload(ROOT / args.champions, {})
    champions = [c for c in (cfg.get("champions") or []) if str(c.get("status")) in {"active", "watch"}]
    if not champions:
        _append_ndjson(ROOT / args.log, {"ts_iso": ts, "event": "RUN_SKIPPED", "reason": "NO_ACTIVE_CHAMPIONS"})
        return 0

    state_path = ROOT / args.state
    log_path = ROOT / args.log
    state = _ensure_state(state_path, champions)

    pairs = sorted({(str(c["asset"]).upper(), str(c["timeframe"]).lower()) for c in champions})
    market: dict[tuple[str, str], dict] = {}

    for asset, tf in pairs:
        ok, out = _ingest(asset, tf, 730)
        if (not ok) and args.retry_once:
            ok, out = _ingest(asset, tf, 730)
        if not ok:
            _append_ndjson(log_path, {"ts_iso": ts, "event": "DATA_INGEST_FAIL", "asset": asset, "timeframe": tf, "error": out[:400]})
            continue
        meta = _latest_meta(asset, tf)
        bars = _load_bars(meta)
        if len(bars) < 50:
            _append_ndjson(log_path, {"ts_iso": ts, "event": "DATA_TOO_SHORT", "asset": asset, "timeframe": tf, "bars": len(bars)})
            continue
        import pandas as pd
        df = pd.DataFrame(bars)
        ind_df = build_indicator_frame(df)
        i = len(ind_df) - 1
        market[(asset, tf)] = {
            "bars": bars,
            "ind_df": ind_df,
            "i": i,
            "bar": bars[i],
            "bar_time": bars[i]["time"],
            "regime": _classify_regime_from_adx(float(ind_df["ADX_14"].iloc[i]) if "ADX_14" in ind_df.columns and str(ind_df["ADX_14"].iloc[i]) != "nan" else None),
        }

    for ch in champions:
        asset, tf = str(ch["asset"]).upper(), str(ch["timeframe"]).lower()
        key = _trade_key(ch)
        lane = state["lanes"][key]
        m = market.get((asset, tf))
        if not m:
            continue

        ind_df = m["ind_df"]
        i = int(m["i"])
        bar = m["bar"]
        params = {}
        params["_entry_long"] = ch.get("entry_long", [])
        params["_entry_short"] = ch.get("entry_short", [])
        long_sig, short_sig = get_signals(ch.get("template_name", "spec_rules"), ind_df, i, params)

        rp = ch.get("risk_policy") or {}
        stop_mult = float(rp.get("stop_atr_mult", 1.0))
        tp_mult = float(rp.get("tp_atr_mult", 2.0))
        risk_pct = float(rp.get("risk_per_trade_pct", 1.0)) / 100.0
        atr = float(ind_df["ATR_14"].iloc[i]) if "ATR_14" in ind_df.columns and str(ind_df["ATR_14"].iloc[i]) != "nan" else 0.0
        close_px = float(bar["close"])

        pos = lane.get("open_position")
        closed_this_bar = False

        if pos:
            side = pos["side"]
            stop = float(pos["stop_price"])
            tp = float(pos["tp_price"])
            exit_px = None
            exit_reason = None

            if side == "long":
                if float(bar["low"]) <= stop:
                    exit_px, exit_reason = stop, "STOP"
                elif float(bar["high"]) >= tp:
                    exit_px, exit_reason = tp, "TP"
                elif short_sig and bool((ch.get("execution_policy") or {}).get("allow_reverse", True)):
                    exit_px, exit_reason = close_px, "REVERSE_SIGNAL"
            else:
                if float(bar["high"]) >= stop:
                    exit_px, exit_reason = stop, "STOP"
                elif float(bar["low"]) <= tp:
                    exit_px, exit_reason = tp, "TP"
                elif long_sig and bool((ch.get("execution_policy") or {}).get("allow_reverse", True)):
                    exit_px, exit_reason = close_px, "REVERSE_SIGNAL"

            if exit_px is not None:
                qty = float(pos["qty"])
                entry = float(pos["entry_price"])
                pnl = (exit_px - entry) * qty if side == "long" else (entry - exit_px) * qty
                fee_bps = 4.5
                fee = ((entry * qty) + (exit_px * qty)) * (fee_bps / 10000.0)
                pnl_after_fee = pnl - fee
                lane["equity"] = round(float(lane["equity"]) + pnl_after_fee, 8)
                lane["open_position"] = None
                lane["status"] = "flat"
                lane["stats"]["closes"] += 1
                lane["stats"]["realized_pnl"] += pnl_after_fee
                if pnl_after_fee >= 0:
                    lane["stats"]["wins"] += 1
                    lane["stats"]["gross_win"] += pnl_after_fee
                else:
                    lane["stats"]["losses"] += 1
                    lane["stats"]["gross_loss"] += abs(pnl_after_fee)

                _append_ndjson(log_path, {
                    "ts_iso": ts,
                    "event": "POSITION_CLOSE",
                    "bar_time": m["bar_time"],
                    "champion_id": ch["id"],
                    "asset": asset,
                    "timeframe": tf,
                    "side": side,
                    "exit_reason": exit_reason,
                    "entry_price": entry,
                    "exit_price": exit_px,
                    "qty": qty,
                    "pnl": round(pnl_after_fee, 8),
                    "equity": lane["equity"],
                    "regime": m["regime"],
                })
                _notify(f"📉 Forward close: {ch['strategy_name']} {asset} {tf} {side} pnl={pnl_after_fee:.2f} reason={exit_reason}")
                closed_this_bar = True

        if lane.get("open_position") is None and not closed_this_bar:
            open_side = "long" if long_sig else ("short" if short_sig else "")
            if open_side:
                if atr <= 0:
                    _append_ndjson(log_path, {"ts_iso": ts, "event": "ENTRY_SKIPPED_NO_ATR", "champion_id": ch["id"], "asset": asset, "timeframe": tf})
                else:
                    if open_side == "long":
                        stop = close_px - (atr * stop_mult)
                        tp = close_px + (atr * tp_mult)
                    else:
                        stop = close_px + (atr * stop_mult)
                        tp = close_px - (atr * tp_mult)
                    qty = _position_qty(float(lane["equity"]), risk_pct, close_px, stop)

                    lane["open_position"] = {
                        "side": open_side,
                        "entry_price": close_px,
                        "entry_time": m["bar_time"],
                        "stop_price": stop,
                        "tp_price": tp,
                        "qty": qty,
                    }
                    lane["status"] = "in_trade"
                    lane["stats"]["entries"] += 1

                    _append_ndjson(log_path, {
                        "ts_iso": ts,
                        "event": "POSITION_OPEN",
                        "bar_time": m["bar_time"],
                        "champion_id": ch["id"],
                        "asset": asset,
                        "timeframe": tf,
                        "side": open_side,
                        "entry_price": close_px,
                        "stop_price": stop,
                        "tp_price": tp,
                        "qty": qty,
                        "equity": lane["equity"],
                        "regime": m["regime"],
                    })
                    _notify(f"📌 Forward entry: {ch['strategy_name']} {asset} {tf} {open_side} @ {close_px:.4f}")
        elif lane.get("open_position") is not None:
            if long_sig or short_sig:
                _append_ndjson(log_path, {
                    "ts_iso": ts,
                    "event": "SIGNAL_BUT_IN_TRADE",
                    "bar_time": m["bar_time"],
                    "champion_id": ch["id"],
                    "asset": asset,
                    "timeframe": tf,
                    "regime": m["regime"],
                })

        _append_ndjson(log_path, {
            "ts_iso": ts,
            "event": "SIGNAL_EVAL",
            "bar_time": m["bar_time"],
            "champion_id": ch["id"],
            "asset": asset,
            "timeframe": tf,
            "long_signal": bool(long_sig),
            "short_signal": bool(short_sig),
            "in_trade": lane.get("open_position") is not None,
            "regime": m["regime"],
        })

    state["updated_at"] = ts
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_ndjson(log_path, {"ts_iso": ts, "event": "RUN_OK", "champions_processed": len(champions)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
