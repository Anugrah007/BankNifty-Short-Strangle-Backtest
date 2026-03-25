# BankNifty Short Strangle Backtest — Interview Preparation Report

> **Purpose:** This document is your complete study guide. Read it like a script. Every section is written as if you are explaining it to a senior quant researcher in an interview. Memorize the flow, the numbers, and the "why" behind every design decision.

---

## TABLE OF CONTENTS

1. [Opening Statement — The 60-Second Pitch](#1-opening-statement)
2. [The Strategy — What We Are Trading](#2-the-strategy)
3. [The Data — What We Worked With](#3-the-data)
4. [Architecture — How The Code Is Built](#4-architecture)
5. [Module-by-Module Deep Dive](#5-module-by-module-deep-dive)
6. [The Results — Key Numbers You Must Know](#6-the-results)
7. [The Risk Profile — Drawdowns and Stop Losses](#7-the-risk-profile)
8. [Performance Analytics — Every Metric Explained](#8-performance-analytics)
9. [Design Decisions — The "Why" Behind Every Choice](#9-design-decisions)
10. [Edge Cases — What Could Go Wrong and How We Handle It](#10-edge-cases)
11. [Anticipated Interview Questions and Answers](#11-interview-questions)
12. [Numbers Cheat Sheet — Quick Reference](#12-numbers-cheat-sheet)

---

## 1. OPENING STATEMENT

*"I built a production-grade backtesting engine for a daily BankNifty short strangle strategy. The system processes 10.2 million rows of 1-minute options data across a full year — January 2023 to January 2024 — covering 247 trading days. The entire pipeline is fully vectorized with zero Python loops on data, runs in 35 seconds, and produces a formatted Excel report with three sheets, professional charts, and a complete data quality audit. The strategy generated a 7.73% return with a Sharpe of 1.14, max drawdown of -4.32%, and a Calmar ratio of 1.79."*

---

## 2. THE STRATEGY — WHAT WE ARE TRADING

### What is a Short Strangle?

A short strangle is a **neutral options strategy** where you simultaneously **sell** (write) an out-of-the-money Call and an out-of-the-money Put on the same underlying. You collect premium on both sides. You profit if the underlying stays within a range — the premiums you collected decay toward zero. You lose if the market makes a large move in either direction.

### Our Specific Implementation

**Entry (every trading day at 09:20):**
- Look at the 1-minute closing prices of ALL available BankNifty options at 09:20
- Find the CE (Call) strike whose premium is closest to Rs. 50
- Find the PE (Put) strike whose premium is closest to Rs. 50
- SELL both — we are collecting premium, betting that BankNifty will not make a large move during the day

**Exit (same day):**
- Normal exit at 15:20 — close both positions at the 15:20 bar's closing price
- OR stop loss at 150% of entry price (50% above), whichever comes first

**Position Sizing:**
- Fixed: 15 units per leg (1 lot of 15), every single day
- No compounding — even if capital grows or shrinks, we always trade exactly 15 units
- Starting capital: Rs. 1,00,000

### Why Rs. 50 Premium?

Rs. 50 premium means we are selecting strikes that are moderately out-of-the-money. This gives us:
- Enough premium to make the trade worthwhile (Rs. 50 x 15 = Rs. 750 collected per leg)
- Strikes far enough from spot that small intraday moves do not trigger stop losses
- A balanced risk-reward profile for a daily intraday strategy

### PnL Calculation

Since we are SHORT (sellers):
```
GrossPnL = (EntryPrice - ExitPrice) x 15
```
- If premium decays (ExitPrice < EntryPrice) → we profit
- If premium rises (ExitPrice > EntryPrice) → we lose
- Max loss per leg = 50% of entry (stop loss)
- Max profit per leg = full premium collected (option expires worthless)

---

## 3. THE DATA — WHAT WE WORKED WITH

### Raw Data Files

| File | Contents | Rows | Columns |
|------|----------|------|---------|
| `Options_data_2023.csv` | 1-minute BankNifty options OHLC | 10,266,681 | Date, Ticker, Time, Open, High, Low, Close, Call/Put |
| `BANKNIFTY_SPOT.csv` | 1-minute BankNifty index OHLC | 136,324 | ts, o, h, l, c |

### Key Data Characteristics

**Options data:**
- Date range: 2023-01-02 to 2024-01-02 (247 trading days — full year)
- 322 unique option tickers
- Ticker format: `BANKNIFTY{strike}{CE|PE}` (e.g., `BANKNIFTY44000CE`)
- Time format: `HH:MM:59` (e.g., `09:20:59`, `15:20:59`)
- Contains OHLC for every 1-minute bar of every option strike

**Spot data:**
- Date range: 2023-10-20 to 2025-04-09 (364 days)
- Time format: `HH:MM:00` (e.g., `09:20:00`)
- Only overlaps with options data for 49 days (Oct 2023 - Jan 2024)

### Critical Data Decision

The spot data is used **only** for the `Banknifty_Close` display column in the tradesheet — the underlying index price at the time of entry. It has **zero impact on strategy logic**. All decisions — strike selection, entry, exit, stop loss, PnL — use options prices exclusively.

Therefore, we run the backtest on the **full year of options data** (247 days), not just the 49-day overlap. The `Banknifty_Close` column is populated where spot data exists and NaN elsewhere. This is a cosmetic column, not a computational one.

### Data Cleaning

| Issue | Count | Handling |
|-------|-------|----------|
| Duplicate rows | 14,546 | Dropped |
| Null rows | 0 | N/A |
| Zero-price rows | 0 | N/A |
| Missing 09:20 entry bars | 0 dates | Would skip that day |
| Missing 15:20 exit bars | 0 dates | Would use last available bar |

### What About WEEKLY-I Prefix?

The assignment mentioned tickers formatted as `BANKNIFTYWEEKLY-I42700CE`. After inspecting the data in Step 0, I found the actual ticker format is plain `BANKNIFTY{strike}{CE|PE}` — no WEEKLY prefix exists. I adapted the code to use all available options. The config has a `WEEK1_IDENTIFIER` parameter that can be set to `"WEEKLY-I"` if the data ever uses that format.

---

## 4. ARCHITECTURE — HOW THE CODE IS BUILT

### File Structure (1,753 lines total)

```
banknifty_strangle_backtest/
│
├── config.py              (50 lines)   All constants — nothing hardcoded anywhere else
├── data_loader.py         (275 lines)  CSV loading, validation, cleaning, dtype optimization
├── strike_selector.py     (84 lines)   Vectorized strike selection at 09:20
├── signal_generator.py    (195 lines)  Entry/exit signals, stop loss detection
├── position_sizer.py      (89 lines)   PnL, capital, NAV calculation
├── backtest_engine.py     (98 lines)   Pipeline orchestrator
├── performance_analytics.py (303 lines) All statistical computations
├── report_generator.py    (525 lines)  Excel (3 sheets) + matplotlib charts
├── main.py                (134 lines)  Entry point with step-by-step timing
│
├── requirements.txt       pandas, numpy, openpyxl, matplotlib
├── .gitignore             Excludes CSVs, output, __pycache__
└── README.md              Full documentation
```

### Data Flow Pipeline

```
BANKNIFTY_SPOT.csv ─────────────────────────────────────────────────────┐
                                                                        │
Options_data_2023.csv                                                   │
    │                                                                   │
    ▼                                                                   │
[data_loader.py]  Load CSVs, validate, clean, optimize dtypes           │
    │                                                                   │
    ▼                                                                   │
[strike_selector.py]  At 09:20, find CE & PE closest to Rs. 50         │
    │                                                                   │
    ▼                                                                   │
[signal_generator.py]  Build trades, attach exits, detect stop losses   │
    │                                                                   │
    ▼                                                                   │
[position_sizer.py]  Calculate PnL, capital, NAV  ◄─────────────────────┘
    │                    (joins spot data here for Banknifty_Close)
    ▼
[performance_analytics.py]  CAGR, Drawdown, Sharpe, Win/Loss, Monthly
    │
    ▼
[report_generator.py]  Excel (3 sheets) + equity_curve.png + drawdown.png
```

### Why This Architecture?

Each module has a **single responsibility**:
- **config.py** — change any parameter (entry time, SL%, lot size) in one place
- **data_loader.py** — if the CSV format changes, only this file needs updating
- **strike_selector.py** — if the selection logic changes (e.g., target Rs. 75), only this file changes
- **signal_generator.py** — if SL logic changes (e.g., trailing SL), only this file changes
- **performance_analytics.py** — new metrics can be added without touching strategy code

This is how systematic trading firms structure their codebase. Separation of concerns means you can modify, test, and validate each component independently.

---

## 5. MODULE-BY-MODULE DEEP DIVE

### 5.1 config.py — The Control Center

Every magic number lives here. Nothing is hardcoded inline in any other file.

```
ENTRY_TIME     = "09:20:59"     Entry bar time (options data format)
EXIT_TIME      = "15:20:59"     Normal exit bar time
TARGET_PREMIUM = 50.0           Strike selection target (Rs.)
STOP_LOSS_PCT  = 0.50           50% above entry
SL_MULTIPLIER  = 1.50           EntryPrice x 1.50 = SL level
LOT_SIZE       = 15             BankNifty lot size
QUANTITY       = 15             Fixed units per leg
INITIAL_CAPITAL= 100,000        Starting capital
BASE_NAV       = 100            Equity curve base
EXPIRY_WEEKDAY = 2              Wednesday (Mon=0)
```

**Interview talking point:** *"I made the system config-driven so that any parameter can be changed for sensitivity analysis. For example, if you wanted to test target premium of Rs. 75 or SL of 30%, you just change one value in config.py and re-run."*

### 5.2 data_loader.py — Ingestion and Validation

**What it does:**
1. Loads spot CSV: renames columns (`ts→DateTime`, `o→Open`, etc.), splits timestamp into Date + Time
2. Loads options CSV: renames `Call/Put → OptionType`, extracts Strike from ticker using regex `BANKNIFTY(\d+)(CE|PE)`
3. Validates: drops nulls, zero-price rows, duplicates
4. Does NOT restrict options to spot overlap — uses full year
5. Optimizes dtypes: `float64 → float32` for OHLC (halves memory), `Ticker → category`
6. Writes a data quality report with all statistics

**Key design choice — dtype optimization:**
```python
df = df.astype({c: "float32" for c in ["Open", "High", "Low", "Close"]})
df["Ticker"] = df["Ticker"].astype("category")
```
On 10.2M rows, this reduces memory from ~600MB to ~350MB. `float32` gives 7 significant digits — more than enough for options prices.

### 5.3 strike_selector.py — The Brain

**This is the module interviewers will scrutinize most.** It must be vectorized and correct.

**Algorithm:**
1. Filter options data to only the 09:20:59 bar
2. Compute `|Close - 50|` for every option on every date
3. For CE options: `groupby('Date')['diff'].idxmin()` → selects the CE strike closest to Rs. 50
4. For PE options: same logic

**Tie-breaking:**
- CE: sort strikes ascending before `idxmin()` → lower strike wins (more conservative, farther OTM)
- PE: sort strikes descending before `idxmin()` → higher strike wins (more conservative, farther OTM)

**Zero loops. The entire strike selection for 247 days happens in 3 lines:**
```python
entry_bars['diff_from_target'] = (entry_bars['Close'] - TARGET_PREMIUM).abs()
ce_idx = ce_bars.groupby('Date')['diff_from_target'].idxmin()
pe_idx = pe_bars.groupby('Date')['diff_from_target'].idxmin()
```

**Interview talking point:** *"This is O(n) where n is the number of option bars at entry time. A loop-based approach would be O(d x s) where d is days and s is strikes. The vectorized approach is not just faster — it's impossible to have off-by-one errors because there's no index to manage."*

### 5.4 signal_generator.py — Entry, Exit, and Stop Loss

**Three sub-functions, called in sequence:**

**`build_trades()`** — Combines selected CE and PE into a unified DataFrame, computes `SL_Price = EntryPrice x 1.50`

**`attach_normal_exit_prices()`** — Merges the 15:20 closing price for each traded ticker. If the 15:20 bar is missing, falls back to the last available bar at or before 15:20.

**`detect_stop_loss()`** — The most critical function:

```python
# Step 1: Get all intraday bars AFTER entry (09:21 to 15:20)
intraday = options_df[(Time > ENTRY_TIME) & (Time <= EXIT_TIME)]

# Step 2: Merge with trades to attach SL_Price to each bar
sl_check = intraday.merge(trades[['Date','Ticker','SL_Price']], on=['Date','Ticker'])

# Step 3: Boolean mask — did this bar's HIGH breach SL?
sl_check['SL_Hit'] = sl_check['High'] >= sl_check['SL_Price']

# Step 4: First breach time per (Date, Ticker)
sl_hits = sl_check[sl_check['SL_Hit']].groupby(['Date','Ticker'])['Time'].min()

# Step 5: Determine final exit
ExitPrice  = SL_Price   if SL hit, else NormalExitPrice
ExitTime   = SL_Time    if SL hit, else 15:20:59
ExitReason = "StopLoss" if SL hit, else "Regular"
```

**Why HIGH, not Close?**

*"We use the HIGH column because intrabar price can touch the stop loss level even if the candle closes below it. If BankNifty spikes during a 1-minute bar and the high reaches 150% of our entry, our stop loss would have been triggered by any real-time order management system. Using Close would miss these intrabar breaches, underestimate stop loss frequency, and artificially inflate strategy performance. In our backtest, 245 of 494 legs — 49.6% — hit stop loss. Using Close instead of High would likely cut that number in half, making the backtest unrealistically optimistic."*

**Why are legs independent?**

*"Each leg's stop loss is evaluated independently. If the CE leg hits SL at 10:30, the PE leg continues to trade until 15:20 or its own SL, whichever comes first. This is how a real short strangle would be managed — the two legs are separate positions with separate risk profiles. In our data, 41 of 247 days had BOTH legs hit SL — those are the worst days."*

### 5.5 position_sizer.py — PnL and Capital

**No compounding.** This is explicitly required by the assignment. Quantity stays at 15 every single day.

```python
trades['GrossPnL']         = (EntryPrice - ExitPrice) x 15
trades['CumulativePnL']    = GrossPnL.cumsum()
trades['AvailableCapital'] = 100,000 + CumulativePnL
trades['NAV']              = 100 x AvailableCapital / 100,000
```

**Expiry day identification:**
```python
IsExpiryDay = (weekday == Wednesday) AND (day_of_month <= 7)
```
This identifies the first Wednesday of each month — the Week 1 BankNifty weekly expiry. In our year, that's 12 expiry days: Jan 4, Feb 1, Mar 1, Apr 5, May 3, Jun 7, Jul 5, Aug 2, Sep 6, Oct 4, Nov 1, Dec 6.

### 5.6 performance_analytics.py — Every Metric

**All 8 required metrics plus 7 bonus metrics, fully vectorized.**

**1. CAGR:**
```
CAGR = (FinalCapital / InitialCapital) ^ (365 / CalendarDays) - 1
     = (107,725.37 / 100,000) ^ (365/365) - 1
     = 7.73%
```
Since our backtest spans exactly 365 calendar days, CAGR equals total return.

**2. Max Drawdown (on NAV):**
```
NAV series starts at 100, ends at 107.73
Rolling peak = cumulative max of NAV at each trade
Drawdown = (NAV - peak) / peak x 100
Max DD = worst (most negative) value = -4.32%
```
Max drawdown occurred on January 18, 2023, during the early-year losing streak.

**3-4. Win/Loss Statistics:**

| Group | Winners | Losers | Total | Win % |
|-------|---------|--------|-------|-------|
| CE | 122 | 125 | 247 | 49.4% |
| PE | 122 | 125 | 247 | 49.4% |
| Combined | 244 | 250 | 494 | 49.4% |

*"The win rate is below 50%, but the strategy is still profitable. This is classic for premium-selling strategies — you win small most of the time (premium decays) and lose bigger when SL hits. The key is that the average win (Rs. 15.64/leg) exceeds the expected loss, giving a positive edge."*

**5. Avg % P&L by Expiry:**

| Category | Avg % PnL |
|----------|-----------|
| CE Expiry | +27.23% |
| CE Non-Expiry | +0.57% |
| PE Expiry | -0.35% |
| PE Non-Expiry | +1.01% |
| Combined Expiry | +13.44% |
| Combined Non-Expiry | +0.79% |

*"CE performs significantly better on expiry days because time decay accelerates as expiry approaches — theta crush. The PE side is roughly flat on expiry. Combined, expiry days contribute +13.44% average vs +0.79% on non-expiry. This suggests the strategy has a structural edge from expiry-day theta collapse."*

**6. Equity Curve:**
NAV starts at 100, dips to ~97.2 in Feb (worst drawdown period), then steadily climbs to 107.73 by year end. 9 of 13 months are profitable.

**7. Monthly P&L:**

| Month | % PnL | Rs. PnL |
|-------|-------|---------|
| 2023-01 | -1.60% | -1,601 |
| 2023-02 | -1.22% | -1,202 |
| 2023-03 | +2.36% | +2,294 |
| 2023-04 | +1.09% | +1,088 |
| 2023-05 | +3.05% | +3,069 |
| 2023-06 | +1.72% | +1,784 |
| 2023-07 | +0.44% | +467 |
| 2023-08 | -1.34% | -1,415 |
| 2023-09 | -0.02% | -19 |
| 2023-10 | +1.29% | +1,352 |
| 2023-11 | +1.30% | +1,372 |
| 2023-12 | +0.33% | +355 |
| 2024-01 | +0.17% | +182 |

*"The strategy had a rough start — down in Jan and Feb. This is common for short strangles during high-volatility periods (Budget season in India). From March onwards, the strategy was consistently profitable with only Aug and Sep as minor drawdowns."*

**8. Drawdown Chart:**
A red filled area chart showing the percentage decline from peak NAV at each point. Max DD of -4.32% is annotated with a yellow dashed line.

**Bonus Metrics:**

| Metric | Value | What It Means |
|--------|-------|---------------|
| Sharpe Ratio | 1.1382 | Good. Above 1.0 is acceptable, above 2.0 is excellent |
| Sortino Ratio | 1.5843 | Better than Sharpe because it only penalizes downside volatility |
| Calmar Ratio | 1.7880 | Return per unit of max drawdown — shows good risk efficiency |

---

## 6. THE RESULTS — KEY NUMBERS YOU MUST KNOW

### Memorize These

| Metric | Value |
|--------|-------|
| **Backtest period** | Jan 2, 2023 — Jan 2, 2024 (247 trading days) |
| **Total return** | +7.73% (Rs. 7,725.37) |
| **CAGR** | +7.73% (365 calendar days = 1 year exactly) |
| **Max drawdown** | -4.32% (Jan 18, 2023) |
| **Sharpe** | 1.14 |
| **Sortino** | 1.58 |
| **Calmar** | 1.79 |
| **Win rate** | 49.4% (244 wins / 494 total) |
| **SL hit rate** | 49.6% (245 / 494) |
| **Avg premium collected** | Rs. 49.40 per leg |
| **Mean daily PnL** | Rs. 31.28 |
| **Max single profit** | Rs. 968.25 |
| **Max single loss** | Rs. -459.75 |
| **Both legs SL same day** | 41 of 247 days |
| **Profitable months** | 9 / 13 |
| **Best month** | May 2023: +3.05% |
| **Worst month** | Jan 2023: -1.60% |
| **Runtime** | 35 seconds on 10.2M rows |

---

## 7. THE RISK PROFILE — DRAWDOWNS AND STOP LOSSES

### Stop Loss Mechanics

```
SL Level = Entry Price x 1.50
```

For a trade entered at Rs. 50, SL triggers at Rs. 75. Since we are SHORT, the option rising to Rs. 75 means we lose Rs. 25 x 15 = Rs. 375 per leg.

**SL Statistics:**
- Total SL hits: 245 of 494 legs (49.6%)
- CE legs SL: 122
- PE legs SL: 123 (remarkably symmetric)
- Both legs SL same day: 41 (16.6% of days — the really bad days)

**What does a "both legs SL" day look like?**

On January 5, 2023:
- BANKNIFTY43300CE: entered at Rs. 58.80, SL at Rs. 88.20, hit at 09:34 → Loss Rs. -441.00
- BANKNIFTY42800PE: entered at Rs. 59.85, SL at Rs. 89.77, hit at 09:22 → Loss Rs. -448.87
- **Total day loss: Rs. -889.87**

This is the worst type of day — a violent whipsaw that triggers both sides. These 41 days are the primary drag on performance.

### Drawdown Analysis

The max drawdown of -4.32% occurred on January 18, 2023 — during the early losing streak (Jan-Feb). The strategy was underwater for approximately 2 months before recovering in March.

**Why is the drawdown relatively small despite 50% SL?**

Because the fixed position sizing (15 units) means each leg's max loss is capped at approximately Rs. 375 (50% of ~Rs. 50 x 15). With Rs. 1,00,000 capital, even a both-legs-SL day only costs ~0.75% of capital. The 4.32% drawdown represents a cumulative cluster of bad days, not a single catastrophic event.

---

## 8. PERFORMANCE ANALYTICS — EVERY METRIC EXPLAINED

### CAGR (Compound Annual Growth Rate)

*"CAGR tells us the annualized rate of return. I compute it as (FinalCapital / InitialCapital) raised to the power of (365 / calendar_days) minus 1. Since our backtest spans exactly 365 days, CAGR equals the simple return of 7.73%. If this were a 6-month backtest showing 7.73%, the CAGR would be much higher — around 16% — due to annualization. This is why I report both CAGR and total return."*

### Max Drawdown

*"Max drawdown is the largest peak-to-trough decline in the NAV equity curve. It answers the question: if I had invested at the worst possible time, what's the most I would have temporarily lost? I compute it on the trade-wise NAV series: at each point, I track the rolling cumulative maximum (the peak). The drawdown is (current NAV - peak) / peak x 100. The worst value across the entire series is the max drawdown. Importantly, even if the portfolio later recovers, the max drawdown remains -4.32% — it's a historical worst-case measure."*

### Sharpe Ratio

```
Sharpe = (mean_daily_pnl / std_daily_pnl) x sqrt(252)
       = (31.28 / 173.35) x 15.87
       = 1.14
```

*"The Sharpe ratio measures risk-adjusted return. I aggregate PnL to the daily level first (sum of both legs per day), then compute mean and standard deviation. The sqrt(252) annualizes the ratio assuming 252 trading days per year. A Sharpe above 1.0 is generally considered acceptable for a systematic strategy. Our 1.14 indicates the strategy generates meaningful return per unit of total volatility."*

### Sortino Ratio

```
Sortino = (mean_daily_pnl / std_downside_pnl) x sqrt(252)
        = (31.28 / 125.12) x 15.87
        = 1.58
```

*"The Sortino ratio is similar to Sharpe but only penalizes downside volatility. Upside volatility — big winning days — is not penalized. For a premium-selling strategy where winning days are small and losing days are larger, the Sortino gives a fairer picture than the Sharpe. Our Sortino of 1.58 is notably higher than the Sharpe of 1.14, indicating that much of our volatility comes from upside (big winning trades), not downside."*

### Calmar Ratio

```
Calmar = CAGR / |Max Drawdown|
       = 0.0773 / 0.0432
       = 1.79
```

*"The Calmar ratio measures return relative to max drawdown — the worst-case scenario. A Calmar above 1.0 means the annual return exceeds the max drawdown. Our 1.79 means for every 1% of max drawdown, we earned 1.79% annual return. This is a solid ratio for an intraday strategy."*

---

## 9. DESIGN DECISIONS — THE "WHY" BEHIND EVERY CHOICE

### Why Zero Loops?

*"The assignment explicitly forbids Python for-loops on data. But beyond the requirement, vectorization is the right approach for financial time series. pandas groupby + merge + np.where operations are backed by optimized C code. On 10.2 million rows, a loop-based SL scan would take minutes; our vectorized approach takes 2.5 seconds."*

**Forbidden patterns (not used anywhere):**
```python
for _, row in df.iterrows()       # O(n) with Python overhead per row
for i in range(len(df))           # Same problem
df.apply(lambda row: ..., axis=1) # Disguised loop
```

**Patterns used instead:**
```python
df.groupby('Date')['diff'].idxmin()                    # Strike selection
df.merge(trades, on=['Date','Ticker'])                  # SL price attachment
np.where(sl_hit, SL_Price, NormalExitPrice)             # Conditional exit
sl_check[sl_check['SL_Hit']].groupby(['Date','Ticker'])['Time'].min()  # First SL breach
```

### Why float32 Instead of float64?

*"Options prices don't need 15 decimal digits of precision. float32 gives 7 significant digits — Rs. 50.30 is stored as 50.30000, which is more than sufficient. On 10.2M rows with 4 OHLC columns, this saves ~150MB of RAM. For a production system processing years of tick data, this difference matters."*

### Why Config-Driven?

*"In a real quant research workflow, you'd want to run parameter sweeps — test target premiums of 30, 50, 75, 100; test SL of 25%, 50%, 75%; test different entry times. Making everything config-driven means you can automate these sweeps without modifying code. Just loop over config values and aggregate results."*

### Why Trade-Wise NAV (Not Daily)?

*"The assignment specifies NAV should update after each trade row. Since we have 2 legs per day (CE and PE), the NAV series has 494 data points — 2 per day. The CE leg's NAV reflects its PnL plus all prior legs. The PE leg's NAV additionally includes the CE leg of the same day. This gives a more granular view of intraday portfolio evolution, which is appropriate for a strategy that has independent legs with independent stop losses."*

---

## 10. EDGE CASES — WHAT COULD GO WRONG AND HOW WE HANDLE IT

| Scenario | Our Handling |
|----------|-------------|
| No CE strike near Rs. 50 on a day | Skip CE leg for that day, PE trades independently. Log a warning. |
| No PE strike near Rs. 50 on a day | Skip PE leg, CE trades independently. Log a warning. |
| Both legs hit SL on the same bar | Both recorded as independent StopLoss events. Each gets its own exit row. |
| 15:20 exit bar missing for a ticker | Fall back to the last available bar at or before 15:20. |
| 09:20 entry bar missing entirely | Skip that trading day. Log a warning. |
| Tie: two strikes equally close to Rs. 50 | CE: pick lower strike (farther OTM, more conservative). PE: pick higher strike (same logic). |
| Holiday / no market data | Naturally skipped — no rows in the data = no trade attempted. |
| First month in monthly P&L | Uses BASE_NAV (100) as the starting reference, not the previous month's end. |

**In our actual data:** No edge cases were triggered. All 247 days had valid CE and PE at 09:20, all had valid 15:20 exit bars, and no days were skipped. The edge case handling is there for robustness, not because our data needed it.

---

## 11. ANTICIPATED INTERVIEW QUESTIONS AND ANSWERS

### Q1: "Walk me through what happens when the market opens on a trading day."

*"At 09:20, the system takes a snapshot of all available BankNifty option premiums. It scans every CE option and finds the one whose closing price at 09:20 is closest to Rs. 50. Same for PE. For example, on January 2, 2023, it selected BANKNIFTY44000CE at Rs. 50.05 and BANKNIFTY42000PE at Rs. 46.80. We sell both at those prices.*

*The system then monitors every 1-minute HIGH bar from 09:21 onwards. For the CE leg, the SL level is Rs. 50.05 x 1.50 = Rs. 75.07. At 09:44, the HIGH of BANKNIFTY44000CE hit Rs. 77.40, which is above Rs. 75.07 — so the CE leg was stopped out. The exit price is recorded as exactly Rs. 75.07 (the SL level, not the actual bar high).*

*The PE leg continued independently because its HIGH never reached its SL level. At 15:20, BANKNIFTY42000PE closed at Rs. 19.35, and we bought it back. PE profit: (46.80 - 19.35) x 15 = Rs. 411.75.*

*Net for the day: -375.37 + 411.75 = +Rs. 36.38."*

### Q2: "Why did you use HIGH for stop loss instead of Close?"

*"In live trading, a stop loss order triggers the moment price touches the SL level — not just at the close of a candle. The HIGH of a 1-minute bar represents the highest price reached during that minute. If the HIGH exceeds our SL level, the stop would have been triggered in real-time even if the candle subsequently closed below it.*

*Using Close would miss these intrabar SL triggers, making the backtest unrealistically optimistic. In our data, 245 of 494 legs — nearly half — hit stop loss when using HIGH. If we used Close, that number would drop significantly, and the strategy would look much better on paper but would not reflect real-world execution."*

### Q3: "Your win rate is below 50%. How is the strategy profitable?"

*"This is the characteristic profile of a premium-selling strategy. The average winning trade makes Rs. 15.64 per leg, but the asymmetry matters. When we win, premium decays — the option might drop from Rs. 50 to Rs. 20, giving us Rs. 450 profit. When we lose to SL, the loss is capped at 50% of entry — about Rs. 375. The wins are frequent enough and large enough to overcome the losses.*

*More importantly, the Sortino ratio of 1.58 — higher than the Sharpe of 1.14 — tells us that the downside volatility is lower than total volatility. Our losing days are relatively contained (thanks to SL), while some winning days are quite large (full premium collection = Rs. 750+ per leg on good days). The max single-trade profit was Rs. 968.25 vs max single-trade loss of Rs. -459.75."*

### Q4: "What would you change to improve this strategy?"

*"Several directions I'd explore:*

*1. Dynamic premium target — Instead of fixed Rs. 50, scale the target with VIX or realized volatility. In high-vol periods, target higher premiums; in low-vol, lower.*

*2. Trailing stop loss — Our current SL is static at 150% of entry. A trailing SL that adjusts as premium decays would lock in profits on winning trades and potentially improve the Sharpe.*

*3. Regime detection — The strategy lost money in Jan-Feb 2023 (budget season, high volatility). A regime filter that reduces position size or skips trading during high-vol regimes would cut drawdowns.*

*4. Transaction costs — This backtest assumes zero brokerage, slippage, and impact cost. Adding realistic costs (Rs. 20/order + 0.5% slippage on illiquid strikes) would give a more accurate P&L.*

*5. Multi-timeframe confirmation — Only enter if a longer-timeframe signal (e.g., hourly trend) supports the neutral stance.*

*6. The SL fill assumption — We assume fills exactly at the SL level. In reality, if the option gaps above SL, the actual fill would be worse. Using the triggering bar's HIGH as the exit price would be more conservative."*

### Q5: "How did you ensure the backtest is correct?"

*"Multiple layers of verification:*

*First, mathematical verification — I independently recomputed every formula (GrossPnL, EntryValue, ExitValue, CumulativePnL, AvailableCapital, NAV) and confirmed zero error to 10 decimal places.*

*Second, stop loss verification — I spot-checked individual SL trades by going back to the raw options data and confirming that (a) the HIGH of the triggering bar actually exceeded the SL level, and (b) no earlier bar had already breached it.*

*Third, structural verification — I confirmed every day has exactly 1 CE + 1 PE, every entry time is 09:20:59, every exit date equals entry date (intraday), every regular exit is at 15:20:59, and every SL exit time falls between 09:21 and 15:20.*

*Fourth, cross-verification — I recomputed CAGR, Sharpe, Sortino, and Calmar manually and confirmed they match the analytics output exactly.*

*Fifth, the data quality report flags any anomalies — missing bars, nulls, duplicates, zero-price rows. All counts are zero or explicitly handled."*

### Q6: "Why does the strategy perform better on expiry days?"

*"On expiry days, time value (theta) collapses rapidly. An option with Rs. 50 premium at 09:20 might be worth Rs. 5 by 15:20 if the underlying stays flat — that's a Rs. 675 profit per leg. On non-expiry days, the premium only decays by a few rupees (normal theta). Our data shows CE legs average +27.23% on expiry days vs +0.57% on non-expiry days. The combined expiry average of +13.44% vs +0.79% confirms that theta crush on expiry is a significant driver of our edge."*

### Q7: "Tell me about the vectorization approach."

*"The key insight is that every operation in the backtest can be expressed as a column-wise or group-wise operation.*

*Strike selection: Instead of looping through 247 days and finding the closest strike each day, I compute the difference from Rs. 50 for ALL options on ALL days in one vectorized operation, then use groupby('Date').idxmin() to pick the winner per day. This is one pass through the data.*

*SL detection: Instead of looping through trades and checking each bar, I merge the intraday bars with the trade-level SL prices. This creates a wide table where every bar is annotated with its SL threshold. A single boolean comparison (High >= SL_Price) flags all breaches, and groupby(['Date','Ticker']).min() picks the first one. Again, one pass.*

*The total pipeline processes 10.2M rows in 35 seconds. The SL detection step, which is the most expensive (it joins 2M+ intraday bars with 494 trade records), takes 2.5 seconds."*

### Q8: "What does the Excel report contain?"

*"Three sheets:*

*Sheet 1 — Guide: Strategy documentation including parameter table, column-by-column definitions of every tradesheet column, how the stop loss mechanism works, and how expiry days are identified. This is for someone opening the file for the first time.*

*Sheet 2 — Tradesheet: 494 rows, one per leg per day. Frozen header row, blue header with white text. Green rows for profitable trades, red for losing trades, orange for stop-loss exits. Auto-fitted column widths. Number formats with comma separators and 2 decimal places. Bold totals row at the bottom showing total PnL of Rs. 7,725.37.*

*Sheet 3 — Statistics: Six sections — Return Metrics, Risk Metrics, Win/Loss table, Avg % PnL by Expiry, Monthly P&L with green/red conditional formatting, and Additional Statistics. At the bottom, the equity curve and drawdown charts are embedded as images."*

---

## 12. NUMBERS CHEAT SHEET — QUICK REFERENCE

Print this page. Glance at it before the interview.

```
STRATEGY:  Short strangle, sell CE+PE at 09:20, exit 15:20, SL=50%, 15 lots
DATA:      10.2M option rows, 247 trading days, Jan 2023 — Jan 2024
CODE:      1,753 lines, 9 modules, zero loops, 35s runtime

RETURN:    +7.73% total = +Rs. 7,725 on Rs. 1,00,000
CAGR:      +7.73%  (365 calendar days = exactly 1 year)
MAX DD:    -4.32%  (Jan 18, 2023)
SHARPE:    1.14    SORTINO: 1.58    CALMAR: 1.79

WIN/LOSS:  244W / 250L = 49.4% win rate (but still profitable)
SL HITS:   245/494 = 49.6%  (CE: 122, PE: 123, Both: 41 days)
AVG PREM:  Rs. 49.40 per leg
DAILY PnL: Rs. 31.28 average
MAX WIN:   Rs. 968.25    MAX LOSS: Rs. -459.75

MONTHS:    9 profitable, 4 losing
BEST:      May +3.05%    WORST: Jan -1.60%
EXPIRY:    12 days, CE +27.23% avg, Combined +13.44% avg

EXCEL:     3 sheets (Guide, Tradesheet, Statistics)
CHARTS:    equity_curve.png, drawdown.png (300 DPI, dark theme)
REPORT:    data_quality_report.txt (all validations)
```

---

## CLOSING STATEMENT FOR THE INTERVIEW

*"In summary, this project demonstrates five key competencies: First, financial domain knowledge — understanding short strangle mechanics, theta decay, independent leg risk management, and weekly expiry dynamics. Second, large-scale data engineering — processing 10.2 million rows efficiently with dtype optimization and vectorized operations. Third, quantitative rigor — every formula is verified to 10 decimal places, every edge case is handled, and the data quality pipeline catches anomalies. Fourth, production software engineering — modular architecture, config-driven design, type hints, docstrings, and comprehensive reporting. Fifth, honest analysis — the win rate is below 50%, the drawdown is clearly reported, and I know exactly which months lost money and why. I'm not overselling the results."*

---

*End of Interview Preparation Report*
