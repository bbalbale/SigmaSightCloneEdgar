import { apiClient } from './apiClient';
import { authManager } from './authManager';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';

/**
 * Fundamentals API Service - Financial Statements and Analyst Estimates
 *
 * This service provides access to comprehensive fundamental financial data
 * stored in the database and populated by the batch orchestrator (Phase 1.5).
 *
 * Features:
 * - Database-backed data (no on-demand API calls)
 * - Fast response times (sub-10ms queries, 50x faster than on-demand fetching)
 * - Configurable number of periods and frequency (quarterly/annual)
 * - Comprehensive financial metrics with calculated ratios
 *
 * Endpoints:
 * 1. Income Statement: Revenue, margins, EPS, operating metrics
 * 2. Balance Sheet: Assets, liabilities, equity, calculated ratios
 * 3. Cash Flow: Operating CF, free cash flow, financing activities
 * 4. Analyst Estimates: Forward estimates for 4 periods (0q, +1q, 0y, +1y)
 *
 * Backend Implementation:
 * - File: backend/app/api/v1/fundamentals.py (270 lines, 4 endpoints)
 * - Tables: income_statements, balance_sheets, cash_flows, company_profiles
 * - Router: Registered in backend/app/api/v1/router.py with /fundamentals prefix
 *
 * Related Documentation:
 * - Backend Implementation: frontend/_docs/FundamentalData/02-BACKEND-IMPLEMENTATION-PLAN.md
 * - API Reference: frontend/_docs/1. API_AND_DATABASE_SUMMARY.md
 *
 * @example
 * ```typescript
 * // Get quarterly income statements
 * const incomeData = await fundamentalsApi.getIncomeStatement('MSFT', 4, 'q');
 * console.log(incomeData.periods[0].total_revenue); // "281724000000.00"
 *
 * // Get balance sheet
 * const balanceData = await fundamentalsApi.getBalanceSheet('AAPL', 4, 'q');
 * console.log(balanceData.periods[0].total_assets); // Balance sheet data
 *
 * // Get analyst estimates (no query params)
 * const estimates = await fundamentalsApi.getAnalystEstimates('GOOGL');
 * console.log(estimates.estimates.current_quarter_eps_avg); // Forward EPS estimate
 * ```
 */

// ===== TYPE DEFINITIONS =====

export interface IncomeStatementPeriod {
  period_date: string;
  frequency: string; // 'q' or 'a'
  fiscal_year: number | null;
  fiscal_quarter: number | null;

  // Revenue & Costs
  total_revenue: string | null;
  cost_of_revenue: string | null;
  gross_profit: string | null;
  gross_margin: string | null; // Calculated

  // Operating Expenses
  research_and_development: string | null;
  selling_general_and_administrative: string | null;

  // Operating Results
  operating_income: string | null;
  operating_margin: string | null; // Calculated
  ebit: string | null;
  ebitda: string | null;

  // Net Income
  net_income: string | null;
  net_margin: string | null; // Calculated
  diluted_eps: string | null;
  basic_eps: string | null;
  basic_average_shares: string | null; // BIGINT for large cap stocks
  diluted_average_shares: string | null; // BIGINT

  // Tax & Interest
  tax_provision: string | null;
  interest_expense: string | null;
  depreciation_and_amortization: string | null;
}

export interface IncomeStatementResponse {
  symbol: string;
  frequency: string;
  currency: string;
  periods_returned: number;
  periods: IncomeStatementPeriod[];
}

export interface BalanceSheetPeriod {
  period_date: string;
  frequency: string; // 'q' or 'a'
  fiscal_year: number | null;
  fiscal_quarter: number | null;

  // Assets
  total_assets: string | null;
  current_assets: string | null;
  cash_and_cash_equivalents: string | null;
  cash_and_short_term_investments: string | null;
  accounts_receivable: string | null;
  inventory: string | null;

  // Liabilities
  total_liabilities: string | null;
  current_liabilities: string | null;
  accounts_payable: string | null;
  short_term_debt: string | null;
  long_term_debt: string | null;
  total_debt: string | null;

