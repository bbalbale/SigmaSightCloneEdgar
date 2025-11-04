import { useState, useEffect } from 'react'
import { useSelectedPortfolioId } from '@/stores/portfolioStore'
import { fetchPortfolioSnapshot } from '@/services/portfolioService'
import { analyticsApi } from '@/services/analyticsApi'
import targetPriceService from '@/services/targetPriceService'
import { portfolioService } from '@/services/portfolioApi'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'

interface HeroMetrics {
  equityBalance: number
  targetReturnEOY: number
  grossExposure: number
  netExposure: number
  longExposure: number
  shortExposure: number
}

interface PerformanceMetrics {
  ytdPnl: number
  mtdPnl: number
  cashBalance: number
  portfolioBeta90d: number | null
  portfolioBeta1y: number | null
  stressTest: { up: number; down: number } | null
}

interface HoldingRow {
  id: string
  symbol: string
  quantity: number
  entryPrice: number
  todaysPrice: number
  targetPrice: number | null
  marketValue: number
  weight: number
  pnlToday: number | null
  pnlTotal: number
  returnPct: number
  targetReturn: number | null
  beta: number | null
  positionType: string
  investmentClass: string
  account_name?: string // For aggregate view - which account/portfolio this holding belongs to
  portfolio_id?: string // For grouping in aggregate view
}

interface RiskMetrics {
  portfolioBeta90d: number | null
  portfolioBeta1y: number | null
  topSector: { name: string; weight: number; vs_sp: number } | null
  largestPosition: { symbol: string; weight: number } | null
  spCorrelation: number | null
  stressTest: { up: number; down: number } | null
}

interface UseCommandCenterDataReturn {
  heroMetrics: HeroMetrics
  performanceMetrics: PerformanceMetrics
  holdings: HoldingRow[]
  riskMetrics: RiskMetrics
  loading: boolean
  error: string | null
}

const normalizeNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) {
    return null
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const calculateWeightedReturnByMarketValue = (
  positions: EnhancedPosition[],
  returnField: 'target_return_eoy' | 'target_return_next_year',
  fallbackField?: 'analyst_return_eoy' | 'analyst_return_next_year'
): number | null => {
  let weightedSum = 0
  let totalWeight = 0

  positions.forEach(position => {
    const marketValue = normalizeNumber(position.current_market_value ?? position.market_value) ?? 0
    const weight = Math.abs(marketValue)
    if (weight === 0) {
      return
    }

    const primary = normalizeNumber(position[returnField])
    const fallback = fallbackField ? normalizeNumber(position[fallbackField]) : null
    const effectiveReturn = primary ?? fallback ?? 0

    weightedSum += effectiveReturn * weight
    totalWeight += weight
  })

  if (totalWeight === 0) {
    return null
  }
  return weightedSum / totalWeight
}

export function useCommandCenterData(refreshTrigger?: number): UseCommandCenterDataReturn {
  const portfolioId = useSelectedPortfolioId()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [heroMetrics, setHeroMetrics] = useState<HeroMetrics>({
    equityBalance: 0,
    targetReturnEOY: 0,
    grossExposure: 0,
    netExposure: 0,
    longExposure: 0,
    shortExposure: 0
  })

  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    ytdPnl: 0,
    mtdPnl: 0,
    cashBalance: 0,
    portfolioBeta90d: null,
    portfolioBeta1y: null,
    stressTest: null
  })

  const [holdings, setHoldings] = useState<HoldingRow[]>([])
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics>({
    portfolioBeta90d: null,
    portfolioBeta1y: null,
    topSector: null,
    largestPosition: null,
    spCorrelation: null,
    stressTest: null
  })

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)

      try {
        // AGGREGATE VIEW: Fetch data across all portfolios
        if (!portfolioId) {
          const portfolios = await portfolioService.getPortfolios()
          if (portfolios.length === 0) {
            setHeroMetrics({
              equityBalance: 0,
              targetReturnEOY: 0,
              grossExposure: 0,
              netExposure: 0,
              longExposure: 0,
              shortExposure: 0
            })
            setHoldings([])
            setPerformanceMetrics({
              ytdPnl: 0,
              mtdPnl: 0,
              cashBalance: 0,
              portfolioBeta90d: null,
              portfolioBeta1y: null,
              stressTest: null
            })
            setRiskMetrics({
              portfolioBeta90d: null,
              portfolioBeta1y: null,
              topSector: null,
              largestPosition: null,
              spCorrelation: null,
              stressTest: null
            })
            setLoading(false)
            return
          }

          const [aggregateAnalytics, enhancedResults] = await Promise.all([
            portfolioService.getAggregateAnalytics().catch(err => {
              console.warn('[useCommandCenterData] Failed to fetch aggregate analytics:', err)
              return null
            }),
            Promise.all(
              portfolios.map(async portfolio => {
                try {
                  const enhanced = await positionResearchService.fetchEnhancedPositions({ portfolioId: portfolio.id })
                  return { portfolio, enhanced }
                } catch (err) {
                  console.warn(`[useCommandCenterData] Failed to fetch enhanced positions for portfolio ${portfolio.id}:`, err)
                  return { portfolio, enhanced: { positions: [], longPositions: [], shortPositions: [], portfolioEquity: 0 } }
                }
              })
            )
          ])

          const combinedPositions = enhancedResults.flatMap(({ portfolio, enhanced }) =>
            enhanced.positions.map(position => ({
              portfolio,
              position
            }))
          )

          const allEnhancedPositions = combinedPositions.map(item => item.position)
          const totalNav = portfolios.reduce((sum, p) => {
            const nav = typeof p.net_asset_value === 'number'
              ? p.net_asset_value
              : typeof p.total_value === 'number'
                ? p.total_value
                : 0
            return sum + (nav > 0 ? nav : 0)
          }, 0)

          let grossExposure = 0
          let netExposure = 0
          let longExposure = 0
          let shortExposure = 0

          combinedPositions.forEach(({ position }) => {
            const marketValue = normalizeNumber(position.current_market_value ?? position.market_value) ?? 0
            const absValue = Math.abs(marketValue)
            grossExposure += absValue
            netExposure += marketValue
            if (marketValue >= 0) {
              longExposure += marketValue
            } else {
              shortExposure += marketValue
            }
          })

          const combinedHoldings: HoldingRow[] = combinedPositions.map(({ portfolio, position }) => {
            const marketValue = normalizeNumber(position.current_market_value ?? position.market_value) ?? 0
            const percentOfEquity = normalizeNumber(position.percent_of_equity)
            const weightBase = totalNav > 0 ? totalNav : grossExposure
            const weight = percentOfEquity !== null
              ? percentOfEquity
              : weightBase > 0
                ? (marketValue / weightBase) * 100
                : 0
          const returnPct = normalizeNumber(position.unrealized_pnl_percent) ?? 0
          const targetPrice =
            normalizeNumber(position.user_target_eoy) ??
            normalizeNumber(position.target_mean_price) ??
            null
          const targetReturn =
            normalizeNumber(position.target_return_eoy) ??
            normalizeNumber(position.analyst_return_eoy) ??
            null

            return {
              id: position.id,
              symbol: position.symbol,
              quantity: position.quantity ?? 0,
              entryPrice: normalizeNumber(position.avg_cost ?? position.entry_price) ?? 0,
              todaysPrice: normalizeNumber(position.current_price ?? (position as any).price) ?? 0,
              targetPrice,
              marketValue,
              weight,
              pnlToday: null,
              pnlTotal: normalizeNumber(position.unrealized_pnl ?? position.pnl) ?? 0,
              returnPct,
              targetReturn,
              beta: normalizeNumber(position.beta),
              positionType: (position.position_type as string) || 'LONG',
              investmentClass: (position.investment_class as string) || 'PUBLIC',
              account_name: portfolio.account_name || portfolio.name || 'Portfolio',
              portfolio_id: portfolio.id
            }
          })

          combinedHoldings.sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
          setHoldings(combinedHoldings)

          const aggregateTargetReturnEOY = calculateWeightedReturnByMarketValue(
            allEnhancedPositions,
            'target_return_eoy',
            'analyst_return_eoy'
          ) ?? 0

          setHeroMetrics({
            equityBalance: aggregateAnalytics?.net_asset_value ?? totalNav,
            targetReturnEOY: aggregateTargetReturnEOY,
            grossExposure,
            netExposure,
            longExposure,
            shortExposure
          })

          setPerformanceMetrics({
            ytdPnl: aggregateAnalytics?.total_realized_pnl ?? 0,
            mtdPnl: 0,
            cashBalance: 0,
            portfolioBeta90d: aggregateAnalytics?.risk_metrics?.portfolio_beta ?? null,
            portfolioBeta1y: null,
            stressTest: null
          })

          const largestHolding = combinedHoldings[0] ?? null
          const topSector = aggregateAnalytics?.sector_allocation?.[0]

          setRiskMetrics({
            portfolioBeta90d: aggregateAnalytics?.risk_metrics?.portfolio_beta ?? null,
            portfolioBeta1y: null,
            topSector: topSector
              ? { name: topSector.sector, weight: topSector.pct_of_total, vs_sp: 0 }
              : null,
            largestPosition: largestHolding
              ? { symbol: largestHolding.symbol, weight: largestHolding.weight }
              : null,
            spCorrelation: null,
            stressTest: null
          })

          setLoading(false)
          return
        }

        // INDIVIDUAL PORTFOLIO VIEW: Existing logic
        console.log('[useCommandCenterData] Fetching individual portfolio data for:', portfolioId)

        // Fetch all data in parallel
        const [
          overviewRaw,
          snapshot,
          enhancedPositionsResult,
          targetSummary,
          sectorData,
          correlationData,
          positionBetas,
          portfolioFactors
        ] = await Promise.all([
          analyticsApi.getOverview(portfolioId),
          fetchPortfolioSnapshot(portfolioId),
          positionResearchService.fetchEnhancedPositions({ portfolioId }),
          targetPriceService.summary(portfolioId).catch((err) => {
            console.warn('[useCommandCenterData] Failed to fetch target summary:', err)
            return null
          }),
          analyticsApi.getSectorExposure(portfolioId).catch(() => ({ data: { available: false } })),
          analyticsApi.getCorrelationMatrix(portfolioId).catch(() => ({ data: { available: false } })),
          analyticsApi.getPositionFactorExposures(portfolioId).catch(() => ({ data: { available: false, positions: [] } })),
          analyticsApi.getPortfolioFactorExposures(portfolioId).catch(() => ({ data: { available: false, factors: [] } }))
        ])

        // Extract hero metrics from raw overview response
        const overviewResponse = overviewRaw.data
        const exposuresRaw = overviewResponse.exposures || {}
        const equityBalance = overviewResponse.equity_balance || 0
        const cashBalance = overviewResponse.cash_balance || 0

        // Process holdings table
        const enhancedPositions = enhancedPositionsResult.positions || []
        console.log('[useCommandCenterData] Enhanced positions count:', enhancedPositions.length)
        if (enhancedPositions.length > 0) {
          console.log('[useCommandCenterData] Sample enhanced position:', enhancedPositions[0])
        }

        const betaMap = new Map<string, number>()
        if (positionBetas.data.available && positionBetas.data.positions) {
          positionBetas.data.positions.forEach(pos => {
            const marketBeta = pos.exposures['Market Beta']
            if (marketBeta !== undefined && marketBeta !== null) {
              betaMap.set(pos.symbol, marketBeta)
            }
          })
        }

        const holdingsData: HoldingRow[] = enhancedPositions.map((pos: EnhancedPosition) => {
          const marketValue = normalizeNumber(pos.current_market_value ?? pos.market_value) ?? 0
          const percentOfEquity = normalizeNumber(pos.percent_of_equity)
          const weight = percentOfEquity !== null
            ? percentOfEquity
            : equityBalance !== 0
              ? (marketValue / equityBalance) * 100
              : 0
          const returnPct = normalizeNumber(pos.unrealized_pnl_percent) ?? 0
          const targetPrice =
            normalizeNumber(pos.user_target_eoy) ??
            normalizeNumber(pos.target_mean_price) ??
            null
          const targetReturn =
            normalizeNumber(pos.target_return_eoy) ??
            normalizeNumber(pos.analyst_return_eoy) ??
            null

          const pnlToday = normalizeNumber(snapshot?.daily_pnl)

          return {
            id: pos.id,
            symbol: pos.symbol,
            quantity: pos.quantity ?? 0,
            entryPrice: normalizeNumber(pos.avg_cost ?? pos.entry_price) ?? 0,
            todaysPrice: normalizeNumber(pos.current_price ?? (pos as any).price) ?? 0,
            targetPrice,
            marketValue,
            weight,
            pnlToday: pnlToday !== null ? (pnlToday * weight) / 100 : null,
            pnlTotal: normalizeNumber(pos.unrealized_pnl ?? pos.pnl) ?? 0,
            returnPct,
            targetReturn,
            beta: betaMap.get(pos.symbol) ?? normalizeNumber(pos.beta),
            positionType: (pos.position_type as string) || 'LONG',
            investmentClass: (pos.investment_class as string) || 'PUBLIC'
          }
        })

        holdingsData.sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
        setHoldings(holdingsData)

        const summaryTargetReturn = normalizeNumber(targetSummary?.weighted_expected_return_eoy)
        const computedTargetReturn = calculateWeightedReturnByMarketValue(
          enhancedPositions,
          'target_return_eoy',
          'analyst_return_eoy'
        )
        const snapshotTargetReturn = normalizeNumber(snapshot?.target_price_return_eoy)

        const heroTargetReturnEOY =
          snapshotTargetReturn ??
          summaryTargetReturn ??
          computedTargetReturn ??
          0

        setHeroMetrics({
          equityBalance,
          targetReturnEOY: heroTargetReturnEOY,
          grossExposure: exposuresRaw.gross_exposure || 0,
          netExposure: exposuresRaw.net_exposure || 0,
          longExposure: exposuresRaw.long_exposure || 0,
          shortExposure: exposuresRaw.short_exposure || 0,
        })

        // Process risk metrics
        // Extract portfolio betas from factor exposures
        let beta90d = null
        let beta1y = null

        if (portfolioFactors.data?.available && portfolioFactors.data?.factors) {
          const factors = portfolioFactors.data.factors
          const beta90dFactor = factors.find((f: any) => f.name === 'Market Beta (Calculated 90d)')
          const beta1yFactor = factors.find((f: any) => f.name === 'Market Beta (Provider 1y)')

          beta90d = beta90dFactor?.beta || null
          beta1y = beta1yFactor?.beta || null

          console.log('📊 Portfolio Beta from factors - 90d:', beta90d, '1y:', beta1y)
        } else {
          console.log('⚠️ Portfolio factor exposures not available')
        }

        // Top Sector from sector exposure
        let topSector = null
        if ('data' in sectorData) {
          const sectorResponse = sectorData as { data: { available: boolean; data?: any } }
          if (sectorResponse.data.available && sectorResponse.data.data) {
            const sectors = sectorResponse.data.data.portfolio_weights || {}
            const benchmarkWeights = sectorResponse.data.data.benchmark_weights || {}

            const sectorEntries = Object.entries(sectors).map(([name, weight]) => ({
              name,
              weight: (weight as number) * 100,
              vs_sp: ((weight as number) - (benchmarkWeights[name] as number || 0)) * 100
            }))

            if (sectorEntries.length > 0) {
              const top = sectorEntries.sort((a, b) => b.weight - a.weight)[0]
              topSector = top
            }
          }
        }

        // Largest position from holdings
        let largestPosition = null
        if (holdingsData.length > 0) {
          const sorted = [...holdingsData].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
          largestPosition = {
            symbol: sorted[0].symbol,
            weight: sorted[0].weight
          }
        }

        // S&P Correlation from correlation matrix
        let spCorrelation = null
        if ('data' in correlationData) {
          const corrResponse = correlationData as { data: { available: boolean; data?: any } }
          if (corrResponse.data.available && corrResponse.data.data) {
            const matrix = corrResponse.data.data.matrix
            // Look for SPY correlation (portfolio's correlation to SPY)
            if (matrix['SPY']) {
              // Find portfolio correlation in SPY row
              const portfolioCorr = Object.entries(matrix['SPY']).find(([key]) =>
                key.toLowerCase().includes('portfolio') || key === 'PORTFOLIO'
              )
              if (portfolioCorr) {
                spCorrelation = portfolioCorr[1] as number
              }
            }
          }
        }

        // Stress test (±1% market move) - calculate manually
        let stressTest = null
        const netExp = exposuresRaw.net_exposure || 0
        if (beta1y !== null && netExp !== 0) {
          stressTest = {
            up: netExp * beta1y * 0.01,
            down: netExp * beta1y * -0.01
          }
        }

        setRiskMetrics({
          portfolioBeta90d: beta90d,
          portfolioBeta1y: beta1y,
          topSector,
          largestPosition,
          spCorrelation,
          stressTest
        })

        // Set performance metrics with real YTD/MTD P&L from backend
        const pnlData = overviewResponse.pnl || {}

        setPerformanceMetrics({
          ytdPnl: pnlData.ytd_pnl || 0,
          mtdPnl: pnlData.mtd_pnl || 0,
          cashBalance,
          portfolioBeta90d: beta90d,
          portfolioBeta1y: beta1y,
          stressTest
        })

        setLoading(false)
      } catch (err: any) {
        console.error('Failed to load Command Center data:', err)
        setError(err.message || 'Failed to load data')
        setLoading(false)
      }
    }

    fetchData().catch((err) => {
      console.error('[useCommandCenterData] Unhandled error:', err)
      setError(err instanceof Error ? err.message : 'Failed to load data')
      setLoading(false)
    })
  }, [portfolioId, refreshTrigger])

  return {
    heroMetrics,
    performanceMetrics,
    holdings,
    riskMetrics,
    loading,
    error
  }
}
