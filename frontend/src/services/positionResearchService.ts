// src/services/positionResearchService.ts
import { apiClient } from '@/services/apiClient'

// Cache configuration
interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number // milliseconds
}

class CacheManager {
  private cache = new Map<string, CacheEntry<any>>()

  set<T>(key: string, data: T, ttl: number) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key)
    if (!entry) return null

    const age = Date.now() - entry.timestamp
    if (age > entry.ttl) {
      // Expired - remove from cache
      this.cache.delete(key)
      return null
    }

    return entry.data as T
  }

  invalidate(key: string) {
    this.cache.delete(key)
  }

  invalidatePattern(pattern: string) {
    // Invalidate all keys matching pattern
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key)
      }
    }
  }

  clear() {
    this.cache.clear()
  }
}

const cacheManager = new CacheManager()

// Cache TTLs
const CACHE_TTL = {
  COMPANY_PROFILES: 60 * 60 * 1000, // 1 hour (rarely changes)
  POSITIONS: 5 * 60 * 1000,          // 5 minutes (changes when positions added/removed)
  // Target prices NOT cached - always fetch fresh
}

export interface EnhancedPosition {
  // Position basics
  id: string
  symbol: string
  position_type: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
  investment_class?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE'
  quantity: number
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number

  // Tags
  tags: Array<{ id: string; name: string; color: string }>

  // Company profile data
  company_name?: string
  sector?: string
  industry?: string
  market_cap?: number

  // Analyst data
  target_mean_price?: number
  current_year_earnings_avg?: number
  next_year_earnings_avg?: number
  current_year_revenue_avg?: number
  next_year_revenue_avg?: number

  // User targets
  user_target_eoy?: number
  user_target_next_year?: number

  // Calculated fields
  percent_of_equity: number
  target_return_eoy?: number
  target_return_next_year?: number
  analyst_return_eoy?: number
  analyst_return_next_year?: number
}

interface FetchEnhancedPositionsParams {
  portfolioId: string
  investmentClass?: 'PUBLIC' | 'PRIVATE' | 'OPTIONS'
}

interface EnhancedPositionsResult {
  positions: EnhancedPosition[]
  longPositions: EnhancedPosition[]
  shortPositions: EnhancedPosition[]
  portfolioEquity: number
}

