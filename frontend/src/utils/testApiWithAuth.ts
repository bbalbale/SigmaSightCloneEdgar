/**
 * API Testing with Authentication
 * Tests the complete flow including login and portfolio data access
 */

import { apiClient } from '@/services/apiClient';
import { API_ENDPOINTS } from '@/config/api';

// Test user credentials (from backend demo data)
const TEST_CREDENTIALS = {
  email: 'demo@sigmasight.io',
  password: 'demo12345',
};

const DEMO_PORTFOLIO_ID = 'a3209353-9ed5-4885-81e8-d4bbc995f96c';

/**
 * Complete API test with authentication
 */
export async function testApiWithAuth(): Promise<{
  success: boolean;
  results: any[];
  errors: string[];
}> {
  const results: any[] = [];
  const errors: string[] = [];
  let authToken: string | null = null;

  console.log('🔐 Testing API with authentication...');

  try {
    // Step 1: Login to get authentication token
    console.log('📝 Attempting login...');
    const loginResponse = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, {
      email: TEST_CREDENTIALS.email,
      password: TEST_CREDENTIALS.password,
    });

    if (loginResponse.access_token) {
      authToken = loginResponse.access_token;
      results.push({
        test: 'Authentication',
        success: true,
        data: 'Successfully obtained access token',
        token: authToken.substring(0, 20) + '...',
      });
      console.log('✅ Authentication successful');

      // Add auth token to default headers
      apiClient.addRequestInterceptor(async (url, config) => {
        if (authToken) {
          config.headers = {
            ...config.headers,
            'Authorization': `Bearer ${authToken}`,
          };
        }
        return { url, config };
      });
    } else {
      throw new Error('No access token received');
    }
  } catch (error) {
    const errorMsg = `Authentication failed: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Authentication',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Authentication failed:', error);
    
    // Return early if auth fails
    return { success: false, results, errors };
  }

  // Step 2: Test portfolio complete endpoint
  try {
    console.log('📊 Testing portfolio complete endpoint...');
    const portfolioResponse = await apiClient.get(
      API_ENDPOINTS.PORTFOLIOS.COMPLETE(DEMO_PORTFOLIO_ID)
    );

    results.push({
      test: 'Portfolio Complete Data',
      success: true,
      data: {
        portfolioId: portfolioResponse.data?.metadata?.portfolio_id,
        portfolioName: portfolioResponse.data?.portfolio_info?.name,
        totalValue: portfolioResponse.data?.calculation_engines?.portfolio_snapshot?.data?.total_value,
        positionCount: portfolioResponse.data?.portfolio_info?.position_count,
        engines: Object.keys(portfolioResponse.data?.calculation_engines || {}),
      },
    });
    console.log(`✅ Portfolio data loaded: ${portfolioResponse.data?.portfolio_info?.name}`);
  } catch (error) {
    const errorMsg = `Failed to fetch portfolio: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Portfolio Complete Data',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Portfolio data failed:', error);
  }

  // Step 3: Test positions details endpoint
  try {
    console.log('📈 Testing positions details endpoint...');
    const positionsResponse = await apiClient.get(API_ENDPOINTS.POSITIONS.DETAILS);

    results.push({
      test: 'Position Details',
      success: true,
      data: {
        count: positionsResponse.data?.length || 0,
        symbols: positionsResponse.data?.slice(0, 5)?.map((p: any) => p.symbol) || [],
        samplePosition: positionsResponse.data?.[0] || null,
      },
    });
    console.log(`✅ Positions loaded: ${positionsResponse.data?.length || 0} positions`);
  } catch (error) {
    const errorMsg = `Failed to fetch positions: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Position Details',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Positions failed:', error);
  }

  // Step 4: Test market quotes endpoint (optional)
  try {
    console.log('💹 Testing market quotes endpoint...');
    const quotesResponse = await apiClient.get(API_ENDPOINTS.PRICES.QUOTES);

    results.push({
      test: 'Market Quotes',
      success: true,
      data: {
        count: quotesResponse.data?.length || 0,
        sampleQuotes: quotesResponse.data?.slice(0, 3)?.map((q: any) => ({
          symbol: q.symbol,
          price: q.price,
        })) || [],
      },
    });
    console.log(`✅ Market quotes: ${quotesResponse.data?.length || 0} quotes`);
  } catch (error) {
    // Market quotes might be optional
    results.push({
      test: 'Market Quotes',
      success: false,
      error: `Market data unavailable: ${error}`,
      optional: true,
    });
    console.warn('⚠️ Market quotes unavailable (non-critical):', error);
  }

  // Step 5: Test data quality endpoint
  try {
    console.log('🔍 Testing data quality endpoint...');
    const dataQualityResponse = await apiClient.get(
      API_ENDPOINTS.PORTFOLIOS.DATA_QUALITY(DEMO_PORTFOLIO_ID)
    );

    results.push({
      test: 'Data Quality Assessment',
      success: true,
      data: {
        portfolioId: dataQualityResponse.data?.portfolio_id,
        overallScore: dataQualityResponse.data?.overall_score,
        overallStatus: dataQualityResponse.data?.overall_status,
        metricCount: dataQualityResponse.data?.metrics?.length || 0,
      },
    });
    console.log('✅ Data quality assessment loaded');
  } catch (error) {
    results.push({
      test: 'Data Quality Assessment',
      success: false,
      error: `Data quality unavailable: ${error}`,
      optional: true,
    });
    console.warn('⚠️ Data quality unavailable (non-critical):', error);
  }

  // Step 6: Test factor ETF prices
  try {
    console.log('📊 Testing factor ETF prices endpoint...');
    const etfResponse = await apiClient.get(API_ENDPOINTS.FACTORS.ETF_PRICES);

    results.push({
      test: 'Factor ETF Prices',
      success: true,
      data: {
        count: etfResponse.data?.length || 0,
        sampleETFs: etfResponse.data?.slice(0, 3)?.map((etf: any) => ({
          symbol: etf.symbol,
          price: etf.price,
          category: etf.factor_category,
        })) || [],
      },
    });
    console.log(`✅ Factor ETF prices: ${etfResponse.data?.length || 0} ETFs`);
  } catch (error) {
    results.push({
      test: 'Factor ETF Prices',
      success: false,
      error: `Factor ETF data unavailable: ${error}`,
      optional: true,
    });
    console.warn('⚠️ Factor ETF data unavailable (non-critical):', error);
  }

  // Summary
  const success = errors.length === 0;
  const summary = {
    total: results.length,
    passed: results.filter(r => r.success).length,
    failed: results.filter(r => !r.success && !r.optional).length,
    optional: results.filter(r => r.optional).length,
  };

  console.log(`\n📊 API Test Summary:`);
  console.log(`   Total tests: ${summary.total}`);
  console.log(`   Passed: ${summary.passed}`);
  console.log(`   Failed: ${summary.failed}`);
  console.log(`   Optional: ${summary.optional}`);
  console.log(`   Overall: ${success ? '✅ PASSED' : '❌ FAILED'}`);

  if (errors.length > 0) {
    console.log(`\n🚨 Critical Errors:`);
    errors.forEach(error => console.log(`   - ${error}`));
  }

  return {
    success,
    results,
    errors,
  };
}

/**
 * Quick authenticated connection test
 */
export async function quickAuthTest(): Promise<boolean> {
  try {
    console.log('🚀 Quick authenticated connection test...');
    
    // Login
    const loginResponse = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, TEST_CREDENTIALS);
    
    if (!loginResponse.access_token) {
      throw new Error('Authentication failed');
    }

    // Add auth header
    const authToken = loginResponse.access_token;
    apiClient.addRequestInterceptor(async (url, config) => {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${authToken}`,
      };
      return { url, config };
    });

    // Test portfolio endpoint
    const portfolio = await apiClient.get(
      API_ENDPOINTS.PORTFOLIOS.COMPLETE(DEMO_PORTFOLIO_ID)
    );

    console.log(`✅ Authentication & portfolio access successful: ${portfolio.data?.portfolio_info?.name}`);
    return true;
  } catch (error) {
    console.error('❌ Authenticated connection failed:', error);
    return false;
  }
}

// Browser console access
if (typeof window !== 'undefined') {
  (window as any).testApiAuth = {
    testApiWithAuth,
    quickAuthTest,
    credentials: TEST_CREDENTIALS,
    portfolioId: DEMO_PORTFOLIO_ID,
  };
  
  console.log('🔐 Authenticated API test functions available on window.testApiAuth');
  console.log('   - testApiWithAuth()');
  console.log('   - quickAuthTest()');
}