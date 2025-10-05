/**
 * API Configuration and Environment Variables
 * Provides centralized configuration for backend API communication
 */

// Environment-based API configuration
export const API_CONFIG = {
  // Base API URL - defaults to localhost for development
  BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  
  // Request timeout settings (in milliseconds)
  TIMEOUT: {
    DEFAULT: 10000,  // 10 seconds
    LONG: 30000,     // 30 seconds for complex operations
    SHORT: 5000,     // 5 seconds for quick operations
  },
  
  // Retry configuration
  RETRY: {
    COUNT: 2,        // Number of retry attempts
    DELAY: 1000,     // Base delay between retries (ms)
  },
  
  // Cache settings
  CACHE: {
    ENABLED: process.env.NODE_ENV === 'production',
    TTL: 300000,     // 5 minutes in milliseconds
  },
};

// API Endpoint mapping - organized by feature area
export const API_ENDPOINTS = {
  // Authentication endpoints
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    LOGOUT: '/api/v1/auth/logout',
    REFRESH: '/api/v1/auth/refresh',
    ME: '/api/v1/auth/me',
  },
  
  // Portfolio data endpoints (real data available)
  PORTFOLIOS: {
    LIST: '/api/v1/data/portfolios',
    COMPLETE: (id: string) => `/api/v1/data/portfolio/${id}/complete`,
    DATA_QUALITY: (id: string) => `/api/v1/data/portfolio/${id}/data-quality`,
    STRATEGIES: (id: string) => `/api/v1/strategies/?portfolio_id=${id}`,
  },
  
  // Position data endpoints
  POSITIONS: {
    DETAILS: '/api/v1/data/positions/details',
    BY_PORTFOLIO: (portfolioId: string) => `/api/v1/data/positions/details?portfolio_id=${portfolioId}`,
  },
  
  // Market data endpoints  
  PRICES: {
    QUOTES: '/api/v1/data/prices/quotes',
    HISTORICAL: (id: string) => `/api/v1/data/prices/historical/${id}`,
    BATCH_QUOTES: '/api/v1/data/prices/quotes/batch',
  },
  
  // Factor analysis endpoints
  FACTORS: {
    ETF_PRICES: '/api/v1/data/factors/etf-prices',
    ANALYSIS: (portfolioId: string) => `/api/v1/data/factors/analysis?portfolio_id=${portfolioId}`,
  },
  
  // Analytics endpoints
  ANALYTICS: {
    OVERVIEW: (portfolioId: string) => `/api/v1/analytics/portfolio/${portfolioId}/overview`,
    CORRELATION_MATRIX: (portfolioId: string) => `/api/v1/analytics/portfolio/${portfolioId}/correlation-matrix`,
    FACTOR_EXPOSURES: (portfolioId: string) => `/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`,
    POSITIONS_FACTOR_EXPOSURES: (portfolioId: string) => `/api/v1/analytics/portfolio/${portfolioId}/positions/factor-exposures`,
    STRESS_TEST: (portfolioId: string) => `/api/v1/analytics/portfolio/${portfolioId}/stress-test`,
  },

  // Strategy management endpoints
  STRATEGIES: {
    LIST: '/api/v1/strategies/',
    GET: (id: string) => `/api/v1/strategies/${id}`,
    CREATE: '/api/v1/strategies/',
    UPDATE: (id: string) => `/api/v1/strategies/${id}`,
    DELETE: (id: string) => `/api/v1/strategies/${id}`,
    COMBINE: '/api/v1/strategies/combine',
    DETECT: (portfolioId: string) => `/api/v1/strategies/detect/${portfolioId}`,
    TAGS: {
      GET: (id: string) => `/api/v1/strategies/${id}/tags`,
      REPLACE: (id: string) => `/api/v1/strategies/${id}/tags`,
      ADD: (id: string) => `/api/v1/strategies/${id}/tags`,
      REMOVE: (id: string) => `/api/v1/strategies/${id}/tags`,
    },
  },

  // Tag management endpoints (user-scoped tags)
  TAGS: {
    LIST: '/api/v1/tags',
    CREATE: '/api/v1/tags',
    GET: (id: string) => `/api/v1/tags/${id}`,
    UPDATE: (id: string) => `/api/v1/tags/${id}`,
    ARCHIVE: (id: string) => `/api/v1/tags/${id}/archive`,
    RESTORE: (id: string) => `/api/v1/tags/${id}/restore`,
    ASSIGN: '/api/v1/tags/assign',
    BULK_ASSIGN: '/api/v1/tags/bulk-assign',
    STRATEGIES_BY_TAG: (id: string) => `/api/v1/tags/${id}/strategies`,
    POSITIONS_BY_TAG: (id: string) => `/api/v1/tags/${id}/positions`, // New: Position tagging system
    DEFAULTS: '/api/v1/tags/defaults',
  },

  // Position tagging endpoints (new position tagging system)
  POSITION_TAGS: {
    GET: (positionId: string) => `/api/v1/positions/${positionId}/tags`,
    ADD: (positionId: string) => `/api/v1/positions/${positionId}/tags`,
    REMOVE: (positionId: string) => `/api/v1/positions/${positionId}/tags`,
    REPLACE: (positionId: string) => `/api/v1/positions/${positionId}/tags`,
  },
  
  // Admin endpoints (for monitoring)
  ADMIN: {
    BATCH_STATUS: '/api/v1/admin/batch/status',
    HEALTH: '/api/v1/admin/health',
  },
} as const;

