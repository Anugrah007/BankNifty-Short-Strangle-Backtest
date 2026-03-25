"""
Data ingestion, validation, and dtype optimization for BankNifty backtest.

Loads spot and options CSVs, renames columns to canonical names, extracts
strike/option-type from ticker strings, optimizes dtypes for memory, and
filters to the overlapping date range. Generates a data quality report.
"""

import logging
import re
from typing import Tuple

import numpy as np
import pandas as pd

from config import (
    SPOT_CSV,
    OPTIONS_CSV,
    ENTRY_TIME,
    EXIT_TIME,
    TICKER_PATTERN,
    WEEK1_IDENTIFIER,
    DATA_QUALITY_REPORT,
)

logger = logging.getLogger(__name__)


def load_spot_data(path: str = SPOT_CSV) -> pd.DataFrame:
    """
    Load BankNifty spot 1-minute OHLC data.

    The raw CSV has columns: ts, o, h, l, c (plus an unnamed index col).
    We rename to canonical names and split ts into Date + Time.

    Args:
        path: Path to the spot CSV file.

    Returns:
        DataFrame with columns: Date, Time, Open, High, Low, Close.
    """
    df = pd.read_csv(path, usecols=["ts", "o", "h", "l", "c"])
    df.rename(columns={"ts": "DateTime", "o": "Open", "h": "High", "l": "Low", "c": "Close"}, inplace=True)

    # Split combined timestamp into Date and Time strings
    df["Date"] = df["DateTime"].str[:10]
    df["Time"] = df["DateTime"].str[11:]
    df.drop(columns=["DateTime"], inplace=True)

    # Optimize numeric dtypes — batch conversion via dict comprehension
    df = df.astype({c: "float32" for c in ["Open", "High", "Low", "Close"]})

    logger.info("Spot data loaded: %d rows, date range %s to %s", len(df), df["Date"].iloc[0], df["Date"].iloc[-1])
    return df


def load_options_data(path: str = OPTIONS_CSV) -> pd.DataFrame:
    """
    Load BankNifty options 1-minute OHLC data.

    Parses strike and option type from ticker strings (e.g. BANKNIFTY43800CE).
    Applies dtype optimizations for memory efficiency.

    Args:
        path: Path to the options CSV file.

    Returns:
        DataFrame with columns: Date, Ticker, Time, Open, High, Low, Close,
        OptionType, Strike.
    """
    df = pd.read_csv(path, usecols=["Date", "Ticker", "Time", "Open", "High", "Low", "Close", "Call/Put"])
    df.rename(columns={"Call/Put": "OptionType"}, inplace=True)

    # Extract numeric strike from ticker (e.g. BANKNIFTY43800CE → 43800)
    strikes = df["Ticker"].str.extract(TICKER_PATTERN, expand=True)
    df["Strike"] = strikes[0].astype("int32")
    # OptionType already comes from Call/Put column, but verify consistency
    # strikes[1] would be CE/PE from ticker — we trust the Call/Put column

    logger.info(
        "Options data loaded: %d rows, %d unique tickers, date range %s to %s",
        len(df), df["Ticker"].nunique(), df["Date"].iloc[0], df["Date"].iloc[-1],
    )
    return df


