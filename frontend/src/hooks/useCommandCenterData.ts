import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { loadPortfolioData, fetchPortfolioSnapshot } from '@/services/portfolioService'
import { analyticsApi } from '@/services/analyticsApi'
import targetPriceService from '@/services/targetPriceService'

interface HeroMetrics {
  equityBalance: number
  targetReturnEOY: number
  grossExposure: number
  netExposure: number
  longExposure: number
  shortExposure: number
}

interface HoldingRow {
  id: string
  symbol: string
  quantity: number
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
  holdings: HoldingRow[]
  riskMetrics: RiskMetrics
  loading: boolean
  error: string | null
}

export function useCommandCenterData(): UseCommandCenterDataReturn {
  const { portfolioId } = usePortfolioStore()

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
      if (!portfolioId) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
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

        setLoading(false)
      } catch (err: any) {
        console.error('Failed to load Command Center data:', err)
        setError(err.message || 'Failed to load data')
        setLoading(false)
      }
    }

    fetchData()
  }, [portfolioId])

  return {
    heroMetrics,
    holdings,
    riskMetrics,
    loading,
    error
  }
}
