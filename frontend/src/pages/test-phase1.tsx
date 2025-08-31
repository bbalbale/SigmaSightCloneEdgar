/**
 * Phase 1 Browser Test Page
 * Tests all Phase 1 components in the browser environment
 */

import { useEffect, useState } from 'react';
import { formatCurrency, formatPercentage, formatDate } from '@/utils/dataTransform';
import { API_CONFIG, DEMO_PORTFOLIOS, validateEnvironment } from '@/config/api';
import { portfolioApiUtils } from '@/services/portfolioApi';
import type { PortfolioSummaryMetric } from '@/types/portfolio';

interface TestResult {
  category: string;
  test: string;
  success: boolean;
  data?: any;
  error?: string;
}

export default function TestPhase1Page() {
  const [results, setResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [summary, setSummary] = useState({ total: 0, passed: 0, failed: 0 });

  useEffect(() => {
    runTests();
  }, []);

  const runTests = async () => {
    setIsRunning(true);
    const testResults: TestResult[] = [];

    // Test 1: Configuration
    try {
      const envValidation = validateEnvironment();
      testResults.push({
        category: 'Config',
        test: 'Environment Validation',
        success: envValidation.valid,
        data: envValidation.errors.length === 0 ? 'Valid' : envValidation.errors.join(', '),
      });
    } catch (error) {
      testResults.push({
        category: 'Config',
        test: 'Environment Validation',
        success: false,
        error: `${error}`,
      });
    }

    // Test 2: Data Formatting
    const formatTests = [
      {
        name: 'Currency',
        test: () => formatCurrency(1234.56),
        expected: '$1,234.56'
      },
      {
        name: 'Percentage', 
        test: () => formatPercentage(0.1234),
        expected: '+12.34%'
      },
      {
        name: 'Date',
        test: () => formatDate('2025-08-31'),
        expected: 'Aug 31, 2025'
      }
    ];

    formatTests.forEach(({ name, test, expected }) => {
      try {
        const result = test();
        testResults.push({
          category: 'Format',
          test: name,
          success: result === expected,
          data: `${result} ${result === expected ? '✓' : '✗ Expected: ' + expected}`,
        });
      } catch (error) {
        testResults.push({
          category: 'Format',
          test: name,
          success: false,
          error: `${error}`,
        });
      }
    });

    // Test 3: Portfolio Utils
    try {
      const testId = DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR;
      const isDemo = portfolioApiUtils.isDemoPortfolio(testId);
      const isValid = portfolioApiUtils.isValidPortfolioId(testId);
      const name = portfolioApiUtils.getDemoPortfolioName(testId);

      testResults.push({
        category: 'Utils',
        test: 'Portfolio Utils',
        success: isDemo && isValid && name !== null,
        data: { isDemo, isValid, name },
      });
    } catch (error) {
      testResults.push({
        category: 'Utils',
        test: 'Portfolio Utils',
        success: false,
        error: `${error}`,
      });
    }

    // Test 4: Type Safety (compile-time test)
    try {
      const mockMetric: PortfolioSummaryMetric = {
        title: 'Test Metric',
        value: '$100,000',
        subValue: 'Test sub-value',
        description: 'Test description',
        positive: true,
        loading: false,
      };
      
      testResults.push({
        category: 'Types',
        test: 'Interface Compilation',
        success: true,
        data: 'TypeScript interfaces working',
      });
    } catch (error) {
      testResults.push({
        category: 'Types',
        test: 'Interface Compilation',
        success: false,
        error: `${error}`,
      });
    }

    // Calculate summary
    const total = testResults.length;
    const passed = testResults.filter(r => r.success).length;
    const failed = total - passed;

    setResults(testResults);
    setSummary({ total, passed, failed });
    setIsRunning(false);
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      Config: 'bg-blue-50 border-blue-200',
      Format: 'bg-green-50 border-green-200', 
      Utils: 'bg-purple-50 border-purple-200',
      Types: 'bg-orange-50 border-orange-200',
    };
    return colors[category as keyof typeof colors] || 'bg-gray-50 border-gray-200';
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Phase 1 Browser Test Results
          </h1>
          
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.total}</div>
              <div className="text-sm text-blue-600">Total Tests</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-600">{summary.passed}</div>
              <div className="text-sm text-green-600">Passed</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-600">{summary.failed}</div>
              <div className="text-sm text-red-600">Failed</div>
            </div>
          </div>

          <div className="mb-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-800">Test Status</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                summary.failed === 0 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {summary.failed === 0 ? '✅ ALL PASSED' : `❌ ${summary.failed} FAILED`}
              </span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div 
                className="bg-green-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${summary.total > 0 ? (summary.passed / summary.total) * 100 : 0}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {results.map((result, index) => (
            <div 
              key={index}
              className={`border rounded-lg p-4 ${getCategoryColor(result.category)}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <span className="font-medium text-gray-700">{result.category}</span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-800">{result.test}</span>
                </div>
                <span className={`px-2 py-1 rounded text-sm font-medium ${
                  result.success 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {result.success ? '✅ Pass' : '❌ Fail'}
                </span>
              </div>
              
              {result.data && (
                <div className="mt-2 p-2 bg-white rounded text-sm text-gray-600">
                  <strong>Data:</strong> {typeof result.data === 'string' 
                    ? result.data 
                    : JSON.stringify(result.data, null, 2)}
                </div>
              )}
              
              {result.error && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  <strong>Error:</strong> {result.error}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Configuration Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <strong>API Base URL:</strong><br />
              <code className="text-blue-600">{API_CONFIG.BASE_URL}</code>
            </div>
            <div>
              <strong>Demo Portfolio ID:</strong><br />
              <code className="text-blue-600">{DEMO_PORTFOLIOS.INDIVIDUAL_INVESTOR}</code>
            </div>
            <div>
              <strong>Default Timeout:</strong><br />
              <code className="text-blue-600">{API_CONFIG.TIMEOUT.DEFAULT}ms</code>
            </div>
            <div>
              <strong>Retry Count:</strong><br />
              <code className="text-blue-600">{API_CONFIG.RETRY.COUNT}</code>
            </div>
          </div>
        </div>

        <div className="text-center mt-6">
          <button 
            onClick={runTests}
            disabled={isRunning}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
          >
            {isRunning ? 'Running Tests...' : 'Run Tests Again'}
          </button>
        </div>
      </div>
    </div>
  );
}