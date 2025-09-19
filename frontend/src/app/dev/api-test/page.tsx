/**
 * Analytics API Test Page - Shows actual data returned from analytics endpoints
 * Focuses on lookthrough analytics (portfolio exposures, correlations, stress tests, etc.)
 */

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

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    setAuthToken(token);
  }, []);

  const testEndpoints = [
    // Target Price Endpoints
    {
      name: '🎯 Target Prices - Get All',
      endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}`,
      method: 'GET',
      requiresAuth: true,
      category: 'target-prices',
      description: 'Get all target prices for the portfolio with EOY, Next Year, and Downside scenarios'
    },
    {
      name: '📊 Target Prices - Portfolio Summary',
      endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}/summary`,
      method: 'GET',
      requiresAuth: true,
      category: 'target-prices',
      description: 'Portfolio-weighted target price summary with coverage and weighted returns'
    },

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

  const renderDataPreview = (data: any, endpoint: string) => {
    if (!data) return <span className="text-gray-400">No data</span>;

    // Special rendering for target prices
    if (endpoint.includes('target-prices') && !endpoint.includes('summary')) {
      if (Array.isArray(data)) {
        return (
          <div className="space-y-2">
            <div className="text-sm font-medium">{data.length} target prices found</div>
            {data.slice(0, 3).map((tp: any, idx: number) => (
              <div key={idx} className="p-2 bg-gray-50 rounded text-xs space-y-1">
                <div className="font-semibold">{tp.symbol} ({tp.position_type || 'N/A'})</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>Current: ${tp.current_price?.toFixed(2) || 'N/A'}</div>
                  <div>EOY Target: ${tp.target_price_eoy?.toFixed(2) || 'N/A'}</div>
                  <div>Next Year: ${tp.target_price_next_year?.toFixed(2) || 'N/A'}</div>
                  <div>Downside: ${tp.downside_target_price?.toFixed(2) || 'N/A'}</div>
                </div>
                <div className="text-gray-600">
                  EOY Return: {tp.expected_return_eoy ? `${tp.expected_return_eoy.toFixed(1)}%` : 'N/A'} |
                  Next Yr: {tp.expected_return_next_year ? `${tp.expected_return_next_year.toFixed(1)}%` : 'N/A'} |
                  Downside: {tp.downside_return ? `${tp.downside_return.toFixed(1)}%` : 'N/A'}
                </div>
              </div>
            ))}
            {data.length > 3 && (
              <div className="text-xs text-gray-500">...and {data.length - 3} more</div>
            )}
          </div>
        );
      }
    }

    // Special rendering for target price summary
    if (endpoint.includes('target-prices') && endpoint.includes('summary')) {
      return (
        <div className="space-y-2">
          <div className="text-sm">
            <strong>{data.portfolio_name}</strong>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>Positions: {data.total_positions}</div>
            <div>With Targets: {data.positions_with_targets}</div>
            <div>Coverage: {data.coverage_percentage ? `${data.coverage_percentage.toFixed(1)}%` : 'N/A'}</div>
            <div>Target Count: {data.target_prices?.length || 0}</div>
          </div>
          <div className="text-xs space-y-1 pt-1 border-t">
            <div>Weighted EOY Return: {data.weighted_expected_return_eoy ? `${data.weighted_expected_return_eoy.toFixed(1)}%` : 'N/A'}</div>
            <div>Weighted Next Year Return: {data.weighted_expected_return_next_year ? `${data.weighted_expected_return_next_year.toFixed(1)}%` : 'N/A'}</div>
            <div>Weighted Downside Return: {data.weighted_downside_return ? `${data.weighted_downside_return.toFixed(1)}%` : 'N/A'}</div>
          </div>
        </div>
      );
    }

    // Special rendering for specific endpoint types
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

          {/* Target Prices Section */}
          <div className="space-y-2">
            <h3 className="text-lg font-medium text-gray-700 bg-purple-50 px-4 py-2 rounded">
              Target Price Endpoints
            </h3>
            {results.filter(r => r.url.includes('/target-prices/')).map((result, index) => (
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