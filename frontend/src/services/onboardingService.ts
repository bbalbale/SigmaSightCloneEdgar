/**
 * Onboarding Service
 * Handles user registration, portfolio upload, and batch processing
 */

import { apiClient } from './apiClient';

export interface RegisterUserData {
  full_name: string;
  email: string;
  password: string;
  invite_code: string;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
  full_name: string;
  message: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface CreatePortfolioResponse {
  portfolio_id: string;
  portfolio_name: string;
  account_name: string;
  account_type: string;
  equity_balance: number;
  positions_imported: number;
  positions_failed: number;
  total_positions: number;
  message: string;
  next_step: {
    action: string;
    endpoint: string;
    description: string;
  };
}

export interface TriggerCalculationsResponse {
  portfolio_id: string;
  batch_run_id: string;
  status: string;
  message: string;
}

export interface BatchStatusResponse {
  status: 'idle' | 'running' | 'completed' | 'failed';
  batch_run_id: string;
  portfolio_id: string;
  started_at: string;
  triggered_by: string;
  elapsed_seconds: number;
}

// Phase 7.2: Onboarding Status Types
export interface ActivityLogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'warning' | 'error';
}

export interface CurrentPhaseProgress {
  current: number;
  total: number;
  unit: string;
}

export interface OverallProgress {
  current_phase: string | null;
  current_phase_name: string | null;
  phases_completed: number;
  phases_total: number;
  percent_complete: number;
}

export interface PhaseDetail {
  phase_id: string;
  phase_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current: number;
  total: number;
  unit: string;
  duration_seconds: number | null;
}

export interface OnboardingStatusResponse {
  portfolio_id: string;
  status: 'running' | 'completed' | 'failed' | 'not_found';
  started_at: string | null;
  elapsed_seconds: number;
  overall_progress: OverallProgress | null;
  current_phase_progress: CurrentPhaseProgress | null;
  activity_log: ActivityLogEntry[];
  phases: PhaseDetail[] | null;
}

/**
 * Onboarding Service
 */
export const onboardingService = {
  /**
   * Register a new user
   */
  register: async (data: RegisterUserData): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>(
      '/api/v1/onboarding/register',
      data
    );
    return response;  // apiClient.post already returns the data directly
  },

  /**
   * Login with email and password
   */
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>(
      '/api/v1/auth/login',
      { email, password }  // Backend expects JSON with email and password
    );
    return response;  // apiClient.post already returns the data directly
  },

  /**
   * Create portfolio with CSV upload
   * IMPORTANT: Do NOT set Content-Type manually - browser adds boundary automatically
   */
  createPortfolio: async (formData: FormData): Promise<CreatePortfolioResponse> => {
    const response = await apiClient.post<CreatePortfolioResponse>(
      '/api/v1/onboarding/create-portfolio',
      formData
      // No headers! Browser sets Content-Type with boundary
    );
    return response;  // apiClient.post already returns the data directly
  },

  /**
   * Trigger batch calculations for portfolio
   */
  triggerCalculations: async (portfolioId: string): Promise<TriggerCalculationsResponse> => {
    const response = await apiClient.post<TriggerCalculationsResponse>(
      `/api/v1/portfolios/${portfolioId}/calculate`  // Fixed: portfolios (plural)
    );
    return response;  // apiClient.post already returns the data directly
  },

  /**
   * Get batch processing status
   */
  getBatchStatus: async (portfolioId: string, batchRunId: string): Promise<BatchStatusResponse> => {
    const response = await apiClient.get<BatchStatusResponse>(
      `/api/v1/portfolios/${portfolioId}/batch-status/${batchRunId}`  // Fixed: portfolios (plural)
    );
    return response;  // apiClient.get already returns the data directly
  },

  /**
   * Download CSV template
   */
  downloadTemplate: () => {
    // Create a temporary anchor element to trigger download
    const link = document.createElement('a');
    link.href = '/api/proxy/api/v1/onboarding/csv-template';
    link.download = 'sigmasight_portfolio_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  /**
   * Get real-time onboarding status (Phase 7.2)
   * Poll this endpoint every 2 seconds during batch processing
   */
  getOnboardingStatus: async (portfolioId: string): Promise<OnboardingStatusResponse> => {
    const response = await apiClient.get<OnboardingStatusResponse>(
      `/api/v1/onboarding/status/${portfolioId}`
    );
    return response;
  },

  /**
   * Download onboarding logs (Phase 7.2)
   * Triggers browser download of the log file
   */
  downloadLogs: async (portfolioId: string, format: 'txt' | 'json' = 'txt'): Promise<void> => {
    // Get auth token using same priority as apiClient:
    // 1. Clerk token (primary), 2. localStorage (legacy fallback)
    let token: string | null = null;

    // Try Clerk token first (primary auth system)
    try {
      const { getClerkTokenAsync } = await import('@/lib/clerkTokenStore');
      token = await getClerkTokenAsync();
    } catch {
      // Clerk token store not available
    }

    // Fall back to localStorage (legacy auth)
    if (!token) {
      token = localStorage.getItem('access_token');
    }

    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(
      `/api/proxy/api/v1/onboarding/status/${portfolioId}/logs?format=${format}`,
      {
        method: 'GET',
        credentials: 'include',
        headers,
      }
    );

    if (!response.ok) {
      throw new Error('Failed to download logs');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    // Extract filename from Content-Disposition header or generate one
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `portfolio_setup_log_${portfolioId.slice(0, 8)}.${format}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) {
        filename = match[1];
      }
    }

    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};

export default onboardingService;
