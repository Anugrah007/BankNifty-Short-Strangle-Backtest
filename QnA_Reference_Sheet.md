# BankNifty Short Strangle Backtest — Q&A Reference Sheet

> All answers below are derived from the actual backtest output.
> Data period: **2023-01-02 to 2024-01-02** (247 trading days — full year of options data).

---

## 1. What is the strategy?

A **daily short strangle** on BankNifty index options.
- At **09:20** each trading day, we **sell (short)** one CE and one PE option whose premium is closest to **Rs. 50**.
- Each leg has an **independent 50% stop loss** — SL Price = EntryPrice × 1.50.
- Normal exit at **15:20** (end of day).
- Fixed position: **15 units per leg** (1 lot × 15 lot size). No compounding.
- Initial capital: **Rs. 1,00,000**.

**PnL Formula (SHORT):**
```
GrossPnL = (EntryPrice − ExitPrice) × 15
```
We profit when the option premium decays (ExitPrice < EntryPrice).

---

## 2. What data was used?

| Item | Detail |
|------|--------|
| Spot file | `BANKNIFTY_SPOT.csv` — 1,36,324 rows |
| Options file | `Options_data_2023.csv` — 1,02,66,681 rows |
| Spot date range | 2023-10-20 to 2025-04-09 (364 unique days) |
| Options date range | 2023-01-02 to 2024-01-02 (247 trading days) |
| **Backtest period** | **2023-01-02 to 2024-01-02 (247 trading days — full year)** |
| Days with spot coverage | 49 (overlap period: Oct 2023 – Jan 2024) |
| Unique option tickers | 322 |
| Duplicate rows dropped | 14,546 |
| Ticker format | `BANKNIFTY{strike}{CE/PE}` (e.g. `BANKNIFTY44500CE`) |
| Time format (options) | `HH:MM:59` (e.g. `09:20:59`) |
| Time format (spot) | `HH:MM:00` (e.g. `09:20:00`) |

> **Note:** The dataset does not contain a `WEEKLY-I` prefix. All options tickers are plain `BANKNIFTY{strike}{CE|PE}`, so all options were treated as tradeable.
>
> **Note on spot data:** Spot data is used **only** for the `Banknifty_Close` display column in the tradesheet — it has zero impact on strategy logic (strike selection, entry, exit, stop loss, PnL). All strategy decisions use options prices exclusively. Therefore the backtest runs on the full year of options data; the Banknifty_Close column is populated where spot data overlaps (49 days) and is NaN elsewhere.

---

## 3. What is the CAGR?

**CAGR = +7.73%**

```
Calendar days = (2024-01-02 − 2023-01-02) = 365 days
Final Capital = Rs. 1,07,725.37
CAGR = (1,07,725.37 / 1,00,000) ^ (365/365) − 1 = 7.73%
```

Since the backtest spans exactly ~1 year, CAGR ≈ Total Return.

---

## 4. What is the Maximum Drawdown?

**Max Drawdown = −4.32%**

Calculated on the **NAV equity curve** (base = 100):
1. Rolling peak = cumulative maximum of NAV at each point
2. Drawdown = (NAV − rolling_peak) / rolling_peak × 100
3. Max DD = worst (most negative) value across the series

Even if the portfolio later recovered, the max drawdown remains −4.32% as it is a **historical worst** measure.

---

## 5. What are the Win/Loss statistics?

| Group | Winners | Losers | Total Trades | Win % | Loss % |
|-------|--------:|-------:|-------------:|------:|-------:|
| **CE** | 122 | 125 | 247 | 49.4% | 50.6% |
| **PE** | 122 | 125 | 247 | 49.4% | 50.6% |
| **Combined** | 244 | 250 | 494 | 49.4% | 50.6% |

> A trade with GrossPnL > 0 is a winner; GrossPnL ≤ 0 is a loser.
> Despite a sub-50% win rate, the strategy is profitable because winning trades earn more on average than losing trades lose.

---

## 6. What is the Average % P&L on Expiry vs Non-Expiry days?

| Category | Avg % PnL |
|----------|----------:|
| CE — Expiry Day | +27.23% |
| CE — Non-Expiry | +0.57% |
| PE — Expiry Day | −0.35% |
| PE — Non-Expiry | +1.01% |
| Combined — Expiry | +13.44% |
| Combined — Non-Expiry | +0.79% |

> **Expiry Day** = Wednesday falling in the first 7 days of a month (week 1 expiry).
> In the full year, there were **12 expiry days** (24 trade legs).

**Interpretation:** CE legs perform significantly better on expiry days (accelerated time decay), while PE legs are approximately flat. On non-expiry days, both legs show a small positive edge.

---

## 7. What does the Equity Curve (NAV) look like?

**Starting NAV = 100.00 | Final NAV = 107.73**

The equity curve chart is saved at `output/equity_curve.png` (300 DPI, dark theme). The NAV progresses from 100 to ~107.73 over the year with a visible drawdown in Jan–Feb 2023 before recovering and trending upward through the rest of the year.