  // Equity
  total_stockholders_equity: string | null;
  retained_earnings: string | null;
  common_stock: string | null;

  // Calculated Metrics
  working_capital: string | null;
  net_debt: string | null;
  current_ratio: string | null;
  debt_to_equity: string | null;
}

export interface BalanceSheetResponse {
  symbol: string;
  frequency: string;
  currency: string;
  periods_returned: number;
  periods: BalanceSheetPeriod[];
}

export interface CashFlowPeriod {
  period_date: string;
  frequency: string; // 'q' or 'a'
  fiscal_year: number | null;
  fiscal_quarter: number | null;

  // Operating Activities
  operating_cash_flow: string | null;
  stock_based_compensation: string | null;

  // Investing Activities
  investing_cash_flow: string | null;
  capital_expenditures: string | null;

  // Financing Activities
  financing_cash_flow: string | null;
  dividends_paid: string | null;
  stock_repurchased: string | null;
  debt_issuance: string | null;
  debt_repayment: string | null;

  // Net Changes
  net_change_in_cash: string | null;

  // Calculated Metrics
  free_cash_flow: string | null; // Operating CF - CapEx
  fcf_margin: string | null; // FCF / Revenue
}

export interface CashFlowResponse {
  symbol: string;
  frequency: string;
  currency: string;
  periods_returned: number;
  periods: CashFlowPeriod[];
}

export interface AnalystEstimates {
  // Current Quarter (0q)
  current_quarter_eps_avg: string | null;
  current_quarter_eps_low: string | null;
  current_quarter_eps_high: string | null;
  current_quarter_revenue_avg: string | null;
  current_quarter_revenue_low: string | null;
  current_quarter_revenue_high: string | null;
  current_quarter_analyst_count: number | null;

  // Next Quarter (+1q)
  next_quarter_eps_avg: string | null;
  next_quarter_eps_low: string | null;
  next_quarter_eps_high: string | null;
  next_quarter_revenue_avg: string | null;
  next_quarter_revenue_low: string | null;
  next_quarter_revenue_high: string | null;
  next_quarter_analyst_count: number | null;

  // Current Year (0y)
  current_year_earnings_avg: string | null;
  current_year_earnings_low: string | null;
  current_year_earnings_high: string | null;
  current_year_revenue_avg: string | null;
  current_year_revenue_low: string | null;
  current_year_revenue_high: string | null;
  current_year_analyst_count: number | null;

  // Next Year (+1y)
  next_year_earnings_avg: string | null;
  next_year_earnings_low: string | null;
  next_year_earnings_high: string | null;
  next_year_revenue_avg: string | null;
  next_year_revenue_low: string | null;
  next_year_revenue_high: string | null;
  next_year_analyst_count: number | null;
}

export interface AnalystEstimatesResponse {
  symbol: string;
  estimates: AnalystEstimates;
}

// ===== SERVICE CLASS =====

export class FundamentalsApi {
  private getAuthHeaders() {
    const token = authManager.getAccessToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    return {
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * Get income statement data for a symbol
   *
   * Returns comprehensive income statement metrics including revenue, margins,
   * operating income, net income, EPS, and tax/interest information.
   *
   * @param symbol - Stock symbol (e.g., 'MSFT', 'AAPL')
   * @param periods - Number of periods to return (default: 4, range: 1-20)
   * @param frequency - 'q' for quarterly or 'a' for annual (default: 'q')
   * @returns Income statement data with specified number of periods
   * @throws Error if not authenticated or symbol not found (404)
   *
   * @example
   * ```typescript
   * const data = await fundamentalsApi.getIncomeStatement('MSFT', 4, 'q');
   * console.log(data.periods[0].total_revenue); // "$281,724,000,000.00"
   * console.log(data.periods[0].diluted_eps); // "13.6400"
   * ```
   */
  async getIncomeStatement(
    symbol: string,
    periods: number = 4,
    frequency: 'q' | 'a' = 'q'
  ): Promise<IncomeStatementResponse> {
    const url = `${API_ENDPOINTS.FUNDAMENTALS.INCOME_STATEMENT(symbol)}?periods=${periods}&frequency=${frequency}`;
    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });
    return resp as IncomeStatementResponse;
  }

