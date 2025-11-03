import { useState, useEffect } from 'react';
import fundamentalsApi from '@/services/fundamentalsApi';

/**
 * Custom hook to fetch and manage fundamental financial data
 *
 * Fetches income statements, cash flows, and analyst estimates for a symbol
 * and transforms the data into a unified structure for display
 *
 * @param symbol - Stock symbol (e.g., 'AAPL', 'MSFT')
 * @param frequency - 'q' for quarterly or 'a' for annual (default: 'a')
 * @param periods - Number of historical periods to fetch (default: 4)
 */

export interface FinancialYearData {
  year: number;
  isEstimate: boolean;

  // Revenue
  revenue: number | null;
  revenueGrowth: number | null;

  // Gross Profit
  grossProfit: number | null;
  grossMargin: number | null;
  grossProfitGrowth: number | null;

  // EBIT (Operating Income)
  ebit: number | null;
  ebitMargin: number | null;
  ebitGrowth: number | null;

  // Net Income
  netIncome: number | null;
  netMargin: number | null;
  netIncomeGrowth: number | null;

  // EPS
  eps: number | null;
  epsGrowth: number | null;

  // Free Cash Flow
  fcf: number | null;
  fcfMargin: number | null;
  fcfGrowth: number | null;
}

export interface FundamentalsData {
  symbol: string;
  years: FinancialYearData[];
  fiscalYearEnd: string | null; // e.g., "09-30" for September 30
  analystCount: number | null;
  lastUpdated: string | null;
}