---

## 8. What is the Monthly P&L?

| Month | Start NAV | End NAV | % P&L | Abs P&L (Rs.) |
|-------|----------:|--------:|------:|--------------:|
| 2023-01 | 100.00 | 98.40 | −1.60% | −1,600.87 |
| 2023-02 | 98.40 | 97.20 | −1.22% | −1,201.87 |
| 2023-03 | 97.20 | 99.49 | +2.36% | +2,294.25 |
| 2023-04 | 99.49 | 100.58 | +1.09% | +1,087.87 |
| 2023-05 | 100.58 | 103.65 | +3.05% | +3,069.38 |
| 2023-06 | 103.65 | 105.43 | +1.72% | +1,783.87 |
| 2023-07 | 105.43 | 105.90 | +0.44% | +466.87 |
| 2023-08 | 105.90 | 104.48 | −1.34% | −1,414.88 |
| 2023-09 | 104.48 | 104.47 | −0.02% | −18.75 |
| 2023-10 | 104.47 | 105.82 | +1.29% | +1,351.50 |
| 2023-11 | 105.82 | 107.19 | +1.30% | +1,371.75 |
| 2023-12 | 107.19 | 107.54 | +0.33% | +354.75 |
| 2024-01 | 107.54 | 107.73 | +0.17% | +181.50 |

> First month uses BASE_NAV (100) as start. Subsequent months use previous month's end NAV.
> **9 profitable months, 4 losing months.** Largest gain: May (+3.05%). Largest loss: Jan (−1.60%).

---

## 9. What does the Drawdown chart show?

The drawdown chart (`output/drawdown.png`) shows the percentage decline from the rolling peak NAV at each trade point.

- **Max drawdown: −4.32%** occurred in early 2023
- The strategy experienced its deepest drawdown in Jan–Feb 2023 before recovering in March
- After May 2023, drawdowns were relatively shallow
- The chart is a red filled area going downward, with the max DD annotated with a yellow dashed line

---

## 10. What are the risk-adjusted return ratios?

| Metric | Value | Interpretation |
|--------|------:|----------------|
| **Sharpe Ratio** | 1.1382 | Acceptable risk-adjusted return (>1 is good) |
| **Sortino Ratio** | 1.5843 | Good downside risk-adjusted return |
| **Calmar Ratio** | 1.7880 | Solid return per unit of max drawdown |

**Formulas:**
```
Sharpe  = (mean_daily_pnl / std_daily_pnl) × √252
Sortino = (mean_daily_pnl / std_downside_pnl) × √252
Calmar  = CAGR / |Max Drawdown %|
```

---

## 11. How does the Stop Loss mechanism work?

| Parameter | Value |
|-----------|-------|
| SL Price | EntryPrice × 1.50 (50% above entry) |
| Monitoring | Every 1-min **HIGH** bar from 09:21 to 15:20 |
| SL Exit Price | Exactly EntryPrice × 1.50 (assumed fill at SL level) |
| Leg independence | Each leg checked independently — one hitting SL does NOT affect the other |

**Why HIGH column, not Close?**
Because the intrabar price can touch the SL level even if the candle closes below it. Using Close would underestimate SL frequency and artificially inflate strategy performance.

**SL Statistics:**

| Metric | Count |
|--------|------:|
| Total legs stopped out | 245 / 494 (49.6%) |
| CE legs hit SL | 122 |
| PE legs hit SL | 123 |
| Days where BOTH legs hit SL | 41 |

---

## 12. How is the Expiry Day identified?

```
IsExpiryDay = (weekday == Wednesday) AND (day of month ≤ 7)
```

- Wednesday = weekday index 2 (Monday=0)
- First 7 days of a month = week 1
- In our full-year sample: **12 expiry days** were identified (24 trade legs)

---

## 13. What are the position sizing rules?

| Parameter | Value |
|-----------|-------|
| Lot Size | 15 |
| Number of Lots | 1 |
| Quantity per leg | 15 (= 15 × 1) |
| Compounding | **NONE** — quantity stays 15 every day regardless of P&L |
| Capital tracking | Available Capital = Initial Capital + Cumulative PnL |

---

## 14. What are the additional production statistics?

| Metric | Value |
|--------|------:|
| Total Trading Days | 247 |
| Total Legs Traded | 494 |
| Avg Premium Collected per leg | Rs. 49.40 |
| Mean Daily PnL (both legs) | Rs. 31.28 |
| Avg Trade PnL (per leg) | Rs. 15.64 |
| Max Single Trade Profit | Rs. 968.25 |
| Max Single Trade Loss | Rs. −459.75 |
| Initial Capital | Rs. 1,00,000 |
| Final Capital | Rs. 1,07,725.37 |
| Total P&L | Rs. 7,725.37 |

---

## 15. What is the strike selection logic?

