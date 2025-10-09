// src/services/positionResearchService.ts
import { apiClient } from '@/services/apiClient'

export interface EnhancedPosition {
  // Position basics
  id: string
  symbol: string
  position_type: 'LONG' | 'SHORT'
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
    // Fetch all data in parallel
    const [positionsRes, profilesRes, targetsRes] = await Promise.all([
      apiClient.get<{
        positions: any[]
        summary: { total_market_value: number }
      }>(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`),

      apiClient.get<{ profiles: any[] }>(
        `/api/v1/data/company-profiles?portfolio_id=${portfolioId}`
      ),

      apiClient.get<any[]>(`/api/v1/target-prices/${portfolioId}`)
    ])

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

      // Calculate target returns (user-entered targets)
      const target_return_eoy = target?.target_price_eoy && pos.current_price
        ? ((target.target_price_eoy - pos.current_price) / pos.current_price) * 100
        : undefined

      const target_return_next_year = target?.target_price_next_year && pos.current_price
        ? ((target.target_price_next_year - pos.current_price) / pos.current_price) * 100
        : undefined

      // Calculate analyst-based returns (fallback when user hasn't entered targets)
      const analyst_return_eoy = profile?.target_mean_price && pos.current_price
        ? ((profile.target_mean_price - pos.current_price) / pos.current_price) * 100
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

    // Split into longs and shorts
    const longPositions = enhanced.filter(p => p.position_type === 'LONG')
    const shortPositions = enhanced.filter(p => p.position_type === 'SHORT')

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
  }
}
