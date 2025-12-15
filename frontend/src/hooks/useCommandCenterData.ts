/**
 * useCommandCenterData Hook
 *
 * Fetches and aggregates data for the Command Center page.
 *
 * Updated December 2025: Uses backend aggregate endpoints for equity-weighted metrics
 * - Beta: Uses /aggregate/beta endpoint instead of client-side calculation
 * - Volatility: Uses /aggregate/volatility endpoint instead of client-side calculation
 * - Sector: Uses /aggregate/sector-exposure endpoint
 * - Concentration: Uses /aggregate/concentration endpoint
 *
 * This ensures consistency with Risk Metrics page calculations.
 */

import { useState, useEffect } from 'react'
import { useSelectedPortfolioId } from '@/stores/portfolioStore'
import { fetchPortfolioSnapshot } from '@/services/portfolioService'
import { analyticsApi } from '@/services/analyticsApi'
import targetPriceService from '@/services/targetPriceService'
import { portfolioService } from '@/services/portfolioApi'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'
import equityChangeService, {
  type EquityChange,
  type EquityChangeSummary,
} from '@/services/equityChangeService'
import type {
  VolatilityMetricsResponse,
  AggregateBetaResponse,
  AggregateVolatilityResponse,
  AggregateSectorExposureResponse,
  AggregateConcentrationResponse,
} from '@/types/analytics'

type CapitalChangeType = 'CONTRIBUTION' | 'WITHDRAWAL'

interface HeroMetrics {
  equityBalance: number
  targetReturnEOY: number
  grossExposure: number
  netExposure: number
  longExposure: number
  shortExposure: number
  totalCapitalFlow: number
  netCapitalFlow30d: number
  lastCapitalChange: {
    type: CapitalChangeType
    amount: number
    changeDate: string
  } | null
}

interface PerformanceMetrics {
  ytdPnl: number
  mtdPnl: number
  cashBalance: number
  portfolioBeta90d: number | null
  portfolioBeta1y: number | null
  stressTest: { up: number; down: number } | null
  volatility: {
    current21d: number | null
    historical63d: number | null
    forward21d: number | null
  }
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

interface AggregateSection {
  heroMetrics: HeroMetrics
  performanceMetrics: PerformanceMetrics
  riskMetrics: RiskMetrics
  holdings: HoldingRow[]
  equitySummary?: EquityChangeSummary
  equityChanges?: EquityChange[]
}

interface PortfolioSection extends AggregateSection {
  portfolioId: string
  accountName: string
  equitySummary: EquityChangeSummary
  equityChanges: EquityChange[]
}

interface UseCommandCenterDataReturn {
  aggregate: AggregateSection | null
  portfolios: PortfolioSection[]
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

const calculateWeightedReturnByPercentOfEquity = (
  positions: EnhancedPosition[],
  returnField: 'target_return_eoy' | 'target_return_next_year',
  fallbackField?: 'analyst_return_eoy' | 'analyst_return_next_year'
): number | null => {
  let weightedSum = 0
  let totalWeight = 0

  positions.forEach(position => {
    const weight = position.percent_of_equity || 0
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
  const selectedPortfolioId = useSelectedPortfolioId()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aggregateData, setAggregateData] = useState<AggregateSection | null>(null)
  const [portfolioSections, setPortfolioSections] = useState<PortfolioSection[]>([])



  const buildPortfolioSection = async (portfolioId: string, accountName: string): Promise<PortfolioSection> => {
    console.log('[useCommandCenterData] Fetching portfolio data for:', portfolioId)

    const [
      overviewRaw,
      snapshot,
      enhancedPositionsResult,
      targetSummary,
      sectorData,
      correlationData,
      positionBetas,
      portfolioFactors,
      volatilityResponse,
      equitySummaryResponse,
      equityChangesResponse
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
      analyticsApi.getPortfolioFactorExposures(portfolioId).catch(() => ({ data: { available: false, factors: [] } })),
      analyticsApi.getVolatility(portfolioId).catch(() => ({ data: { available: false, portfolio_id: portfolioId, calculation_date: null, data: null } })),
      equityChangeService.getSummary(portfolioId).catch((err) => {
        console.warn('[useCommandCenterData] Failed to fetch equity summary:', err)
        return null
      }),
      equityChangeService.list(portfolioId, { page: 1, pageSize: 5 }).catch((err) => {
        console.warn('[useCommandCenterData] Failed to fetch equity changes:', err)
        return null
      })
    ])

    const overviewResponse = overviewRaw.data
    const exposuresRaw = overviewResponse.exposures || {}
    const equityBalance = overviewResponse.equity_balance || 0
    const cashBalance = overviewResponse.cash_balance || 0

    const enhancedPositions = enhancedPositionsResult.positions || []
    if (enhancedPositions.length > 0) {
      console.log('[useCommandCenterData] Sample enhanced position:', enhancedPositions[0])
    }

    const betaMap = new Map<string, number>()
    if (positionBetas.data.available && positionBetas.data.positions) {
      positionBetas.data.positions.forEach((pos: any) => {
        // Use correct factor name from backend: 'Market Beta (90D)'
        const marketBeta = pos.exposures?.['Market Beta (90D)']
        if (marketBeta !== undefined && marketBeta !== null) {
          betaMap.set(pos.symbol, marketBeta)
        }
      })
    }

    const pnlToday = normalizeNumber(snapshot?.daily_pnl)

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
        investmentClass: (pos.investment_class as string) || 'PUBLIC',
        account_name: accountName,
        portfolio_id: portfolioId
      }
    })

