/**
 * Phase 1 Comprehensive Testing
 * Tests all components built in Phase 1 without requiring backend
 */

import { apiClient, ApiError, NetworkError, TimeoutError } from '@/services/apiClient';
import { API_CONFIG, API_ENDPOINTS, DEMO_PORTFOLIOS, validateEnvironment } from '@/config/api';
import { portfolioService, dashboardService, portfolioApiUtils } from '@/services/portfolioApi';
import { 
  formatCurrency, 
  formatPercentage, 
  formatNumber, 
  formatDate, 
  transformToSummaryMetrics,
  transformPositionsToTableRows,
  validatePortfolioData,
  safeParseFloat 
} from '@/utils/dataTransform';
import type { PortfolioReport, Position } from '@/types/portfolio';

interface TestResult {
  category: string;
  test: string;
  success: boolean;
  data?: any;
  error?: string;
  duration?: number;
}

/**
 * Test all Phase 1 components
 */
export async function testPhase1Complete(): Promise<{
  success: boolean;
  results: TestResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    categories: Record<string, { passed: number; total: number }>;
  };
}> {
  console.log('🧪 Starting Phase 1 Comprehensive Testing...\n');
  
  const results: TestResult[] = [];
  const startTime = Date.now();

  // Test 1: Configuration and Environment
  console.log('📋 Testing Configuration...');
  await testConfiguration(results);

  // Test 2: Type Definitions and Imports
  console.log('🏗️ Testing Type Definitions...');
  await testTypeDefinitions(results);

  // Test 3: API Client (without network calls)
  console.log('🌐 Testing API Client...');
  await testApiClient(results);

  // Test 4: Data Transformation Utilities
  console.log('🔄 Testing Data Transformation...');
  await testDataTransformation(results);

  // Test 5: Portfolio Service (mock mode)
  console.log('📊 Testing Portfolio Services...');
  await testPortfolioServices(results);

  // Test 6: Error Handling
  console.log('🚨 Testing Error Handling...');
  await testErrorHandling(results);

  const totalTime = Date.now() - startTime;
  const summary = generateSummary(results);

  console.log(`\n📊 Phase 1 Test Summary (${totalTime}ms):`);
  console.log(`   Total Tests: ${summary.total}`);
  console.log(`   Passed: ${summary.passed} (${Math.round(summary.passed/summary.total*100)}%)`);
  console.log(`   Failed: ${summary.failed}`);
  
  Object.entries(summary.categories).forEach(([category, stats]) => {
    const percent = Math.round(stats.passed/stats.total*100);
    console.log(`   ${category}: ${stats.passed}/${stats.total} (${percent}%)`);
  });

  console.log(`\n${summary.failed === 0 ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`);

  return {
    success: summary.failed === 0,
    results,
    summary,
  };
}

/**
 * Test configuration and environment setup
 */
