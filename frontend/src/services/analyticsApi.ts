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
    let endpoint = API_ENDPOINTS.ANALYTICS.CORRELATION_MATRIX(portfolioId);
    const urlObj = new URL(apiClient.buildUrl(endpoint));
    if (params?.lookback_days != null) urlObj.searchParams.set('lookback_days', String(params.lookback_days));
    if (params?.min_overlap != null) urlObj.searchParams.set('min_overlap', String(params.min_overlap));
    const finalUrl = urlObj.toString();
    const data = await apiClient.get<CorrelationMatrixResponse>(finalUrl, {
      ...REQUEST_CONFIGS.CALCULATION,
      headers: { ...getAuthHeader() },
    });
    return { data, url: finalUrl };
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
    let endpoint = API_ENDPOINTS.ANALYTICS.POSITIONS_FACTOR_EXPOSURES(portfolioId);
    const urlObj = new URL(apiClient.buildUrl(endpoint));
    if (params?.limit != null) urlObj.searchParams.set('limit', String(params.limit));
    if (params?.offset != null) urlObj.searchParams.set('offset', String(params.offset));
    const finalUrl = urlObj.toString();
    const data = await apiClient.get<PositionFactorExposuresResponse>(finalUrl, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: { ...getAuthHeader() },
    });
    return { data, url: finalUrl };
  },

  async getStressTest(
    portfolioId: string,
    params?: { scenarios?: string }
  ): Promise<{ data: StressTestResponse; url: string }>
  {
    let endpoint = API_ENDPOINTS.ANALYTICS.STRESS_TEST(portfolioId);
    const urlObj = new URL(apiClient.buildUrl(endpoint));
    if (params?.scenarios) urlObj.searchParams.set('scenarios', params.scenarios);
    const finalUrl = urlObj.toString();
    const data = await apiClient.get<StressTestResponse>(finalUrl, {
      ...REQUEST_CONFIGS.CALCULATION,
      headers: { ...getAuthHeader() },
    });
    return { data, url: finalUrl };
  },
};

export default analyticsApi;

