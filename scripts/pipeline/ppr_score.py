#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PPRThresholds:
    pass_min: float = 1.0
    promote_min: float = 3.0


@dataclass(frozen=True)
class PPRConfig:
    pf_cap: float = 2.5
    pf_suspect: float = 4.0
    dd_zero_score_pct: float = 40.0
    grade_trade_ramp: int = 30
    min_trades_hard_fail: int = 10
    suspect_min_trades: int = 25


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def compute_ppr(*, profit_factor: float, max_drawdown_pct: float, trade_count: int, config: PPRConfig | None = None, thresholds: PPRThresholds | None = None) -> dict:
    cfg = config or PPRConfig()
    th = thresholds or PPRThresholds()

    pf = float(profit_factor or 0.0)
    dd = max(0.0, float(max_drawdown_pct or 0.0))
    trades = max(0, int(trade_count or 0))

    edge = _clamp01((min(pf, cfg.pf_cap) - 1.0) / (cfg.pf_cap - 1.0))
    resilience = _clamp01(1.0 - (dd / cfg.dd_zero_score_pct))
    grade = _clamp01(trades / float(cfg.grade_trade_ramp)) if cfg.grade_trade_ramp > 0 else 0.0

    score = float(edge * resilience * grade)

    flags: list[str] = []
    if trades < cfg.min_trades_hard_fail:
        decision = 'FAIL'
        flags.append('LOW_SAMPLE_HARD_FAIL')
    elif pf > cfg.pf_suspect and trades < cfg.suspect_min_trades:
        decision = 'SUSPECT'
        flags.append('HIGH_PF_LOW_SAMPLE')
    elif score >= th.promote_min:
        decision = 'PROMOTE'
    elif score >= th.fail_max:
        decision = 'PASS'
    else:
        decision = 'FAIL'

    return {
        'name': 'PPR',
        'version': '1.0',
        'score': round(score, 6),
        'decision': decision,
        'components': {
            'edge': round(edge, 6),
            'resilience': round(resilience, 6),
            'grade': round(grade, 6),
        },
        'inputs': {
            'profit_factor': round(pf, 8),
            'max_drawdown_pct': round(dd, 4),
            'trade_count': trades,
        },
        'thresholds': {
            'fail_max': th.fail_max,
            'promote_min': th.promote_min,
        },
        'flags': flags,
    }