At 09:20 each day:
1. Look at the 1-min CLOSE price of all available options
2. For CE: pick the strike whose close is **closest to Rs. 50** (tie → lower strike)
3. For PE: pick the strike whose close is **closest to Rs. 50** (tie → higher strike)
4. These are the strikes we SHORT (sell to open)

**Vectorized implementation** — zero Python loops:
```python
entry_bars['diff_from_target'] = (entry_bars['Close'] - 50).abs()
ce_idx = ce_bars.groupby('Date')['diff_from_target'].idxmin()
pe_idx = pe_bars.groupby('Date')['diff_from_target'].idxmin()
```

---

## 16. Sample trades from the tradesheet

| Ticker | Type | Date | Entry | Exit Time | Exit Price | Reason | PnL (Rs.) |
|--------|------|------|------:|----------:|-----------:|--------|----------:|
| BANKNIFTY44500CE | CE | 2023-10-20 | 50.30 | 15:20:59 | 44.25 | Regular | +90.75 |
| BANKNIFTY42900PE | PE | 2023-10-20 | 50.40 | 15:20:59 | 45.55 | Regular | +72.75 |
| BANKNIFTY44400CE | CE | 2023-10-23 | 44.80 | 15:20:59 | 11.90 | Regular | +493.50 |
| BANKNIFTY43200PE | PE | 2023-10-23 | 53.45 | 10:13:59 | 80.18 | StopLoss | −400.88 |
| BANKNIFTY43700CE | CE | 2023-10-25 | 48.95 | 15:20:59 | 8.40 | Regular | +608.25 |
| BANKNIFTY42900PE | PE | 2023-10-25 | 49.00 | 09:25:59 | 73.50 | StopLoss | −367.50 |

---

## 17. How was vectorization (zero loops) achieved?

The assignment explicitly forbids Python loops. Every operation uses vectorized pandas/numpy:

| Operation | Technique Used |
|-----------|----------------|
| Strike selection | `groupby('Date')['diff'].idxmin()` |
| SL detection | `merge` + boolean mask `High >= SL_Price` + `groupby.min()` |
| Exit determination | `np.where(SL_hit, SL_Price, NormalExitPrice)` |
| PnL calculation | Vectorized column arithmetic |
| Expiry detection | Vectorized `dt.weekday` + `dt.day` conditions |
| Cumulative PnL | `Series.cumsum()` |

**Forbidden patterns (NOT used anywhere):**
```python
for _, row in df.iterrows()      # NOT USED
for i in range(len(df))          # NOT USED
df.apply(lambda row: ..., axis=1) # NOT USED
```

---

## 18. What output files are generated?

| File | Description |
|------|-------------|
| `output/backtest_results.xlsx` | Excel workbook with 3 sheets (Guide, Tradesheet, Statistics) |
| `output/equity_curve.png` | NAV equity curve chart (300 DPI, dark theme) |
| `output/drawdown.png` | Drawdown chart (300 DPI, dark theme) |
| `output/data_quality_report.txt` | Data validation summary |

**Excel Sheet Details:**
- **Guide** — Strategy overview, parameter table, column definitions, SL explanation
- **Tradesheet** — 494 trade rows with color coding: green (profit), red (loss), orange (stop loss), frozen header, auto-fit columns
- **Statistics** — All metrics, win/loss tables, monthly P&L, avg % PnL by expiry, embedded charts

---

## 19. How does the code handle edge cases?

| Edge Case | Handling |
|-----------|----------|
| No CE near Rs. 50 | Skip CE leg, PE trades independently |
| No PE near Rs. 50 | Skip PE leg, CE trades independently |
| Both legs hit SL same bar | Both recorded as StopLoss independently |
| 15:20 bar missing | Uses last available bar ≤ 15:20 as exit |
| 09:20 bar missing | Day is skipped entirely |
| Tie in premium closeness | Lower strike for CE, higher strike for PE |
| Holiday (no data) | Skipped naturally — no rows = no trade |
| First month in monthly P&L | Uses BASE_NAV (100) as start |

---

## 20. What is the project architecture?

```
banknifty_strangle_backtest/
├── config.py                 <- All constants (never hardcoded inline)
├── data_loader.py            <- CSV loading, validation, dtype optimization
├── strike_selector.py        <- Vectorized strike selection at 09:20
├── signal_generator.py       <- Entry/exit/SL engine (vectorized)
├── position_sizer.py         <- PnL, capital, NAV calculation
├── backtest_engine.py        <- Pipeline orchestrator
├── performance_analytics.py  <- CAGR, DD, Sharpe, Sortino, Calmar, etc.
├── report_generator.py       <- Excel (3 sheets) + matplotlib charts
├── main.py                   <- Entry point with step-by-step timing
├── requirements.txt          <- pandas, numpy, openpyxl, matplotlib
├── .gitignore                <- Excludes CSVs, output/, __pycache__/
└── README.md                 <- Full GitHub-ready documentation
```

**Runtime: ~35 seconds** (target: < 60s)
