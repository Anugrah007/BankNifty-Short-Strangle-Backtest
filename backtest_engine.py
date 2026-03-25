"""
Core pipeline orchestrator for BankNifty Short Strangle Backtest.

Coordinates all modules: data loading → strike selection → signal generation
→ position sizing → analytics. Returns the final trades DataFrame and
all computed statistics.
"""

import logging
from typing import Tuple

import pandas as pd

from data_loader import (
    load_spot_data,
    load_options_data,
    filter_week1_options,
    optimize_dtypes,
    validate_and_clean,
    write_data_quality_report,
)
from config import ENTRY_TIME
from strike_selector import select_strikes
from signal_generator import generate_signals
from position_sizer import calculate_pnl
from performance_analytics import compute_all_analytics

logger = logging.getLogger(__name__)


def run_backtest() -> Tuple[pd.DataFrame, dict, dict]:
    """
    Execute the full backtest pipeline end-to-end.

    Steps:
        1. Load & validate data
        2. Filter Week 1 options universe
        3. Select strikes at 09:20
        4. Generate entry/exit signals and detect SL
        5. Calculate PnL and capital
        6. Compute performance analytics

    Returns:
        Tuple of:
            - trades: Final trades DataFrame with all columns
            - analytics: Dict of all performance metrics
            - quality_stats: Dict of data quality statistics
    """
    # ── Step 1: Load & validate ──────────────────────────────────────────
    spot_df = load_spot_data()
    options_df = load_options_data()
    spot_df, options_df, quality_stats = validate_and_clean(spot_df, options_df)

    # ── Step 2: Filter Week 1 options ────────────────────────────────────
    week1_options = filter_week1_options(options_df)
    week1_options = optimize_dtypes(week1_options)

    # ── Step 3: Strike selection ─────────────────────────────────────────
    selected_ce, selected_pe = select_strikes(week1_options)

    if selected_ce.empty and selected_pe.empty:
        logger.error("No trades generated — no strikes found near target premium")
        raise ValueError("No trades generated")

    # Track days skipped
    all_entry_dates = set(week1_options[week1_options["Time"] == ENTRY_TIME]["Date"].unique())
    ce_dates = set(selected_ce["Date"]) if not selected_ce.empty else set()
    pe_dates = set(selected_pe["Date"]) if not selected_pe.empty else set()
    traded_dates = ce_dates | pe_dates
    quality_stats["days_skipped"] = len(all_entry_dates - traded_dates)

    # ── Step 4: Signal generation & SL detection ─────────────────────────
    trades, sl_stats = generate_signals(selected_ce, selected_pe, week1_options)

    # ── Step 5: Position sizing & PnL ────────────────────────────────────
    trades = calculate_pnl(trades, spot_df)

    # ── Step 6: Performance analytics ────────────────────────────────────
    analytics = compute_all_analytics(trades)

    # ── Write data quality report ────────────────────────────────────────
    trade_stats = {**sl_stats, "days_skipped": quality_stats.get("days_skipped", 0)}
    write_data_quality_report(quality_stats, trade_stats)

    # ── Select and order output columns ──────────────────────────────────
    output_columns = [
        "Ticker", "Option_Type", "EntryDate", "EntryTime", "EntryPrice",
        "ExitDate", "ExitTime", "ExitPrice", "ExitReason",
        "Banknifty_Close", "LotSize", "Quantity",
        "EntryValue", "ExitValue", "GrossPnL",
        "CumulativePnL", "AvailableCapital", "IsExpiryDay", "Strike",
        "NAV", "PnL_Pct",
    ]
    # Only keep columns that exist
    output_columns = [c for c in output_columns if c in trades.columns]
    trades = trades[output_columns].copy()

    return trades, analytics, quality_stats
