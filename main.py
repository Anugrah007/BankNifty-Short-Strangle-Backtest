"""
Entry point for BankNifty Short Strangle Backtester.

Orchestrates the full pipeline with step-by-step timing and console output.
Each step is timed and logged. Total runtime target: < 60 seconds.
"""

import logging
import os
import sys
import time
from contextlib import contextmanager

# ─── Setup logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@contextmanager
def step_timer(step_num: int, description: str):
    """Context manager that prints step name and elapsed time."""
    print(f"  [Step {step_num}] {description:<48}", end="", flush=True)
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    marker = "✓" if elapsed < 30 else "⚠"
    print(f"{elapsed:6.2f}s {marker}")


def main() -> None:
    """Run the full backtest pipeline with step-by-step timing."""
    # Ensure working directory is the project root (where CSVs live)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(script_dir))

    # Import here after chdir so config paths resolve correctly
    from config import EXCEL_FILENAME, EQUITY_CURVE_PNG, DRAWDOWN_PNG, DATA_QUALITY_REPORT, OUTPUT_DIR, ENTRY_TIME
    from data_loader import (
        load_spot_data, load_options_data, filter_week1_options,
        optimize_dtypes, validate_and_clean, write_data_quality_report,
    )
    from strike_selector import select_strikes
    from signal_generator import generate_signals
    from position_sizer import calculate_pnl
    from performance_analytics import compute_all_analytics
    from report_generator import generate_charts, generate_excel_report

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_start = time.perf_counter()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║    BankNifty Short Strangle Backtester — Production Engine  ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # ── Step 1: Load & validate data ─────────────────────────────────────
    with step_timer(1, "Loading & validating data..."):
        spot_df = load_spot_data()
        options_df = load_options_data()
        spot_df, options_df, quality_stats = validate_and_clean(spot_df, options_df)

    # ── Step 2: Filter Week 1 options ────────────────────────────────────
    with step_timer(2, "Filtering Week 1 options universe..."):
        week1_options = filter_week1_options(options_df)
        week1_options = optimize_dtypes(week1_options)

    # ── Step 3: Strike selection ─────────────────────────────────────────
    with step_timer(3, "Strike selection (09:20 module)..."):
        selected_ce, selected_pe = select_strikes(week1_options)
        if selected_ce.empty and selected_pe.empty:
            print("\n  ✗ No trades generated — no strikes found near target premium")
            sys.exit(1)

    # Track days skipped (no CE or PE found near target premium)
    all_entry_dates = set(week1_options[week1_options["Time"] == ENTRY_TIME]["Date"].unique())
    ce_dates = set(selected_ce["Date"]) if not selected_ce.empty else set()
    pe_dates = set(selected_pe["Date"]) if not selected_pe.empty else set()
    quality_stats["days_skipped"] = len(all_entry_dates - (ce_dates | pe_dates))

    # ── Step 4: Signal generation & SL detection ─────────────────────────
    with step_timer(4, "Signal generation & SL detection..."):
        trades, sl_stats = generate_signals(selected_ce, selected_pe, week1_options)

    # ── Step 5: Position sizing & PnL ────────────────────────────────────
    with step_timer(5, "Position sizing & PnL calculation..."):
        trades = calculate_pnl(trades, spot_df)

    # ── Step 6: Performance analytics ────────────────────────────────────
    with step_timer(6, "Performance analytics..."):
        analytics = compute_all_analytics(trades)

    # ── Step 7: Excel report ─────────────────────────────────────────────
    with step_timer(7, "Generating Excel report (3 sheets)..."):
        # Generate charts first so they can be embedded in Excel
        generate_charts(trades, analytics)
        generate_excel_report(trades, analytics)

    # ── Step 8: Charts (already done in step 7, but report timing) ───────
    with step_timer(8, "Writing data quality report..."):
        trade_stats = {**sl_stats, "days_skipped": quality_stats.get("days_skipped", 0)}
        write_data_quality_report(quality_stats, trade_stats)

    # ── Summary ──────────────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - total_start
    print("  ──────────────────────────────────────────────────────────")
    print(f"  Total runtime: {total_elapsed:.2f}s   (Target: < 60s)")
    print(f"  Output Excel : {EXCEL_FILENAME}")
    print(f"  Equity Curve : {EQUITY_CURVE_PNG}")
    print(f"  Drawdown Plot: {DRAWDOWN_PNG}")
    print(f"  Data Quality : {DATA_QUALITY_REPORT}")
    print("╚══════════════════════════════════════════════════════════════╝")

    # ── Print key metrics ────────────────────────────────────────────────
    print()
    print("  KEY RESULTS:")
    print(f"    CAGR:            {analytics['cagr']*100:+.2f}%")
    print(f"    Total Return:    {analytics['total_return_pct']:+.2f}%")
    print(f"    Max Drawdown:    {analytics['max_drawdown_pct']:.2f}%")
    print(f"    Sharpe Ratio:    {analytics['sharpe_ratio']:.4f}")
    print(f"    Sortino Ratio:   {analytics['sortino_ratio']:.4f}")
    print(f"    Calmar Ratio:    {analytics['calmar_ratio']:.4f}")
    print(f"    Trading Days:    {analytics['total_trading_days']}")
    print(f"    Total Legs:      {analytics['total_legs_traded']}")
    print(f"    Final Capital:   Rs. {analytics['final_capital']:,.2f}")
    print()


if __name__ == "__main__":
    main()