async function testConfiguration(results: TestResult[]) {
  const category = 'Configuration';

  // Test environment validation
  try {
    const validation = validateEnvironment();
    results.push({
      category,
      test: 'Environment Validation',
      success: validation.valid,
      data: validation.errors.length === 0 ? 'All environment variables valid' : validation.errors,
    });
  } catch (error) {
    results.push({
      category,
      test: 'Environment Validation',
      success: false,
      error: `${error}`,
    });
  }

  // Test API config values
  try {
    const configValid = API_CONFIG.BASE_URL && 
                       API_CONFIG.TIMEOUT.DEFAULT > 0 &&
                       API_CONFIG.RETRY.COUNT >= 0;
    
    results.push({
      category,
      test: 'API Configuration',
      success: configValid,
      data: {
        baseUrl: API_CONFIG.BASE_URL,
        timeout: API_CONFIG.TIMEOUT.DEFAULT,
        retries: API_CONFIG.RETRY.COUNT,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'API Configuration',
      success: false,
      error: `${error}`,
    });
  }

  // Test endpoint definitions
  try {
    const endpointsValid = Object.keys(API_ENDPOINTS).length > 0 &&
                          API_ENDPOINTS.AUTH.LOGIN &&
                          API_ENDPOINTS.PORTFOLIOS.COMPLETE;

    results.push({
      category,
      test: 'Endpoint Definitions',
      success: endpointsValid,
      data: {
        endpointCount: Object.keys(API_ENDPOINTS).length,
        authEndpoints: Object.keys(API_ENDPOINTS.AUTH).length,
        portfolioEndpoints: Object.keys(API_ENDPOINTS.PORTFOLIOS).length,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Endpoint Definitions',
      success: false,
      error: `${error}`,
    });
  }

  // Test demo portfolio IDs
  try {
    const demoPortfoliosValid = Object.values(DEMO_PORTFOLIOS).length > 0 &&
                               portfolioApiUtils.isValidPortfolioId(DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR);

    results.push({
      category,
      test: 'Demo Portfolio IDs',
      success: demoPortfoliosValid,
      data: {
        count: Object.keys(DEMO_PORTFOLIOS).length,
        individualInvestor: DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR,
        validFormat: portfolioApiUtils.isValidPortfolioId(DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR),
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Demo Portfolio IDs',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Test TypeScript definitions and imports
 */
async function testTypeDefinitions(results: TestResult[]) {
  const category = 'Types';

  // Test portfolio interfaces exist and have required properties
  try {
    const mockPortfolio: Partial<PortfolioReport> = {
      version: '1.0',
      metadata: {
        portfolio_id: 'test-id',
        portfolio_name: 'Test Portfolio',
        report_date: '2025-08-31',
        anchor_date: '2025-08-31',
        generated_at: '2025-08-31T19:00:00Z',
        precision_policy: {
          monetary_values: '2',
          greeks: '4',
          correlations: '3',
          factor_exposures: '2',
        },
      },
    };

    results.push({
      category,
      test: 'Portfolio Types',
      success: true,
      data: 'Portfolio interface compilation successful',
    });
  } catch (error) {
    results.push({
      category,
      test: 'Portfolio Types',
      success: false,
      error: `${error}`,
    });
  }

  // Test position types
  try {
    const mockPosition: Partial<Position> = {
      id: 'test-id',
      portfolio_id: 'portfolio-id',
      symbol: 'AAPL',
      quantity: 100,
      position_type: 'long',
    };

    results.push({
      category,
      test: 'Position Types',
      success: true,
      data: 'Position interface compilation successful',
    });
  } catch (error) {
    results.push({
      category,
      test: 'Position Types',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Test API client functionality (without network)
 */
async function testApiClient(results: TestResult[]) {
  const category = 'API Client';

  // Test API client instantiation
  try {
    const client = apiClient;
    const hasRequiredMethods = typeof client.get === 'function' &&
                              typeof client.post === 'function' &&
                              typeof client.buildUrl === 'function';

    results.push({
      category,
      test: 'Client Instantiation',
      success: hasRequiredMethods,
      data: {
        baseUrl: client.getBaseURL(),
        methods: ['get', 'post', 'put', 'delete'],
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Client Instantiation',
      success: false,
      error: `${error}`,
    });
  }

  // Test URL building
  try {
    const testUrl = apiClient.buildUrl('/test/endpoint', { param1: 'value1', param2: 123 });
    const urlValid = testUrl.includes('param1=value1') && testUrl.includes('param2=123');

    results.push({
      category,
      test: 'URL Building',
      success: urlValid,
      data: testUrl,
    });
  } catch (error) {
    results.push({
      category,
      test: 'URL Building',
      success: false,
      error: `${error}`,
    });
  }

  // Test error classes
  try {
    const apiError = new ApiError(404, 'Not Found', { message: 'Test error' }, '/test');
    const networkError = new NetworkError('Connection failed', new Error('Network down'));
    const timeoutError = new TimeoutError(5000);

    const errorsValid = apiError.status === 404 &&
                       networkError.name === 'NetworkError' &&
                       timeoutError.name === 'TimeoutError';

    results.push({
      category,
      test: 'Error Classes',
      success: errorsValid,
      data: {
        apiError: apiError.message,
        networkError: networkError.message,
        timeoutError: timeoutError.message,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Error Classes',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Test data transformation utilities
 */
async function testDataTransformation(results: TestResult[]) {
  const category = 'Data Transform';

  // Test currency formatting
  try {
    const tests = [
      { input: 1234.56, expected: '$1,234.56' },
      { input: '1000000', expected: '$1.0M', options: { compact: true } },
      { input: 999.99, expected: '$1,000', options: { showCents: false } },
    ];

    let allPassed = true;
    const results_detail = tests.map(test => {
      const result = formatCurrency(test.input, test.options);
      const passed = result === test.expected;
      if (!passed) allPassed = false;
      return { input: test.input, expected: test.expected, actual: result, passed };
    });

    results.push({
      category,
      test: 'Currency Formatting',
      success: allPassed,
      data: results_detail,
    });
  } catch (error) {
    results.push({
      category,
      test: 'Currency Formatting',
      success: false,
      error: `${error}`,
    });
  }

  // Test percentage formatting
  try {
    const tests = [
      { input: 0.1234, expected: '+12.34%' },
      { input: -0.05, expected: '-5.00%' },
      { input: '0.001', expected: '+0.10%' },
    ];

    let allPassed = true;
    const results_detail = tests.map(test => {
      const result = formatPercentage(test.input);
      const passed = result === test.expected;
      if (!passed) allPassed = false;
      return { input: test.input, expected: test.expected, actual: result, passed };
    });

    results.push({
      category,
      test: 'Percentage Formatting',
      success: allPassed,
      data: results_detail,
    });
  } catch (error) {
    results.push({
      category,
      test: 'Percentage Formatting',
      success: false,
      error: `${error}`,
    });
  }

  // Test date formatting
  try {
    const testDate = '2025-08-31T12:34:56Z';
    const formatted = formatDate(testDate);
    const isValid = formatted.includes('Aug') && formatted.includes('31');

    results.push({
      category,
      test: 'Date Formatting',
      success: isValid,
      data: { input: testDate, output: formatted },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Date Formatting',
      success: false,
      error: `${error}`,
    });
  }

  // Test safe parsing
  try {
    const tests = [
      { input: '123.45', expected: 123.45 },
      { input: 'invalid', expected: 0 },
      { input: null, expected: 0 },
      { input: 42, expected: 42 },
    ];

    let allPassed = true;
    tests.forEach(test => {
      const result = safeParseFloat(test.input as any);
      if (result !== test.expected) allPassed = false;
    });

    results.push({
      category,
      test: 'Safe Number Parsing',
      success: allPassed,
      data: tests,
    });
  } catch (error) {
    results.push({
      category,
      test: 'Safe Number Parsing',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Test portfolio services
 */
async function testPortfolioServices(results: TestResult[]) {
  const category = 'Services';

  // Test service instantiation
  try {
    const hasPortfolioService = typeof portfolioService.getPortfolios === 'function';
    const hasDashboardService = typeof dashboardService.loadDashboardData === 'function';

    results.push({
      category,
      test: 'Service Instantiation',
      success: hasPortfolioService && hasDashboardService,
      data: {
        portfolioService: hasPortfolioService,
        dashboardService: hasDashboardService,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Service Instantiation',
      success: false,
      error: `${error}`,
    });
  }

  // Test utility functions
  try {
    const testId = DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR;
    const isDemoValid = portfolioApiUtils.isDemoPortfolio(testId);
    const isValidFormat = portfolioApiUtils.isValidPortfolioId(testId);
    const demoName = portfolioApiUtils.getDemoPortfolioName(testId);

    results.push({
      category,
      test: 'Portfolio Utils',
      success: isDemoValid && isValidFormat && demoName !== null,
      data: {
        isDemoPortfolio: isDemoValid,
        isValidId: isValidFormat,
        demoName: demoName,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Portfolio Utils',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Test error handling scenarios
 */
async function testErrorHandling(results: TestResult[]) {
  const category = 'Error Handling';

  // Test data validation with invalid data
  try {
    const invalidData = { invalid: 'data' };
    const validation = validatePortfolioData(invalidData);
    
    results.push({
      category,
      test: 'Data Validation',
      success: !validation.valid && validation.errors.length > 0,
      data: {
        valid: validation.valid,
        errorCount: validation.errors.length,
        errors: validation.errors.slice(0, 3), // First 3 errors
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Data Validation',
      success: false,
      error: `${error}`,
    });
  }

  // Test formatting with invalid inputs
  try {
    const invalidCurrency = formatCurrency('not-a-number');
    const invalidPercentage = formatPercentage('invalid');
    const invalidDate = formatDate('not-a-date');

    const handlesInvalidInputs = invalidCurrency === '$0.00' &&
                                invalidPercentage === '0.00%' &&
                                invalidDate === 'not-a-date'; // Should return original on failure

    results.push({
      category,
      test: 'Invalid Input Handling',
      success: handlesInvalidInputs,
      data: {
        invalidCurrency,
        invalidPercentage,
        invalidDate,
      },
    });
  } catch (error) {
    results.push({
      category,
      test: 'Invalid Input Handling',
      success: false,
      error: `${error}`,
    });
  }
}

/**
 * Generate test summary
 */
function generateSummary(results: TestResult[]) {
  const total = results.length;
  const passed = results.filter(r => r.success).length;
  const failed = total - passed;

  const categories: Record<string, { passed: number; total: number }> = {};
  
  results.forEach(result => {
    if (!categories[result.category]) {
      categories[result.category] = { passed: 0, total: 0 };
    }
    categories[result.category].total++;
    if (result.success) {
      categories[result.category].passed++;
    }
  });

  return { total, passed, failed, categories };
}

// Browser console access
if (typeof window !== 'undefined') {
  (window as any).testPhase1 = {
    testPhase1Complete,
    formatCurrency,
    formatPercentage,
    apiClient,
    portfolioService,
  };
  
  console.log('🧪 Phase 1 test functions available on window.testPhase1');
  console.log('   - testPhase1Complete() - Run all tests');
}

export default testPhase1Complete;