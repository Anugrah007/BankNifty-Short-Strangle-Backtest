"""
Configuration constants for BankNifty Short Strangle Backtester.

All strategy parameters, paths, and magic numbers live here.
Nothing is hardcoded inline in any other module.
"""

# ─── Strategy Parameters ────────────────────────────────────────────────────
ENTRY_TIME: str = "09:20:59"        # 1-min bar close time for entry (options data format)
EXIT_TIME: str = "15:20:59"         # 1-min bar close time for normal exit
SPOT_ENTRY_TIME: str = "09:20:00"   # Spot data uses HH:MM:00 format
SPOT_EXIT_TIME: str = "15:20:00"

TARGET_PREMIUM: float = 50.0        # Rs. target premium for strike selection
STOP_LOSS_PCT: float = 0.50         # 50% stop loss above entry price per leg
SL_MULTIPLIER: float = 1.0 + STOP_LOSS_PCT  # = 1.50

LOT_SIZE: int = 15                  # BankNifty lot size
NUM_LOTS: int = 1                   # Fixed lots per day per leg
QUANTITY: int = LOT_SIZE * NUM_LOTS  # = 15 units per leg

# ─── Capital ────────────────────────────────────────────────────────────────
INITIAL_CAPITAL: float = 100_000.0  # Starting capital in Rs.
BASE_NAV: float = 100.0             # Equity curve base index value

# ─── Expiry Logic ───────────────────────────────────────────────────────────
EXPIRY_WEEKDAY: int = 2             # Wednesday = 2 (Monday=0 ... Sunday=6)
# No WEEKLY-I identifier in this dataset — tickers are plain BANKNIFTY{strike}{CE|PE}
# All options in the dataset are treated as tradeable weekly options
WEEK1_IDENTIFIER: str = ""          # Empty — no weekly prefix filtering needed

# ─── Ticker Parsing ────────────────────────────────────────────────────────
# Tickers are formatted as: BANKNIFTY{strike}{CE|PE}
# e.g. BANKNIFTY43800CE → strike=43800, option_type=CE
TICKER_PREFIX: str = "BANKNIFTY"
TICKER_PATTERN: str = r"BANKNIFTY(\d+)(CE|PE)"

# ─── Output Paths ──────────────────────────────────────────────────────────
OUTPUT_DIR: str = "output"
EXCEL_FILENAME: str = "output/backtest_results.xlsx"
EQUITY_CURVE_PNG: str = "output/equity_curve.png"
DRAWDOWN_PNG: str = "output/drawdown.png"
DATA_QUALITY_REPORT: str = "output/data_quality_report.txt"

# ─── Data Files ─────────────────────────────────────────────────────────────
SPOT_CSV: str = "BANKNIFTY_SPOT.csv"
OPTIONS_CSV: str = "Options_data_2023.csv"

# ─── Annualization ──────────────────────────────────────────────────────────
TRADING_DAYS_PER_YEAR: int = 252
