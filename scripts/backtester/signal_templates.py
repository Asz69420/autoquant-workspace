#!/usr/bin/env python3
from __future__ import annotations

"""
Signal template registry for the backtester.

Each template returns (long_signal, short_signal) booleans for a single bar index.
Templates are designed to consume indicator columns produced by build_indicator_frame.

Public API:
- get_signals(template_name, df, row_index, variant_params) -> tuple[bool, bool]
- resolve_template(variant: dict) -> str
- TEMPLATE_REGISTRY
"""

from typing import Callable
import re

import pandas as pd

SignalFn = Callable[[pd.DataFrame, int, dict], tuple[bool, bool]]


def _to_int(params: dict, key: str, default: int) -> int:
    try:
        return int(params.get(key, default))
    except Exception:
        return default


def _to_float(params: dict, key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except Exception:
        return default


def _ready(df: pd.DataFrame, i: int, cols: list[str], lookback: int = 1) -> bool:
    if i < lookback or i >= len(df):
        return False
    for c in cols:
        if c not in df.columns:
            return False
        v = df[c].iloc[i]
        if pd.isna(v):
            return False
    return True


def _crossed_above(a_prev: float, a_now: float, b_prev: float, b_now: float) -> bool:
    return (a_prev <= b_prev) and (a_now > b_now)


def _crossed_below(a_prev: float, a_now: float, b_prev: float, b_now: float) -> bool:
    return (a_prev >= b_prev) and (a_now < b_now)


# ─────────────────────────────────────────────
# EXISTING TEMPLATES
# ─────────────────────────────────────────────
def ema_crossover(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """EMA_9 crosses EMA_21."""
    if not _ready(df, i, ["EMA_9", "EMA_21"], lookback=1):
        return False, False
    e9_prev, e9_now = df["EMA_9"].iloc[i - 1], df["EMA_9"].iloc[i]
    e21_prev, e21_now = df["EMA_21"].iloc[i - 1], df["EMA_21"].iloc[i]
    if pd.isna(e9_prev) or pd.isna(e21_prev):
        return False, False
    long_sig = _crossed_above(e9_prev, e9_now, e21_prev, e21_now)
    short_sig = _crossed_below(e9_prev, e9_now, e21_prev, e21_now)
    return bool(long_sig), bool(short_sig)


def rsi_pullback(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Trend + pullback template."""
    ema_trend = _to_int(params, "ema_trend", 200)
    ema_slope = _to_int(params, "ema_slope", 50)
    rsi_long_max = _to_float(params, "rsi_long_max", 40.0)
    rsi_short_min = _to_float(params, "rsi_short_min", 60.0)

    c_trend = f"EMA_{ema_trend}"
    c_slope = f"EMA_{ema_slope}"
    cols = ["close", "RSI_14", c_trend, c_slope]
    if not _ready(df, i, cols, lookback=1):
        return False, False

    close_now = df["close"].iloc[i]
    rsi = df["RSI_14"].iloc[i]
    slope_prev, slope_now = df[c_slope].iloc[i - 1], df[c_slope].iloc[i]
    trend_ema = df[c_trend].iloc[i]

    if pd.isna(slope_prev):
        return False, False

    slope_up = slope_now > slope_prev
    slope_down = slope_now < slope_prev

    long_sig = (close_now > trend_ema) and slope_up and (rsi <= rsi_long_max)
    short_sig = (close_now < trend_ema) and slope_down and (rsi >= rsi_short_min)
    return bool(long_sig), bool(short_sig)


def macd_confirmation(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """MACDh_12_26_9 zero-line cross confirmed by close vs EMA_50."""
    cols = ["MACDh_12_26_9", "EMA_50", "close"]
    if not _ready(df, i, cols, lookback=1):
        return False, False

    h_prev, h_now = df["MACDh_12_26_9"].iloc[i - 1], df["MACDh_12_26_9"].iloc[i]
    close_now, ema50 = df["close"].iloc[i], df["EMA_50"].iloc[i]
    if pd.isna(h_prev):
        return False, False

    long_sig = (h_prev <= 0.0) and (h_now > 0.0) and (close_now > ema50)
    short_sig = (h_prev >= 0.0) and (h_now < 0.0) and (close_now < ema50)
    return bool(long_sig), bool(short_sig)


def supertrend_follow(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """SUPERTd_7_3.0 direction flip with ADX_14 > 20 filter."""
    adx_min = _to_float(params, "adx_min", 20.0)
    cols = ["SUPERTd_7_3.0", "ADX_14"]
    if not _ready(df, i, cols, lookback=1):
        return False, False

    d_prev, d_now = df["SUPERTd_7_3.0"].iloc[i - 1], df["SUPERTd_7_3.0"].iloc[i]
    adx = df["ADX_14"].iloc[i]
    if pd.isna(d_prev):
        return False, False

    long_sig = (d_prev <= 0) and (d_now > 0) and (adx > adx_min)
    short_sig = (d_prev >= 0) and (d_now < 0) and (adx > adx_min)
    return bool(long_sig), bool(short_sig)


def bollinger_breakout(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Close breaks Bollinger bands with optional volume confirmation."""
    vol_ratio_min = _to_float(params, "volume_ratio_min", 1.0)
    cols = ["close", "BBU_20_2.0", "BBL_20_2.0"]
    if not _ready(df, i, cols, lookback=0):
        return False, False

    close_now = df["close"].iloc[i]
    bbu = df["BBU_20_2.0"].iloc[i]
    bbl = df["BBL_20_2.0"].iloc[i]

    vol_ok = True
    if "volume" in df.columns:
        if i < 20:
            vol_ok = False
        else:
            v = df["volume"].iloc[i]
            vma = df["volume"].rolling(20).mean().iloc[i]
            vol_ok = (not pd.isna(v)) and (not pd.isna(vma)) and (vma > 0) and ((v / vma) >= vol_ratio_min)

    long_sig = (close_now > bbu) and vol_ok
    short_sig = (close_now < bbl) and vol_ok
    return bool(long_sig), bool(short_sig)


def stochastic_reversal(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Stochastic K/D crossover in OB/OS zones."""
    ob = _to_float(params, "stoch_ob", 80.0)
    os_val = _to_float(params, "stoch_os", 20.0)
    cols = ["STOCHk_14_3_3", "STOCHd_14_3_3"]
    if not _ready(df, i, cols, lookback=1):
        return False, False

    k_prev, k_now = df["STOCHk_14_3_3"].iloc[i - 1], df["STOCHk_14_3_3"].iloc[i]
    d_prev, d_now = df["STOCHd_14_3_3"].iloc[i - 1], df["STOCHd_14_3_3"].iloc[i]
    if pd.isna(k_prev) or pd.isna(d_prev):
        return False, False

    long_sig = _crossed_above(k_prev, k_now, d_prev, d_now) and (k_now < os_val)
    short_sig = _crossed_below(k_prev, k_now, d_prev, d_now) and (k_now > ob)
    return bool(long_sig), bool(short_sig)


def ema_rsi_atr(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """EMA trend + RSI confirmation + ATR volatility gate."""
    rsi_long_min = _to_float(params, "rsi_long_min", 40.0)
    rsi_long_max = _to_float(params, "rsi_long_max", 70.0)
    rsi_short_min = _to_float(params, "rsi_short_min", 30.0)
    rsi_short_max = _to_float(params, "rsi_short_max", 60.0)

    cols = ["EMA_9", "EMA_21", "RSI_14", "ATR_14"]
    if not _ready(df, i, cols, lookback=20):
        return False, False

    ema9, ema21 = df["EMA_9"].iloc[i], df["EMA_21"].iloc[i]
    rsi = df["RSI_14"].iloc[i]
    atr = df["ATR_14"].iloc[i]
    atr_ma20 = df["ATR_14"].rolling(20).mean().iloc[i]
    if pd.isna(atr_ma20) or atr_ma20 <= 0:
        return False, False

    vol_gate = atr > atr_ma20
    long_sig = (ema9 > ema21) and (rsi_long_min <= rsi <= rsi_long_max) and vol_gate
    short_sig = (ema9 < ema21) and (rsi_short_min <= rsi <= rsi_short_max) and vol_gate
    return bool(long_sig), bool(short_sig)


# ─────────────────────────────────────────────
# QUANDALF-DESIGNED TEMPLATES
# ─────────────────────────────────────────────
def choppiness_donchian_fade(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Mean-reversion in confirmed ranges.

    Quandalf Strategy 1.
    Enters AGAINST local move when Choppiness Index confirms range-bound market.
    Fades Donchian channel edges with RSI oversold/overbought confirmation.
    Designed for ranging/transitional regimes where 19/23 ACCEPTs already profit.

    Params:
        chop_min (float): Minimum CHOP_14 to confirm range. Default 61.8
        rsi_os (float): RSI oversold threshold for long. Default 35.0
        rsi_ob (float): RSI overbought threshold for short. Default 65.0
    """
    chop_min = _to_float(params, "chop_min", 61.8)
    rsi_os = _to_float(params, "rsi_os", 35.0)
    rsi_ob = _to_float(params, "rsi_ob", 65.0)

    cols = ["CHOP_14_1_100", "DCU_20_20", "DCL_20_20", "DCM_20_20", "RSI_14", "close"]
    if not _ready(df, i, cols, lookback=1):
        return False, False

    chop = df["CHOP_14_1_100"].iloc[i]
    close_now = df["close"].iloc[i]
    dcu = df["DCU_20_20"].iloc[i]
    dcl = df["DCL_20_20"].iloc[i]
    rsi = df["RSI_14"].iloc[i]

    is_choppy = chop > chop_min

    long_sig = is_choppy and (close_now <= dcl) and (rsi < rsi_os)
    short_sig = is_choppy and (close_now >= dcu) and (rsi > rsi_ob)
    return bool(long_sig), bool(short_sig)


def kama_vortex_divergence(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Early trend exhaustion detection.

    Quandalf Strategy 2.
    KAMA flattening (trend losing momentum) + Vortex crossover (new direction emerging)
    + ATR volatility gate. Catches reversals early before they become obvious.

    Params:
        kama_slope_threshold (float): Max abs slope for "flattening". Default 0.001
        atr_lookback (int): ATR MA lookback for volatility gate. Default 20
    """
    kama_slope_thresh = _to_float(params, "kama_slope_threshold", 0.001)
    atr_lookback = _to_int(params, "atr_lookback", 20)

    cols = ["KAMA_10_2_30", "VTXP_14", "VTXM_14", "ATR_14"]
    if not _ready(df, i, cols, lookback=max(2, atr_lookback)):
        return False, False

    kama_now = df["KAMA_10_2_30"].iloc[i]
    kama_prev = df["KAMA_10_2_30"].iloc[i - 1]
    kama_prev2 = df["KAMA_10_2_30"].iloc[i - 2]
    if pd.isna(kama_prev) or pd.isna(kama_prev2):
        return False, False

    # KAMA slope: was moving, now flattening
    slope_now = kama_now - kama_prev
    slope_prev = kama_prev - kama_prev2

    # Normalize slope by price level to make threshold asset-agnostic
    price_ref = kama_now if kama_now > 0 else 1.0
    norm_slope_now = slope_now / price_ref
    norm_slope_prev = slope_prev / price_ref

    # Flattening = slope magnitude decreasing and currently near zero
    flattening_from_down = (norm_slope_prev < -kama_slope_thresh) and (norm_slope_now > -kama_slope_thresh)
    flattening_from_up = (norm_slope_prev > kama_slope_thresh) and (norm_slope_now < kama_slope_thresh)

    # Vortex crossover
    vtxp_now = df["VTXP_14"].iloc[i]
    vtxm_now = df["VTXM_14"].iloc[i]
    vtxp_prev = df["VTXP_14"].iloc[i - 1]
    vtxm_prev = df["VTXM_14"].iloc[i - 1]
    if pd.isna(vtxp_prev) or pd.isna(vtxm_prev):
        return False, False

    vtx_bull_cross = _crossed_above(vtxp_prev, vtxp_now, vtxm_prev, vtxm_now)
    vtx_bear_cross = _crossed_below(vtxp_prev, vtxp_now, vtxm_prev, vtxm_now)

    # ATR volatility gate
    atr = df["ATR_14"].iloc[i]
    atr_ma = df["ATR_14"].rolling(atr_lookback).mean().iloc[i]
    if pd.isna(atr_ma) or atr_ma <= 0:
        return False, False

    vol_present = atr > atr_ma

    long_sig = flattening_from_down and vtx_bull_cross and vol_present
    short_sig = flattening_from_up and vtx_bear_cross and vol_present
    return bool(long_sig), bool(short_sig)


def stc_cycle_timing(df: pd.DataFrame, i: int, params: dict) -> tuple[bool, bool]:
    """Cycle-based entries using Schaff Trend Cycle.

    Quandalf Strategy 3.
    STC crosses threshold levels (smoothed MACD/Stochastic hybrid for cycle timing)
    confirmed by EMA_50 slope direction and Choppiness below threshold (not too choppy).

    Params:
        stc_os (float): STC oversold level for long entry. Default 25.0
        stc_ob (float): STC overbought level for short entry. Default 75.0
        chop_max (float): Max CHOP_14 — rejects if market too choppy. Default 50.0
        ema_slope_lookback (int): Bars to measure EMA_50 slope. Default 3
    """
    stc_os = _to_float(params, "stc_os", 25.0)
    stc_ob = _to_float(params, "stc_ob", 75.0)
    chop_max = _to_float(params, "chop_max", 50.0)
    slope_lb = _to_int(params, "ema_slope_lookback", 3)

    cols = ["STC_10_12_26_0.5", "EMA_50", "CHOP_14_1_100"]
    if not _ready(df, i, cols, lookback=max(2, slope_lb)):
        return False, False

    stc_now = df["STC_10_12_26_0.5"].iloc[i]
    stc_prev = df["STC_10_12_26_0.5"].iloc[i - 1]
    if pd.isna(stc_prev):
        return False, False

    chop = df["CHOP_14_1_100"].iloc[i]
    not_too_choppy = chop < chop_max

    ema50_now = df["EMA_50"].iloc[i]
    ema50_back = df["EMA_50"].iloc[i - slope_lb]
    if pd.isna(ema50_back):
        return False, False

    ema_rising = ema50_now > ema50_back
    ema_falling = ema50_now < ema50_back

    # STC crosses up through oversold = long; crosses down through overbought = short
    stc_cross_up = (stc_prev <= stc_os) and (stc_now > stc_os)
    stc_cross_down = (stc_prev >= stc_ob) and (stc_now < stc_ob)

    long_sig = stc_cross_up and ema_rising and not_too_choppy
    short_sig = stc_cross_down and ema_falling and not_too_choppy
    return bool(long_sig), bool(short_sig)


# ─────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────
TEMPLATE_REGISTRY: dict[str, SignalFn] = {
    "ema_crossover": ema_crossover,
    "rsi_pullback": rsi_pullback,
    "macd_confirmation": macd_confirmation,
    "supertrend_follow": supertrend_follow,
    "bollinger_breakout": bollinger_breakout,
    "stochastic_reversal": stochastic_reversal,
    "ema_rsi_atr": ema_rsi_atr,
    "choppiness_donchian_fade": choppiness_donchian_fade,
    "kama_vortex_divergence": kama_vortex_divergence,
    "stc_cycle_timing": stc_cycle_timing,
}


def _parse_roleframework(filters: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in filters or []:
        m = re.match(r"RoleFramework\[(\w+)\]=(.+)", str(f).strip())
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip().lower()
    return out


def resolve_template(variant: dict) -> str:
    """Choose best template from variant metadata.

    Selection order:
      1) Explicit template_name in variant
      2) Clues in components[]
      3) RoleFramework tags in filters[]
      4) Variant name heuristics
      5) Fallback: ema_crossover
    """
    if not isinstance(variant, dict):
        return "ema_crossover"

    # Direct template specification — highest priority
    explicit = str(variant.get("template_name") or "").strip().lower()
    if explicit and explicit in TEMPLATE_REGISTRY:
        return explicit

    name = str(variant.get("name") or "").lower()
    components = variant.get("components") or []
    filters = variant.get("filters") or []

    comp_blob = " ".join(
        f"{str(c.get('role', '')).lower()} {str(c.get('indicator', '')).lower()} {str(c.get('notes', '')).lower()}"
        for c in components
        if isinstance(c, dict)
    )

    # Quandalf templates — check first since they use specific indicator combos
    if "chop" in comp_blob and "donchian" in comp_blob:
        return "choppiness_donchian_fade"
    if "kama" in comp_blob and "vortex" in comp_blob:
        return "kama_vortex_divergence"
    if "stc" in comp_blob or "schaff" in comp_blob:
        return "stc_cycle_timing"

    # Original templates
    if "supertrend" in comp_blob:
        return "supertrend_follow"
    if "bollinger" in comp_blob:
        return "bollinger_breakout"
    if "stoch" in comp_blob:
        return "stochastic_reversal"
    if "macd" in comp_blob:
        return "macd_confirmation"
    if "rsi" in comp_blob and "atr" in comp_blob and "ema" in comp_blob:
        return "ema_rsi_atr"
    if "rsi" in comp_blob:
        return "rsi_pullback"

    roles = _parse_roleframework(filters)
    role_values = " ".join(roles.values())

    # Quandalf templates in role framework
    if "chop" in role_values and "donchian" in role_values:
        return "choppiness_donchian_fade"
    if "kama" in role_values and "vortex" in role_values:
        return "kama_vortex_divergence"
    if "stc" in role_values or "schaff" in role_values:
        return "stc_cycle_timing"

    if all(k in roles for k in ("baseline", "confirmation", "volume_volatility")) and all(
        x in role_values for x in ("ema", "rsi", "atr")
    ):
        return "ema_rsi_atr"

    if "supertrend" in role_values:
        return "supertrend_follow"
    if "bollinger" in role_values:
        return "bollinger_breakout"
    if "stoch" in role_values:
        return "stochastic_reversal"
    if "macd" in role_values:
        return "macd_confirmation"
    if "rsi" in role_values:
        return "rsi_pullback"

    # Name heuristics — Quandalf templates
    if "chop" in name and ("donchian" in name or "fade" in name):
        return "choppiness_donchian_fade"
    if "kama" in name and "vortex" in name:
        return "kama_vortex_divergence"
    if "stc" in name or "schaff" in name or "cycle" in name:
        return "stc_cycle_timing"

    # Name heuristics — original templates
    if "supertrend" in name:
        return "supertrend_follow"
    if "bollinger" in name or "breakout" in name:
        return "bollinger_breakout"
    if "stoch" in name:
        return "stochastic_reversal"
    if "macd" in name:
        return "macd_confirmation"
    if "rsi" in name or "pullback" in name:
        return "rsi_pullback"

    selected = "ema_crossover"
    if selected == "ema_crossover" and "trendpullback" in name:
        return "rsi_pullback"
    return selected


def get_signals(template_name: str, df: pd.DataFrame, row_index: int, variant_params: dict) -> tuple[bool, bool]:
    """Dispatch signal generation by template name.

    Unknown template names fall back to ema_crossover.
    """
    fn = TEMPLATE_REGISTRY.get(str(template_name or "").strip().lower(), ema_crossover)
    try:
        return fn(df, int(row_index), variant_params or {})
    except Exception:
        return False, False


__all__ = [
    "get_signals",
    "resolve_template",
    "TEMPLATE_REGISTRY",
    "ema_crossover",
    "rsi_pullback",
    "macd_confirmation",
    "supertrend_follow",
    "bollinger_breakout",
    "stochastic_reversal",
    "ema_rsi_atr",
    "choppiness_donchian_fade",
    "kama_vortex_divergence",
    "stc_cycle_timing",
]