export const positionResearchService = {
  /**
   * Fetch and merge position data from multiple APIs
   * - Positions API: Basic position data, tags, prices
   * - Company Profiles API: Company info, analyst targets, estimates
   * - Target Prices API: User-defined target prices
   */
  async fetchEnhancedPositions({
    portfolioId,
    investmentClass
  }: FetchEnhancedPositionsParams): Promise<EnhancedPositionsResult> {
    // Cache keys
    const positionsCacheKey = `positions:${portfolioId}`
    const profilesCacheKey = `profiles:${portfolioId}`

    // Try to get cached data
    const cachedPositions = cacheManager.get<{
      positions: any[]
      summary: { total_market_value: number }
    }>(positionsCacheKey)

    const cachedProfiles = cacheManager.get<{ profiles: any[] }>(profilesCacheKey)

    // Fetch data (use cache when available)
    const fetchPromises: Promise<any>[] = []

    // Positions - use cache or fetch
    if (cachedPositions) {
      console.log('✅ Using cached positions data')
      fetchPromises.push(Promise.resolve(cachedPositions))
    } else {
      console.log('🔄 Fetching fresh positions data')
      fetchPromises.push(
        apiClient.get<{
          positions: any[]
          summary: { total_market_value: number }
        }>(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`)
          .then(data => {
            cacheManager.set(positionsCacheKey, data, CACHE_TTL.POSITIONS)
            return data
          })
      )
    }

    // Company profiles - use cache or fetch
    if (cachedProfiles) {
      console.log('✅ Using cached company profiles')
      fetchPromises.push(Promise.resolve(cachedProfiles))
    } else {
      console.log('🔄 Fetching fresh company profiles')
      fetchPromises.push(
        apiClient.get<{ profiles: any[] }>(
          `/api/v1/data/company-profiles?portfolio_id=${portfolioId}`
        ).then(data => {
          cacheManager.set(profilesCacheKey, data, CACHE_TTL.COMPANY_PROFILES)
          return data
        })
      )
    }

    // Target prices - ALWAYS fetch fresh (no cache)
    console.log('🔄 Fetching fresh target prices (not cached)')
    fetchPromises.push(
      apiClient.get<any[]>(`/api/v1/target-prices/${portfolioId}`)
    )

    const [positionsRes, profilesRes, targetsRes] = await Promise.all(fetchPromises)

    // Filter by investment class if specified
    let filteredPositions = positionsRes.positions
    if (investmentClass) {
      filteredPositions = filteredPositions.filter(
        p => p.investment_class === investmentClass
      )
    }

    // Get portfolio equity for % calculations
    const portfolioEquity = positionsRes.summary?.total_market_value || 0

    // Create lookup maps for O(1) access
    const profilesMap = new Map(
      profilesRes.profiles.map(p => [p.symbol, p])
    )
    const targetsMap = new Map(
      targetsRes.map(t => [t.symbol, t])
    )

    // Merge data and calculate derived fields
    const enhanced: EnhancedPosition[] = filteredPositions.map(pos => {
      const profile = profilesMap.get(pos.symbol)
      const target = targetsMap.get(pos.symbol)

      // Calculate % of portfolio equity
      const percent_of_equity = portfolioEquity > 0
        ? (pos.market_value / portfolioEquity) * 100
        : 0

      // Check if position is short (for analyst calculation only)
      const isShort = ['SHORT', 'SC', 'SP'].includes(pos.position_type)

      // Use backend-calculated returns from target prices API
      // Backend already handles short position inversion and stores calculated values
      const target_return_eoy = target?.expected_return_eoy ?? undefined
      const target_return_next_year = target?.expected_return_next_year ?? undefined

      // Calculate analyst-based returns (fallback when user hasn't entered targets)
      // Only needed for display when no user target exists
      const analyst_return_eoy = profile?.target_mean_price && pos.current_price
        ? isShort
          ? ((pos.current_price - profile.target_mean_price) / pos.current_price) * 100
          : ((profile.target_mean_price - pos.current_price) / pos.current_price) * 100
        : undefined

      return {
        ...pos,
        // Company profile fields
        company_name: profile?.company_name,
        sector: profile?.sector,
        industry: profile?.industry,
        market_cap: profile?.market_cap,
        target_mean_price: profile?.target_mean_price,
        current_year_earnings_avg: profile?.current_year_earnings_avg,
        next_year_earnings_avg: profile?.next_year_earnings_avg,
        current_year_revenue_avg: profile?.current_year_revenue_avg,
        next_year_revenue_avg: profile?.next_year_revenue_avg,
        // User target fields
        user_target_eoy: target?.target_price_eoy,
        user_target_next_year: target?.target_price_next_year,
        // Calculated fields
        percent_of_equity,
        target_return_eoy,
        target_return_next_year,
        analyst_return_eoy,
        analyst_return_next_year: undefined // No analyst data for next year
      }
    })

    // Split into longs and shorts (including options)
    // Long: LONG stock + LC (Long Call) + LP (Long Put)
    // Short: SHORT stock + SC (Short Call) + SP (Short Put)
    const longPositions = enhanced.filter(p =>
      p.position_type === 'LONG' || p.position_type === 'LC' || p.position_type === 'LP'
    )
    const shortPositions = enhanced.filter(p =>
      p.position_type === 'SHORT' || p.position_type === 'SC' || p.position_type === 'SP'
    )

    return {
      positions: enhanced,
      longPositions,
      shortPositions,
      portfolioEquity
    }
  },

  /**
   * Calculate weighted aggregate return for a set of positions
   * @param positions - Array of enhanced positions
   * @param returnField - Primary return field (user-entered targets)
   * @param fallbackField - Fallback return field (analyst targets) when primary is null
   */
  calculateAggregateReturn(
    positions: EnhancedPosition[],
    returnField: 'target_return_eoy' | 'target_return_next_year',
    fallbackField?: 'analyst_return_eoy' | 'analyst_return_next_year'
  ): number {
    const totalWeight = positions.reduce((sum, p) => sum + p.percent_of_equity, 0)
    if (totalWeight === 0) return 0

    const weightedSum = positions.reduce((sum, p) => {
      // Use user target if available, otherwise fall back to analyst target, then 0
      const ret = p[returnField] ?? (fallbackField ? p[fallbackField] : null) ?? 0
      return sum + (ret * p.percent_of_equity)
    }, 0)

    return weightedSum / totalWeight
  },

  /**
   * Invalidate cached positions for a portfolio
   * Call this when positions are added/removed
   */
  invalidatePositionsCache(portfolioId: string) {
    const positionsCacheKey = `positions:${portfolioId}`
    cacheManager.invalidate(positionsCacheKey)
    console.log('🗑️ Invalidated positions cache for', portfolioId)
  },

  /**
   * Invalidate cached company profiles for a portfolio
   * Call this when company data changes (rare)
   */
  invalidateProfilesCache(portfolioId: string) {
    const profilesCacheKey = `profiles:${portfolioId}`
    cacheManager.invalidate(profilesCacheKey)
    console.log('🗑️ Invalidated profiles cache for', portfolioId)
  },

  /**
   * Invalidate all cached data for a portfolio
   * Use when unsure what changed
   */
  invalidateAllCache(portfolioId: string) {
    cacheManager.invalidatePattern(portfolioId)
    console.log('🗑️ Invalidated all cache for', portfolioId)
  },

  /**
   * Clear entire cache
   * Use sparingly (e.g., on logout)
   */
  clearCache() {
    cacheManager.clear()
    console.log('🗑️ Cleared entire cache')
  }
}
