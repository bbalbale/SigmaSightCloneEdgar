/**
 * Benchmark Service
 *
 * Provides benchmark data (SPY, QQQ) including:
 * - Historical returns (1M, 3M, YTD, 1Y) calculated from price data
 * - Volatility metrics (1Y, 90D) calculated from price data
 * - Daily change data from factor ETF endpoint
 */

import { apiClient } from './apiClient'

export interface BenchmarkReturns {
  m1: number | null
  m3: number | null
  ytd: number | null
  y1: number | null
  daily: number | null
}

export interface BenchmarkVolatility {
  y1: number | null
  d90: number | null
  forward: number | null // Not available for benchmarks
}

export interface BenchmarkData {
  returns: BenchmarkReturns
  volatility: BenchmarkVolatility
  currentPrice: number | null
  available: boolean
}

interface BenchmarkHistoricalResponse {
  symbol: string
  available: boolean
  message?: string
  metadata: {
    lookback_days: number
    start_date: string
    end_date: string
    trading_days_found: number
    first_date?: string
    last_date?: string
  }
  data: {
    dates: string[]
    open: number[]
    high: number[]
    low: number[]
    close: number[]
    volume: number[]
  } | null
}

interface FactorETFResponse {
  [symbol: string]: {
    factor_name: string
    symbol: string
    current_price: number
    open?: number
    high?: number
    low?: number
    volume?: number
    date?: string
    updated_at?: string
    data_source?: string
    daily_return?: number
    change_percent?: number
  }
}

// Cache for benchmark data to reduce API calls
const benchmarkCache: Record<string, { data: BenchmarkData; timestamp: number }> = {}
const CACHE_DURATION_MS = 5 * 60 * 1000 // 5 minutes

/**
 * Default empty benchmark data
 */
const emptyBenchmarkData: BenchmarkData = {
  returns: { m1: null, m3: null, ytd: null, y1: null, daily: null },
  volatility: { y1: null, d90: null, forward: null },
  currentPrice: null,
  available: false,
}

/**
 * Calculate return percentage between two prices
 */
function calculateReturn(currentPrice: number, previousPrice: number): number {
  return ((currentPrice - previousPrice) / previousPrice) * 100
}

/**
 * Calculate annualized volatility from daily returns
 * @param prices Array of closing prices (oldest to newest)
 * @param tradingDays Number of trading days to use
 * @returns Annualized volatility as a percentage
 */
function calculateVolatility(prices: number[], tradingDays: number): number | null {
  if (prices.length < tradingDays + 1) {
    return null
  }

  // Get the last N+1 prices to calculate N returns
  const recentPrices = prices.slice(-(tradingDays + 1))

  // Calculate daily returns
  const dailyReturns: number[] = []
  for (let i = 1; i < recentPrices.length; i++) {
    const dailyReturn = (recentPrices[i] - recentPrices[i - 1]) / recentPrices[i - 1]
    dailyReturns.push(dailyReturn)
  }

  if (dailyReturns.length === 0) {
    return null
  }

  // Calculate mean return
  const meanReturn = dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length

  // Calculate variance
  const variance =
    dailyReturns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) / dailyReturns.length

  // Calculate standard deviation
  const stdDev = Math.sqrt(variance)

  // Annualize (252 trading days per year)
  const annualizedVol = stdDev * Math.sqrt(252) * 100

  return annualizedVol
}

/**
 * Find the price at or closest to a target date
 */
function findPriceAtDate(
  dates: string[],
  closes: number[],
  targetDate: Date
): { price: number; date: string } | null {
  const targetStr = targetDate.toISOString().split('T')[0]

  // Look for exact match or closest date before target
  let bestIndex = -1
  let bestDate: string | null = null

  for (let i = 0; i < dates.length; i++) {
    const dateStr = dates[i]
    if (dateStr <= targetStr) {
      bestIndex = i
      bestDate = dateStr
    } else {
      break
    }
  }

  if (bestIndex >= 0 && bestDate) {
    return { price: closes[bestIndex], date: bestDate }
  }

  return null
}

/**
 * Fetch historical benchmark data from backend
 */
async function fetchBenchmarkHistoricalData(
  symbol: string
): Promise<BenchmarkHistoricalResponse | null> {
  try {
    const response = await apiClient.get<BenchmarkHistoricalResponse>(
      `/api/v1/data/prices/benchmark/${symbol}?lookback_days=400`
    )
    return response
  } catch (error) {
    console.warn(`Failed to fetch benchmark historical data for ${symbol}:`, error)
    return null
  }
}

/**
 * Fetch factor ETF data from backend (for daily change)
 */
async function fetchFactorETFData(): Promise<FactorETFResponse | null> {
  try {
    const response = await apiClient.get<FactorETFResponse>('/api/v1/data/factors/etf-prices')
    return response
  } catch (error) {
    console.warn('Failed to fetch factor ETF prices:', error)
    return null
  }
}

/**
 * Calculate returns from historical price data
 */
