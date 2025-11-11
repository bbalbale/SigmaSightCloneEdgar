/**
 * Spread Factor API Service
 *
 * Handles API calls for portfolio spread factor exposures.
 * Spread factors are long-short factors (VUG-VTV, MTUM-SPY, etc.)
 * calculated using 180-day OLS regression.
 *
 * Created: 2025-10-20
 */

import { apiClient } from './apiClient';

/**
 * Individual spread factor data with interpretation
 */
export interface SpreadFactor {
  name: string;
  beta: number;
  exposure_dollar?: number;
  direction: string;          // Growth/Value, Momentum/Contrarian, etc.
  magnitude: string;          // Strong, Moderate, Weak
  risk_level: string;         // high, medium, low
  explanation: string;        // Plain English explanation
}

/**
 * Spread factors API response
 */
export interface SpreadFactorsResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date?: string;
  factors: SpreadFactor[];
  metadata: {
    calculation_method?: string;
    regression_window_days?: number;
    factors_calculated?: number;
    expected_factors?: number;
    reason?: string;
    error?: string;
  };
}

/**
 * Get portfolio spread factor exposures
 *
 * Returns 4 long-short spread factors with user-friendly interpretations:
 * - Growth-Value Spread (VUG - VTV)
 * - Momentum Spread (MTUM - SPY)
 * - Size Spread (IWM - SPY)
 * - Quality Spread (QUAL - SPY)
 *
 * @param portfolioId - Portfolio UUID
 * @returns Promise with spread factors data
 *
 * @example
 * ```typescript
 * const data = await getSpreadFactors(portfolioId);
 * if (data.available) {
 *   console.log(`Found ${data.factors.length} spread factors`);
 *   data.factors.forEach(factor => {
 *     console.log(`${factor.name}: ${factor.beta} (${factor.direction})`);
 *   });
 * }
 * ```
 */
export async function getSpreadFactors(
  portfolioId: string
): Promise<SpreadFactorsResponse> {
  const response = await apiClient.get<SpreadFactorsResponse>(
    `/api/v1/analytics/portfolio/${portfolioId}/spread-factors`
  );
  return response;
}

/**
 * Type guard to check if spread factors are available
 */
export function hasSpreadFactors(
  response: SpreadFactorsResponse
): response is SpreadFactorsResponse & { available: true; factors: SpreadFactor[] } {
  return response.available && response.factors.length > 0;
}

/**
 * Get risk level color for UI styling
 */
export function getRiskLevelColor(riskLevel: string): string {
  switch (riskLevel) {
    case 'high':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'medium':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'low':
      return 'text-green-600 bg-green-50 border-green-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

/**
 * Get magnitude badge color
 */
export function getMagnitudeBadgeColor(magnitude: string): string {
  switch (magnitude) {
    case 'Strong':
      return 'bg-purple-100 text-purple-800 border-purple-200';
    case 'Moderate':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'Weak':
      return 'bg-gray-100 text-gray-600 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200';
  }
}

/**
 * Format beta value for display
 *
 * Returns the signed beta value formatted to 3 decimal places.
 * The sign indicates the direction of exposure shown in the badge.
 */
export function formatBeta(beta: number): string {
  const sign = beta >= 0 ? '+' : '';
  return `${sign}${beta.toFixed(3)}`;
}
