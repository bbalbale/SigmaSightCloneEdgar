# Polygon API Endpoints Required for SigmaSight

## Overview
This document lists all Polygon API endpoints needed for full functionality of the SigmaSight portfolio analytics system, organized by priority and use case.

---

## 🔴 CRITICAL - Required for Core Functionality

### 1. Options Contracts Reference Data
**Endpoint**: `/v3/reference/options/contracts`  
**Status**: ✅ Working on Starter Plan  
**Usage**: List all options contracts for a given underlying ticker  
**Why Critical**: Need strike prices, expiration dates, and contract types for portfolio positions  

### 2. Options Last Trade
**Endpoint**: `/v2/last/trade/{options_ticker}`  
**Status**: ❌ NOT AUTHORIZED on Starter Plan  
**Usage**: Get the most recent trade price for an options contract  
**Example**: `/v2/last/trade/O:AAPL250117C00150000`  
**Why Critical**: Required for:
- Current market value calculations
- P&L calculations  
- Greeks calculations (need current option price)
- Position valuation

### 3. Stock/ETF Last Trade
**Endpoint**: `/v2/last/trade/{ticker}`  
**Status**: ❌ NOT AUTHORIZED on Starter Plan  
**Usage**: Get the most recent trade price for stocks/ETFs  
**Example**: `/v2/last/trade/AAPL`  
**Why Critical**: Required for:
- Underlying price for options Greeks
- Stock position valuations
- Real-time portfolio value

### 4. Options Aggregates (OHLC Bars)
**Endpoint**: `/v2/aggs/ticker/{options_ticker}/range/{multiplier}/{timespan}/{from}/{to}`  
**Status**: ❌ NOT AUTHORIZED on Starter Plan  
**Usage**: Historical OHLC data for options contracts  
**Example**: `/v2/aggs/ticker/O:AAPL250117C00150000/range/1/day/2024-01-01/2024-12-31`  
**Why Critical**: Required for:
- Historical volatility calculations
- Options price trends
- Backtesting

---

## 🟡 IMPORTANT - Needed for Advanced Features

### 5. Options Chain Snapshot
**Endpoint**: `/v3/snapshot/options/{underlyingTicker}`  
**Status**: ❌ Unknown availability  
**Usage**: Get a snapshot of an entire options chain with current prices  
**Example**: `/v3/snapshot/options/AAPL`  
**Why Important**: 
- Bulk pricing for entire options chain
- More efficient than individual contract queries
- Implied volatility surface analysis

### 6. Options Quotes (Bid/Ask)
**Endpoint**: `/v3/quotes/{options_ticker}`  
**Status**: ❌ Likely requires Advanced plan  
**Usage**: Real-time bid/ask spreads for options  
**Example**: `/v3/quotes/O:AAPL250117C00150000`  
**Why Important**:
- More accurate valuations using mid-price
- Spread analysis for trading costs
- Liquidity assessment

### 7. Stock/ETF Aggregates (OHLC Bars)
**Endpoint**: `/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`  
**Status**: ⚠️ Partially working (limited history on Starter)  
**Usage**: Historical OHLC data for stocks/ETFs  
**Example**: `/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-12-31`  
**Why Important**:
- Factor analysis (need 150 days history, previously 252d)
- Correlation calculations
- Performance analytics

### 8. Options Trades Stream
**Endpoint**: `/v3/trades/{options_ticker}`  
**Status**: ❌ Requires Developer plan or higher  
**Usage**: Stream of individual trades for options  
**Why Important**:
- Volume analysis
- Trade flow analytics
- More granular price discovery

---

## 🟢 NICE TO HAVE - Enhanced Analytics

### 9. Options Greeks from Polygon
**Endpoint**: `/v2/snapshot/options/{underlyingTicker}/{contract}/greeks`  
**Status**: ❌ May not exist  
**Usage**: Pre-calculated Greeks from Polygon  
**Why Nice**: Would save computation, though we calculate our own

### 10. Implied Volatility
**Endpoint**: `/v3/reference/options/contracts/{options_ticker}/iv`  
**Status**: ❌ May not exist  
**Usage**: IV data for options contracts  
**Why Nice**: Better Greeks calculations

### 11. Open Interest
**Endpoint**: Part of snapshot or contracts endpoint  
**Status**: ⚠️ Partially available  
**Usage**: Open interest for options contracts  
**Why Nice**: Liquidity and sentiment analysis

---

## Current Workarounds

Since we only have Starter Plan access, we're using:

1. **FMP for all stock/ETF prices** instead of Polygon endpoints 3, 7
2. **No options pricing** - missing endpoints 2, 4, 5, 6, 8
3. **Theoretical Greeks** - calculating ourselves since we can't get option prices

---

## Minimum Required Plan

Based on endpoint requirements:

### For Demo/Development:
- **Current Starter Plan + FMP**: Workable with limitations
- Missing: Real options valuations

### For Production:
- **Developer Plan ($79)**: Would need to verify it includes:
  - `/v2/last/trade/{options_ticker}` ❓
  - `/v2/aggs/ticker/{options_ticker}/...` ❓
  
- **Advanced Plan ($199)**: Likely includes all needed endpoints
  - Real-time data
  - Quotes endpoint
  - Trades endpoint
  - Need to confirm options coverage

---

## Questions for Polygon Support

1. **Which plan includes `/v2/last/trade/` for OPTIONS (not just stocks)?**
2. **Does Developer plan include options aggregates/bars?**
3. **Is options snapshot available on any plan?**
4. **Can we get a trial of Developer/Advanced to test options endpoints?**
5. **Any discounts for startups or annual prepayment?**

---

## Priority for Upgrade

If upgrading, we absolutely need:
1. Options last trade prices (endpoint #2)
2. Stock last trade prices (endpoint #3) 
3. Options historical bars (endpoint #4)

These three endpoints would restore full functionality for:
- Portfolio valuations
- Greeks calculations  
- P&L reporting
- Risk analytics