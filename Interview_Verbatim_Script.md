# Exact Verbatim Script — "Explain This Project" (7-10 Minutes)

> **Instructions:** Read this out loud 5-6 times until it flows naturally. The script is broken into 8 sections. Each section is 45-90 seconds. Pause briefly between sections — take a breath, make eye contact, let the interviewer absorb. If they interrupt with a question, answer it, then say "Coming back to..." and resume from the next section.

---

## SECTION 1: The Hook (45 seconds)

"So the project I built is a production-grade backtesting engine for a daily BankNifty short strangle strategy. The idea is simple — every morning at 9:20 AM, we sell a Call option and a Put option on BankNifty, collect premium on both sides, and close the positions by 3:20 PM the same day. We have a 50% stop loss per leg that is monitored independently throughout the day.

I built this end-to-end in Python — it processes 10.2 million rows of 1-minute options data across 247 trading days, from January 2023 to January 2024. The entire pipeline is fully vectorized — zero Python for-loops on data — runs in about 35 seconds, and outputs a formatted Excel report with three sheets, professional charts, and a complete data quality audit.

The headline numbers: 7.73% return on 1 lakh starting capital, a Sharpe of 1.14, and a max drawdown of just 4.32%."

---

## SECTION 2: The Strategy Logic (60 seconds)

"Let me walk you through the actual mechanics.

A short strangle means we're simultaneously selling an out-of-the-money Call and an out-of-the-money Put. We profit when the premiums decay — which they do naturally as the day progresses, especially if BankNifty stays in a range. We lose if the market makes a sharp directional move.

For strike selection — at 9:20 AM, the system scans every available BankNifty option's closing price at that minute. It picks the CE strike and the PE strike whose premium is closest to Rs. 50. Why 50? Because that gives us strikes that are moderately out-of-the-money — far enough from spot that small moves don't trigger stop losses, but close enough to collect meaningful premium. Rs. 50 times 15 units is Rs. 750 collected per leg.

Position sizing is fixed — 15 units per leg, which is one lot of BankNifty, every single day. No compounding. Even if capital grows or shrinks, we always trade exactly 15 units. Starting capital is Rs. 1 lakh.

For exit — either we close at 3:20 PM at the market price, or the stop loss triggers if the option premium rises to 150% of our entry price — which is a 50% loss on that leg. And critically, each leg is independent. If the CE hits stop loss at 10:30 AM, the PE continues trading until 3:20 or its own stop loss."

---

## SECTION 3: The Data (60 seconds)

"Now, the data. This was one of the most important parts of the project because I spent time in Step 0 actually inspecting the raw CSVs before writing a single line of code.

The options file has 10.2 million rows — 1-minute OHLC data for 322 unique BankNifty option tickers across a full year. The ticker format is plain BANKNIFTY followed by the strike and CE or PE — for example, BANKNIFTY44000CE. The time format is HH:MM:59, so our entry bar is 09:20:59.

The spot file — BankNifty index data — has about 136,000 rows, but it only overlaps with the options data for 49 out of 247 days. This was a critical design decision. The spot data is only used for one display column — BankNifty Close at entry time. It has zero impact on any strategy logic. All entry prices, exit prices, stop losses, and PnL calculations use options prices exclusively. So I ran the backtest on the full year of options data, not just the 49-day overlap. Where spot data exists, we show the index price. Where it doesn't, it's NaN. It's a cosmetic column.

On the cleaning side — I dropped 14,546 duplicate rows, checked for nulls and zero-price rows, and confirmed all 247 days had valid 9:20 entry bars and 3:20 exit bars. Everything is documented in a data quality report that the system generates automatically."

---

## SECTION 4: The Architecture (60 seconds)

"The codebase is about 1,750 lines across 9 Python modules, and the architecture follows a clean pipeline pattern — each module has a single responsibility.

Config.py holds every constant — entry time, exit time, target premium, stop loss percentage, lot size, capital. Nothing is hardcoded anywhere else. If you want to run a sensitivity analysis — say, test target premiums of 30, 50, 75 — you just change one value in config and re-run.

