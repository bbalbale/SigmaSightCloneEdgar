/**
 * Admin API Service
 * Handles all admin dashboard API calls
 * Created: December 22, 2025 (Phase 6 Admin Dashboard)
 */

import { adminAuthService } from './adminAuthService'

// =============================================================================
// Types
// =============================================================================

// Onboarding Analytics Types
export interface OnboardingFunnel {
  funnel_steps: {
    step: string
    count: number
    conversion_rate: number | null
    drop_off_rate: number | null
  }[]
  period_days: number
  total_started: number
  total_completed: number
  overall_conversion_rate: number
}

export interface OnboardingError {
  error_code: string
  count: number
  percentage: number
  samples: string[]
}

export interface OnboardingErrors {
  period_days: number
  total_errors: number
  errors: OnboardingError[]
}

export interface OnboardingDailyTrend {
  date: string
  events: Record<string, number>
}

export interface OnboardingDaily {
  period_days: number
  trends: OnboardingDailyTrend[]
}

export interface OnboardingEvent {
  id: string
  user_id: string | null
  session_id: string | null
  event_type: string
  event_category: string
  event_data: Record<string, unknown>
  error_code: string | null
  created_at: string
}

// AI Metrics Types
export interface AIMetricsSummary {
  period_days: number
  total_requests: number
  avg_latency_ms: number | null
  avg_input_tokens: number | null
  avg_output_tokens: number | null
  error_rate: number
  tool_usage_rate: number
}

export interface AILatencyPercentiles {
  date_range: { start: string; end: string }
  sample_count: number
  p50_ms: number | null
  p75_ms: number | null
  p90_ms: number | null
  p95_ms: number | null
  p99_ms: number | null
  avg_ms: number | null
  min_ms: number | null
  max_ms: number | null
  avg_first_token_ms: number | null
}

export interface AITokenUsage {
  date_range: { start: string; end: string }
  total_input_tokens: number
  total_output_tokens: number
  daily: {
    date: string
    total_input_tokens: number
    total_output_tokens: number
    total_tokens: number
    request_count: number
    avg_input_tokens: number | null
    avg_output_tokens: number | null
  }[]
}

export interface AIErrorBreakdown {
  date_range: { start: string; end: string }
  total_errors: number
  error_rate: number
  breakdown: {
    error_type: string
    count: number
    percentage: number
    sample_messages: string[]
  }[]
}

export interface AIToolUsage {
  date_range: { start: string; end: string }
  total_tool_calls: number
  requests_with_tools: number
  avg_tools_per_request: number
  tools: {
    tool_name: string
    call_count: number
    percentage: number
  }[]
}

export interface AIModelUsage {
  date_range: { start: string; end: string }
  models: {
    model: string
    request_count: number
    percentage: number
    avg_latency_ms: number | null
    avg_tokens: number | null
  }[]
}

// Batch History Types
export interface BatchRun {
  id: string
  batch_run_id: string
  triggered_by: string
  started_at: string | null
  completed_at: string | null
  status: 'running' | 'completed' | 'failed' | 'partial'
  total_jobs: number
  completed_jobs: number
  failed_jobs: number
  duration_seconds: number | null
  phase_durations: Record<string, number>
  has_errors: boolean
}

export interface BatchRunDetails extends BatchRun {
  jobs: {
    total: number
    completed: number
    failed: number
    success_rate: number
  }
  error_summary: {
    count: number
    types: string[]
    details: string[]
  } | null
  created_at: string | null
}

export interface BatchHistory {
  success: boolean
  total_count: number
  days: number
  status_filter: string | null
  runs: BatchRun[]
}

export interface BatchHistorySummary {
  period_days: number
  total_runs: number
  status_breakdown: {
    completed: number
    failed: number
    partial: number
    running: number
  }
  success_rate_percent: number
  avg_duration_seconds: number | null
  most_recent: {
    batch_run_id: string | null
    status: string | null
    started_at: string | null
  } | null
}

// Dashboard Overview Types
export interface DashboardOverview {
  users: {
    total: number
    recent_registrations: number
  }
  conversations: {
    active_24h: number
    total: number
  }
  ai: {
    requests_today: number
    avg_latency_ms: number | null
    error_rate: number
  }
  batch: {
    last_run_status: string | null
    last_run_at: string | null
  }
}

// =============================================================================
// API Helper
// =============================================================================

