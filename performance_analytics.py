"""
Statistical performance analytics for BankNifty Short Strangle Backtest.

Computes all 8 assignment-required metrics plus bonus ratios:
1. CAGR
2. Max Drawdown (on NAV equity curve)
3. Winners / Losers / Win% / Loss% by CE, PE, Combined
4. (same table)
5. Average % P&L by CE/PE/Combined × Expiry/Non-Expiry
6. Equity Curve (NAV series)
7. Monthly % P&L table
8. Drawdown series (for plotting)

Bonus: Sharpe, Sortino, Calmar, SL stats, avg premium, max profit/loss.
"""

import logging

import numpy as np
import pandas as pd

from config import INITIAL_CAPITAL, BASE_NAV, TRADING_DAYS_PER_YEAR

logger = logging.getLogger(__name__)


def compute_cagr(trades: pd.DataFrame) -> float:
    """
    Compute Compound Annual Growth Rate from first to last trade date.

    CAGR = (FinalCapital / InitialCapital) ^ (365 / calendar_days) - 1

    Args:
        trades: Trades DataFrame with EntryDate_dt and AvailableCapital.

    Returns:
        CAGR as a decimal (e.g. 0.15 = 15%).
    """
    if "EntryDate_dt" not in trades.columns:
        trades = trades.copy()
        trades["EntryDate_dt"] = pd.to_datetime(trades["EntryDate"])

    total_days = (trades["EntryDate_dt"].max() - trades["EntryDate_dt"].min()).days
    if total_days <= 0:
        return 0.0

    final_capital = INITIAL_CAPITAL + trades["GrossPnL"].sum()
    cagr = (final_capital / INITIAL_CAPITAL) ** (365.0 / total_days) - 1
    return cagr


def compute_drawdown(trades: pd.DataFrame) -> dict:
    """
    Compute max drawdown on the NAV equity curve.

    Steps (as specified in assignment):
    1. Build trade-wise NAV series (base = 100)
    2. Rolling peak = cummax of NAV
    3. Drawdown at each point = (NAV - peak) / peak × 100
    4. Max drawdown = worst (most negative) value

    Args:
        trades: Trades DataFrame with NAV column.

    Returns:
        Dict with max_drawdown_pct, max_drawdown_date, drawdown_series, nav_series.
    """
    nav = trades["NAV"].values.copy()
    rolling_peak = pd.Series(nav).cummax().values

    # Drawdown at each trade = % decline from peak (negative values)
    drawdown_series = (nav - rolling_peak) / rolling_peak * 100

    max_dd_idx = np.argmin(drawdown_series)
    max_dd_pct = drawdown_series[max_dd_idx]
    max_dd_date = trades.iloc[max_dd_idx]["EntryDate"] if max_dd_idx < len(trades) else "N/A"

    return {
        "max_drawdown_pct": float(max_dd_pct),
        "max_drawdown_date": max_dd_date,
        "drawdown_series": drawdown_series,
        "nav_series": nav,
        "rolling_peak": rolling_peak,
    }