def filter_week1_options(options_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to Week 1 weekly options only.

    In this dataset there is no WEEKLY-I prefix — all tickers are plain
    BANKNIFTY{strike}{CE|PE}. So we return the full dataset. If the data
    had a WEEKLY-I identifier, we would filter on it here.

    Args:
        options_df: Raw options DataFrame.

    Returns:
        Filtered DataFrame (unchanged in this dataset).
    """
    if WEEK1_IDENTIFIER:
        filtered = options_df[options_df["Ticker"].str.contains(WEEK1_IDENTIFIER, regex=False)].copy()
        logger.info("Filtered to Week 1 options: %d rows (from %d)", len(filtered), len(options_df))
        return filtered
    else:
        logger.info("No WEEKLY identifier — using all %d option rows as Week 1", len(options_df))
        return options_df.copy()


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast numeric columns and categorize strings to reduce memory.

    Args:
        df: Options DataFrame.

    Returns:
        Same DataFrame with optimized dtypes.
    """
    # Batch dtype conversion — no loops
    ohlc_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    if ohlc_cols:
        df = df.astype({c: "float32" for c in ohlc_cols})
    if "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype("category")
    if "OptionType" in df.columns:
        df["OptionType"] = df["OptionType"].astype("category")

    return df


def validate_and_clean(
    spot_df: pd.DataFrame, options_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Validate data quality, drop bad rows, restrict to overlapping dates.

    Generates quality metrics dict used later for the data quality report.

    Args:
        spot_df: Loaded spot DataFrame.
        options_df: Loaded options DataFrame.

    Returns:
        Tuple of (cleaned_spot, cleaned_options, quality_stats dict).
    """
    stats: dict = {}
    stats["spot_total_rows"] = len(spot_df)
    stats["options_total_rows"] = len(options_df)

    # Date ranges
    stats["spot_date_range"] = (spot_df["Date"].min(), spot_df["Date"].max())
    stats["options_date_range"] = (options_df["Date"].min(), options_df["Date"].max())

    # Unique trading days
    spot_dates = set(spot_df["Date"].unique())
    opt_dates = set(options_df["Date"].unique())
    stats["spot_trading_days"] = len(spot_dates)
    stats["options_trading_days"] = len(opt_dates)

    # Overlap
    overlap_dates = sorted(spot_dates & opt_dates)
    stats["overlap_trading_days"] = len(overlap_dates)
    if overlap_dates:
        stats["overlap_range"] = (overlap_dates[0], overlap_dates[-1])
    else:
        stats["overlap_range"] = ("N/A", "N/A")

    stats["unique_option_tickers"] = options_df["Ticker"].nunique()

    # Drop nulls
    spot_nulls = spot_df.isnull().any(axis=1).sum()
    opt_nulls = options_df.isnull().any(axis=1).sum()
    spot_df = spot_df.dropna()
    options_df = options_df.dropna()
    stats["spot_nulls_dropped"] = int(spot_nulls)
    stats["options_nulls_dropped"] = int(opt_nulls)

    # Drop zero-price rows in options
    zero_mask = (options_df["Close"] <= 0) | (options_df["Open"] <= 0)
    stats["zero_price_rows_dropped"] = int(zero_mask.sum())
    options_df = options_df[~zero_mask]

    # Drop duplicates
    spot_dups = spot_df.duplicated().sum()
    opt_dups = options_df.duplicated().sum()
    spot_df = spot_df.drop_duplicates()
    options_df = options_df.drop_duplicates()
    stats["spot_duplicates_dropped"] = int(spot_dups)
    stats["options_duplicates_dropped"] = int(opt_dups)

    # Use ALL options dates (full year) — spot is only for display/reporting
    # Spot data is left-joined later; missing spot dates get NaN Banknifty_Close
    all_trading_dates = sorted(opt_dates)
    stats["trading_dates_used"] = len(all_trading_dates)
    stats["spot_coverage_dates"] = len(overlap_dates)
    # Only restrict spot to overlap (for efficient merge), but do NOT restrict options
    spot_df = spot_df[spot_df["Date"].isin(overlap_dates)].copy()

    # Check for missing entry/exit bars
    entry_dates = set(options_df[options_df["Time"] == ENTRY_TIME]["Date"].unique())
    exit_dates = set(options_df[options_df["Time"] == EXIT_TIME]["Date"].unique())
    all_dates = set(options_df["Date"].unique())
    stats["missing_entry_bar_dates"] = sorted(all_dates - entry_dates)
    stats["missing_exit_bar_dates"] = sorted(all_dates - exit_dates)

    if stats["missing_entry_bar_dates"]:
        logger.warning("Missing 09:20 entry bars on %d dates — those days will be skipped", len(stats["missing_entry_bar_dates"]))
    if stats["missing_exit_bar_dates"]:
        logger.warning("Missing 15:20 exit bars on %d dates — will use last available bar", len(stats["missing_exit_bar_dates"]))

    logger.info(
        "Validation complete: %d options trading days (%d with spot coverage), %d spot rows, %d options rows",
        len(all_trading_dates), len(overlap_dates), len(spot_df), len(options_df),
    )
    return spot_df, options_df, stats


def write_data_quality_report(stats: dict, trade_stats: dict = None) -> None:
    """
    Write a human-readable data quality report to disk.

    Args:
        stats: Quality stats from validate_and_clean.
        trade_stats: Optional trade-level stats (SL hits etc.) added after backtest.
    """
    lines = [
        "=" * 60,
        "DATA QUALITY REPORT — BankNifty Short Strangle Backtest",
        "=" * 60,
        "",
        f"Spot data rows loaded:         {stats['spot_total_rows']:,}",
        f"Options data rows loaded:      {stats['options_total_rows']:,}",
        "",
        f"Spot date range:               {stats['spot_date_range'][0]} to {stats['spot_date_range'][1]}",
        f"Options date range:            {stats['options_date_range'][0]} to {stats['options_date_range'][1]}",
        f"Overlapping date range:        {stats['overlap_range'][0]} to {stats['overlap_range'][1]}",
        "",
        f"Spot trading days:             {stats['spot_trading_days']}",
        f"Options trading days:          {stats['options_trading_days']}",
        f"Trading days used (backtest):  {stats.get('trading_dates_used', stats['options_trading_days'])}",
        f"Days with spot coverage:       {stats.get('spot_coverage_dates', stats['overlap_trading_days'])}",
        f"Overlapping trading days:      {stats['overlap_trading_days']}",
        "",
        f"Unique option tickers (raw):   {stats['unique_option_tickers']}",
        "",
        f"Null rows dropped (spot):      {stats['spot_nulls_dropped']}",
        f"Null rows dropped (options):   {stats['options_nulls_dropped']}",
        f"Zero-price rows dropped:       {stats['zero_price_rows_dropped']}",
        f"Duplicate rows dropped (spot): {stats['spot_duplicates_dropped']}",
        f"Duplicate rows dropped (opts): {stats['options_duplicates_dropped']}",
        "",
        f"Missing 09:20 entry bars:      {len(stats['missing_entry_bar_dates'])} dates",
        f"Missing 15:20 exit bars:       {len(stats['missing_exit_bar_dates'])} dates",
    ]

    if trade_stats:
        lines += [
            "",
            "-" * 60,
            "TRADE-LEVEL STATISTICS",
            "-" * 60,
            f"Days skipped (no CE/PE):       {trade_stats.get('days_skipped', 0)}",
            f"CE legs hit SL:                {trade_stats.get('ce_sl_hits', 0)}",
            f"PE legs hit SL:                {trade_stats.get('pe_sl_hits', 0)}",
            f"Both legs hit SL same day:     {trade_stats.get('both_sl_hits', 0)}",
        ]

    lines.append("")
    lines.append("=" * 60)

    with open(DATA_QUALITY_REPORT, "w") as f:
        f.write("\n".join(lines))

    logger.info("Data quality report written to %s", DATA_QUALITY_REPORT)
