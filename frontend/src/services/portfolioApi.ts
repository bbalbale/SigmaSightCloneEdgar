/**
 * Portfolio API Service Layer
 * Provides high-level methods for portfolio data operations
 */

import { apiClient } from './apiClient';
import { API_ENDPOINTS, REQUEST_CONFIGS, DEMO_PORTFOLIOS } from '@/config/api';
import type {
  PortfolioReport,
  PortfolioListItem,
  Position,
  MarketQuote,
  HistoricalPriceResponse,
  FactorETFPrice,
  DataQualityResponse,
  ApiResponse,
  ApiListResponse,
  LoadingState,
} from '@/types/portfolio';

/**
 * Portfolio Service Class
 * Handles all portfolio-related API operations
 */
export class PortfolioService {
  /**
   * Get list of all available portfolios
   */
  async getPortfolios(): Promise<PortfolioListItem[]> {
    try {
      const response = await apiClient.get<ApiListResponse<PortfolioListItem>>(
        API_ENDPOINTS.PORTFOLIOS.LIST,
        REQUEST_CONFIGS.STANDARD
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch portfolios:', error);
      throw new Error('Unable to load portfolio list. Please check your connection and try again.');
    }
  }

  /**
   * Get complete portfolio data including all calculation engines
   */
  async getPortfolioComplete(portfolioId: string): Promise<PortfolioReport> {
    try {
      const response = await apiClient.get<ApiResponse<PortfolioReport>>(
        API_ENDPOINTS.PORTFOLIOS.COMPLETE(portfolioId),
        REQUEST_CONFIGS.STANDARD
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch portfolio ${portfolioId}:`, error);
      throw new Error(`Unable to load portfolio data. Portfolio ID: ${portfolioId}`);
    }
  }

  /**
   * Get portfolio data quality assessment
   */
  async getPortfolioDataQuality(portfolioId: string): Promise<DataQualityResponse> {
    try {
      const response = await apiClient.get<ApiResponse<DataQualityResponse>>(
        API_ENDPOINTS.PORTFOLIOS.DATA_QUALITY(portfolioId),
        REQUEST_CONFIGS.STANDARD
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch data quality for ${portfolioId}:`, error);
      throw new Error('Unable to load data quality assessment.');
    }
  }

  /**
   * Get detailed position information
   */
  async getPositionDetails(portfolioId?: string): Promise<Position[]> {
    try {
      const endpoint = portfolioId 
        ? API_ENDPOINTS.POSITIONS.BY_PORTFOLIO(portfolioId)
        : API_ENDPOINTS.POSITIONS.DETAILS;

      const response = await apiClient.get<ApiListResponse<Position>>(
        endpoint,
        REQUEST_CONFIGS.STANDARD
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch position details:', error);
      throw new Error('Unable to load position data. Please try again.');
    }
  }

  /**
   * Get real-time market quotes for symbols
   */
  async getMarketQuotes(symbols?: string[]): Promise<MarketQuote[]> {
    try {
      const endpoint = symbols?.length 
        ? `${API_ENDPOINTS.PRICES.QUOTES}?symbols=${symbols.join(',')}`
        : API_ENDPOINTS.PRICES.QUOTES;

      const response = await apiClient.get<ApiListResponse<MarketQuote>>(
        endpoint,
        REQUEST_CONFIGS.REALTIME
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch market quotes:', error);
      // Don't throw for market data failures - graceful degradation
      return [];
    }
  }

  /**
   * Get historical price data for a symbol
   */
  async getHistoricalPrices(symbolId: string, days: number = 30): Promise<HistoricalPriceResponse> {
    try {
      const endpoint = `${API_ENDPOINTS.PRICES.HISTORICAL(symbolId)}?days=${days}`;
      const response = await apiClient.get<ApiResponse<HistoricalPriceResponse>>(
        endpoint,
        REQUEST_CONFIGS.STANDARD
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch historical prices for ${symbolId}:`, error);
      throw new Error(`Unable to load historical data for ${symbolId}.`);
    }
  }

  /**
   * Get factor ETF prices for factor analysis
   */
  async getFactorETFPrices(): Promise<FactorETFPrice[]> {
    try {
      const response = await apiClient.get<ApiListResponse<FactorETFPrice>>(
        API_ENDPOINTS.FACTORS.ETF_PRICES,
        REQUEST_CONFIGS.STANDARD
      );
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch factor ETF prices:', error);
      // Non-critical data - return empty array for graceful degradation
      return [];
    }
  }

  /**
   * Get batch status for monitoring backend calculations
   */
  async getBatchStatus(): Promise<any> {
    try {
      const response = await apiClient.get<any>(
        API_ENDPOINTS.ADMIN.BATCH_STATUS,
        REQUEST_CONFIGS.STANDARD
      );
      return response;
    } catch (error) {
      console.error('Failed to fetch batch status:', error);
      return null;
    }
  }
}

/**
 * Composite Service for Portfolio Dashboard
 * Combines multiple API calls for dashboard display
 */
export class PortfolioDashboardService extends PortfolioService {
  /**
   * Load all data needed for portfolio dashboard
   */
  async loadDashboardData(portfolioId: string): Promise<{
    portfolio: PortfolioReport;
    positions: Position[];
    quotes: MarketQuote[];
    dataQuality: DataQualityResponse | null;
  }> {
    try {
      // Start all requests in parallel for better performance
      const [
        portfolioPromise,
        positionsPromise,
        quotesPromise,
        dataQualityPromise,
      ] = await Promise.allSettled([
        this.getPortfolioComplete(portfolioId),
        this.getPositionDetails(portfolioId),
        this.getMarketQuotes(),
        this.getPortfolioDataQuality(portfolioId).catch(() => null), // Optional
      ]);

      // Extract results and handle failures gracefully
      const portfolio = portfolioPromise.status === 'fulfilled' 
        ? portfolioPromise.value 
        : null;

      const positions = positionsPromise.status === 'fulfilled'
        ? positionsPromise.value
        : [];

      const quotes = quotesPromise.status === 'fulfilled'
        ? quotesPromise.value
        : [];

      const dataQuality = dataQualityPromise.status === 'fulfilled'
        ? dataQualityPromise.value
        : null;

      if (!portfolio) {
        throw new Error('Failed to load essential portfolio data');
      }

      return {
        portfolio,
        positions,
        quotes,
        dataQuality,
      };
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      throw error;
    }
  }

  /**
   * Refresh market data only (for periodic updates)
   */
  async refreshMarketData(symbols: string[]): Promise<MarketQuote[]> {
    return this.getMarketQuotes(symbols);
  }
}

// Create service instances
export const portfolioService = new PortfolioService();
export const dashboardService = new PortfolioDashboardService();

/**
 * Hook-style functions for React components
 * These provide loading states and error handling
 */

/**
 * Create a loading state wrapper for async operations
 */
export function createLoadingState<T>(initialData: T | null = null): LoadingState<T> {
  return {
    data: initialData,
    loading: false,
    error: null,
    lastUpdated: undefined,
  };
}

/**
 * Execute async operation with loading state management
 */
export async function withLoadingState<T>(
  operation: () => Promise<T>,
  loadingState: LoadingState<T>
): Promise<LoadingState<T>> {
  try {
    loadingState.loading = true;
    loadingState.error = null;
    
    const result = await operation();
    
    return {
      data: result,
      loading: false,
      error: null,
      lastUpdated: new Date().toISOString(),
    };
  } catch (error) {
    return {
      data: loadingState.data, // Keep previous data if any
      loading: false,
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
      lastUpdated: loadingState.lastUpdated,
    };
  }
}

/**
 * Portfolio API utility functions
 */
export const portfolioApiUtils = {
  /**
   * Check if a portfolio ID is a demo portfolio
   */
  isDemoPortfolio(portfolioId: string): boolean {
    return Object.values(DEMO_PORTFOLIOS).includes(portfolioId as any);
  },

  /**
   * Get demo portfolio name from ID
   */
  getDemoPortfolioName(portfolioId: string): string | null {
    switch (portfolioId) {
      case DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR:
        return 'Demo Individual Investor';
      case DEMO_PORTFOLIOS.HIGH_NET_WORTH:
        return 'Demo High Net Worth';
      case DEMO_PORTFOLIOS.HEDGE_FUND_STYLE:
        return 'Demo Hedge Fund Style';
      default:
        return null;
    }
  },

  /**
   * Get all demo portfolio IDs
   */
  getDemoPortfolioIds(): string[] {
    return Object.values(DEMO_PORTFOLIOS);
  },

  /**
   * Get default portfolio ID
   */
  getDefaultPortfolioId(): string {
    return process.env.NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID || DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR;
  },

  /**
   * Validate portfolio ID format (UUID)
   */
  isValidPortfolioId(portfolioId: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(portfolioId);
  },

  /**
   * Extract symbols from positions for market data requests
   */
  extractSymbols(positions: Position[]): string[] {
    return [...new Set(positions.map(p => p.symbol))];
  },
};

// Export default service for convenience
export default portfolioService;