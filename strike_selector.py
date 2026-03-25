"""
Strike selection module for BankNifty Short Strangle.

At 09:20 each trading day, selects the CE and PE strikes whose close price
is closest to the TARGET_PREMIUM (Rs. 50). Fully vectorized — zero loops.

Tie-breaking: lower strike for CE, higher strike for PE (conservative).
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

from config import ENTRY_TIME, TARGET_PREMIUM

logger = logging.getLogger(__name__)


def select_strikes(options_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Select CE and PE strikes closest to TARGET_PREMIUM at entry time each day.

    For each trading day, filters the 09:20:59 bar for all available options,
    computes |Close - 50| for each, and picks the strike with the minimum
    difference via groupby + idxmin. Zero Python loops.

    Tie-breaking logic:
        - CE: if two strikes tie, pick the LOWER strike (sorts ascending, first wins)
        - PE: if two strikes tie, pick the HIGHER strike (sorts descending, first wins)

    Args:
        options_df: Options DataFrame with columns Date, Ticker, Time, Close,
                    OptionType, Strike.

    Returns:
        Tuple of (selected_ce, selected_pe) DataFrames, one row per trading day,
        with columns: Date, Ticker, OptionType, Strike, Close (= entry premium).
    """
    # Filter to entry-time bars only
    entry_bars = options_df[options_df["Time"] == ENTRY_TIME].copy()

    if entry_bars.empty:
        logger.warning("No entry bars found at time %s", ENTRY_TIME)
        return pd.DataFrame(), pd.DataFrame()

    # Absolute distance from target premium
    entry_bars["diff_from_target"] = (entry_bars["Close"] - TARGET_PREMIUM).abs()

    # ── CE selection ─────────────────────────────────────────────────────
    ce_bars = entry_bars[entry_bars["OptionType"] == "CE"].copy()
    # Sort by strike ascending so that in ties, lower strike appears first → idxmin picks it
    ce_bars = ce_bars.sort_values(["Date", "Strike"], ascending=[True, True])
    ce_idx = ce_bars.groupby("Date")["diff_from_target"].idxmin()
    selected_ce = ce_bars.loc[ce_idx, ["Date", "Ticker", "OptionType", "Strike", "Close"]].copy()
    selected_ce.rename(columns={"Close": "EntryPremium"}, inplace=True)

    # ── PE selection ─────────────────────────────────────────────────────
    pe_bars = entry_bars[entry_bars["OptionType"] == "PE"].copy()
    # Sort by strike descending so that in ties, higher strike appears first → idxmin picks it
    pe_bars = pe_bars.sort_values(["Date", "Strike"], ascending=[True, False])
    pe_idx = pe_bars.groupby("Date")["diff_from_target"].idxmin()
    selected_pe = pe_bars.loc[pe_idx, ["Date", "Ticker", "OptionType", "Strike", "Close"]].copy()
    selected_pe.rename(columns={"Close": "EntryPremium"}, inplace=True)

    logger.info(
        "Strike selection: %d CE legs, %d PE legs across %d unique dates",
        len(selected_ce), len(selected_pe),
        entry_bars["Date"].nunique(),
    )

    # Log days where one leg is missing (set operations — no row iteration)
    ce_dates = set(selected_ce["Date"])
    pe_dates = set(selected_pe["Date"])
    all_dates = set(entry_bars["Date"].unique())
    missing_ce = all_dates - ce_dates
    missing_pe = all_dates - pe_dates
    if missing_ce:
        logger.warning("No CE strike near Rs. %.0f on %d dates — CE leg skipped", TARGET_PREMIUM, len(missing_ce))
    if missing_pe:
        logger.warning("No PE strike near Rs. %.0f on %d dates — PE leg skipped", TARGET_PREMIUM, len(missing_pe))

    return selected_ce.reset_index(drop=True), selected_pe.reset_index(drop=True)
