/**
 * AI Tool Definitions and Execution
 *
 * This file wraps existing services (analyticsApi, portfolioService) into tools
 * that OpenAI can call. NO new API calls - just using what already exists!
 */

import { analyticsApi } from '@/services/analyticsApi';
import { loadPortfolioData } from '@/services/portfolioService';

// Tool definitions for OpenAI Chat Completions API
export const toolDefinitions = [
  {
    type: 'function',
    function: {
      name: 'get_portfolio_complete',
      description: 'Get comprehensive portfolio data with positions, metrics, and P&L',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          }
        },
        required: ['portfolio_id']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_factor_exposures',
      description: 'Get factor exposures for portfolio (Market Beta, Value, Growth, Momentum, Quality, Size, Low Volatility)',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          }
        },
        required: ['portfolio_id']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_position_factor_exposures',
      description: 'Get factor exposures for individual positions in portfolio',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          },
          limit: {
            type: 'integer',
            description: 'Number of positions to return (default: 50)'
          }
        },
        required: ['portfolio_id']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_correlation_matrix',
      description: 'Get correlation matrix showing how portfolio positions move together',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          },
          lookback_days: {
            type: 'integer',
            description: 'Days of history for correlation calculation (default: 90)'
          }
        },
        required: ['portfolio_id']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_stress_test',
      description: 'Run stress test scenarios on portfolio to see impact of market moves',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          },
          scenarios: {
            type: 'string',
            description: 'Comma-separated scenario names (e.g., "market_crash,rate_hike")'
          }
        },
        required: ['portfolio_id']
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_portfolio_overview',
      description: 'Get high-level portfolio overview with total value, exposures, and P&L',
      parameters: {
        type: 'object',
        properties: {
          portfolio_id: {
            type: 'string',
            description: 'Portfolio UUID'
          }
        },
        required: ['portfolio_id']
      }
    }
  }
];

/**
 * Execute a tool by name
 *
 * This function wraps existing services - NO new API calls!
 * Each tool just calls one of your existing service methods.
 */
export async function executeTool(
  toolName: string,
  args: any
): Promise<any> {
  try {
    console.log(`[AI Tool] Executing: ${toolName}`, args);

    switch (toolName) {
      case 'get_portfolio_complete': {
        // Uses existing portfolioService
        console.log('[AI Tool] Calling loadPortfolioData()');
        const portfolioData = await loadPortfolioData(
          undefined,
          { portfolioId: args.portfolio_id }
        );

        return {
          success: true,
          tool: toolName,
          data: {
            portfolio_id: portfolioData.portfolioId,
            positions: portfolioData.positions,
            exposures: portfolioData.exposures,
            factor_exposures: portfolioData.factorExposures,
            portfolio_info: portfolioData.portfolioInfo
          }
        };
      }

      case 'get_factor_exposures': {
        // Uses existing analyticsApi
        console.log('[AI Tool] Calling analyticsApi.getPortfolioFactorExposures()');
        const factorData = await analyticsApi.getPortfolioFactorExposures(
          args.portfolio_id
        );

        return {
          success: true,
          tool: toolName,
          data: factorData.data
        };
      }

      case 'get_position_factor_exposures': {
        // Uses existing analyticsApi
        console.log('[AI Tool] Calling analyticsApi.getPositionFactorExposures()');
        const positionFactorData = await analyticsApi.getPositionFactorExposures(
          args.portfolio_id,
          { limit: args.limit || 50 }
        );

        return {
          success: true,
          tool: toolName,
          data: positionFactorData.data
        };
      }

      case 'get_correlation_matrix': {
        // Uses existing analyticsApi
        console.log('[AI Tool] Calling analyticsApi.getCorrelationMatrix()');
        const correlationData = await analyticsApi.getCorrelationMatrix(
          args.portfolio_id,
          { lookback_days: args.lookback_days || 90 }
        );

        return {
          success: true,
          tool: toolName,
          data: correlationData.data
        };
      }

      case 'get_stress_test': {
        // Uses existing analyticsApi
        console.log('[AI Tool] Calling analyticsApi.getStressTest()');
        const stressTestData = await analyticsApi.getStressTest(
          args.portfolio_id,
          args.scenarios ? { scenarios: args.scenarios } : undefined
        );

        return {
          success: true,
          tool: toolName,
          data: stressTestData.data
        };
      }

      case 'get_portfolio_overview': {
        // Uses existing analyticsApi
        console.log('[AI Tool] Calling analyticsApi.getOverview()');
        const overviewData = await analyticsApi.getOverview(args.portfolio_id);

        return {
          success: true,
          tool: toolName,
          data: overviewData.data
        };
      }

      default:
        throw new Error(`Unknown tool: ${toolName}`);
    }
  } catch (error) {
    console.error(`[AI Tool] Error executing ${toolName}:`, error);

    return {
      success: false,
      tool: toolName,
      error: error instanceof Error ? error.message : 'Unknown error',
      error_type: error instanceof Error ? error.name : 'Error'
    };
  }
}