function calculateReturnsFromHistory(
  dates: string[],
  closes: number[],
  dailyChange: number | null
): BenchmarkReturns {
  if (closes.length === 0) {
    return { m1: null, m3: null, ytd: null, y1: null, daily: dailyChange }
  }

  const currentPrice = closes[closes.length - 1]
  const today = new Date()

  // Calculate 1M return (~21 trading days ago, use 30 calendar days)
  const oneMonthAgo = new Date(today)
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
  const m1Data = findPriceAtDate(dates, closes, oneMonthAgo)
  const m1 = m1Data ? calculateReturn(currentPrice, m1Data.price) : null

  // Calculate 3M return (~63 trading days ago, use 90 calendar days)
  const threeMonthsAgo = new Date(today)
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3)
  const m3Data = findPriceAtDate(dates, closes, threeMonthsAgo)
  const m3 = m3Data ? calculateReturn(currentPrice, m3Data.price) : null

  // Calculate YTD return (from Jan 1 of current year)
  const yearStart = new Date(today.getFullYear(), 0, 1)
  const ytdData = findPriceAtDate(dates, closes, yearStart)
  const ytd = ytdData ? calculateReturn(currentPrice, ytdData.price) : null

  // Calculate 1Y return (~252 trading days ago, use 365 calendar days)
  const oneYearAgo = new Date(today)
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
  const y1Data = findPriceAtDate(dates, closes, oneYearAgo)
  const y1 = y1Data ? calculateReturn(currentPrice, y1Data.price) : null

  return { m1, m3, ytd, y1, daily: dailyChange }
}

/**
 * Calculate volatility from historical price data
 */
function calculateVolatilityFromHistory(closes: number[]): BenchmarkVolatility {
  if (closes.length === 0) {
    return { y1: null, d90: null, forward: null }
  }

  // 1-year volatility (252 trading days)
  const y1 = calculateVolatility(closes, 252)

  // 90-day volatility
  const d90 = calculateVolatility(closes, 90)

  return { y1, d90, forward: null }
}

/**
 * Fetch and calculate complete benchmark data for a symbol
 */
async function fetchBenchmarkData(symbol: string): Promise<BenchmarkData> {
  // Check cache
  const cached = benchmarkCache[symbol]
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION_MS) {
    return cached.data
  }

  try {
    // Fetch both historical data and factor ETF data in parallel
    const [historicalData, factorData] = await Promise.all([
      fetchBenchmarkHistoricalData(symbol),
      fetchFactorETFData(),
    ])

    // Get daily change from factor ETF data
    const dailyChange = factorData?.[symbol]?.daily_return ?? factorData?.[symbol]?.change_percent ?? null
    const currentPrice = factorData?.[symbol]?.current_price ?? null

    if (historicalData?.available && historicalData.data) {
      const { dates, close: closes } = historicalData.data

      const returns = calculateReturnsFromHistory(dates, closes, dailyChange)
      const volatility = calculateVolatilityFromHistory(closes)

      const data: BenchmarkData = {
        returns,
        volatility,
        currentPrice: currentPrice ?? closes[closes.length - 1] ?? null,
        available: true,
      }

      // Update cache
      benchmarkCache[symbol] = { data, timestamp: Date.now() }
      return data
    }

    // No historical data available, return what we have from factor ETF
    if (factorData?.[symbol]) {
      const data: BenchmarkData = {
        returns: { m1: null, m3: null, ytd: null, y1: null, daily: dailyChange },
        volatility: { y1: null, d90: null, forward: null },
        currentPrice,
        available: true,
      }

      benchmarkCache[symbol] = { data, timestamp: Date.now() }
      return data
    }

    return emptyBenchmarkData
  } catch (error) {
    console.warn(`Failed to fetch benchmark data for ${symbol}:`, error)
    return emptyBenchmarkData
  }
}

/**
 * Get benchmark returns for multiple symbols
 */
export async function getBenchmarkReturns(
  symbols: string[]
): Promise<Record<string, BenchmarkReturns>> {
  const results: Record<string, BenchmarkReturns> = {}

  // Fetch all symbols in parallel
  const promises = symbols.map((symbol) => fetchBenchmarkData(symbol))
  const benchmarkDataResults = await Promise.all(promises)

  symbols.forEach((symbol, index) => {
    results[symbol] = benchmarkDataResults[index].returns
  })

  return results
}

/**
 * Get benchmark volatility for multiple symbols
 */
export async function getBenchmarkVolatility(
  symbols: string[]
): Promise<Record<string, BenchmarkVolatility>> {
  const results: Record<string, BenchmarkVolatility> = {}

  // Fetch all symbols in parallel
  const promises = symbols.map((symbol) => fetchBenchmarkData(symbol))
  const benchmarkDataResults = await Promise.all(promises)

  symbols.forEach((symbol, index) => {
    results[symbol] = benchmarkDataResults[index].volatility
  })

  return results
}

/**
 * Get all benchmark data (returns + volatility) for multiple symbols
 */
export async function getBenchmarkData(
  symbols: string[]
): Promise<Record<string, BenchmarkData>> {
  const results: Record<string, BenchmarkData> = {}

  // Fetch all symbols in parallel
  const promises = symbols.map((symbol) => fetchBenchmarkData(symbol))
  const benchmarkDataResults = await Promise.all(promises)

  symbols.forEach((symbol, index) => {
    results[symbol] = benchmarkDataResults[index]
  })

  return results
}

/**
 * Clear the benchmark cache
 */
export function clearBenchmarkCache(): void {
  Object.keys(benchmarkCache).forEach((key) => delete benchmarkCache[key])
}

export const benchmarkService = {
  getBenchmarkReturns,
  getBenchmarkVolatility,
  getBenchmarkData,
  clearBenchmarkCache,
}
