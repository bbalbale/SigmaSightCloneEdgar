# Comments
## 1.  Positioning 
- I think we should position ourselves as a tool for sophisticated individuals to to evaluate their investment portfolios. This would allow us to create cascading degrees of sophistication in analysis at different price points, all building on the same engine. Each level builds on the level before it
- 
## 2. Cascading set of Users and Segments
Elliott's comments: new set of user personas.
### 2.1 Baseline
- Demo User 1:One time analysis of your portfolio to measure your current portfolio risks and exposures. User uploads their portfolio and we calculate correlation between the names in their portfolio, portfolio factor exposures and what it means: Overweights and Underweights relative to the index, and predictions on how their portfolio will perform in various market environments. 
- Simple portfolio: some mutual funds (FMAGX, FCNTX), and 20 stocks. Amazon, Google, Microsoft, Apple, Tesla, JNJ, JPM, PFE, V, XOM, with some juice: RIVN, PLTR, SBUX, RL, NIKE, DIS, NFLX. 
- Will need to pull the top 10 holdings of these mututal funds to then calculate the true exposure, as these funds often overlap with these holdings. 
- One time $5 fee (as an example)

### 2.2 Expanded Baseline
- Demo User 2: Provide a template to add in other assets you own, such as real estate, private equity, etc. Allow inputting of target prices on the portfolio to determine expected returns. For positions that are not defined (funds, ETFs, Real Estate) allow a % annual increase/decrease to determine expected returns.  
- Would also allow users to add RSUs and Option Grants and put these into context of their portfolio. 
- Same portfolio as above, but add in some RSUs and Option Grants: we can pick Google as an example or lets perhaps pick another company. I don't know what these typical grants are though. 
- Add in a portfolio of some rental real estate. User would need to input Asset Value, Mortgage, any rental income. 
- Add in a venture fund. User would need to input NAV, expected annual return. 
- Monthly fee of $5

### 2.3 Long/Short Swing Trader
- Demo User 3: Much of this has been defined to date: Gross, Net, Long, Short, Correlation, Factor Exposures, etc.  We need to add in the abilty to view expected return per 2.2 above. 
- Will come back to you with a portfolio for this, but should include 20 longs, 25 shorts, complex options. 
- Monthly fee of $10, scaling up base upon data feeds and features provided 

## 3. Calculation 
### 3.1 Options Calculations
Elliott's comments: modified project to support delta adjusted exposure. 
- Need to be able to calculate Dollar, and Notional Exposure and Delta Adjusted Exposure. The calculations as presented are only Dollar exposure 
- See https://www.reddit.com/r/thinkorswim/comments/16ofp70/delta_adjusted_notional_value/ for an example of why this is problematic. 
- Dollar Exposure is the dollar value of the contracts
- Notional Exposure is the dollar value of the contracts if they were at 100 delta
- Delta Adjusted Exposure is the dollar value of the contracts if they were at the current delta. The Delta of the contract should be available from the Greeks calculation but I'm guessing Polygon might actually give us the Delta. In fact, Polygon likely gives us all the Greeks for the options. Per your research, perhaps we can use Polygon for a fall back if our calculations fail. 
### 3.2 Future Returns Calculations
Elliott's comments: less postpone this to V1.5
- Need to allow the user to input target prices per stock and carry these through to the future value of the stock or option 
- Options future value can be calculated at expiry, and will be the difference between the target price of the underlying, and contract price and adjusted for the value of the contract. 
### 3.3 Non Listed Positions (for User 2.2, perhaps this is in a future build).
Elliott's comments: let's postpone this to V1.5.
- Need a set of fields to allow user to input non-listed securities, such as real estate, private equity, etc.  - Will need to allow user to input expected returns per year and perhaps prior period returns

