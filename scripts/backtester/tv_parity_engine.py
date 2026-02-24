#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Bar:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def load_bars(path: Path) -> list[Bar]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        low = {h.lower().strip(): h for h in headers}
        c_time = low.get("time") or low.get("date")
        c_open = low.get("open")
        c_high = low.get("high")
        c_low = low.get("low")
        c_close = low.get("close")
        c_vol = low.get("volume") or low.get("vol")
        out = []
        for row in r:
            out.append(Bar(
                time=row[c_time],
                open=float(row[c_open]),
                high=float(row[c_high]),
                low=float(row[c_low]),
                close=float(row[c_close]),
                volume=float(row.get(c_vol, 0) or 0),
            ))
    return out


def pick_variant(spec: dict, name: str) -> dict:
    for v in spec.get("variants", []):
        if v.get("name") == name:
            return v
    raise ValueError(f"Variant not found: {name}")


def parse_rule_kv(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def signal_eval(sig: str, bar: Bar) -> bool:
    sig = sig.strip().lower()
    if sig == "close_gt_open":
        return bar.close > bar.open
    if sig == "close_lt_open":
        return bar.close < bar.open
    return False


def compute_metrics(trades: list[dict]) -> dict:
    pnls = [float(t["pnl"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return {
        "trades": len(trades),
        "net_return": round(sum(pnls), 8),
        "max_drawdown_proxy": round(abs(dd), 8),
        "win_rate": round((len(wins) / len(trades)) if trades else 0.0, 8),
        "profit_factor": round((gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0), 8),
    }


def close_trade(trades: list[dict], pos: dict, bar: Bar, exit_price: float, reason: str, commission_pct: float, i: int) -> None:
    side = pos["side"]
    ep = float(pos["entry_price"])
    qty = float(pos["qty"])
    gross = ((exit_price - ep) if side == "long" else (ep - exit_price)) * qty
    commission = ((ep + exit_price) * qty) * (commission_pct / 100.0)
    pnl = gross - commission
    trades.append({
        "entry_time": pos["entry_time"],
        "entry_price": round(ep, 8),
        "exit_time": bar.time,
        "exit_price": round(float(exit_price), 8),
        "side": side,
        "qty": qty,
        "pnl": round(pnl, 8),
        "reason": reason,
        "bars_held": int(max(1, i - int(pos["entry_idx"]) + 1)),
    })


def main() -> int:
    ap = argparse.ArgumentParser(description="TradingView parity backtest engine (stage-1).")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--strategy-spec", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--commission-pct", type=float, default=0.0)
    ap.add_argument("--fill-rule", choices=["bar_close", "next_open", "close_entry"], default="bar_close")
    ap.add_argument("--tie-break", choices=["stop_priority", "worst_case", "best_case"], default="stop_priority")
    args = ap.parse_args()

    dataset = Path(args.dataset)
    bars = load_bars(dataset)
    spec = json.loads(Path(args.strategy_spec).read_text(encoding="utf-8"))
    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    variant = pick_variant(spec, args.variant)

    risk = parse_rule_kv(variant.get("risk_rules", []))
    stop_loss_pct = float(risk.get("stop_loss_pct", "0"))
    take_profit_pct = float(risk.get("take_profit_pct", "0"))

    long_signals = [s for s in variant.get("entry_long", []) if s.strip()]
    short_signals = [s for s in variant.get("entry_short", []) if s.strip()]
    exit_signals = [s for s in variant.get("exit_rules", []) if s.strip()]

    trades: list[dict] = []
    pos: dict | None = None

    for i, bar in enumerate(bars):
        long_sig = any(signal_eval(s, bar) for s in long_signals)
        short_sig = any(signal_eval(s, bar) for s in short_signals)

        # Reversal-first semantics at bar close
        if pos is not None:
            if pos["side"] == "long" and short_sig:
                close_trade(trades, pos, bar, bar.close, "reversal", args.commission_pct, i)
                pos = {"side": "short", "entry_price": bar.close, "entry_time": bar.time, "entry_idx": i, "qty": 1.0}
                continue
            if pos["side"] == "short" and long_sig:
                close_trade(trades, pos, bar, bar.close, "reversal", args.commission_pct, i)
                pos = {"side": "long", "entry_price": bar.close, "entry_time": bar.time, "entry_idx": i, "qty": 1.0}
                continue

        if pos is not None:
            side = pos["side"]
            ep = float(pos["entry_price"])
            stop = ep * (1 - stop_loss_pct) if side == "long" else ep * (1 + stop_loss_pct)
            tp = ep * (1 + take_profit_pct) if side == "long" else ep * (1 - take_profit_pct)
            hit_sl = stop_loss_pct > 0 and ((bar.low <= stop) if side == "long" else (bar.high >= stop))
            hit_tp = take_profit_pct > 0 and ((bar.high >= tp) if side == "long" else (bar.low <= tp))

            if hit_sl and hit_tp:
                if args.tie_break in ("stop_priority", "worst_case"):
                    close_trade(trades, pos, bar, stop, "sl", args.commission_pct, i)
                else:
                    close_trade(trades, pos, bar, tp, "tp", args.commission_pct, i)
                pos = None
                continue
            if hit_sl:
                close_trade(trades, pos, bar, stop, "sl", args.commission_pct, i)
                pos = None
                continue
            if hit_tp:
                close_trade(trades, pos, bar, tp, "tp", args.commission_pct, i)
                pos = None
                continue
            if any(signal_eval(s, bar) for s in exit_signals):
                close_trade(trades, pos, bar, bar.close, "close", args.commission_pct, i)
                pos = None
                continue

        if pos is None:
            if long_sig:
                entry_price = bar.close if args.fill_rule == "bar_close" else (bars[i + 1].open if i + 1 < len(bars) else bar.close)
                pos = {"side": "long", "entry_price": entry_price, "entry_time": bar.time, "entry_idx": i, "qty": 1.0}
            elif short_sig:
                entry_price = bar.close if args.fill_rule == "bar_close" else (bars[i + 1].open if i + 1 < len(bars) else bar.close)
                pos = {"side": "short", "entry_price": entry_price, "entry_time": bar.time, "entry_idx": i, "qty": 1.0}

    run_id = f"tvp_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    day_dir = ROOT / "artifacts" / "backtests" / datetime.now().strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    trade_list = {"schema_version": "1.0", "id": run_id, "created_at": datetime.now(UTC).isoformat(), "trades": trades}
    trade_path = day_dir / f"{run_id}.trade_list.json"
    trade_path.write_text(json.dumps(trade_list, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    result = {
        "schema_version": "1.0",
        "id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "inputs": {"dataset_path": str(dataset), "strategy_spec_path": str(Path(args.strategy_spec)), "variant": args.variant},
        "settings": {"commission_pct": args.commission_pct, "slippage": 0, "fill_rule": args.fill_rule, "tie_break": args.tie_break, "tv_timezone": meta.get("timezone")},
        "results": compute_metrics(trades),
    }
    encoded = json.dumps(result, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 80 * 1024:
        raise ValueError("backtest_result exceeds 80KB")
    result_path = day_dir / f"{run_id}.backtest_result.json"
    result_path.write_text(encoded, encoding="utf-8")

    print(json.dumps({"trade_list": str(trade_path), "backtest_result": str(result_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