def compute_win_loss_stats(trades: pd.DataFrame) -> dict:
    """
    Compute winners, losers, win%, loss% for CE, PE, and Combined.

    Fully vectorized: uses groupby + aggregation, no Python loops over rows.

    Args:
        trades: Trades DataFrame with GrossPnL and Option_Type.

    Returns:
        Dict keyed by 'CE', 'PE', 'Combined' with sub-dicts of stats.
    """
    # Vectorized: compute win/loss flags once
    is_winner = trades["GrossPnL"] > 0

    # Per-option-type stats via groupby
    grouped = trades.groupby("Option_Type")["GrossPnL"]
    winners_by_type = trades[is_winner].groupby("Option_Type")["GrossPnL"].count()
    totals_by_type = grouped.count()

    results = {}
    # CE stats
    ce_total = int(totals_by_type.get("CE", 0))
    ce_winners = int(winners_by_type.get("CE", 0))
    ce_losers = ce_total - ce_winners
    results["CE"] = {
        "winners": ce_winners, "losers": ce_losers, "total": ce_total,
        "win_pct": ce_winners / ce_total * 100 if ce_total > 0 else 0.0,
        "loss_pct": ce_losers / ce_total * 100 if ce_total > 0 else 0.0,
    }

    # PE stats
    pe_total = int(totals_by_type.get("PE", 0))
    pe_winners = int(winners_by_type.get("PE", 0))
    pe_losers = pe_total - pe_winners
    results["PE"] = {
        "winners": pe_winners, "losers": pe_losers, "total": pe_total,
        "win_pct": pe_winners / pe_total * 100 if pe_total > 0 else 0.0,
        "loss_pct": pe_losers / pe_total * 100 if pe_total > 0 else 0.0,
    }

    # Combined stats
    combined_total = len(trades)
    combined_winners = int(is_winner.sum())
    combined_losers = combined_total - combined_winners
    results["Combined"] = {
        "winners": combined_winners, "losers": combined_losers, "total": combined_total,
        "win_pct": combined_winners / combined_total * 100 if combined_total > 0 else 0.0,
        "loss_pct": combined_losers / combined_total * 100 if combined_total > 0 else 0.0,
    }

    return results


def compute_avg_pnl_by_expiry(trades: pd.DataFrame) -> dict:
    """
    Compute average % P&L for CE/PE/Combined on Expiry vs Non-Expiry days.

    Vectorized: uses groupby on (Option_Type, IsExpiryDay), then reads results.

    Args:
        trades: Trades DataFrame with PnL_Pct, Option_Type, IsExpiryDay.

    Returns:
        Dict keyed by '{type}_{expiry_flag}' with average PnL %.
    """
    # Vectorized groupby: average PnL_Pct by (Option_Type, IsExpiryDay)
    avg_by_group = trades.groupby(["Option_Type", "IsExpiryDay"])["PnL_Pct"].mean()
    # Combined (all types): average PnL_Pct by IsExpiryDay only
    avg_combined = trades.groupby("IsExpiryDay")["PnL_Pct"].mean()

    expiry_labels = {True: "Expiry", False: "NonExpiry"}
    results = {}

    # CE and PE breakdowns
    results["CE_Expiry"] = float(avg_by_group.get(("CE", True), 0.0))
    results["CE_NonExpiry"] = float(avg_by_group.get(("CE", False), 0.0))
    results["PE_Expiry"] = float(avg_by_group.get(("PE", True), 0.0))
    results["PE_NonExpiry"] = float(avg_by_group.get(("PE", False), 0.0))
    results["Combined_Expiry"] = float(avg_combined.get(True, 0.0))
    results["Combined_NonExpiry"] = float(avg_combined.get(False, 0.0))

    return results


