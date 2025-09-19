# Updated API Test Page with Target Price Endpoints

This file shows the complete updated code for `/src/app/dev/api-test/page.tsx` with all Target Price endpoints integrated.

## Key Changes Made:
1. Added 10 target price endpoints to the `testEndpoints` array
2. Added state for tracking portfolio positions and created target prices
3. Added new "Target Price Management" section with purple theme
4. Enhanced data preview renderers for target price responses
5. Added dynamic data fetching for real portfolio positions

```typescript
/**
 * Analytics API Test Page - Shows actual data returned from analytics endpoints
 * Focuses on lookthrough analytics (portfolio exposures, correlations, stress tests, etc.)
 * UPDATED: Added comprehensive Target Price Management endpoints
 */

'use client'

import { useEffect, useState } from 'react';
import { API_CONFIG, DEMO_PORTFOLIOS } from '@/config/api';

interface ApiTestResult {
  endpoint: string;
  method: string;
  url: string;
  status: number | null;
  statusText: string;
  success: boolean;
  responseTime: number;
  data: any;
  error: string | null;
  headers: Record<string, string>;
}

export default function ApiTestPage() {
  const [results, setResults] = useState<ApiTestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedResult, setSelectedResult] = useState<ApiTestResult | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [selectedPortfolio, setSelectedPortfolio] = useState(DEMO_PORTFOLIOS.HIGH_NET_WORTH);
  const [expandedData, setExpandedData] = useState<Record<string, boolean>>({});

  // NEW: State for dynamic data operations
  const [portfolioPositions, setPortfolioPositions] = useState<any[]>([]);
  const [createdTargetPrices, setCreatedTargetPrices] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    setAuthToken(token);
  }, []);

  // NEW: Fetch portfolio positions for dynamic testing
  useEffect(() => {
    const fetchPositions = async () => {
      if (!selectedPortfolio || !authToken) return;

      try {
        const response = await fetch(
          `/api/proxy/api/v1/data/positions/details?portfolio_id=${selectedPortfolio}`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          }
        );

        if (response.ok) {
          const data = await response.json();
          setPortfolioPositions(data.positions || []);
        }
      } catch (error) {
        console.error('Failed to fetch positions:', error);
      }
    };

    fetchPositions();
  }, [selectedPortfolio, authToken]);

  // NEW: Helper function to create target price data using EXISTING database fields
  const createTargetPriceData = (position: any) => ({
    symbol: position.symbol,
    position_id: position.id,
    position_type: position.position_type || "LONG",
    target_price_eoy: position.last_price * 1.1,        // 10% upside for EOY
    target_price_next_year: position.last_price * 1.2,   // 20% upside for next year
    downside_target_price: position.last_price * 0.9,    // 10% downside scenario
    current_price: position.last_price,
  });

  // NEW: Generate CSV from actual positions using correct field names
  const generateCSV = () => {
    const headers = 'symbol,position_type,target_eoy,target_next_year,downside';
    const rows = portfolioPositions.slice(0, 5).map(pos =>
      `${pos.symbol},LONG,${(pos.last_price * 1.1).toFixed(2)},${(pos.last_price * 1.2).toFixed(2)},${(pos.last_price * 0.9).toFixed(2)}`
    );
    return [headers, ...rows].join('\n');
  };

  const testEndpoints = [
    // Analytics Lookthrough Endpoints
    {
      name: '📊 Portfolio Overview Analytics',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/overview`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Comprehensive portfolio analytics with exposures, P&L, and position metrics'
    },
    {
      name: '📈 Correlation Matrix',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/correlation-matrix?lookback_days=90&min_overlap=30&max_symbols=25`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Pairwise correlations between portfolio positions'
    },
    {
      name: '🎯 Diversification Score',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/diversification-score?lookback_days=90&min_overlap=30`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Weighted absolute portfolio correlation (0-1 scale)'
    },
    {
      name: '📉 Portfolio Factor Exposures',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/factor-exposures`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Portfolio-level factor betas and dollar exposures'
    },
    {
      name: '🔍 Position Factor Exposures',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/positions/factor-exposures?limit=10`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Position-by-position factor exposure breakdown'
    },
    {
      name: '⚡ Stress Test Results',
      endpoint: `/api/proxy/api/v1/analytics/portfolio/${selectedPortfolio}/stress-test`,
      method: 'GET',
      requiresAuth: true,
      category: 'analytics',
      description: 'Precomputed stress testing scenarios with correlated impacts'
    },

    // Raw Data Endpoints for Comparison
    {
      name: '📁 Portfolio Complete Data',
      endpoint: `/api/proxy/api/v1/data/portfolio/${selectedPortfolio}/complete`,
      method: 'GET',
      requiresAuth: true,
      category: 'raw-data',
      description: 'Full portfolio snapshot with all raw data'
    },
    {
      name: '✅ Data Quality Check',
      endpoint: `/api/proxy/api/v1/data/portfolio/${selectedPortfolio}/data-quality`,
      method: 'GET',
      requiresAuth: true,
      category: 'raw-data',
      description: 'Data completeness and quality metrics'
    },
    {
      name: '📋 Position Details',
      endpoint: `/api/proxy/api/v1/data/positions/details?portfolio_id=${selectedPortfolio}`,
      method: 'GET',
      requiresAuth: true,
      category: 'raw-data',
      description: 'Detailed position data with P&L'
    },

    // ============= NEW: TARGET PRICE ENDPOINTS =============

    // Target Price GET Operations
    {
      name: '🎯 List Portfolio Target Prices',
      endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}`,
      method: 'GET',
      requiresAuth: true,
      category: 'target-prices',
      description: 'All target prices for portfolio with smart price resolution'
    },
    {
      name: '📊 Target Price Portfolio Summary',
      endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/summary`,
      method: 'GET',
      requiresAuth: true,
      category: 'target-prices',
      description: 'Portfolio summary with risk metrics and target achievement'
    },
    {
      name: '📥 Export Target Prices to CSV',
      endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/export-csv`,
      method: 'GET',
      requiresAuth: true,
      category: 'target-prices',
      description: 'Export all target prices to CSV format'
    },

    // Target Price Mutations - Dynamic data based on actual positions
    ...(portfolioPositions.length > 0 ? [
      {
        name: '➕ Create Target Price (First Position)',
        endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}`,
        method: 'POST',
        body: createTargetPriceData(portfolioPositions[0]),
        requiresAuth: true,
        category: 'target-prices-mutations',
        description: `Create target price for ${portfolioPositions[0].symbol}`
      }
    ] : []),

    ...(portfolioPositions.length >= 3 ? [
      {
        name: '📦 Bulk Create Target Prices (Top 3 Positions)',
        endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/bulk`,
        method: 'POST',
        body: {
          target_prices: portfolioPositions.slice(0, 3).map(createTargetPriceData)
        },
        requiresAuth: true,
        category: 'target-prices-mutations',
        description: `Bulk create for: ${portfolioPositions.slice(0, 3).map(p => p.symbol).join(', ')}`
      }
    ] : []),

    ...(portfolioPositions.length >= 5 ? [
      {
        name: '📤 Import Target Prices from CSV',
        endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/import-csv`,
        method: 'POST',
        body: {
          csv_content: generateCSV(),
          update_existing: false
        },
        requiresAuth: true,
        category: 'target-prices-mutations',
        description: 'Import target prices via CSV (5 positions)'
      }
    ] : []),

    // Dynamic UPDATE/DELETE based on created target prices
    ...(createdTargetPrices.length > 0 ? [
      {
        name: '✏️ Update Target Price (First Created)',
        endpoint: `/api/proxy/api/v1/target-prices/${createdTargetPrices[0].id}`,
        method: 'PUT',
        body: {
          target_price_eoy: createdTargetPrices[0].target_price_eoy * 1.05,
          target_price_next_year: createdTargetPrices[0].target_price_next_year * 1.05,
          downside_target_price: createdTargetPrices[0].downside_target_price * 0.95,
        },
        requiresAuth: true,
        category: 'target-prices-mutations',
        description: `Update target price for ${createdTargetPrices[0].symbol}`
      },
      {
        name: '🗑️ Delete Target Price (First Created)',
        endpoint: `/api/proxy/api/v1/target-prices/${createdTargetPrices[0].id}`,
        method: 'DELETE',
        requiresAuth: true,
        category: 'target-prices-mutations',
        description: `Delete target price for ${createdTargetPrices[0].symbol}`
      }
    ] : []),

    // Position-specific endpoint (if positions exist)
    ...(portfolioPositions.length > 0 ? [
      {
        name: '🔎 Get Target Prices by Position',
        endpoint: `/api/proxy/api/v1/target-prices/position/${portfolioPositions[0].id}`,
        method: 'GET',
        requiresAuth: true,
        category: 'target-prices',
        description: `Get target prices for position: ${portfolioPositions[0].symbol}`
      }
    ] : []),

    // Clear all target prices
    {
      name: '🗑️ Clear All Target Prices',
      endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}`,
      method: 'DELETE',
      requiresAuth: true,
      category: 'target-prices-mutations',
      description: 'Remove all target prices for portfolio'
    },
  ];

  const runTests = async () => {
    setIsRunning(true);
    const testResults: ApiTestResult[] = [];

    for (const test of testEndpoints) {
      const startTime = performance.now();
      let result: ApiTestResult = {
        endpoint: test.name,
        method: test.method,
        url: test.endpoint,
        status: null,
        statusText: '',
        success: false,
        responseTime: 0,
        data: null,
        error: null,
        headers: {},
      };

      try {
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };

        if (test.requiresAuth && authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
        }

        const response = await fetch(test.endpoint, {
          method: test.method,
          headers,
          // UPDATED: Handle body for POST/PUT operations
          body: test.body ? JSON.stringify(test.body) : undefined,
        });

        const endTime = performance.now();
        result.responseTime = Math.round(endTime - startTime);
        result.status = response.status;
        result.statusText = response.statusText;
        result.success = response.ok;

        // Capture response headers
        const responseHeaders: Record<string, string> = {};
        response.headers.forEach((value, key) => {
          responseHeaders[key] = value;
        });
        result.headers = responseHeaders;

        // Parse response data
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          result.data = await response.json();

          // NEW: Capture created target prices for UPDATE/DELETE operations
          if (test.method === 'POST' && test.endpoint.includes('target-prices') && result.data?.id) {
            setCreatedTargetPrices(prev => [...prev, result.data]);
          }
        } else {
          result.data = await response.text();
        }

      } catch (error) {
        const endTime = performance.now();
        result.responseTime = Math.round(endTime - startTime);
        result.error = error instanceof Error ? error.message : String(error);
      }

      testResults.push(result);
    }

    setResults(testResults);
    setIsRunning(false);
  };

  const formatJson = (data: any, indent = 2) => {
    if (!data) return 'null';
    if (typeof data === 'string') return data;
    return JSON.stringify(data, null, indent);
  };

  const getStatusColor = (status: number | null) => {
    if (!status) return 'text-gray-500';
    if (status >= 200 && status < 300) return 'text-green-600';
    if (status >= 400 && status < 500) return 'text-orange-600';
    if (status >= 500) return 'text-red-600';
    return 'text-yellow-600';
  };

  // ENHANCED: Added target price specific preview renderers
  const renderDataPreview = (data: any, endpoint: string) => {
    if (!data) return <span className="text-gray-400">No data</span>;

    // NEW: Target price specific renderers
    if (endpoint.includes('target-prices')) {
      // Portfolio summary
      if (endpoint.includes('summary')) {
        return (
          <div className="space-y-1">
            <div className="text-sm font-semibold">
              Total Targets: {data.total_targets || 0}
            </div>
            {data.portfolio_metrics && (
              <div className="text-xs text-gray-600">
                Portfolio Value: ${(data.portfolio_metrics.total_value / 1000000).toFixed(2)}M
              </div>
            )}
            {data.aggregate_metrics && (
              <div className="text-xs text-gray-600">
                Avg EOY Return: {(data.aggregate_metrics.avg_eoy_return * 100).toFixed(1)}%
              </div>
            )}
          </div>
        );
      }

      // CSV export
      if (endpoint.includes('export-csv')) {
        return (
          <div className="text-xs">
            CSV data with {data.split('\n').length - 1} rows
          </div>
        );
      }

      // Target price list or single target
      if (Array.isArray(data)) {
        return (
          <div className="space-y-1">
            <div className="text-sm">{data.length} target prices</div>
            {data.length > 0 && (
              <div className="text-xs text-gray-600">
                <div>Symbols: {data.slice(0, 3).map(tp => tp.symbol).join(', ')}
                  {data.length > 3 && ` ... +${data.length - 3} more`}
                </div>
                {data[0].target_price_eoy && (
                  <div className="mt-1">
                    First: {data[0].symbol} -
                    EOY: ${data[0].target_price_eoy?.toFixed(2)},
                    Return: {((data[0].expected_return_eoy || 0) * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            )}
          </div>
        );
      }

      // Single target price object
      if (data.symbol) {
        return (
          <div className="space-y-1">
            <div className="text-sm font-semibold">{data.symbol}</div>
            <div className="text-xs text-gray-600">
              {data.target_price_eoy && `EOY: $${data.target_price_eoy.toFixed(2)}`}
              {data.expected_return_eoy && ` (${(data.expected_return_eoy * 100).toFixed(1)}%)`}
            </div>
            {data.target_price_next_year && (
              <div className="text-xs text-gray-600">
                Next Year: ${data.target_price_next_year.toFixed(2)}
                {data.expected_return_next_year && ` (${(data.expected_return_next_year * 100).toFixed(1)}%)`}
              </div>
            )}
            {data.position_weight && (
              <div className="text-xs text-gray-500">
                Weight: {(data.position_weight * 100).toFixed(2)}%
              </div>
            )}
          </div>
        );
      }
    }

    // Original preview renderers for other endpoints
    if (endpoint.includes('correlation-matrix') && data.matrix) {
      return (
        <div className="space-y-2">
          <div className="text-xs text-gray-600">
            Matrix Size: {data.symbols?.length || 0} x {data.symbols?.length || 0}
          </div>
          {data.available === false && (
            <div className="text-xs text-orange-600">Data not available</div>
          )}
          {data.symbols && (
            <div className="text-xs">
              Symbols: {data.symbols.slice(0, 5).join(', ')}
              {data.symbols.length > 5 && ` ... +${data.symbols.length - 5} more`}
            </div>
          )}
        </div>
      );
    }

    if (endpoint.includes('diversification-score')) {
      return (
        <div className="space-y-1">
          <div className="text-lg font-semibold">
            Score: {data.score !== undefined ? `${(data.score * 100).toFixed(1)}%` : 'N/A'}
          </div>
          {data.metadata && (
            <div className="text-xs text-gray-600">
              Positions: {data.metadata.position_count},
              Valid Pairs: {data.metadata.valid_pairs}
            </div>
          )}
        </div>
      );
    }

    if (endpoint.includes('factor-exposures')) {
      const exposures = data.exposures || data.positions || [];
      return (
        <div className="space-y-1">
          <div className="text-xs">
            {data.exposures ? `${Object.keys(data.exposures).length} factors` :
             data.positions ? `${data.positions.length} positions` : 'No exposures'}
          </div>
          {data.metadata && (
            <div className="text-xs text-gray-600">
              Date: {data.metadata.calculation_date}
            </div>
          )}
        </div>
      );
    }

    if (endpoint.includes('stress-test')) {
      return (
        <div className="space-y-1">
          <div className="text-xs">
            {data.scenarios ? `${data.scenarios.length} scenarios` : 'No scenarios'}
          </div>
          {data.baseline_value && (
            <div className="text-xs text-gray-600">
              Baseline: ${(data.baseline_value / 1000000).toFixed(2)}M
            </div>
          )}
        </div>
      );
    }

    // Default preview - show first few keys
    const keys = Object.keys(data);
    return (
      <div className="text-xs">
        {keys.slice(0, 3).join(', ')}
        {keys.length > 3 && ` ... +${keys.length - 3} more fields`}
      </div>
    );
  };

  const toggleDataExpansion = (endpoint: string) => {
    setExpandedData(prev => ({
      ...prev,
      [endpoint]: !prev[endpoint]
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Analytics Lookthrough API Test
          </h1>

          <div className="mb-6 space-y-4">
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Auth Token: {authToken ? '✅ Present' : '❌ Missing'}
              </span>
              {!authToken && (
                <span className="text-sm text-red-600">
                  Please login first at /login to test authenticated endpoints
                </span>
              )}
            </div>

            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">Portfolio:</label>
              <select
                value={selectedPortfolio}
                onChange={(e) => setSelectedPortfolio(e.target.value as typeof DEMO_PORTFOLIOS.HIGH_NET_WORTH)}
                className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
              >
                <option value={DEMO_PORTFOLIOS.HIGH_NET_WORTH}>High Net Worth</option>
                <option value={DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR}>Individual Investor</option>
                <option value={DEMO_PORTFOLIOS.HEDGE_FUND_STYLE}>Hedge Fund</option>
              </select>
            </div>

            {/* NEW: Display dynamic data status */}
            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
              <div>📊 Portfolio Positions: {portfolioPositions.length} loaded</div>
              <div>🎯 Created Target Prices: {createdTargetPrices.length} in session</div>
              {portfolioPositions.length === 0 && (
                <div className="text-orange-600 mt-1">
                  ⚠️ No positions loaded - some target price tests will be disabled
                </div>
              )}
            </div>
          </div>

          <button
            onClick={runTests}
            disabled={isRunning}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
          >
            {isRunning ? 'Running Tests...' : 'Run API Tests'}
          </button>
        </div>

        {/* Results Summary */}
        {results.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Summary</h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{results.length}</div>
                <div className="text-sm text-gray-600">Total Tests</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {results.filter(r => r.success).length}
                </div>
                <div className="text-sm text-gray-600">Success</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {results.filter(r => !r.success).length}
                </div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">
                  {Math.round(results.reduce((sum, r) => sum + r.responseTime, 0) / results.length)}ms
                </div>
                <div className="text-sm text-gray-600">Avg Time</div>
              </div>
            </div>
          </div>
        )}

        {/* Detailed Results */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-800">Test Results</h2>

          {/* Analytics Section */}
          <div className="space-y-2">
            <h3 className="text-lg font-medium text-gray-700 bg-blue-50 px-4 py-2 rounded">
              Analytics Lookthrough Endpoints
            </h3>
            {results.filter(r => r.url.includes('/analytics/')).map((result, index) => (
              <div
                key={`analytics-${index}`}
                className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-medium text-gray-800">{result.endpoint}</div>
                    <div className="text-xs text-gray-500 mt-1">{result.url}</div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`font-mono text-sm ${getStatusColor(result.status)}`}>
                      {result.status || 'ERROR'}
                    </span>
                    <span className="text-sm text-gray-500">{result.responseTime}ms</span>
                  </div>
                </div>

                {result.error && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
                    Error: {result.error}
                  </div>
                )}

                {result.data && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Response Data:</span>
                      <button
                        onClick={() => toggleDataExpansion(result.endpoint)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        {expandedData[result.endpoint] ? 'Collapse' : 'Expand Full Data'}
                      </button>
                    </div>

                    {!expandedData[result.endpoint] ? (
                      <div className="p-3 bg-gray-50 rounded">
                        {renderDataPreview(result.data, result.url)}
                      </div>
                    ) : (
                      <div className="max-h-96 overflow-y-auto">
                        <pre className="text-xs bg-gray-100 p-4 rounded overflow-x-auto">
                          {formatJson(result.data)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* NEW: Target Price Management Section */}
          <div className="space-y-2">
            <h3 className="text-lg font-medium text-gray-700 bg-purple-50 px-4 py-2 rounded">
              🎯 Target Price Management
            </h3>
            {results.filter(r => r.url.includes('/target-prices') && !r.url.includes('mutations')).map((result, index) => (
              <div
                key={`target-${index}`}
                className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-medium text-gray-800">{result.endpoint}</div>
                    <div className="text-xs text-gray-500 mt-1">{result.url}</div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`font-mono text-sm ${getStatusColor(result.status)}`}>
                      {result.status || 'ERROR'}
                    </span>
                    <span className="text-sm text-gray-500">{result.responseTime}ms</span>
                  </div>
                </div>

                {result.error && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
                    Error: {result.error}
                  </div>
                )}

                {result.data && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Response Data:</span>
                      <button
                        onClick={() => toggleDataExpansion(result.endpoint)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        {expandedData[result.endpoint] ? 'Collapse' : 'Expand Full Data'}
                      </button>
                    </div>

                    {!expandedData[result.endpoint] ? (
                      <div className="p-3 bg-gray-50 rounded">
                        {renderDataPreview(result.data, result.url)}
                      </div>
                    ) : (
                      <div className="max-h-96 overflow-y-auto">
                        <pre className="text-xs bg-gray-100 p-4 rounded overflow-x-auto">
                          {formatJson(result.data)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Raw Data Section */}
          <div className="space-y-2">
            <h3 className="text-lg font-medium text-gray-700 bg-green-50 px-4 py-2 rounded">
              Raw Data Endpoints (for comparison)
            </h3>
            {results.filter(r => r.url.includes('/data/')).map((result, index) => (
              <div
                key={`data-${index}`}
                className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-medium text-gray-800">{result.endpoint}</div>
                    <div className="text-xs text-gray-500 mt-1">{result.url}</div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`font-mono text-sm ${getStatusColor(result.status)}`}>
                      {result.status || 'ERROR'}
                    </span>
                    <span className="text-sm text-gray-500">{result.responseTime}ms</span>
                  </div>
                </div>

                {result.error && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
                    Error: {result.error}
                  </div>
                )}

                {result.data && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Response Data:</span>
                      <button
                        onClick={() => toggleDataExpansion(result.endpoint)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        {expandedData[result.endpoint] ? 'Collapse' : 'Expand Full Data'}
                      </button>
                    </div>

                    {!expandedData[result.endpoint] ? (
                      <div className="p-3 bg-gray-50 rounded">
                        {renderDataPreview(result.data, result.url)}
                      </div>
                    ) : (
                      <div className="max-h-96 overflow-y-auto">
                        <pre className="text-xs bg-gray-100 p-4 rounded overflow-x-auto">
                          {formatJson(result.data)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## Summary of Changes

### 1. **State Management** (Lines 34-36)
- Added `portfolioPositions` state to store fetched positions
- Added `createdTargetPrices` state to track created target prices for UPDATE/DELETE

### 2. **Position Fetching** (Lines 44-67)
- Added useEffect to fetch actual portfolio positions when portfolio changes
- Uses existing auth token and selected portfolio

### 3. **Helper Functions** (Lines 70-85)
- `createTargetPriceData`: Creates target price using EXISTING database fields
- `generateCSV`: Generates CSV with correct field names from schema

### 4. **Target Price Endpoints** (Lines 163-263)
- Added 10 target price endpoints to testEndpoints array
- GET operations: List, Summary, Export CSV, Position-specific
- POST operations: Create, Bulk Create, CSV Import (dynamic based on positions)
- PUT/DELETE: Update and Delete (dynamic based on created target prices)
- Clear All: Delete all target prices

### 5. **Request Handling** (Line 292)
- Added body handling for POST/PUT operations

### 6. **Response Capture** (Lines 310-314)
- Captures created target prices from POST responses for later UPDATE/DELETE

### 7. **Enhanced Preview Renderers** (Lines 334-423)
- Added specific renderers for target price responses
- Shows EOY targets, returns, position weights
- Handles arrays, single objects, and CSV data

### 8. **UI Updates** (Lines 547-555)
- Added status display showing loaded positions and created target prices
- Added warning when no positions are loaded

### 9. **New Target Price Section** (Lines 656-709)
- Purple-themed section for target price endpoints
- Consistent with existing Analytics and Raw Data sections

## Notes

- All endpoints use the existing `selectedPortfolio` variable
- Authentication uses existing token from localStorage
- Dynamic operations only appear when positions are loaded
- UPDATE/DELETE endpoints only appear after creating target prices
- All field names match the actual database schema (no made-up fields)