/**
 * useHomePageData Hook
 *
 * Fetches and aggregates data for the Home page.
 * Provides returns, exposures, volatility, and benchmark data.
 */

import { useState, useEffect } from 'react'
import { useSelectedPortfolioId } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import targetPriceService from '@/services/targetPriceService'
import { benchmarkService } from '@/services/benchmarkService'

export interface ReturnsData {
  portfolio: {
    targetReturnEOY: number | null
    targetReturnNextYear: number | null
  }
  benchmarks: {
    SPY: { m1: number | null; m3: number | null; ytd: number | null; y1: number | null; daily: number | null } | null
    QQQ: { m1: number | null; m3: number | null; ytd: number | null; y1: number | null; daily: number | null } | null
  }
}

export interface ExposuresData {
  equityBalance: number
  longExposure: number
  shortExposure: number
  grossExposure: number
  netExposure: number
  longPct: number
  shortPct: number
  grossPct: number
  netPct: number
}

export interface VolatilityData {
  portfolio: {
    y1: number | null
    d90: number | null
    forward: number | null
  }
  SPY: {
    y1: number | null
    d90: number | null
    forward: number | null
  } | null
  QQQ: {
    y1: number | null
    d90: number | null
    forward: number | null
  } | null
}

export interface HomePageData {
  returns: ReturnsData
  exposures: ExposuresData
  volatility: VolatilityData
  loading: boolean
  error: string | null
  refetch: () => void
}

const defaultReturns: ReturnsData = {
  portfolio: {
    targetReturnEOY: null,
    targetReturnNextYear: null,
  },
  benchmarks: {
    SPY: null,
    QQQ: null,
  },
}

const defaultExposures: ExposuresData = {
  equityBalance: 0,
  longExposure: 0,
  shortExposure: 0,
  grossExposure: 0,
  netExposure: 0,
  longPct: 0,
  shortPct: 0,
  grossPct: 0,
  netPct: 0,
}

const defaultVolatility: VolatilityData = {
  portfolio: {
    y1: null,
    d90: null,
    forward: null,
  },
  SPY: null,
  QQQ: null,
}

export function useHomePageData(): HomePageData {
  const selectedPortfolioId = useSelectedPortfolioId()
  const [returns, setReturns] = useState<ReturnsData>(defaultReturns)
  const [exposures, setExposures] = useState<ExposuresData>(defaultExposures)
  const [volatility, setVolatility] = useState<VolatilityData>(defaultVolatility)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const refetch = () => setRefreshTrigger((prev) => prev + 1)

  useEffect(() => {
    let isCancelled = false

    async function fetchData() {
      if (!selectedPortfolioId) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        // Fetch data in parallel
        const [overviewResult, targetResult, volatilityResult] = await Promise.all([
          analyticsApi.getOverview(selectedPortfolioId).catch((err) => {
            console.warn('Failed to fetch overview:', err)
            return null
          }),
          targetPriceService.summary(selectedPortfolioId).catch((err) => {
            console.warn('Failed to fetch target prices:', err)
            return null
          }),
          analyticsApi.getVolatility(selectedPortfolioId).catch((err) => {
            console.warn('Failed to fetch volatility:', err)
            return null
          }),
        ])

        if (isCancelled) return

        // Process exposures from overview
        if (overviewResult) {
          const overview = overviewResult.data
          const nav = overview.equity_balance || overview.net_asset_value || 0
          setExposures({
            equityBalance: overview.equity_balance || overview.net_asset_value || 0,
            longExposure: overview.exposures?.long_exposure || 0,
            shortExposure: overview.exposures?.short_exposure || 0,
            grossExposure: overview.exposures?.gross_exposure || 0,
            netExposure: overview.exposures?.net_exposure || 0,
            longPct: nav > 0 ? ((overview.exposures?.long_exposure || 0) / nav) * 100 : 0,
            shortPct: nav > 0 ? (Math.abs(overview.exposures?.short_exposure || 0) / nav) * 100 : 0,
            grossPct: nav > 0 ? ((overview.exposures?.gross_exposure || 0) / nav) * 100 : 0,
            netPct: nav > 0 ? ((overview.exposures?.net_exposure || 0) / nav) * 100 : 0,
          })
        }

        // Process target returns
        if (targetResult) {
          setReturns((prev) => ({
            ...prev,
            portfolio: {
              targetReturnEOY: targetResult.weighted_expected_return_eoy || null,
              targetReturnNextYear: targetResult.weighted_expected_return_next_year || null,
            },
          }))
        }

        // Process volatility
        if (volatilityResult) {
          const volResponse = volatilityResult.data
          const volMetrics = volResponse.data
          if (volResponse.available && volMetrics) {
            setVolatility((prev) => ({
              ...prev,
              portfolio: {
                y1: null, // Will be calculated from historical data later
                d90: volMetrics.realized_volatility_63d
                  ? volMetrics.realized_volatility_63d * 100
                  : null,
                forward: volMetrics.expected_volatility_21d
                  ? volMetrics.expected_volatility_21d * 100
                  : null,
              },
            }))
          }
        }

        // Fetch benchmark data (SPY, QQQ) - runs in parallel but doesn't block main data
        benchmarkService.getBenchmarkData(['SPY', 'QQQ']).then((benchmarkData) => {
          if (isCancelled) return

          // Update returns with benchmark data
          setReturns((prev) => ({
            ...prev,
            benchmarks: {
              SPY: benchmarkData.SPY?.returns || null,
              QQQ: benchmarkData.QQQ?.returns || null,
            },
          }))

          // Update volatility with benchmark data
          setVolatility((prev) => ({
            ...prev,
            SPY: benchmarkData.SPY?.volatility || null,
            QQQ: benchmarkData.QQQ?.volatility || null,
          }))
        }).catch((err) => {
          console.warn('Failed to fetch benchmark data:', err)
        })

      } catch (err) {
        if (!isCancelled) {
          console.error('Error fetching home page data:', err)
          setError(err instanceof Error ? err.message : 'Failed to load data')
        }
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()

    return () => {
      isCancelled = true
    }
  }, [selectedPortfolioId, refreshTrigger])

  return {
    returns,
    exposures,
    volatility,
    loading,
    error,
    refetch,
  }
}
