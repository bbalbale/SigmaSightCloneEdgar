import { useState, useEffect } from 'react'
import { useSelectedPortfolioId } from '@/stores/portfolioStore'
import { loadPortfolioData, fetchPortfolioSnapshot } from '@/services/portfolioService'
import { analyticsApi } from '@/services/analyticsApi'
import targetPriceService from '@/services/targetPriceService'
import { portfolioService } from '@/services/portfolioApi'

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
          console.log('[useCommandCenterData] Fetching aggregate view data')

          // Fetch all portfolios to get account names
          const portfolios = await portfolioService.getPortfolios()
          console.log('[useCommandCenterData] Fetched portfolios:', portfolios)

          // Create portfolio ID to account name map
          const portfolioMap = new Map<string, string>()
          portfolios.forEach(p => {
            portfolioMap.set(p.id, p.account_name)
          })

          // Fetch aggregate analytics
          const aggregateAnalytics = await portfolioService.getAggregateAnalytics()
          console.log('[useCommandCenterData] Aggregate analytics:', aggregateAnalytics)

          // Fetch positions for each portfolio and combine them
          const positionPromises = portfolios.map(p => portfolioService.getPositionDetails(p.id))
          const positionArrays = await Promise.all(positionPromises)
          const allPositions = positionArrays.flat()

          // Set hero metrics from aggregate data
          setHeroMetrics({
            equityBalance: aggregateAnalytics.net_asset_value,
            targetReturnEOY: 0, // TODO: Calculate from aggregate target prices
            grossExposure: 0, // TODO: Calculate from positions
            netExposure: 0, // TODO: Calculate from positions
            longExposure: 0, // TODO: Calculate from positions
            shortExposure: 0, // TODO: Calculate from positions
          })

          // Process holdings with account names
          const totalValue = aggregateAnalytics.net_asset_value
          const holdingsData: HoldingRow[] = allPositions.map((pos: any) => {
            const weight = totalValue > 0 ? (Math.abs(pos.marketValue || 0) / totalValue) * 100 : 0
            const returnPct = pos.marketValue !== 0 ? ((pos.pnl || 0) / Math.abs(pos.marketValue)) * 100 : 0

            return {
              id: pos.id,
              symbol: pos.symbol,
              quantity: pos.quantity,
              entryPrice: pos.entry_price || 0,
              todaysPrice: pos.price || 0,
              targetPrice: null, // TODO: Fetch target prices
              marketValue: pos.marketValue || 0,
              weight,
              pnlToday: null, // TODO: Calculate from snapshot
              pnlTotal: pos.pnl || 0,
              returnPct,
              targetReturn: null, // TODO: Calculate from target prices
              beta: null, // TODO: Fetch from position factor exposures
              positionType: pos.type || 'LONG',
              investmentClass: pos.investment_class || 'PUBLIC',
              account_name: portfolioMap.get(pos.portfolio_id) || 'Unknown Account',
              portfolio_id: pos.portfolio_id
            }
          })

          // Sort holdings by portfolio_id and then by weight
          holdingsData.sort((a, b) => {
            if (a.portfolio_id !== b.portfolio_id) {
              return (a.portfolio_id || '').localeCompare(b.portfolio_id || '')
            }
            return Math.abs(b.weight) - Math.abs(a.weight)
          })

          setHoldings(holdingsData)

          // Set performance metrics
          setPerformanceMetrics({
            ytdPnl: aggregateAnalytics.total_realized_pnl || 0,
            mtdPnl: 0, // TODO: Calculate MTD from snapshots
            cashBalance: 0, // TODO: Calculate from portfolios
            portfolioBeta90d: aggregateAnalytics.risk_metrics?.portfolio_beta || null,
            portfolioBeta1y: null,
            stressTest: null,
          })

          // Set risk metrics
          setRiskMetrics({
            portfolioBeta90d: aggregateAnalytics.risk_metrics?.portfolio_beta || null,
            portfolioBeta1y: null,
            topSector: aggregateAnalytics.sector_allocation?.[0] ? {
              name: aggregateAnalytics.sector_allocation[0].sector,
              weight: aggregateAnalytics.sector_allocation[0].pct_of_total,
              vs_sp: 0 // TODO: Calculate vs S&P
            } : null,
            largestPosition: aggregateAnalytics.top_holdings?.[0] ? {
              symbol: aggregateAnalytics.top_holdings[0].symbol,
              weight: aggregateAnalytics.top_holdings[0].pct_of_total
            } : null,
            spCorrelation: null,
            stressTest: null,
          })

          setLoading(false)
          return
        }

        // INDIVIDUAL PORTFOLIO VIEW: Existing logic
        console.log('[useCommandCenterData] Fetching individual portfolio data for:', portfolioId)

        // Fetch all data in parallel
        const [
          portfolioData,
          overviewRaw,
          snapshot,
          targets,
          sectorData,
          correlationData,
          positionBetas,
          portfolioFactors
        ] = await Promise.all([
          loadPortfolioData(undefined, { portfolioId, skipFactorExposures: true }),
          analyticsApi.getOverview(portfolioId),
          fetchPortfolioSnapshot(portfolioId),
          targetPriceService.list(portfolioId).catch(() => []),
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

        setHeroMetrics({
          equityBalance,
          targetReturnEOY: snapshot?.target_price_return_eoy || 0,
          grossExposure: exposuresRaw.gross_exposure || 0,
          netExposure: exposuresRaw.net_exposure || 0,
          longExposure: exposuresRaw.long_exposure || 0,
          shortExposure: exposuresRaw.short_exposure || 0,
        })

        // Process holdings table
        const positions = portfolioData.positions || []
        const totalValue = equityBalance

        // Create beta map from position factor exposures
        const betaMap = new Map<string, number>()
        if (positionBetas.data.available && positionBetas.data.positions) {
          positionBetas.data.positions.forEach(pos => {
            const marketBeta = pos.exposures['Market Beta']
            if (marketBeta !== undefined && marketBeta !== null) {
              betaMap.set(pos.symbol, marketBeta)
            }
          })
        }

        // Create target price map
        const targetMap = new Map<string, any>()
        targets.forEach((t: any) => {
          const key = `${t.symbol}_${t.position_type}`
          targetMap.set(key, t)
        })

        const holdingsData: HoldingRow[] = positions.map((pos: any) => {
          const targetKey = `${pos.symbol}_${pos.type}`
          const target = targetMap.get(targetKey)
          const weight = totalValue > 0 ? (Math.abs(pos.marketValue) / totalValue) * 100 : 0
          const returnPct = pos.marketValue !== 0 ? (pos.pnl / Math.abs(pos.marketValue)) * 100 : 0

          return {
            id: pos.id,
            symbol: pos.symbol,
            quantity: pos.quantity,
            entryPrice: pos.entry_price || 0,
            todaysPrice: pos.price || 0,
            targetPrice: target?.target_price_eoy || null,
            marketValue: pos.marketValue || 0,
            weight,
            pnlToday: snapshot?.daily_pnl ? (snapshot.daily_pnl * weight / 100) : null,
            pnlTotal: pos.pnl || 0,
            returnPct,
            targetReturn: target?.expected_return_eoy || null,
            beta: betaMap.get(pos.symbol) || null,
            positionType: pos.type || 'LONG',
            investmentClass: pos.investment_class || 'PUBLIC'
          }
        })

        setHoldings(holdingsData)

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

    fetchData()
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