Data Loader handles CSV ingestion, validation, and dtype optimization. I convert float64 to float32 for all OHLC columns and Ticker to a categorical type — on 10 million rows, this cuts memory usage from roughly 600MB to 350MB.

Strike Selector is the core selection logic — three lines of vectorized pandas that select strikes across all 247 days simultaneously.

Signal Generator handles entry, exit, and most importantly, stop loss detection — which is the most computationally intensive step.

Position Sizer calculates PnL, cumulative PnL, available capital, and NAV.

Performance Analytics computes all the statistical metrics.

And Report Generator produces the Excel file with three formatted sheets plus the equity curve and drawdown charts at 300 DPI.

The whole thing flows as a pipeline: load data, select strikes, generate signals, size positions, compute analytics, generate reports."

---

## SECTION 5: The Key Technical Challenges (90 seconds)

"I want to highlight three technical pieces that I think are the most interesting.

First — strike selection. Instead of looping through 247 days and scanning strikes each day, I compute the absolute difference from Rs. 50 for every single option on every single day in one vectorized operation. Then I call groupby Date, idxmin — and pandas gives me the closest strike per day in one pass. For tie-breaking, I sort CE strikes ascending so the lower strike wins — that's more conservative, farther out-of-the-money. PE sorts descending, same logic. The entire strike selection for the full year is three lines of code.

Second — stop loss detection. This is the critical one. I take all intraday bars between 9:21 and 3:20, merge them with the trade records to attach each bar's SL price threshold. Then a single boolean comparison — is this bar's HIGH greater than or equal to the SL price? — flags every breach. Then groupby Date and Ticker, take the min of Time, and I have the first SL trigger time for every trade. One pass through the data, 2.5 seconds.

And I want to emphasize — I use the HIGH column, not the Close. Because in live trading, a stop loss triggers the moment the price touches the SL level, even if the candle closes below it. The High of a 1-minute bar captures the worst intrabar price. Using Close would miss these intrabar breaches and make the backtest unrealistically optimistic. In our data, 245 out of 494 legs — nearly half — hit stop loss. If I'd used Close instead of High, that number would be significantly lower, and the results would look better on paper but wouldn't reflect reality.

Third — the NAV is trade-wise, not daily. Since we have two independent legs per day, the NAV updates after each leg. So we get 494 data points — two per day — which gives a more granular view of how the portfolio evolves intraday."

---

## SECTION 6: The Results (75 seconds)

"Now the numbers.

Total return: plus 7.73%, which is Rs. 7,725 on 1 lakh starting capital. Since the backtest spans exactly 365 calendar days, the CAGR also equals 7.73%.

Max drawdown: negative 4.32%, which occurred on January 18, 2023, during an early losing streak in January and February. The strategy was underwater for about two months before recovering in March.

Risk-adjusted metrics: Sharpe ratio is 1.14 — above 1 is generally considered acceptable for a systematic strategy. Sortino ratio is 1.58 — notably higher than the Sharpe because the Sortino only penalizes downside volatility. And the Calmar ratio is 1.79 — meaning for every 1% of max drawdown, we earned 1.79% annual return.

Win rate: 49.4% — 244 winners out of 494 total legs. Now, the win rate is below 50%, but the strategy is still profitable. This is characteristic of premium-selling strategies. When we win, premium decays — say the option drops from 50 to 20, giving us Rs. 450 profit. When we lose to SL, the loss is capped at 50% of entry, roughly Rs. 375. So the wins don't need to be more frequent — they just need to be large enough. And the max single-trade profit of Rs. 968 versus max single-trade loss of Rs. 460 confirms that the payoff distribution is favorable despite the sub-50% hit rate.

Stop loss stats: 245 out of 494 legs hit SL — that's 49.6%. CE and PE were remarkably symmetric — 122 CE and 123 PE. On 41 out of 247 days, both legs hit stop loss. Those are the worst days — roughly Rs. 750 to 900 in losses per day."

---

## SECTION 7: Monthly Pattern and Expiry Effect (60 seconds)

