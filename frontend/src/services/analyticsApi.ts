import { apiClient } from './apiClient';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';
import type {
  PortfolioOverviewResponse,
  CorrelationMatrixResponse,
  PortfolioFactorExposuresResponse,
  PositionFactorExposuresResponse,
  StressTestResponse,
} from '@/types/analytics';

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const analyticsApi = {
  async getOverview(portfolioId: string): Promise<{ data: PortfolioOverviewResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.OVERVIEW(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<PortfolioOverviewResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: { ...getAuthHeader() },
    });
    return { data, url };
  },

  async getCorrelationMatrix(
    portfolioId: string,
    params?: { lookback_days?: number; min_overlap?: number }
  ): Promise<{ data: CorrelationMatrixResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.CORRELATION_MATRIX(portfolioId);
    const queryParams = new URLSearchParams();
    if (params?.lookback_days != null) queryParams.set('lookback_days', String(params.lookback_days));
    if (params?.min_overlap != null) queryParams.set('min_overlap', String(params.min_overlap));
    const queryString = queryParams.toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
    const url = apiClient.buildUrl(fullEndpoint);
    const data = await apiClient.get<CorrelationMatrixResponse>(fullEndpoint, {
      ...REQUEST_CONFIGS.CALCULATION,
      headers: { ...getAuthHeader() },
    });
    return { data, url };
  },

  async getPortfolioFactorExposures(
    portfolioId: string
  ): Promise<{ data: PortfolioFactorExposuresResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.FACTOR_EXPOSURES(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<PortfolioFactorExposuresResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: { ...getAuthHeader() },
    });
    return { data, url };
  },

  async getPositionFactorExposures(
    portfolioId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<{ data: PositionFactorExposuresResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.POSITIONS_FACTOR_EXPOSURES(portfolioId);
    const queryParams = new URLSearchParams();
    if (params?.limit != null) queryParams.set('limit', String(params.limit));
    if (params?.offset != null) queryParams.set('offset', String(params.offset));
    const queryString = queryParams.toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
    const url = apiClient.buildUrl(fullEndpoint);
    const data = await apiClient.get<PositionFactorExposuresResponse>(fullEndpoint, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: { ...getAuthHeader() },
    });
    return { data, url };
  },

  async getStressTest(
    portfolioId: string,
    params?: { scenarios?: string }
  ): Promise<{ data: StressTestResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.STRESS_TEST(portfolioId);
    const queryParams = new URLSearchParams();
    if (params?.scenarios) queryParams.set('scenarios', params.scenarios);
    const queryString = queryParams.toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
    const url = apiClient.buildUrl(fullEndpoint);
    const data = await apiClient.get<StressTestResponse>(fullEndpoint, {
      ...REQUEST_CONFIGS.CALCULATION,
      headers: { ...getAuthHeader() },
    });
    return { data, url };
  },
};

export default analyticsApi;