// Demo Portfolio IDs (from backend reports)
export const DEMO_PORTFOLIOS = {
  INDIVIDUAL_INVESTOR: 'a3209353-9ed5-4885-81e8-d4bbc995f96c',
  HIGH_NET_WORTH: 'b4310464-aed6-5b96-92f9-e5ccd006fa0d', // TODO: Get actual ID from backend
  HEDGE_FUND_STYLE: 'c5421575-bf07-6ca7-a30a-f6dde117gb1e', // TODO: Get actual ID from backend
} as const;

// Request configuration presets for different operation types
export const REQUEST_CONFIGS = {
  // Standard portfolio data requests
  STANDARD: {
    timeout: API_CONFIG.TIMEOUT.DEFAULT,
    retries: API_CONFIG.RETRY.COUNT,
    cache: API_CONFIG.CACHE.ENABLED,
  },
  
  // Real-time market data (short timeout, no cache)
  REALTIME: {
    timeout: API_CONFIG.TIMEOUT.SHORT,
    retries: 1,
    cache: false,
  },
  
  // Long-running calculations
  CALCULATION: {
    timeout: API_CONFIG.TIMEOUT.LONG,
    retries: 3,
    cache: false,
  },
  
  // Authentication requests
  AUTH: {
    timeout: API_CONFIG.TIMEOUT.DEFAULT,
    retries: 1,
    cache: false,
  },
} as const;

// Environment validation
export const validateEnvironment = (): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];
  
  // Check required environment variables
  if (!process.env.NEXT_PUBLIC_API_BASE_URL && process.env.NODE_ENV === 'production') {
    errors.push('NEXT_PUBLIC_API_BASE_URL is required in production');
  }
  
  // Validate API URL format
  try {
    new URL(API_CONFIG.BASE_URL);
  } catch {
    errors.push(`Invalid API_BASE_URL format: ${API_CONFIG.BASE_URL}`);
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
};

// Utility function to build full API URLs
export const buildApiUrl = (endpoint: string): string => {
  if (endpoint.startsWith('http')) {
    return endpoint;
  }
  
  const baseUrl = API_CONFIG.BASE_URL.replace(/\/$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  return `${baseUrl}${cleanEndpoint}`;
};

// Export types for TypeScript support
export type ApiEndpoint = typeof API_ENDPOINTS;
export type RequestConfig = typeof REQUEST_CONFIGS[keyof typeof REQUEST_CONFIGS];

export default API_CONFIG;
