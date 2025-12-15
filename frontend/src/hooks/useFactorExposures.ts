/**
 * Hook: useFactorExposures
 *
 * Fetches portfolio-level factor betas via analyticsApi and normalizes
 * legacy/new response formats. Returns loading/error flags plus
 * calculation metadata for display in the risk metrics hero cards.
 *
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for equity-weighted averages across all portfolios.
 *
 * Created for Risk Metrics hero refactor (Nov 2025).
 * Updated for aggregate support (Dec 2025).
 */

import { useEffect, useState } from 'react'
import { analyticsApi } from '@/services/analyticsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type {
  FactorExposure,
  FactorExposuresMetadata,
  DataQualityInfo,
  DataStalenessInfo,
  PortfolioFactorExposuresResponse,
  AggregateFactorExposuresResponse,
} from '@/types/analytics'

type FactorResponse = PortfolioFactorExposuresResponse & {
  factors?: FactorExposure[]
  calculation_date?: string
  data_quality?: DataStalenessInfo | DataQualityInfo | null
  metadata?: FactorExposuresMetadata | PortfolioFactorExposuresResponse['metadata']
}

type FactorMetadata =
  | FactorExposuresMetadata
  | PortfolioFactorExposuresResponse['metadata']
  | undefined

type FactorDataQuality = DataStalenessInfo | DataQualityInfo | PortfolioFactorExposuresResponse['data_quality'] | null | undefined

interface UseFactorExposuresReturn {
  factors: FactorExposure[] | null
  loading: boolean
  error: string | null
  available: boolean
  calculationDate: string | null
  metadata: FactorMetadata
  dataQuality: FactorDataQuality
  reason?: string
  refetch: () => void
}

function normalizeFactorExposure(response: FactorResponse | null | undefined): {
  factors: FactorExposure[] | null
  available: boolean
  calculationDate: string | null
  metadata: FactorMetadata
  dataQuality: FactorDataQuality
  reason?: string
} {
  if (!response) {
    return {
      factors: null,
      available: false,
      calculationDate: null,
      metadata: undefined,
      dataQuality: null,
      reason: undefined,
    }
  }

  // Preferred modern structure (FactorExposuresResponse)
  if (Array.isArray(response.factors) && response.factors.length > 0) {
    return {
      factors: response.factors,
      available: true,
      calculationDate: response.calculation_date ?? response.metadata?.calculation_date ?? null,
      metadata: response.metadata,
      dataQuality: response.data_quality,
      reason: response.reason,
    }
  }

  // Legacy structure (data array + exposure numbers)
  if (Array.isArray(response.data) && response.data.length > 0) {
    const factors: FactorExposure[] = response.data.map(rawItem => {
      const item = rawItem as {
        factor?: string
        name?: string
        exposure?: number
        beta?: number
        exposure_dollar?: number
      }

      const resolvedName = item.factor ?? item.name ?? 'Factor'
      const resolvedBeta =
        typeof item.exposure === 'number'
          ? item.exposure
          : typeof item.beta === 'number'
            ? item.beta
            : 0
      const resolvedDollar =
        typeof item.exposure_dollar === 'number' ? item.exposure_dollar : 0

      return {
        name: resolvedName,
        beta: resolvedBeta,
        exposure_dollar: resolvedDollar,
      }
    })

    return {
      factors,
      available: true,
      calculationDate: response.metadata?.calculation_date ?? null,
      metadata: response.metadata,
      dataQuality: response.data_quality,
      reason: response.reason,
    }
  }

  return {
    factors: null,
    available: Boolean(response.available),
    calculationDate: response.calculation_date ?? response.metadata?.calculation_date ?? null,
    metadata: response.metadata,
    dataQuality: response.data_quality,
    reason: response.reason,
  }
}

// Normalize aggregate response to match single-portfolio format
function normalizeAggregateFactorResponse(response: AggregateFactorExposuresResponse): {
  factors: FactorExposure[] | null
  available: boolean
  calculationDate: string | null
  metadata: FactorMetadata
  dataQuality: FactorDataQuality
  reason?: string
} {
  if (!response?.factors || response.factors.length === 0) {
    return {
      factors: null,
      available: false,
      calculationDate: null,
      metadata: undefined,
      dataQuality: null,
      reason: undefined,
    }
  }

  const factors: FactorExposure[] = response.factors.map(f => ({
    name: f.name,
    beta: f.aggregate_beta,
    exposure_dollar: f.aggregate_exposure_dollar,
  }))

  return {
    factors,
    available: true,
    calculationDate: response.calculation_date ?? null,
    metadata: {
      factor_model: 'aggregate',
      calculation_method: 'equity_weighted',
      completeness: 'full',
      total_active_factors: factors.length,
      factors_calculated: factors.length,
      has_market_beta: factors.some(f => f.name.toLowerCase() === 'market') ? 1 : 0,
    },
    dataQuality: null,
    reason: undefined,
  }
}

export function useFactorExposures(): UseFactorExposuresReturn {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [factors, setFactors] = useState<FactorExposure[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [available, setAvailable] = useState(false)
  const [calculationDate, setCalculationDate] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<FactorMetadata>(undefined)
  const [dataQuality, setDataQuality] = useState<FactorDataQuality>(null)
  const [reason, setReason] = useState<string | undefined>(undefined)
  const [refetchToken, setRefetchToken] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadFactorExposures() {
      // For aggregate view, we don't need a portfolioId
      // For single-portfolio view, we need the portfolioId
      if (!isAggregateView && !portfolioId) {
        if (isMounted) {
          setFactors(null)
          setAvailable(false)
          setCalculationDate(null)
          setMetadata(undefined)
          setDataQuality(null)
          setError(null)
          setReason(undefined)
        }
        return
      }

      setLoading(true)
      setError(null)

      try {
        let normalized: {
          factors: FactorExposure[] | null
          available: boolean
          calculationDate: string | null
          metadata: FactorMetadata
          dataQuality: FactorDataQuality
          reason?: string
        }

        if (isAggregateView) {
          // Call aggregate endpoint for equity-weighted average across all portfolios
          const { data } = await analyticsApi.getAggregateFactorExposures()
          normalized = normalizeAggregateFactorResponse(data)
        } else {
          // Call single-portfolio endpoint
          const { data } = await analyticsApi.getPortfolioFactorExposures(portfolioId!)
          normalized = normalizeFactorExposure(data as FactorResponse)
        }

        if (!isMounted) {
          return
        }

        setFactors(normalized.factors)
        setAvailable(normalized.available)
        setCalculationDate(normalized.calculationDate)
        setMetadata(normalized.metadata)
        setDataQuality(normalized.dataQuality)
        setReason(normalized.reason)
      } catch (err: any) {
        if (!isMounted) {
          return
        }

        console.error('[useFactorExposures] Failed to load factor exposures:', err)
        setError(err?.message ?? 'Failed to load factor exposures')
        setFactors(null)
        setAvailable(false)
        setCalculationDate(null)
        setMetadata(undefined)
        setDataQuality(null)
        setReason(err?.reason ?? undefined)
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadFactorExposures()

    return () => {
      isMounted = false
    }
  }, [isAggregateView, portfolioId, refetchToken])

  const refetch = () => {
    setRefetchToken(prev => prev + 1)
  }

  return {
    factors,
    loading,
    error,
    available,
    calculationDate,
    metadata,
    dataQuality,
    reason,
    refetch,
  }
}