    holdingsData.sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))

    const summaryTargetReturn = normalizeNumber(targetSummary?.weighted_expected_return_eoy)
    const computedTargetReturn = calculateWeightedReturnByPercentOfEquity(
      enhancedPositions,
      'target_return_eoy',
      'analyst_return_eoy'
    )
    const snapshotTargetReturn = normalizeNumber(snapshot?.target_price_return_eoy)

    // Debug logging for target return calculation
    console.log('[useCommandCenterData] Target Return Debug:', {
      portfolioId,
      snapshot: snapshot,
      snapshotKeys: snapshot ? Object.keys(snapshot) : [],
      snapshotTargetReturn,
      summaryTargetReturn,
      computedTargetReturn
    })

    // For target returns, treat 0 as "no data" and fall through to computed (includes analyst fallback)
    const heroTargetReturnEOY =
      (snapshotTargetReturn !== null && snapshotTargetReturn !== 0 ? snapshotTargetReturn : null) ??
      (summaryTargetReturn !== null && summaryTargetReturn !== 0 ? summaryTargetReturn : null) ??
      computedTargetReturn ??
      0

    let beta90d: number | null = null
    let beta1y: number | null = null

    if (portfolioFactors.data?.available && portfolioFactors.data?.factors) {
      const factors = portfolioFactors.data.factors
      const beta90dFactor = factors.find((f: any) => f.name === 'Market Beta (90D)')
      const beta1yFactor = factors.find((f: any) => f.name === 'Provider Beta (1Y)')
      beta90d = normalizeNumber(beta90dFactor?.beta)
      beta1y = normalizeNumber(beta1yFactor?.beta)
    }

    let topSector: { name: string; weight: number; vs_sp: number } | null = null
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
          topSector = sectorEntries.sort((a, b) => b.weight - a.weight)[0]
        }
      }
    }

    let largestPosition: { symbol: string; weight: number } | null = null
    if (holdingsData.length > 0) {
      const topHolding = [...holdingsData].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))[0]
      largestPosition = {
        symbol: topHolding.symbol,
        weight: topHolding.weight
      }
    }

    let spCorrelation: number | null = null
    if ('data' in correlationData) {
      const corrResponse = correlationData as { data: { available: boolean; data?: any } }
      if (corrResponse.data.available && corrResponse.data.data) {
        const matrix = corrResponse.data.data.matrix
        if (matrix['SPY']) {
          const portfolioCorr = Object.entries(matrix['SPY']).find(([key]) =>
            key.toLowerCase().includes('portfolio') || key === 'PORTFOLIO'
          )
          if (portfolioCorr) {
            spCorrelation = portfolioCorr[1] as number
          }
        }
      }
    }

    const netExp = exposuresRaw.net_exposure || 0
    const stressTest =
      beta1y !== null && netExp !== 0
        ? {
            up: netExp * beta1y * 0.01,
            down: netExp * beta1y * -0.01
          }
        : null

    const defaultSummary: EquityChangeSummary = {
      portfolioId,
      totalContributions: 0,
      totalWithdrawals: 0,
      netFlow: 0,
      periods: {},
    }

    const equitySummary = equitySummaryResponse ?? defaultSummary
    const equityChanges = equityChangesResponse?.items ?? []
    const netCapitalFlow30d = equitySummary.periods?.['30d']?.netFlow ?? 0
    const totalCapitalFlow = equitySummary.netFlow ?? 0
    const latestCapitalChange = equitySummary.lastChange ?? null

    const pnlData = overviewResponse.pnl || {}
    const volatilityPayload = (volatilityResponse as { data?: VolatilityMetricsResponse } | null)?.data ?? null
    const volatilityData =
      volatilityPayload && volatilityPayload.available && volatilityPayload.data
        ? volatilityPayload.data
        : null
    const volatilityMetrics = {
      current21d: normalizeNumber(volatilityData?.realized_volatility_21d),
      historical63d: normalizeNumber(volatilityData?.realized_volatility_63d),
      forward21d: normalizeNumber(volatilityData?.expected_volatility_21d)
    }

    return {
      portfolioId,
      accountName,
      heroMetrics: {
        equityBalance,
        targetReturnEOY: heroTargetReturnEOY,
        grossExposure: exposuresRaw.gross_exposure || 0,
        netExposure: exposuresRaw.net_exposure || 0,
        longExposure: exposuresRaw.long_exposure || 0,
        shortExposure: exposuresRaw.short_exposure || 0,
        totalCapitalFlow,
        netCapitalFlow30d,
        lastCapitalChange: latestCapitalChange
          ? {
              type: latestCapitalChange.changeType,
              amount: latestCapitalChange.amount,
              changeDate: latestCapitalChange.changeDate,
            }
          : null,
      },
      performanceMetrics: {
        ytdPnl: pnlData.ytd_pnl || 0,
        mtdPnl: pnlData.mtd_pnl || 0,
        cashBalance,
        portfolioBeta90d: beta90d,
        portfolioBeta1y: beta1y,
        stressTest,
        volatility: volatilityMetrics
      },
      riskMetrics: {
        portfolioBeta90d: beta90d,
        portfolioBeta1y: beta1y,
        topSector,
        largestPosition,
        spCorrelation,
        stressTest
      },
      holdings: holdingsData,
      equitySummary,
      equityChanges
    }
  }

  useEffect(() => {
    let isCancelled = false

    const fetchData = async () => {
      setLoading(true)
      setError(null)

      try {
        if (!selectedPortfolioId) {
          const portfolios = await portfolioService.getPortfolios()

          if (isCancelled) {
            return
          }

          if (portfolios.length === 0) {
            setAggregateData(null)
            setPortfolioSections([])
            setLoading(false)
            return
          }

          const [aggregateAnalytics, sectionResults] = await Promise.all([
            portfolioService.getAggregateAnalytics().catch(err => {
              console.warn('[useCommandCenterData] Failed to fetch aggregate analytics:', err)
              return null
            }),
            Promise.all(
              portfolios.map(async (portfolio) => {
                try {
                  return await buildPortfolioSection(
                    portfolio.id,
                    portfolio.account_name || portfolio.name || 'Portfolio'
                  )
                } catch (err) {
                  console.warn('[useCommandCenterData] Failed to load portfolio:', portfolio.id, err)
                  return null
                }
              })
            )
          ])

          if (isCancelled) {
            return
          }

          const validSections = sectionResults.filter((section): section is PortfolioSection => section !== null)

          setPortfolioSections(validSections)

          if (portfolios.length > 1 && validSections.length > 0) {
            const aggregateHoldingsRaw = validSections.flatMap((section) =>
              section.holdings.map((holding) => ({
                ...holding,
                account_name: section.accountName,
                portfolio_id: section.portfolioId
              }))
            )

            const totalEquity = validSections.reduce(
              (sum, section) => sum + section.heroMetrics.equityBalance,
              0
            )
            const grossExposure = validSections.reduce(
              (sum, section) => sum + section.heroMetrics.grossExposure,
              0
            )
            const netExposure = validSections.reduce(
              (sum, section) => sum + section.heroMetrics.netExposure,
              0
            )
            const longExposure = validSections.reduce(
              (sum, section) => sum + section.heroMetrics.longExposure,
              0
            )
            const shortExposure = validSections.reduce(
              (sum, section) => sum + section.heroMetrics.shortExposure,
              0
            )

            const totalCapitalFlow = validSections.reduce(
              (sum, section) => sum + (section.heroMetrics.totalCapitalFlow ?? 0),
              0
            )
            const netCapitalFlow30d = validSections.reduce(
              (sum, section) => sum + (section.heroMetrics.netCapitalFlow30d ?? 0),
              0
            )

            const aggregatePeriod = (key: string) =>
              validSections.reduce(
                (acc, section) => {
                  const period = section.equitySummary?.periods?.[key]
                  return {
                    contributions: acc.contributions + (period?.contributions ?? 0),
                    withdrawals: acc.withdrawals + (period?.withdrawals ?? 0),
                    netFlow: acc.netFlow + (period?.netFlow ?? 0),
                  }
                },
                { contributions: 0, withdrawals: 0, netFlow: 0 }
              )

            const period30d = aggregatePeriod('30d')
            const period90d = aggregatePeriod('90d')

            const combinedChanges: EquityChange[] = validSections.flatMap(
              (section) => section.equityChanges ?? []
            )
            if (combinedChanges.length === 0) {
              validSections.forEach((section) => {
                if (section.equitySummary?.lastChange) {
                  combinedChanges.push(section.equitySummary.lastChange)
                }
              })
            }
            combinedChanges.sort(
              (a, b) =>
                new Date(b.changeDate).getTime() - new Date(a.changeDate).getTime()
            )
            const aggregateLastChange = combinedChanges.length > 0 ? combinedChanges[0] : null

            const totalAbsMarketValue = aggregateHoldingsRaw.reduce(
              (sum, holding) => sum + Math.abs(holding.marketValue),
              0
            )

            const aggregateHoldings = aggregateHoldingsRaw.map((holding) => ({
              ...holding,
              weight: totalAbsMarketValue > 0
                ? (Math.abs(holding.marketValue) / totalAbsMarketValue) * 100
                : 0
            }))

            const weightedTargetReturn =
              totalAbsMarketValue > 0
                ? aggregateHoldingsRaw.reduce(
                    (sum, holding) =>
                      sum + (holding.targetReturn ?? 0) * Math.abs(holding.marketValue),
                    0
                  ) / totalAbsMarketValue
                : 0

            // Fetch backend aggregate metrics (equity-weighted calculations)
            // This ensures consistency with Risk Metrics page
            const [
              aggregateBetaResponse,
              aggregateVolatilityResponse,
              aggregateSectorResponse,
              aggregateConcentrationResponse,
            ] = await Promise.all([
              analyticsApi.getAggregateBeta().catch((err) => {
                console.warn('[useCommandCenterData] Failed to fetch aggregate beta:', err)
                return null
              }),
              analyticsApi.getAggregateVolatility().catch((err) => {
                console.warn('[useCommandCenterData] Failed to fetch aggregate volatility:', err)
                return null
              }),
              analyticsApi.getAggregateSectorExposure().catch((err) => {
                console.warn('[useCommandCenterData] Failed to fetch aggregate sector:', err)
                return null
              }),
              analyticsApi.getAggregateConcentration().catch((err) => {
                console.warn('[useCommandCenterData] Failed to fetch aggregate concentration:', err)
                return null
              }),
            ])

            if (isCancelled) {
              return
            }

            // Use backend aggregate beta (equity-weighted) instead of client-side calculation
            const aggregateBeta90d = aggregateBetaResponse?.data?.aggregate_beta_90d ?? null
            const aggregateBeta180d = aggregateBetaResponse?.data?.aggregate_beta_180d ?? null

            // Use backend aggregate volatility (equity-weighted) instead of client-side calculation
            const aggregateVolatility = {
              current21d: aggregateVolatilityResponse?.data?.aggregate_volatility_21d ?? null,
              historical63d: aggregateVolatilityResponse?.data?.aggregate_volatility_63d ?? null,
              forward21d: aggregateVolatilityResponse?.data?.aggregate_expected_volatility_21d ?? null,
            }

            const aggregateHero: HeroMetrics = {
              equityBalance: aggregateAnalytics?.net_asset_value ?? totalEquity,
              targetReturnEOY: weightedTargetReturn,
              grossExposure,
              netExposure,
              longExposure,
              shortExposure,
              totalCapitalFlow,
              netCapitalFlow30d,
              lastCapitalChange: aggregateLastChange
                ? {
                    type: aggregateLastChange.changeType,
                    amount: aggregateLastChange.amount,
                    changeDate: aggregateLastChange.changeDate,
                  }
                : null,
            }

            const aggregatePerformance: PerformanceMetrics = {
              ytdPnl:
                aggregateAnalytics?.total_realized_pnl ??
                validSections.reduce((sum, section) => sum + section.performanceMetrics.ytdPnl, 0),
              mtdPnl: validSections.reduce((sum, section) => sum + section.performanceMetrics.mtdPnl, 0),
              cashBalance: validSections.reduce((sum, section) => sum + section.performanceMetrics.cashBalance, 0),
              portfolioBeta90d: aggregateBeta90d,
              portfolioBeta1y: aggregateBeta180d,  // Use backend aggregate beta (equity-weighted)
              stressTest:
                aggregateBeta180d !== null && netExposure !== 0
                  ? {
                      up: netExposure * aggregateBeta180d * 0.01,
                      down: netExposure * aggregateBeta180d * -0.01
                    }
                  : null,
              volatility: aggregateVolatility
            }

            const aggregateLargestHolding = aggregateHoldings
              .slice()
              .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))[0] || null

            // Use backend aggregate sector data if available (equity-weighted), fallback to aggregateAnalytics
            // Convert aggregate_portfolio_weights Record to find top sector
            const sectorWeights = aggregateSectorResponse?.data?.aggregate_portfolio_weights
            const benchmarkWeights = aggregateSectorResponse?.data?.benchmark_weights
            let topSectorData = null
            if (sectorWeights && Object.keys(sectorWeights).length > 0) {
              // Find sector with highest weight
              const sortedSectors = Object.entries(sectorWeights).sort(([, a], [, b]) => b - a)
              const [topSectorName, topSectorWeight] = sortedSectors[0]
              const benchmarkWeight = benchmarkWeights?.[topSectorName] ?? 0
              topSectorData = {
                name: topSectorName,
                weight: topSectorWeight,
                vs_sp: topSectorWeight - benchmarkWeight
              }
            } else if (aggregateAnalytics?.sector_allocation?.length) {
              topSectorData = {
                name: aggregateAnalytics.sector_allocation[0].sector,
                weight: aggregateAnalytics.sector_allocation[0].pct_of_total,
                vs_sp: 0
              }
            }

            // Use backend aggregate concentration data for largest position (equity-weighted), fallback to client calc
            const topPositionFromBackend = aggregateConcentrationResponse?.data?.top_positions?.[0]
            const largestPositionData = topPositionFromBackend
              ? {
                  symbol: topPositionFromBackend.symbol,
                  weight: topPositionFromBackend.weight
                }
              : aggregateLargestHolding
                ? {
                    symbol: aggregateLargestHolding.symbol,
                    weight: aggregateLargestHolding.weight
                  }
                : null

            const aggregateRisk: RiskMetrics = {
              portfolioBeta90d: aggregateBeta90d,
              portfolioBeta1y: aggregateBeta180d,  // Use backend aggregate beta (equity-weighted)
              topSector: topSectorData,
              largestPosition: largestPositionData,
              spCorrelation: null,
              stressTest:
                aggregateBeta180d !== null && netExposure !== 0
                  ? {
                      up: netExposure * aggregateBeta180d * 0.01,
                      down: netExposure * aggregateBeta180d * -0.01
                    }
                : null
            }

            const aggregateSummary: EquityChangeSummary = {
              portfolioId: 'aggregate',
              totalContributions: validSections.reduce(
                (sum, section) => sum + (section.equitySummary?.totalContributions ?? 0),
                0
              ),
              totalWithdrawals: validSections.reduce(
                (sum, section) => sum + (section.equitySummary?.totalWithdrawals ?? 0),
                0
              ),
              netFlow: totalCapitalFlow,
              periods: {
                '30d': period30d,
                '90d': period90d,
              },
              lastChange: aggregateLastChange ?? undefined,
            }

            const aggregateRecentChanges = combinedChanges.slice(0, 10)

            setAggregateData({
              heroMetrics: aggregateHero,
              performanceMetrics: aggregatePerformance,
              riskMetrics: aggregateRisk,
              holdings: aggregateHoldings,
              equitySummary: aggregateSummary,
              equityChanges: aggregateRecentChanges,
            })
          } else {
            setAggregateData(null)
          }

          setLoading(false)
          return
        }

        let accountName = 'Portfolio'
        try {
          const portfolios = await portfolioService.getPortfolios()
          const selected = portfolios.find((p) => p.id === selectedPortfolioId)
          if (selected) {
            accountName = selected.account_name || selected.name || 'Portfolio'
          }
        } catch (err) {
          console.warn('[useCommandCenterData] Failed to fetch portfolios for selected view:', err)
        }

        const section = await buildPortfolioSection(selectedPortfolioId, accountName)

        if (isCancelled) {
          return
        }

        setPortfolioSections([section])
        setAggregateData(null)
        setLoading(false)
      } catch (err: any) {
        if (isCancelled) {
          return
        }
        console.error('Failed to load Command Center data:', err)
        setError(err.message || 'Failed to load data')
        setAggregateData(null)
        setPortfolioSections([])
        setLoading(false)
      }
    }

    fetchData().catch((err) => {
      console.error('[useCommandCenterData] Unhandled error:', err)
      if (!isCancelled) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
        setAggregateData(null)
        setPortfolioSections([])
        setLoading(false)
      }
    })

    return () => {
      isCancelled = true
    }
  }, [selectedPortfolioId, refreshTrigger])

  return {
    aggregate: aggregateData,
    portfolios: portfolioSections,
    loading,
    error
  }
}