## 4. Risk Metrics
### 4.1 Objectives 
- I am becoming of the view that we need to give users a view of their risk metrics in a way that is easy to understand, specifically: what will happen to the user's portfolio under a set of circumstances. 
### 4.2 Exposure
- Calculations for Gross/Net appear accurate
### 4.3. Factor Exposure
Elliott's Comments: Discussing with Ben today 8/4/25. Sent email summarizing the issues.  Issue resolved and integrated into the todo.md
- I thought there was a Parametric script built to do this, but I don't see it in the calculations section
- Believe the approach used was to run a co-variance calculation comparing the historical portfolio to the factor ETF performance 
- I think *Forward Looking* guidance might be more valuable than the historical view.  (Not to say historical isn't relevant, but the backward look might be more valuable to an institution than to an prosumer).
- This would mean comparing the last twelve month performance of each name in a portfolio to the last twelve month performance of the factor ETFs, weighting this by the position size of the name in the portfolio and then aggregating the results to give a forward looking view of the portfolio's factor exposures.  This methodology probably needs to be run though Claude to confirm. 
### 4.4 Concentration
#### 4.4.1 Mutual Fund/ETF Lookthrough
Elliott's Comments: I can imagine an isolated separate Mutual Fund/ETF concentration report that wouldn't interact with any of the pipeline of the rest of our analyses.  Maybe that could list out top positions after the ETF lookthrough and then calculate factor exposures based on those positions and the updated portfolio weighting. For us to plumb this through the entire platform would be a major rewrite.  We need to decide if we want to do this. It would definitely add a lot of complexity.
After Ben/Elliott meeting:
- Change API from Polygon to something else so we can get access to Mutual Funds as single names.
- Treat them as Tickers in the overall portfolio.  That powers Factor Analysis.
- Create a concentration report that includes Mutual Fund/ETF lookthrough.
- Ben to pick the APIs
Original comments:
- Don't see calculations for these
-Position size: if a portfolio is all stock, this is easy enough. But if a portfolio holds options or ETFs, it is worth highlighting the expected impact of a position to returns. On ETFS, Grok tells me API feeds from Finnworlds, Tradefeeds, TwelveData  and Financial Modeling Prep can provide ETF look through data, and on review of their websites it seems like that is true (and they also provide stock data. I was perhaps too quick ito suggest Polyon without looking at all the offerings.

#### 4.4.2 Position Correlation
- Position Correlation: This is likely a high value add for both all 3 user types. It is easy to have multiple positions that all move in the same direction. This would requrie a historical correlation analysis of each name to each other name in the book. Bloomberg provided this analysis, but it only looked at one stock vs another or vs. the portfolio. 
Elliott's Comments: We need to discuss what this might look like:
- Pairwise correlation grid by name, ordered by exposure
- Portfolio-level correlation metrics - 0 to 1 in a bar chart format

### 4.5. Market Risks: Market Up/Down and Interest Rates
Elliott's Comments: Added this to the plan under 1.4.5 Market Risk Scenarios.  But the rest of the Stress Scenarios from the legacy script are not in the plan. I added it to 1.4.7 Comprehensive Stress Testing Framework. 
- Don't see calculatons for these.
We have market down 10% - probably should be market down 1%. Easy enough, I think, just use the portfolio beta and apply it to the market down 1% and up 1%. Probably should be a back end that optimizes this calculation to see how accurate it acutally is and adjusts accordingly. 
- Interest rate risks. Would have to run back tested calculations of yields and the underlying names in the portfolio and then use this back test of interest rate beta and apply it to each name in the portfolio. 
- Query other risks? This seems harder...tariff risk to earnigns, for example. Would be a lot to model...

### 4.6. Defer work on historical analysis features
Elliott's comments: deferring as much of this as possible.
- simplify the plan based on deferring the historical analysis features

### 4.7. UI will become a chat-centric experience, not a dashboard

### 4.8. Look at where you would pre-calculate for 95% of the market universe daily, and then just pull from the table for an individual portfolio.
- precalculate 98% of market universe daily (approximately 3000 names - Russell, Nasdaq, S&P)
- if a portfolio adds a name not in the precalculated table, then calculate on the fly, and add to the list.
