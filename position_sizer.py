"""
Position sizing and PnL calculation for BankNifty Short Strangle.

CRITICAL: NO compounding. Quantity stays fixed at 15 every single day
regardless of wins or losses. Available capital changes, but quantity/lots
never change. This is a fixed-lot strategy as specified in the assignment.
"""

import logging

import numpy as np
import pandas as pd

from config import (
    LOT_SIZE,
    QUANTITY,
    INITIAL_CAPITAL,
    BASE_NAV,
    EXPIRY_WEEKDAY,
    SPOT_ENTRY_TIME,
)

logger = logging.getLogger(__name__)


def calculate_pnl(trades: pd.DataFrame, spot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate PnL, cumulative PnL, capital, and NAV for all trade legs.

    SHORT position: profit when ExitPrice < EntryPrice (premium decays in our favor).
    GrossPnL = (EntryPrice - ExitPrice) × Quantity per leg.

    Args:
        trades: Trades DataFrame with EntryPrice, ExitPrice, Date, OptionType, Strike.
        spot_df: Spot DataFrame for attaching BankNifty close at entry.

    Returns:
        Trades DataFrame with PnL, capital, NAV, and expiry columns added.
    """
    # ── Fixed position sizing (no compounding) ───────────────────────────
    trades["LotSize"] = LOT_SIZE
    trades["Quantity"] = QUANTITY

    # Entry and exit values
    trades["EntryValue"] = trades["EntryPrice"] * trades["Quantity"]
    trades["ExitValue"] = trades["ExitPrice"] * trades["Quantity"]

    # SHORT PnL: we sell at entry, buy back at exit
    trades["GrossPnL"] = (trades["EntryPrice"] - trades["ExitPrice"]) * trades["Quantity"]

    # ── Attach BankNifty spot close at entry ─────────────────────────────
    spot_entry = spot_df[spot_df["Time"] == SPOT_ENTRY_TIME][["Date", "Close"]].copy()
    spot_entry.rename(columns={"Close": "Banknifty_Close"}, inplace=True)
    trades = trades.merge(spot_entry, on="Date", how="left")

    # ── Sort chronologically: by date, then CE before PE ─────────────────
    trades = trades.sort_values(["Date", "OptionType"], ascending=[True, True]).reset_index(drop=True)

    # ── Cumulative PnL and capital ───────────────────────────────────────
    trades["CumulativePnL"] = trades["GrossPnL"].cumsum()
    trades["AvailableCapital"] = INITIAL_CAPITAL + trades["CumulativePnL"]

    # ── NAV (equity curve index, base = 100) ─────────────────────────────
    trades["NAV"] = BASE_NAV * trades["AvailableCapital"] / INITIAL_CAPITAL

    # ── Expiry day identification ────────────────────────────────────────
    trades["EntryDate_dt"] = pd.to_datetime(trades["EntryDate"])
    trades["IsExpiryDay"] = (
        (trades["EntryDate_dt"].dt.weekday == EXPIRY_WEEKDAY)  # Wednesday
        & (trades["EntryDate_dt"].dt.day <= 7)                  # First week of month
    )

    # ── PnL percentage (relative to entry value) ─────────────────────────
    trades["PnL_Pct"] = np.where(
        trades["EntryValue"] != 0,
        trades["GrossPnL"] / trades["EntryValue"] * 100,
        0.0,
    )

    # ── Column name for output: Option_Type ──────────────────────────────
    trades["Option_Type"] = trades["OptionType"]

    logger.info(
        "PnL calculated: total GrossPnL = Rs. %.2f, final capital = Rs. %.2f",
        trades["GrossPnL"].sum(),
        trades["AvailableCapital"].iloc[-1],
    )

    return trades
