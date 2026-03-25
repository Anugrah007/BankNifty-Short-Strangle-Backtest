# BankNifty Short Strangle Backtester

Production-grade backtesting engine for a daily BankNifty short strangle strategy using 1-minute options data.

---

## Strategy Overview

**Short Strangle:** At 09:20 each trading day, sell one CE and one PE option with premium closest to Rs. 50. Each leg has an independent 50% stop loss (SL Price = Entry × 1.50). Normal exit at 15:20. Fixed lot size of 15 units per leg, no compounding.

**PnL Formula (SHORT):** `GrossPnL = (EntryPrice - ExitPrice) × Quantity`

**Stop Loss:** Uses the HIGH column (not Close) because intrabar price can touch SL even if the candle closes below it.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Place data files in parent directory:
#   ../BANKNIFTY_SPOT.csv
#   ../Options_data_2023.csv

# Run backtest
cd banknifty_strangle_backtest
python main.py
```

---

## Project Architecture

```
banknifty_strangle_backtest/
├── config.py                   # All constants — never hardcoded inline
├── data_loader.py              # Data ingestion, validation, dtype optimization
├── strike_selector.py          # Strike selection (vectorized groupby + idxmin)
├── signal_generator.py         # Entry/exit/stoploss engine (vectorized)
├── position_sizer.py           # PnL and capital calculation
├── backtest_engine.py          # Core pipeline orchestrator
├── performance_analytics.py    # All statistical computations
├── report_generator.py         # Excel (3 sheets) + chart generation
├── main.py                     # Entry point with step-by-step timing
├── requirements.txt            # Dependencies
├── .gitignore                  # Excludes CSVs, outputs, __pycache__
└── README.md                   # This file
```

**Data Flow:**
```
CSV Files → data_loader → strike_selector → signal_generator → position_sizer
                                                                      ↓
                    report_generator ← performance_analytics ← backtest_engine
                         ↓
              Excel (3 sheets) + PNG charts + Data Quality Report
```

---

## Data Files (Not Included)

The raw CSV data files are **not included** in this repository due to size constraints and data licensing. To run the backtest, place the following files in the **parent directory** of this project:

| File | Description | Size | Rows |
|------|-------------|------|------|
| `BANKNIFTY_SPOT.csv` | BankNifty index 1-min OHLC | ~5 MB | 136,324 |
| `Options_data_2023.csv` | BankNifty options 1-min OHLC | ~800 MB | 10,266,681 |

**Expected schema — `BANKNIFTY_SPOT.csv`:**
| Column | Example | Description |
|--------|---------|-------------|
| `ts` | `2023-10-20 09:15:00` | Timestamp (YYYY-MM-DD HH:MM:SS) |
| `o` | `44125.50` | Open |
| `h` | `44130.00` | High |
| `l` | `44120.25` | Low |
| `c` | `44128.75` | Close |

**Expected schema — `Options_data_2023.csv`:**
| Column | Example | Description |
|--------|---------|-------------|
| `Date` | `2023-01-02` | Trading date |
| `Ticker` | `BANKNIFTY44000CE` | Option ticker (format: BANKNIFTY{strike}{CE\|PE}) |
| `Time` | `09:20:59` | Bar close time (HH:MM:59 format) |
| `Open` | `52.30` | Open price |
| `High` | `55.10` | High price |
| `Low` | `48.90` | Low price |
| `Close` | `50.05` | Close price |
| `Call/Put` | `CE` | Option type |

> **Note:** The `output/` folder with all generated results (Excel report, charts, data quality report) **is included** so you can review the backtest results without running the code.

---

## Strategy Logic

1. **Data Loading:** Load spot and options CSVs, validate, clean, optimize dtypes. Uses full year of options data (247 days); spot data is only for display.
2. **Strike Selection:** At 09:20, for each day, find CE and PE with close nearest Rs. 50 using `groupby('Date')['diff'].idxmin()`. Zero loops.
3. **Signal Generation:** Entry at 09:20 close. SL = Entry × 1.50. Scan every HIGH bar 09:21–15:20 for SL breach via vectorized merge + boolean mask + groupby min.
4. **Position Sizing:** Fixed 15 units/leg. `GrossPnL = (Entry - Exit) × 15`. Cumulative PnL, capital, NAV (base=100).
5. **Expiry Detection:** Wednesday (weekday=2) in the first 7 days of each month.

---

## Output Description

### Excel Report (3 sheets)
- **Guide:** Strategy overview, parameter table, column definitions, SL explanation
- **Tradesheet:** Formatted trade log with green (profit) / red (loss) / orange (SL) coloring
- **Statistics:** CAGR, Max Drawdown, Win/Loss tables, Monthly P&L, embedded charts

### Charts (300 DPI, dark theme)
- `output/equity_curve.png` — NAV line with drawdown shading
- `output/drawdown.png` — Filled area chart with max DD annotation

### Data Quality Report
- `output/data_quality_report.txt` — Row counts, date ranges, missing bars, SL stats

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Vectorized pandas/numpy** | Zero Python loops — required by assignment, and 100x faster |
| **HIGH for SL detection** | Intrabar price can touch SL even if candle closes below |
| **Independent leg SL** | One leg stopping out doesn't affect the other |
| **No compounding** | Fixed 15 units regardless of capital — assignment spec |
| **NAV base 100** | Standard equity curve indexing for drawdown calculation |
| **float32 optimization** | Halves memory for OHLC columns on 10M+ row dataset |

---

## Skills Demonstrated

- Vectorized pandas/numpy for large-scale financial time series (zero Python loops)
- Options market microstructure (short strangle mechanics, weekly expiry calendar)
- Risk management (independent leg stop loss using intrabar High column)
- Production software architecture (modular, config-driven, fully type-hinted)
- Financial performance analytics (CAGR, Max Drawdown on NAV, Sharpe, Sortino, Calmar)
- Professional reporting (openpyxl Excel with 3 sheets, matplotlib charts at 300 DPI)
- Data quality validation pipeline with anomaly logging
- Memory optimization (float32, category dtypes) for 10M+ row datasets

---

## Potential Improvements

- Add transaction costs / slippage modeling
- Support multiple expiry series (WEEKLY-I through IV)
- Parameterize and optimize target premium via grid search
- Add intraday equity curve (minute-level NAV)
- Implement regime-based position sizing
- Add VIX-based dynamic stop loss
- Multi-asset strangle across Nifty + BankNifty

---

## License

MIT
