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
      `/api/v1/portfolio/${portfolioId}/calculate`
    );
    return response;  // apiClient.post already returns the data directly
  },

  /**
   * Get batch processing status
   */
  getBatchStatus: async (portfolioId: string, batchRunId: string): Promise<BatchStatusResponse> => {
    const response = await apiClient.get<BatchStatusResponse>(
      `/api/v1/portfolio/${portfolioId}/batch-status/${batchRunId}`
    );
    return response;  // apiClient.get already returns the data directly
  },

  /**
   * Download CSV template
   */
  downloadTemplate: () => {
    window.open('/api/proxy/api/v1/onboarding/csv-template', '_blank');
  },
};

export default onboardingService;
