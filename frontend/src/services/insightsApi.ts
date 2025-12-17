/**
 * AI Insights API Service
 *
 * Service layer for interacting with the AI insights backend endpoints.
 * Handles all API calls related to generating and managing portfolio insights.
 *
 * Pattern: Follows tagsApi.ts and portfolioService.ts patterns
 * Authentication: Uses existing apiClient with JWT token management
 *
 * Endpoints:
 * - POST   /api/v1/insights/generate                → Generate new insight
 * - GET    /api/v1/insights/portfolio/{portfolio_id} → List insights
 * - GET    /api/v1/insights/{insight_id}            → Get single insight
 * - PATCH  /api/v1/insights/{insight_id}            → Update metadata
 * - POST   /api/v1/insights/{insight_id}/feedback   → Submit feedback
 */

import { apiClient } from './apiClient'
import { API_ENDPOINTS } from '@/config/api'

// ============================================================================
// Type Definitions
// ============================================================================

export type InsightType =
  | 'daily_summary'
  | 'morning_briefing'
  | 'volatility_analysis'
  | 'concentration_risk'
  | 'hedge_quality'
  | 'factor_exposure'
  | 'stress_test_review'
  | 'custom'

export type InsightSeverity =
  | 'critical'
  | 'warning'
  | 'elevated'
  | 'normal'
  | 'info'

export interface InsightPerformance {
  cost_usd: number
  generation_time_ms: number
  token_count: number
}

export interface AIInsight {
  id: string
  portfolio_id: string
  insight_type: InsightType
  title: string
  severity: InsightSeverity
  summary: string
  key_findings: string[]
  recommendations: string[]
  full_analysis: string
  data_limitations: string
  focus_area: string | null
  user_question: string | null
  created_at: string
  viewed: boolean
  dismissed: boolean
  user_rating: number | null
  user_feedback: string | null
  performance: InsightPerformance
}

export interface GenerateInsightRequest {
  portfolio_id: string
  insight_type: InsightType
  focus_area?: string
  user_question?: string
}

export interface InsightsListResponse {
  insights: AIInsight[]
  total: number
  has_more: boolean
}

export interface UpdateInsightRequest {
  viewed?: boolean
  dismissed?: boolean
}

export interface InsightFeedbackRequest {
  rating: number
  feedback?: string
}

// ============================================================================
// API Service
// ============================================================================

const insightsApi = {
  /**
   * Generate a new AI insight for a portfolio
   *
   * Cost: ~$0.02, Time: 25-30 seconds
   * Rate limit: Max 10 per portfolio per day
   *
   * @param request - Generation request with portfolio_id, insight_type, optional focus_area/question
   * @returns Generated AIInsight with analysis and recommendations
   * @throws Error if generation fails or rate limit exceeded
   */
  async generateInsight(request: GenerateInsightRequest): Promise<AIInsight> {
    try {
      // Use 150 second timeout for Anthropic API calls (backend timeout is 120s + buffer)
      const response = await apiClient.post(API_ENDPOINTS.INSIGHTS.GENERATE, request, { timeout: 150000 })
      return response as AIInsight
    } catch (error: any) {
      console.error('Failed to generate insight:', error)

      // Handle rate limiting
      if (error.status === 429) {
        throw new Error('Daily insight generation limit reached (10 per portfolio per day)')
      }

      // Handle validation errors
      if (error.status === 400) {
        throw new Error(error.message || 'Invalid insight request')
      }

      throw new Error(error.message || 'Failed to generate insight')
    }
  },

  /**
   * List insights for a portfolio with filtering and pagination
   *
   * @param portfolioId - Portfolio UUID
   * @param options - Optional filters (insightType, daysBack, limit, offset)
   * @returns InsightsListResponse with insights array, total count, and has_more flag
   */
  async listInsights(
    portfolioId: string,
    options?: {
      insightType?: InsightType
      daysBack?: number
      limit?: number
      offset?: number
    }
  ): Promise<InsightsListResponse> {
    try {
      const params = new URLSearchParams()
      if (options?.insightType) params.append('insight_type', options.insightType)
      if (options?.daysBack) params.append('days_back', options.daysBack.toString())
      if (options?.limit) params.append('limit', options.limit.toString())
      if (options?.offset) params.append('offset', options.offset.toString())

      const queryString = params.toString()
      const url = queryString
        ? `${API_ENDPOINTS.INSIGHTS.LIST(portfolioId)}?${queryString}`
        : API_ENDPOINTS.INSIGHTS.LIST(portfolioId)

      const response = await apiClient.get(url)
      return response as InsightsListResponse
    } catch (error: any) {
      console.error('Failed to list insights:', error)
      throw new Error(error.message || 'Failed to fetch insights')
    }
  },

  /**
   * Get a single insight by ID
   *
   * Note: This endpoint automatically marks the insight as viewed
   *
   * @param insightId - Insight UUID
   * @returns AIInsight with full details
   */
  async getInsight(insightId: string): Promise<AIInsight> {
    try {
      const response = await apiClient.get(API_ENDPOINTS.INSIGHTS.GET(insightId))
      return response as AIInsight
    } catch (error: any) {
      console.error('Failed to get insight:', error)

      if (error.status === 404) {
        throw new Error('Insight not found')
      }

      throw new Error(error.message || 'Failed to fetch insight')
    }
  },

  /**
   * Update insight metadata (viewed, dismissed flags)
   *
   * @param insightId - Insight UUID
   * @param updates - Fields to update (viewed, dismissed)
   * @returns Updated AIInsight
   */
  async updateInsight(
    insightId: string,
    updates: UpdateInsightRequest
  ): Promise<AIInsight> {
    try {
      const response = await apiClient.patch(API_ENDPOINTS.INSIGHTS.UPDATE(insightId), updates)
      return response as AIInsight
    } catch (error: any) {
      console.error('Failed to update insight:', error)
      throw new Error(error.message || 'Failed to update insight')
    }
  },

  /**
   * Submit user feedback/rating for an insight
   *
   * @param insightId - Insight UUID
   * @param feedback - Rating (1-5) and optional text feedback
   * @returns Success message
   */
  async submitFeedback(
    insightId: string,
    feedback: InsightFeedbackRequest
  ): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.INSIGHTS.FEEDBACK(insightId), feedback)
    } catch (error: any) {
      console.error('Failed to submit feedback:', error)
      throw new Error(error.message || 'Failed to submit feedback')
    }
  },
}

export default insightsApi