  /**
   * Get balance sheet data for a symbol
   *
   * Returns comprehensive balance sheet metrics including assets, liabilities,
   * equity, and calculated ratios (working capital, current ratio, debt-to-equity).
   *
   * @param symbol - Stock symbol (e.g., 'MSFT', 'AAPL')
   * @param periods - Number of periods to return (default: 4, range: 1-20)
   * @param frequency - 'q' for quarterly or 'a' for annual (default: 'q')
   * @returns Balance sheet data with specified number of periods
   * @throws Error if not authenticated or symbol not found (404)
   *
   * @example
   * ```typescript
   * const data = await fundamentalsApi.getBalanceSheet('AAPL', 4, 'q');
   * console.log(data.periods[0].total_assets); // Total assets
   * console.log(data.periods[0].current_ratio); // Current ratio
   * ```
   */
  async getBalanceSheet(
    symbol: string,
    periods: number = 4,
    frequency: 'q' | 'a' = 'q'
  ): Promise<BalanceSheetResponse> {
    const url = `${API_ENDPOINTS.FUNDAMENTALS.BALANCE_SHEET(symbol)}?periods=${periods}&frequency=${frequency}`;
    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });
    return resp as BalanceSheetResponse;
  }

  /**
   * Get cash flow data for a symbol
   *
   * Returns comprehensive cash flow metrics including operating cash flow,
   * capital expenditures, free cash flow, and financing activities.
   *
   * @param symbol - Stock symbol (e.g., 'MSFT', 'AAPL')
   * @param periods - Number of periods to return (default: 4, range: 1-20)
   * @param frequency - 'q' for quarterly or 'a' for annual (default: 'q')
   * @returns Cash flow data with specified number of periods
   * @throws Error if not authenticated or symbol not found (404)
   *
   * @example
   * ```typescript
   * const data = await fundamentalsApi.getCashFlow('GOOGL', 4, 'q');
   * console.log(data.periods[0].free_cash_flow); // Free cash flow
   * console.log(data.periods[0].fcf_margin); // FCF margin percentage
   * ```
   */
  async getCashFlow(
    symbol: string,
    periods: number = 4,
    frequency: 'q' | 'a' = 'q'
  ): Promise<CashFlowResponse> {
    const url = `${API_ENDPOINTS.FUNDAMENTALS.CASH_FLOW(symbol)}?periods=${periods}&frequency=${frequency}`;
    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });
    return resp as CashFlowResponse;
  }

  /**
   * Get analyst estimates for a symbol
   *
   * Returns forward estimates for 4 periods:
   * - Current Quarter (0q): Next earnings release
   * - Next Quarter (+1q): Following quarter
   * - Current Year (0y): Full fiscal year
   * - Next Year (+1y): Following fiscal year
   *
   * Includes EPS and revenue estimates with analyst count and ranges (low/avg/high).
   *
   * @param symbol - Stock symbol (e.g., 'MSFT', 'AAPL')
   * @returns Analyst estimates for all 4 periods
   * @throws Error if not authenticated or symbol not found (404)
   *
   * @example
   * ```typescript
   * const data = await fundamentalsApi.getAnalystEstimates('MSFT');
   * console.log(data.estimates.current_quarter_eps_avg); // "3.8700"
   * console.log(data.estimates.next_year_earnings_avg); // "18.5700"
   * console.log(data.estimates.current_quarter_analyst_count); // 34
   * ```
   */
  async getAnalystEstimates(symbol: string): Promise<AnalystEstimatesResponse> {
    const url = API_ENDPOINTS.FUNDAMENTALS.ANALYST_ESTIMATES(symbol);
    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });
    return resp as AnalystEstimatesResponse;
  }
}

// Export singleton instance
const fundamentalsApi = new FundamentalsApi();
export default fundamentalsApi;