interface UseFundamentalsReturn {
  data: FundamentalsData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useFundamentals(
  symbol: string | null,
  frequency: 'q' | 'a' = 'a',
  periods: number = 4
): UseFundamentalsReturn {
  const [data, setData] = useState<FundamentalsData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState<number>(0);

  useEffect(() => {
    if (!symbol) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const fetchFundamentals = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch all data in parallel
        const [incomeData, cashFlowData, estimatesData] = await Promise.all([
          fundamentalsApi.getIncomeStatement(symbol, periods, frequency),
          fundamentalsApi.getCashFlow(symbol, periods, frequency),
          fundamentalsApi.getAnalystEstimates(symbol),
        ]);

        // Transform data into unified structure
        const transformedData = transformToTableData(
          incomeData,
          cashFlowData,
          estimatesData
        );

        setData(transformedData);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch fundamental data'));
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchFundamentals();
  }, [symbol, frequency, periods, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger(prev => prev + 1);
  };

  return { data, loading, error, refetch };
}

/**
 * Helper function to calculate YoY growth percentage
 */
function calculateGrowth(current: string | number | null, previous: string | number | null): number | null {
  if (current === null || previous === null) return null;

  const curr = typeof current === 'string' ? parseFloat(current) : current;
  const prev = typeof previous === 'string' ? parseFloat(previous) : previous;

  if (prev === 0 || isNaN(curr) || isNaN(prev)) return null;

  return ((curr - prev) / prev) * 100;
}

/**
 * Helper function to safely parse numeric values
 */
function parseNumeric(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === 'string' ? parseFloat(value) : value;
  return isNaN(parsed) ? null : parsed;
}

/**
 * Transform backend API responses into unified table data structure
 */
function transformToTableData(
  incomeData: any,
  cashFlowData: any,
  estimatesData: any
): FundamentalsData {

  // 1. Create historical years (2021-2024)
  const historical: FinancialYearData[] = incomeData.periods.map((stmt: any, index: number, array: any[]) => {
    const prevStmt = array[index + 1]; // Previous year for growth calculation
    const matchingCashFlow = cashFlowData.periods.find((cf: any) => cf.fiscal_year === stmt.fiscal_year);

    return {
      year: stmt.fiscal_year || 0,
      isEstimate: false,

      // Revenue
      revenue: parseNumeric(stmt.total_revenue),
      revenueGrowth: prevStmt ? calculateGrowth(stmt.total_revenue, prevStmt.total_revenue) : null,

      // Gross Profit
      grossProfit: parseNumeric(stmt.gross_profit),
      grossMargin: stmt.gross_margin ? parseNumeric(stmt.gross_margin) * 100 : null,
      grossProfitGrowth: prevStmt ? calculateGrowth(stmt.gross_profit, prevStmt.gross_profit) : null,

      // EBIT (Operating Income)
      ebit: parseNumeric(stmt.operating_income),
      ebitMargin: stmt.operating_margin ? parseNumeric(stmt.operating_margin) * 100 : null,
      ebitGrowth: prevStmt ? calculateGrowth(stmt.operating_income, prevStmt.operating_income) : null,

      // Net Income
      netIncome: parseNumeric(stmt.net_income),
      netMargin: stmt.net_margin ? parseNumeric(stmt.net_margin) * 100 : null,
      netIncomeGrowth: prevStmt ? calculateGrowth(stmt.net_income, prevStmt.net_income) : null,

      // EPS
      eps: parseNumeric(stmt.diluted_eps),
      epsGrowth: prevStmt ? calculateGrowth(stmt.diluted_eps, prevStmt.diluted_eps) : null,

      // FCF
      fcf: matchingCashFlow ? parseNumeric(matchingCashFlow.free_cash_flow) : null,
      fcfMargin: matchingCashFlow && matchingCashFlow.fcf_margin
        ? parseNumeric(matchingCashFlow.fcf_margin) * 100
        : null,
      fcfGrowth: null, // Could calculate if we track previous CF data
    };
  });

  // 2. Get latest year data for calculations
  const latestYear = historical[0];
  const latestStmt = incomeData.periods[0];
  const latestShares = parseNumeric(latestStmt.diluted_average_shares);

  // 3. Create current year estimate (2025E)
  const currentYearEstimate: FinancialYearData = {
    year: latestYear.year + 1,
    isEstimate: true,

    // Revenue - from analyst estimates
    revenue: parseNumeric(estimatesData.estimates.current_year_revenue_avg),
    revenueGrowth: calculateGrowth(
      estimatesData.estimates.current_year_revenue_avg,
      latestYear.revenue
    ),

    // Gross Profit - N/A (not estimated)
    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    // EBIT - N/A (not estimated)
    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    // Net Income - CALCULATED from EPS × Shares
    netIncome: latestShares
      ? parseNumeric(estimatesData.estimates.current_year_earnings_avg)! * latestShares
      : null,
    netMargin: latestShares && parseNumeric(estimatesData.estimates.current_year_revenue_avg)
      ? (parseNumeric(estimatesData.estimates.current_year_earnings_avg)! * latestShares) /
        parseNumeric(estimatesData.estimates.current_year_revenue_avg)! * 100
      : null,
    netIncomeGrowth: latestShares
      ? calculateGrowth(
          parseNumeric(estimatesData.estimates.current_year_earnings_avg)! * latestShares,
          latestYear.netIncome
        )
      : null,

    // EPS - from analyst estimates
    eps: parseNumeric(estimatesData.estimates.current_year_earnings_avg),
    epsGrowth: calculateGrowth(
      estimatesData.estimates.current_year_earnings_avg,
      latestYear.eps
    ),

    // FCF - N/A (not estimated)
    fcf: null,
    fcfMargin: null,
    fcfGrowth: null,
  };

  // 4. Create next year estimate (2026E)
  const nextYearEstimate: FinancialYearData = {
    year: latestYear.year + 2,
    isEstimate: true,

    // Revenue
    revenue: parseNumeric(estimatesData.estimates.next_year_revenue_avg),
    revenueGrowth: calculateGrowth(
      estimatesData.estimates.next_year_revenue_avg,
      estimatesData.estimates.current_year_revenue_avg
    ),

    // Gross Profit - N/A
    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    // EBIT - N/A
    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    // Net Income - CALCULATED
    netIncome: latestShares
      ? parseNumeric(estimatesData.estimates.next_year_earnings_avg)! * latestShares
      : null,
    netMargin: latestShares && parseNumeric(estimatesData.estimates.next_year_revenue_avg)
      ? (parseNumeric(estimatesData.estimates.next_year_earnings_avg)! * latestShares) /
        parseNumeric(estimatesData.estimates.next_year_revenue_avg)! * 100
      : null,
    netIncomeGrowth: latestShares
      ? calculateGrowth(
          parseNumeric(estimatesData.estimates.next_year_earnings_avg)! * latestShares,
          parseNumeric(estimatesData.estimates.current_year_earnings_avg)! * latestShares
        )
      : null,

    // EPS
    eps: parseNumeric(estimatesData.estimates.next_year_earnings_avg),
    epsGrowth: calculateGrowth(
      estimatesData.estimates.next_year_earnings_avg,
      estimatesData.estimates.current_year_earnings_avg
    ),

    // FCF - N/A
    fcf: null,
    fcfMargin: null,
    fcfGrowth: null,
  };

  // 5. Combine all years and sort ascending by year
  const allYears = [...historical, currentYearEstimate, nextYearEstimate].sort(
    (a, b) => a.year - b.year
  );

  // 6. Determine fiscal year end (extract from period_date)
  let fiscalYearEnd: string | null = null;
  if (latestStmt.period_date) {
    const date = new Date(latestStmt.period_date);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    fiscalYearEnd = `${month}-${day}`;
  }

  return {
    symbol: incomeData.symbol,
    years: allYears,
    fiscalYearEnd,
    analystCount: parseNumeric(estimatesData.estimates.current_year_analyst_count),
    lastUpdated: new Date().toISOString(),
  };
}
