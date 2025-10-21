/**
 * Hook to fetch and merge position factor exposures with company profile betas
 *
 * Combines data from two sources:
 * 1. Position factor exposures (7-factor model calculated betas)
 * 2. Company profiles (market beta from financial data provider)
 */

import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/analyticsApi'
import { apiClient } from '@/services/apiClient'
import type { PositionFactorData } from '@/types/analytics'

interface CompanyProfile {
  symbol: string
  company_name?: string
  beta?: number
  sector?: string
  industry?: string
}

interface CompanyProfilesResponse {
  profiles: CompanyProfile[]
  meta: {
    query_type: string
    returned_profiles: number
    missing_profiles: string[]
  }
}

export function usePositionFactorData(portfolioId: string | null): PositionFactorData {
  const [data, setData] = useState<PositionFactorData>({
    factorExposures: new Map(),
    companyBetas: new Map(),
    loading: true,
    error: null,
    calculationDate: null
  })

  useEffect(() => {
    if (!portfolioId) {
      setData({
        factorExposures: new Map(),
        companyBetas: new Map(),
        loading: false,
        error: 'No portfolio ID provided',
        calculationDate: null
      })
      return
    }

    let isMounted = true
    const abortController = new AbortController()

    async function fetchData() {
      try {
        setData(prev => ({ ...prev, loading: true, error: null }))

        // Fetch both data sources in parallel
        const [factorExposuresResult, companyProfilesResult] = await Promise.allSettled([
          analyticsApi.getPositionFactorExposures(portfolioId, { limit: 200 }),
          apiClient.get<CompanyProfilesResponse>(
            `/api/v1/data/company-profiles?portfolio_id=${portfolioId}`,
            { signal: abortController.signal }
          )
        ])

        if (!isMounted) return

        // Process factor exposures
        const factorExposuresMap = new Map<string, Record<string, number>>()
        let calculationDate: string | null = null

        if (factorExposuresResult.status === 'fulfilled') {
          const response = factorExposuresResult.value.data

          if (response.available && response.positions) {
            calculationDate = response.calculation_date

            // Build map of symbol → factor exposures
            response.positions.forEach(pos => {
              if (pos.exposures) {
                factorExposuresMap.set(pos.symbol, pos.exposures)
              }
            })

            console.log(`✅ Loaded factor exposures for ${factorExposuresMap.size} positions`)
          } else {
            console.log('⚠️ Factor exposures not available (may not be calculated yet)')
          }
        } else {
          console.error('❌ Failed to fetch factor exposures:', factorExposuresResult.reason)
        }

        // Process company profiles (market betas)
        const companyBetasMap = new Map<string, number>()

        if (companyProfilesResult.status === 'fulfilled') {
          const profiles = companyProfilesResult.value.profiles

          profiles.forEach(profile => {
            if (profile.beta !== null && profile.beta !== undefined) {
              companyBetasMap.set(profile.symbol, profile.beta)
            }
          })

          console.log(`✅ Loaded company betas for ${companyBetasMap.size} positions`)
        } else {
          console.error('❌ Failed to fetch company profiles:', companyProfilesResult.reason)
        }

        // Update state with both data sources
        if (isMounted) {
          setData({
            factorExposures: factorExposuresMap,
            companyBetas: companyBetasMap,
            loading: false,
            error: null,
            calculationDate
          })
        }

      } catch (error: any) {
        if (isMounted && error.name !== 'AbortError') {
          console.error('❌ Error fetching position factor data:', error)
          setData(prev => ({
            ...prev,
            loading: false,
            error: error.message || 'Failed to fetch factor data'
          }))
        }
      }
    }

    fetchData()

    return () => {
      isMounted = false
      abortController.abort()
    }
  }, [portfolioId])

  return data
}
