/**
 * Hook: useFactorExposures
 *
 * Fetches portfolio-level factor betas via analyticsApi and normalizes
 * legacy/new response formats. Returns loading/error flags plus
 * calculation metadata for display in the risk metrics hero cards.
 *
 * Created for Risk Metrics hero refactor (Nov 2025).
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

export function useFactorExposures(): UseFactorExposuresReturn {
  const portfolioId = usePortfolioStore(state => state.portfolioId)

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
      if (!portfolioId) {
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
        const { data } = await analyticsApi.getPortfolioFactorExposures(portfolioId)
        const normalized = normalizeFactorExposure(data as FactorResponse)

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
  }, [portfolioId, refetchToken])

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
