import { apiClient } from './apiClient';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';
import type {
  PortfolioOverviewResponse,
  CorrelationMatrixResponse,
  DiversificationScoreResponse,
  PortfolioFactorExposuresResponse,
  PositionFactorExposuresResponse,
  StressTestResponse,
  VolatilityMetricsResponse,
  SectorExposureResponse,
  ConcentrationMetricsResponse,
  // Aggregate types
  AggregateOverviewResponse,
  AggregateBreakdownResponse,
  AggregateBetaResponse,
  AggregateVolatilityResponse,
  AggregateFactorExposuresResponse,
  AggregateSectorExposureResponse,
  AggregateConcentrationResponse,
  AggregateCorrelationMatrixResponse,
  AggregateStressTestResponse,
} from '@/types/analytics';

// Note: apiClient handles Clerk token auth via interceptor, no manual auth headers needed

export const analyticsApi = {
  async getOverview(portfolioId: string): Promise<{ data: PortfolioOverviewResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.OVERVIEW(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<PortfolioOverviewResponse>(endpoint, {
      ...REQUEST_CONFIGS.ANALYTICS_HEAVY,
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
    });
    return { data, url };
  },

  async getDiversificationScore(
    portfolioId: string
  ): Promise<{ data: DiversificationScoreResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.DIVERSIFICATION_SCORE(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<DiversificationScoreResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getPortfolioFactorExposures(
    portfolioId: string,
    useLatestSuccessful: boolean = true  // Graceful degradation by default
  ): Promise<{ data: PortfolioFactorExposuresResponse; url: string }>
  {
    const baseEndpoint = API_ENDPOINTS.ANALYTICS.FACTOR_EXPOSURES(portfolioId);
    const endpoint = useLatestSuccessful
      ? `${baseEndpoint}?use_latest_successful=true`
      : baseEndpoint;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<PortfolioFactorExposuresResponse>(endpoint, {
      ...REQUEST_CONFIGS.ANALYTICS_HEAVY,
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
    });
    return { data, url };
  },

  async getVolatility(
    portfolioId: string
  ): Promise<{ data: VolatilityMetricsResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.VOLATILITY(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<VolatilityMetricsResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getSectorExposure(
    portfolioId: string
  ): Promise<{ data: SectorExposureResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.SECTOR_EXPOSURE(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<SectorExposureResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getConcentration(
    portfolioId: string
  ): Promise<{ data: ConcentrationMetricsResponse; url: string }>
  {
    const endpoint = API_ENDPOINTS.ANALYTICS.CONCENTRATION(portfolioId);
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<ConcentrationMetricsResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  // ============================================================================
  // Aggregate Methods (Equity-weighted across all portfolios)
  // ============================================================================

  async getAggregateOverview(): Promise<{ data: AggregateOverviewResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.OVERVIEW;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateOverviewResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateBreakdown(): Promise<{ data: AggregateBreakdownResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.BREAKDOWN;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateBreakdownResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateBeta(): Promise<{ data: AggregateBetaResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.BETA;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateBetaResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateVolatility(): Promise<{ data: AggregateVolatilityResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.VOLATILITY;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateVolatilityResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateFactorExposures(): Promise<{ data: AggregateFactorExposuresResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.FACTOR_EXPOSURES;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateFactorExposuresResponse>(endpoint, {
      ...REQUEST_CONFIGS.ANALYTICS_HEAVY,
    });
    return { data, url };
  },

  async getAggregateSectorExposure(): Promise<{ data: AggregateSectorExposureResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.SECTOR_EXPOSURE;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateSectorExposureResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateConcentration(): Promise<{ data: AggregateConcentrationResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.CONCENTRATION;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateConcentrationResponse>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    });
    return { data, url };
  },

  async getAggregateCorrelationMatrix(
    params?: { lookback_days?: number; max_positions?: number }
  ): Promise<{ data: AggregateCorrelationMatrixResponse; url: string }> {
    const baseEndpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.CORRELATION_MATRIX;
    const queryParams = new URLSearchParams();
    if (params?.lookback_days != null) queryParams.set('lookback_days', String(params.lookback_days));
    if (params?.max_positions != null) queryParams.set('max_positions', String(params.max_positions));
    const queryString = queryParams.toString();
    const endpoint = queryString ? `${baseEndpoint}?${queryString}` : baseEndpoint;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateCorrelationMatrixResponse>(endpoint, {
      ...REQUEST_CONFIGS.CALCULATION,
    });
    return { data, url };
  },

  async getAggregateStressTest(): Promise<{ data: AggregateStressTestResponse; url: string }> {
    const endpoint = API_ENDPOINTS.ANALYTICS.AGGREGATE.STRESS_TEST;
    const url = apiClient.buildUrl(endpoint);
    const data = await apiClient.get<AggregateStressTestResponse>(endpoint, {
      ...REQUEST_CONFIGS.CALCULATION,
    });
    return { data, url };
  },
};

export default analyticsApi;