def compute_monthly_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly P&L table using end-of-month NAV values.

    Vectorized: uses groupby + shift on the monthly end-NAV series.
    For the first month: (end_nav - BASE_NAV) / BASE_NAV × 100
    For subsequent months: (end_nav - prev_end_nav) / prev_end_nav × 100

    Args:
        trades: Trades DataFrame with EntryDate_dt and NAV.

    Returns:
        DataFrame with columns: Month, StartNAV, EndNAV, PctPnL, AbsPnL.
    """
    if "EntryDate_dt" not in trades.columns:
        trades = trades.copy()
        trades["EntryDate_dt"] = pd.to_datetime(trades["EntryDate"])

    trades_copy = trades.copy()
    trades_copy["YearMonth"] = trades_copy["EntryDate_dt"].dt.to_period("M")

    # End-of-month NAV via groupby (vectorized)
    monthly_end_nav = trades_copy.groupby("YearMonth")["NAV"].last()

    # Start NAV: previous month's end NAV, shifted by 1; first month uses BASE_NAV
    start_nav = monthly_end_nav.shift(1).fillna(BASE_NAV)

    # Vectorized percentage and absolute P&L
    pct_pnl = (monthly_end_nav - start_nav) / start_nav * 100
    # Absolute P&L in Rs. = NAV change converted back to capital terms
    abs_pnl = (monthly_end_nav - start_nav) / BASE_NAV * INITIAL_CAPITAL

    # Build result DataFrame — all vectorized, no row-by-row loop
    result = pd.DataFrame({
        "Month": monthly_end_nav.index.astype(str),
        "StartNAV": start_nav.round(2).values,
        "EndNAV": monthly_end_nav.round(2).values,
        "PctPnL": pct_pnl.round(2).values,
        "AbsPnL": abs_pnl.round(2).values,
    })

    return result


def compute_bonus_metrics(trades: pd.DataFrame, cagr: float, max_dd_pct: float) -> dict:
    """
    Compute bonus production metrics: Sharpe, Sortino, Calmar, etc.

    Args:
        trades: Trades DataFrame.
        cagr: Pre-computed CAGR.
        max_dd_pct: Pre-computed max drawdown percentage (negative).

    Returns:
        Dict of bonus metrics.
    """
    if "EntryDate_dt" not in trades.columns:
        trades = trades.copy()
        trades["EntryDate_dt"] = pd.to_datetime(trades["EntryDate"])

    # Daily PnL (sum of both legs per day)
    daily_pnl = trades.groupby("EntryDate")["GrossPnL"].sum()

    mean_daily = daily_pnl.mean()
    std_daily = daily_pnl.std()
    downside = daily_pnl[daily_pnl < 0]
    std_downside = downside.std() if len(downside) > 0 else 1.0

    sharpe = (mean_daily / std_daily) * np.sqrt(TRADING_DAYS_PER_YEAR) if std_daily > 0 else 0.0
    sortino = (mean_daily / std_downside) * np.sqrt(TRADING_DAYS_PER_YEAR) if std_downside > 0 else 0.0
    calmar = cagr / abs(max_dd_pct / 100) if max_dd_pct != 0 else 0.0

    sl_trades = trades[trades["ExitReason"] == "StopLoss"]

    return {
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "total_sl_hits": len(sl_trades),
        "ce_sl_hits": int((sl_trades["Option_Type"] == "CE").sum()),
        "pe_sl_hits": int((sl_trades["Option_Type"] == "PE").sum()),
        "avg_premium_collected": round(trades["EntryPrice"].mean(), 2),
        "max_single_profit": round(trades["GrossPnL"].max(), 2),
        "max_single_loss": round(trades["GrossPnL"].min(), 2),
        "total_trading_days": trades["EntryDate"].nunique(),
        "total_legs_traded": len(trades),
        "mean_daily_pnl": round(mean_daily, 2),
        "avg_trade_pnl": round(trades["GrossPnL"].mean(), 2),
    }


def compute_all_analytics(trades: pd.DataFrame) -> dict:
    """
    Master function: compute all performance analytics in one call.

    Args:
        trades: Final trades DataFrame.

    Returns:
        Dict containing all metrics, sub-dicts, and series.
    """
    cagr = compute_cagr(trades)
    dd = compute_drawdown(trades)
    win_loss = compute_win_loss_stats(trades)
    avg_pnl_expiry = compute_avg_pnl_by_expiry(trades)
    monthly_pnl = compute_monthly_pnl(trades)
    bonus = compute_bonus_metrics(trades, cagr, dd["max_drawdown_pct"])

    final_capital = INITIAL_CAPITAL + trades["GrossPnL"].sum()
    total_return_pct = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    analytics = {
        "cagr": cagr,
        "total_return_pct": total_return_pct,
        "final_capital": final_capital,
        "max_drawdown_pct": dd["max_drawdown_pct"],
        "max_drawdown_date": dd["max_drawdown_date"],
        "drawdown_series": dd["drawdown_series"],
        "nav_series": dd["nav_series"],
        "rolling_peak": dd["rolling_peak"],
        "win_loss": win_loss,
        "avg_pnl_expiry": avg_pnl_expiry,
        "monthly_pnl": monthly_pnl,
        **bonus,
    }

    logger.info(
        "Analytics: CAGR=%.2f%%, MaxDD=%.2f%%, Sharpe=%.2f, Total Return=%.2f%%",
        cagr * 100, dd["max_drawdown_pct"], bonus["sharpe_ratio"], total_return_pct,
    )

    return analytics
