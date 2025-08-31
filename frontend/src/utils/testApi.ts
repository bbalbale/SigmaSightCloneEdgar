/**
 * API Testing Utility
 * Tests connectivity with backend demo portfolio data
 */

import { portfolioService, dashboardService, portfolioApiUtils } from '@/services/portfolioApi';
import { DEMO_PORTFOLIOS } from '@/config/api';
import { validatePortfolioData } from '@/utils/dataTransform';

/**
 * Test basic API connectivity
 */
export async function testApiConnectivity(): Promise<{
  success: boolean;
  results: any[];
  errors: string[];
}> {
  const results: any[] = [];
  const errors: string[] = [];

  console.log('🧪 Testing API connectivity...');

  try {
    // Test 1: Get portfolios list
    console.log('📋 Testing portfolio list...');
    const portfolios = await portfolioService.getPortfolios();
    results.push({
      test: 'Portfolio List',
      success: true,
      data: `Found ${portfolios.length} portfolios`,
      details: portfolios.map(p => `${p.name} (${p.id})`),
    });
    console.log(`✅ Portfolio list: ${portfolios.length} portfolios found`);
  } catch (error) {
    const errorMsg = `Failed to fetch portfolio list: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Portfolio List',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Portfolio list failed:', error);
  }

  // Test 2: Get demo portfolio complete data
  const testPortfolioId = DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR;
  try {
    console.log(`📊 Testing portfolio data for ID: ${testPortfolioId}...`);
    const portfolio = await portfolioService.getPortfolioComplete(testPortfolioId);
    
    // Validate the data structure
    const validation = validatePortfolioData(portfolio);
    
    results.push({
      test: 'Portfolio Complete Data',
      success: true,
      data: {
        name: portfolio.portfolio_info?.name || 'Unknown',
        totalValue: portfolio.calculation_engines?.portfolio_snapshot?.data?.total_value || 'N/A',
        positionCount: portfolio.portfolio_info?.position_count || 0,
        enginesAvailable: Object.keys(portfolio.calculation_engines || {}).length,
        validation: validation,
      },
    });
    console.log(`✅ Portfolio data loaded: ${portfolio.portfolio_info?.name}`);
    
    if (validation.warnings.length > 0) {
      console.warn('⚠️ Data validation warnings:', validation.warnings);
    }
  } catch (error) {
    const errorMsg = `Failed to fetch portfolio ${testPortfolioId}: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Portfolio Complete Data',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Portfolio data failed:', error);
  }

  // Test 3: Get position details
  try {
    console.log('📈 Testing position details...');
    const positions = await portfolioService.getPositionDetails(testPortfolioId);
    
    results.push({
      test: 'Position Details',
      success: true,
      data: {
        count: positions.length,
        symbols: positions.slice(0, 5).map(p => p.symbol), // First 5 symbols
        types: [...new Set(positions.map(p => p.position_type))],
      },
    });
    console.log(`✅ Position details: ${positions.length} positions found`);
  } catch (error) {
    const errorMsg = `Failed to fetch positions: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Position Details',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Position details failed:', error);
  }

  // Test 4: Get market quotes (optional - may fail gracefully)
  try {
    console.log('💹 Testing market quotes...');
    const quotes = await portfolioService.getMarketQuotes();
    
    results.push({
      test: 'Market Quotes',
      success: true,
      data: {
        count: quotes.length,
        samples: quotes.slice(0, 3).map(q => `${q.symbol}: $${q.price}`),
      },
    });
    console.log(`✅ Market quotes: ${quotes.length} quotes received`);
  } catch (error) {
    // Market data is optional - don't add to errors
    results.push({
      test: 'Market Quotes',
      success: false,
      error: `Market data unavailable: ${error}`,
      optional: true,
    });
    console.warn('⚠️ Market quotes unavailable (non-critical):', error);
  }

  // Test 5: Dashboard composite service
  try {
    console.log('🎯 Testing dashboard service...');
    const dashboardData = await dashboardService.loadDashboardData(testPortfolioId);
    
    results.push({
      test: 'Dashboard Service',
      success: true,
      data: {
        portfolioName: dashboardData.portfolio.portfolio_info?.name,
        positionCount: dashboardData.positions.length,
        quoteCount: dashboardData.quotes.length,
        hasDataQuality: !!dashboardData.dataQuality,
      },
    });
    console.log('✅ Dashboard service: All components loaded');
  } catch (error) {
    const errorMsg = `Dashboard service failed: ${error}`;
    errors.push(errorMsg);
    results.push({
      test: 'Dashboard Service',
      success: false,
      error: errorMsg,
    });
    console.error('❌ Dashboard service failed:', error);
  }

  // Test utility functions
  console.log('🔧 Testing utility functions...');
  const utilTests = [
    {
      name: 'Portfolio ID Validation',
      test: () => portfolioApiUtils.isValidPortfolioId(testPortfolioId),
      expected: true,
    },
    {
      name: 'Demo Portfolio Detection',
      test: () => portfolioApiUtils.isDemoPortfolio(testPortfolioId),
      expected: true,
    },
    {
      name: 'Demo Portfolio Name',
      test: () => portfolioApiUtils.getDemoPortfolioName(testPortfolioId),
      expected: 'Demo Individual Investor',
    },
  ];

  utilTests.forEach(({ name, test, expected }) => {
    try {
      const result = test();
      const success = result === expected;
      results.push({
        test: name,
        success,
        data: result,
        expected: success ? undefined : expected,
      });
      console.log(success ? `✅ ${name}` : `❌ ${name}: got ${result}, expected ${expected}`);
    } catch (error) {
      results.push({
        test: name,
        success: false,
        error: `${error}`,
      });
      console.error(`❌ ${name} failed:`, error);
    }
  });

  const success = errors.length === 0;
  const summary = {
    total: results.length,
    passed: results.filter(r => r.success).length,
    failed: results.filter(r => !r.success && !r.optional).length,
    optional: results.filter(r => r.optional).length,
  };

  console.log(`\n📊 Test Summary:`);
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
 * Quick connection test - just check if backend is responding
 */
export async function quickConnectionTest(): Promise<boolean> {
  try {
    console.log('🚀 Quick connection test...');
    const portfolios = await portfolioService.getPortfolios();
    console.log(`✅ Backend connected: ${portfolios.length} portfolios available`);
    return true;
  } catch (error) {
    console.error('❌ Backend connection failed:', error);
    return false;
  }
}

/**
 * Test specific portfolio by ID
 */
export async function testSpecificPortfolio(portfolioId: string): Promise<any> {
  console.log(`🎯 Testing portfolio: ${portfolioId}`);
  
  try {
    const [portfolio, positions, quotes] = await Promise.allSettled([
      portfolioService.getPortfolioComplete(portfolioId),
      portfolioService.getPositionDetails(portfolioId),
      portfolioService.getMarketQuotes(),
    ]);

    return {
      portfolioId,
      portfolio: portfolio.status === 'fulfilled' ? portfolio.value : null,
      positions: positions.status === 'fulfilled' ? positions.value : [],
      quotes: quotes.status === 'fulfilled' ? quotes.value : [],
      errors: [
        ...(portfolio.status === 'rejected' ? [`Portfolio: ${portfolio.reason}`] : []),
        ...(positions.status === 'rejected' ? [`Positions: ${positions.reason}`] : []),
        ...(quotes.status === 'rejected' ? [`Quotes: ${quotes.reason}`] : []),
      ],
    };
  } catch (error) {
    console.error(`Failed to test portfolio ${portfolioId}:`, error);
    throw error;
  }
}

// Export for external use in console or components
if (typeof window !== 'undefined') {
  (window as any).testApi = {
    testApiConnectivity,
    quickConnectionTest,
    testSpecificPortfolio,
    portfolioService,
    dashboardService,
  };
  
  console.log('🧪 API test functions available on window.testApi');
  console.log('   - testApiConnectivity()');
  console.log('   - quickConnectionTest()');
  console.log('   - testSpecificPortfolio(id)');
}