"Looking at the monthly pattern — 9 out of 13 months were profitable. January and February were the worst — down 1.6% and 1.2% respectively. This makes sense — budget season in India, elevated volatility, which is the enemy of short strangles. From March onwards, the strategy was consistently profitable with only August showing a meaningful drawdown of 1.3%.

The best month was May 2023 at plus 3.05%.

There's also a very interesting expiry effect. On expiry days — which I define as the first Wednesday of each month — CE legs averaged plus 27% return. On non-expiry days, CE averaged just plus 0.6%. This is theta crush — on expiry day, time value collapses rapidly. An option at Rs. 50 in the morning might be worth Rs. 5 by 3:20 PM if the underlying stays flat. The combined expiry-day average is plus 13.4% versus plus 0.8% on non-expiry days. This tells us that expiry-day theta collapse is a significant structural driver of the strategy's edge."

---

## SECTION 8: The Close — Design Philosophy + What I'd Improve (75 seconds)

"I want to close with the design philosophy and what I'd do differently in a production setting.

The system is config-driven, so parameter sweeps are trivial. Every magic number lives in one file. The modules are separated by responsibility — if the SL logic changes to, say, a trailing stop, only signal_generator.py needs to change. If the output format changes, only report_generator.py changes. This is how systematic trading firms structure their codebases.

Every edge case is handled — missing entry bars, missing exit bars, one-legged days, ties in strike selection. In our data none of these fired, but the robustness is there for production use.

If I were to take this forward, I'd explore five things. First — dynamic premium targets that scale with VIX or realized volatility. In high-vol periods, target higher premiums. Second — trailing stop losses instead of static ones, to lock in profits on winning trades. Third — a regime filter that reduces position sizing during high-volatility regimes like budget season, which would have avoided the January-February drawdown. Fourth — adding realistic transaction costs, because this backtest assumes zero brokerage, slippage, and impact cost. And fifth — the SL fill assumption. Currently we assume fills exactly at the SL level. In reality, if the option gaps above SL, the fill would be worse. Using the triggering bar's High as the exit price would be more conservative.

In summary — this project demonstrates financial domain knowledge, large-scale data engineering on 10 million rows, quantitative rigor with every formula verified, production software engineering with modular architecture, and honest analysis. The win rate is below 50%, the drawdown is clearly reported — I'm not overselling the results. The numbers are what they are, and I can defend every single one of them."

---

## IF THEY ASK FOLLOW-UPS — Quick Answers

**"How is the Sharpe computed?"**
"I aggregate PnL to the daily level first — sum of both legs. Then mean daily PnL divided by standard deviation of daily PnL, times square root of 252. Rs. 31.28 mean, Rs. 173.35 std dev, gives us 1.14."

**"How is max drawdown computed?"**
"On the trade-wise NAV series. At each trade, I compute a rolling cumulative maximum — the peak so far. Drawdown is current NAV minus peak, divided by peak. The worst value is minus 4.32%."

**"Why no compounding?"**
"The assignment explicitly specifies fixed lot sizing. But also, for a short strangle, position sizing should ideally scale with margin requirements, not just capital. Fixed sizing keeps the analysis clean and isolates the strategy's alpha from leverage effects."

**"What about transaction costs?"**
"This backtest assumes zero costs. Adding realistic costs — say Rs. 20 per order plus 0.5% slippage — would reduce the 7.73% return. With 494 legs that's 988 orders, so roughly Rs. 20,000 in brokerage alone, which would cut the return to about minus 12%. In practice, discount brokers charge much less and slippage on liquid BankNifty options is minimal. But I'd want to model it before going live."

**"Why is the drawdown so small despite 50% SL?"**
"Because position sizing is fixed and small relative to capital. Each leg's max loss is about Rs. 375 — that's only 0.375% of 1 lakh capital. Even on a both-legs-SL day, that's 0.75%. The 4.32% drawdown is a cumulative cluster of bad days, not a single catastrophic event."

---

*End of script. Total speaking time: approximately 8-9 minutes at natural pace.*
