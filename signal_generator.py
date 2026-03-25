"""
Entry/exit/stop-loss signal engine for BankNifty Short Strangle.

Determines entry prices (09:20 close), normal exit prices (15:20 close),
and detects stop-loss events by scanning intraday HIGH bars. All vectorized.

Stop-loss logic: We SHORT options, so rising price hurts. SL triggers when
any 1-minute HIGH bar reaches EntryPrice × 1.50 (50% above entry). We use
HIGH (not Close) because intrabar price can touch SL even if the candle
closes below it — using Close would underestimate SL frequency.
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

from config import ENTRY_TIME, EXIT_TIME, SL_MULTIPLIER

logger = logging.getLogger(__name__)


def build_trades(
    selected_ce: pd.DataFrame,
    selected_pe: pd.DataFrame,
    options_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine selected CE and PE legs into a unified trades DataFrame with entry prices.

    Args:
        selected_ce: One row per day with Date, Ticker, OptionType, Strike, EntryPremium.
        selected_pe: Same structure for PE legs.
        options_df: Full options DataFrame (needed for exit prices later).

    Returns:
        Trades DataFrame with EntryPrice and SL_Price columns.
    """
    trades = pd.concat([selected_ce, selected_pe], ignore_index=True)
    trades.rename(columns={"EntryPremium": "EntryPrice"}, inplace=True)

    # SL price = entry price × 1.50 (50% above entry for a short position)
    trades["SL_Price"] = trades["EntryPrice"] * SL_MULTIPLIER

    trades["EntryTime"] = ENTRY_TIME
    trades["EntryDate"] = trades["Date"]

    logger.info("Built %d trade legs across %d dates", len(trades), trades["Date"].nunique())
    return trades


def attach_normal_exit_prices(trades: pd.DataFrame, options_df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach normal (15:20) exit prices to each trade leg.

    If the 15:20 bar is missing for a ticker on a date, we fall back to the
    last available bar at or before 15:20.

    Args:
        trades: Trades DataFrame with Date, Ticker columns.
        options_df: Full options data.

    Returns:
        Trades with NormalExitPrice column added.
    """
    # Primary: exact 15:20 bar
    exit_bars = options_df[options_df["Time"] == EXIT_TIME][["Date", "Ticker", "Close"]].copy()
    exit_bars.rename(columns={"Close": "NormalExitPrice"}, inplace=True)

    trades = trades.merge(exit_bars, on=["Date", "Ticker"], how="left")

    # Fallback for missing 15:20 bars: last bar at or before exit time
    missing_mask = trades["NormalExitPrice"].isna()
    if missing_mask.any():
        n_missing = missing_mask.sum()
        logger.warning("%d legs missing 15:20 exit bar — using last available bar", n_missing)

        # Get the last bar <= EXIT_TIME for each (Date, Ticker)
        pre_exit = options_df[options_df["Time"] <= EXIT_TIME].copy()
        last_bars = pre_exit.sort_values("Time").groupby(["Date", "Ticker"])["Close"].last().reset_index()
        last_bars.rename(columns={"Close": "FallbackExitPrice"}, inplace=True)

        trades = trades.merge(last_bars, on=["Date", "Ticker"], how="left")
        trades["NormalExitPrice"] = np.where(
            trades["NormalExitPrice"].isna(),
            trades["FallbackExitPrice"],
            trades["NormalExitPrice"],
        )
        trades.drop(columns=["FallbackExitPrice"], inplace=True)

    return trades


def detect_stop_loss(trades: pd.DataFrame, options_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect stop-loss events using vectorized bar scanning on HIGH column.

    For each open leg, scan every 1-minute HIGH bar from 09:21 to 15:20.
    If any bar's HIGH >= SL_Price, the leg is stopped out at SL_Price.
    The first such bar's time becomes the SL exit time.

    Each leg is independent — one leg hitting SL does not affect the other.

    Zero loops: uses merge + boolean mask + groupby min.

    Args:
        trades: Trades DataFrame with Date, Ticker, SL_Price.
        options_df: Full options data with High column.

    Returns:
        Trades with ExitTime, ExitPrice, ExitDate, ExitReason columns.
    """
    # Intraday bars AFTER entry (09:21:59 onwards) and up to exit time
    intraday = options_df[
        (options_df["Time"] > ENTRY_TIME) & (options_df["Time"] <= EXIT_TIME)
    ][["Date", "Ticker", "Time", "High"]].copy()

    # Merge with trades to get SL_Price for each bar
    sl_check = intraday.merge(
        trades[["Date", "Ticker", "SL_Price"]],
        on=["Date", "Ticker"],
        how="inner",
    )

    # Boolean: did this bar's HIGH breach the SL level?
    sl_check["SL_Hit"] = sl_check["High"] >= sl_check["SL_Price"]

    # First SL breach per (Date, Ticker) — groupby + min gives earliest time
    sl_hits = (
        sl_check[sl_check["SL_Hit"]]
        .groupby(["Date", "Ticker"])["Time"]
        .min()
        .reset_index()
    )
    sl_hits.columns = ["Date", "Ticker", "SL_Time"]

    # Merge SL times back to trades
    trades = trades.merge(sl_hits, on=["Date", "Ticker"], how="left")

    # Determine final exit: SL if hit, else normal exit at 15:20
    trades["ExitTime"] = np.where(
        trades["SL_Time"].notna(), trades["SL_Time"], EXIT_TIME
    )
    trades["ExitPrice"] = np.where(
        trades["SL_Time"].notna(),
        trades["SL_Price"],            # Exit exactly at SL level
        trades["NormalExitPrice"],      # Normal 15:20 close
    )
    trades["ExitReason"] = np.where(
        trades["SL_Time"].notna(), "StopLoss", "Regular"
    )
    trades["ExitDate"] = trades["Date"]  # Intraday strategy — same day

    # Clean up temporary columns
    trades.drop(columns=["SL_Time", "NormalExitPrice"], inplace=True)

    n_sl = (trades["ExitReason"] == "StopLoss").sum()
    logger.info("SL detection: %d of %d legs stopped out", n_sl, len(trades))

    return trades


def generate_signals(
    selected_ce: pd.DataFrame,
    selected_pe: pd.DataFrame,
    options_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, dict]:
    """
    Full signal generation pipeline: build trades → attach exits → detect SL.

    Args:
        selected_ce: Selected CE legs from strike_selector.
        selected_pe: Selected PE legs from strike_selector.
        options_df: Full options DataFrame.

    Returns:
        Tuple of (trades DataFrame, sl_stats dict with SL hit counts).
    """
    trades = build_trades(selected_ce, selected_pe, options_df)
    trades = attach_normal_exit_prices(trades, options_df)
    trades = detect_stop_loss(trades, options_df)

    # Compute SL stats for data quality report
    sl_stats: dict = {}
    sl_trades = trades[trades["ExitReason"] == "StopLoss"]
    sl_stats["ce_sl_hits"] = int((sl_trades["OptionType"] == "CE").sum())
    sl_stats["pe_sl_hits"] = int((sl_trades["OptionType"] == "PE").sum())

    # Days where BOTH legs hit SL
    sl_dates_ce = set(sl_trades[sl_trades["OptionType"] == "CE"]["Date"])
    sl_dates_pe = set(sl_trades[sl_trades["OptionType"] == "PE"]["Date"])
    sl_stats["both_sl_hits"] = len(sl_dates_ce & sl_dates_pe)

    return trades, sl_stats