async function adminFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = adminAuthService.getAccessToken()

  if (!token) {
    throw new Error('Admin not authenticated')
  }

  const response = await fetch(`/api/proxy${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include',
  })

  if (!response.ok) {
    if (response.status === 401) {
      adminAuthService.clearSession()
      throw new Error('Session expired. Please login again.')
    }
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `Request failed with status ${response.status}`)
  }

  return response.json()
}

// =============================================================================
// Admin API Service
// =============================================================================

class AdminApiService {
  // -------------------------------------------------------------------------
  // Onboarding Analytics
  // -------------------------------------------------------------------------

  /**
   * Get onboarding funnel conversion rates
   */
  async getOnboardingFunnel(days: number = 30): Promise<OnboardingFunnel> {
    return adminFetch<OnboardingFunnel>(
      `/api/v1/admin/onboarding/funnel?days=${days}`
    )
  }

  /**
   * Get onboarding error breakdown
   */
  async getOnboardingErrors(days: number = 30): Promise<OnboardingErrors> {
    return adminFetch<OnboardingErrors>(
      `/api/v1/admin/onboarding/errors?days=${days}`
    )
  }

  /**
   * Get daily onboarding trends
   */
  async getOnboardingDaily(days: number = 30): Promise<OnboardingDaily> {
    return adminFetch<OnboardingDaily>(
      `/api/v1/admin/onboarding/daily?days=${days}`
    )
  }

  /**
   * Get recent onboarding events
   */
  async getOnboardingEvents(
    limit: number = 50,
    eventType?: string,
    userId?: string
  ): Promise<{ events: OnboardingEvent[]; total_count: number }> {
    const params = new URLSearchParams({ limit: String(limit) })
    if (eventType) params.append('event_type', eventType)
    if (userId) params.append('user_id', userId)

    return adminFetch(`/api/v1/admin/onboarding/events?${params}`)
  }

  // -------------------------------------------------------------------------
  // AI Metrics
  // -------------------------------------------------------------------------

  /**
   * Get AI metrics summary
   */
  async getAIMetrics(days: number = 7): Promise<AIMetricsSummary> {
    return adminFetch<AIMetricsSummary>(
      `/api/v1/admin/ai/metrics?days=${days}`
    )
  }

  /**
   * Get AI latency percentiles
   */
  async getAILatency(days: number = 7): Promise<AILatencyPercentiles> {
    return adminFetch<AILatencyPercentiles>(
      `/api/v1/admin/ai/latency?days=${days}`
    )
  }

  /**
   * Get AI token usage trends
   */
  async getAITokens(days: number = 7): Promise<AITokenUsage> {
    return adminFetch<AITokenUsage>(
      `/api/v1/admin/ai/tokens?days=${days}`
    )
  }

  /**
   * Get AI error breakdown
   */
  async getAIErrors(days: number = 7): Promise<AIErrorBreakdown> {
    return adminFetch<AIErrorBreakdown>(
      `/api/v1/admin/ai/errors?days=${days}`
    )
  }

  /**
   * Get AI tool usage
   */
  async getAITools(days: number = 7): Promise<AIToolUsage> {
    return adminFetch<AIToolUsage>(
      `/api/v1/admin/ai/tools?days=${days}`
    )
  }

  /**
   * Get AI model usage breakdown
   */
  async getAIModels(days: number = 7): Promise<AIModelUsage> {
    return adminFetch<AIModelUsage>(
      `/api/v1/admin/ai/models?days=${days}`
    )
  }

  // -------------------------------------------------------------------------
  // Batch History
  // -------------------------------------------------------------------------

  /**
   * Get batch processing history
   */
  async getBatchHistory(
    days: number = 30,
    status?: string,
    limit: number = 50
  ): Promise<BatchHistory> {
    const params = new URLSearchParams({
      days: String(days),
      limit: String(limit),
    })
    if (status) params.append('status', status)

    return adminFetch<BatchHistory>(
      `/api/v1/admin/batch/history?${params}`
    )
  }

  /**
   * Get batch run details
   */
  async getBatchRunDetails(batchRunId: string): Promise<BatchRunDetails> {
    return adminFetch<BatchRunDetails>(
      `/api/v1/admin/batch/history/${encodeURIComponent(batchRunId)}`
    )
  }

  /**
   * Get batch history summary
   */
  async getBatchHistorySummary(days: number = 30): Promise<BatchHistorySummary> {
    return adminFetch<BatchHistorySummary>(
      `/api/v1/admin/batch/history/summary?days=${days}`
    )
  }

  // -------------------------------------------------------------------------
  // Dashboard Overview
  // -------------------------------------------------------------------------

  /**
   * Get dashboard overview data
   * Aggregates data from multiple endpoints
   */
  async getDashboardOverview(): Promise<DashboardOverview> {
    // Fetch data in parallel
    const [aiMetrics, batchSummary, onboardingFunnel] = await Promise.all([
      this.getAIMetrics(1).catch(() => null),
      this.getBatchHistorySummary(7).catch(() => null),
      this.getOnboardingFunnel(7).catch(() => null),
    ])

    return {
      users: {
        total: onboardingFunnel?.total_started || 0,
        recent_registrations: onboardingFunnel?.total_completed || 0,
      },
      conversations: {
        active_24h: aiMetrics?.total_requests || 0,
        total: 0, // Would need separate endpoint
      },
      ai: {
        requests_today: aiMetrics?.total_requests || 0,
        avg_latency_ms: aiMetrics?.avg_latency_ms || null,
        error_rate: aiMetrics?.error_rate || 0,
      },
      batch: {
        last_run_status: batchSummary?.most_recent?.status || null,
        last_run_at: batchSummary?.most_recent?.started_at || null,
      },
    }
  }
}

export const adminApiService = new AdminApiService()
