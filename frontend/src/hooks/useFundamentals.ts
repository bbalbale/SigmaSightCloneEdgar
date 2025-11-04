import { useState, useEffect } from 'react';
import fundamentalsApi from '@/services/fundamentalsApi';
import { ApiError } from '@/services/apiClient';

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
        if (err instanceof ApiError && err.status === 404) {
          // Certain instruments (indexes, mutual funds) do not have fundamentals yet
          setData(null);
          setError(null);
        } else {
          setError(err instanceof Error ? err : new Error('Failed to fetch fundamental data'));
          setData(null);
        }
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
  const incomePeriods: any[] = Array.isArray(incomeData?.periods) ? incomeData.periods : []
  const cashFlowPeriods: any[] = Array.isArray(cashFlowData?.periods) ? cashFlowData.periods : []
  const estimates = estimatesData?.estimates ?? {}

  const fallback: FundamentalsData = {
    symbol: incomeData?.symbol ?? '',
    years: [],
    fiscalYearEnd: null,
    analystCount: parseNumeric(estimates?.current_year_analyst_count) ?? null,
    lastUpdated: new Date().toISOString()
  }

  if (incomePeriods.length === 0) {
    return fallback
  }

  // 1. Create historical years (2021-2024)
  const historical: FinancialYearData[] = incomePeriods.map((stmt: any, index: number, array: any[]) => {
    const prevStmt = array[index + 1]; // Previous year for growth calculation
    const matchingCashFlow = cashFlowPeriods.find((cf: any) => cf.fiscal_year === stmt.fiscal_year);
    const grossMarginValue = parseNumeric(stmt.gross_margin)
    const operatingMarginValue = parseNumeric(stmt.operating_margin)
    const netMarginValue = parseNumeric(stmt.net_margin)
    const dilutedEps = parseNumeric(stmt.diluted_eps)
    const cashFlowMarginValue = matchingCashFlow ? parseNumeric(matchingCashFlow.fcf_margin) : null

    // Extract year from period_date (e.g., "2024-09-30" -> 2024)
    let year = stmt.fiscal_year || 0;
    if (year === 0 && stmt.period_date) {
      const date = new Date(stmt.period_date);
      year = date.getFullYear();
    }

    return {
      year,
      isEstimate: false,

      // Revenue
      revenue: parseNumeric(stmt.total_revenue),
      revenueGrowth: prevStmt ? calculateGrowth(stmt.total_revenue, prevStmt.total_revenue) : null,

      // Gross Profit
      grossProfit: parseNumeric(stmt.gross_profit),
      grossMargin: grossMarginValue !== null ? grossMarginValue * 100 : null,
      grossProfitGrowth: prevStmt ? calculateGrowth(stmt.gross_profit, prevStmt.gross_profit) : null,

      // EBIT (Operating Income)
      ebit: parseNumeric(stmt.operating_income),
      ebitMargin: operatingMarginValue !== null ? operatingMarginValue * 100 : null,
      ebitGrowth: prevStmt ? calculateGrowth(stmt.operating_income, prevStmt.operating_income) : null,

      // Net Income
      netIncome: parseNumeric(stmt.net_income),
      netMargin: netMarginValue !== null ? netMarginValue * 100 : null,
      netIncomeGrowth: prevStmt ? calculateGrowth(stmt.net_income, prevStmt.net_income) : null,

      // EPS
      eps: dilutedEps,
      epsGrowth: prevStmt ? calculateGrowth(dilutedEps, prevStmt.diluted_eps) : null,

      // FCF
      fcf: matchingCashFlow ? parseNumeric(matchingCashFlow.free_cash_flow) : null,
      fcfMargin: cashFlowMarginValue !== null ? cashFlowMarginValue * 100 : null,
      fcfGrowth: null, // Could calculate if we track previous CF data
    };
  });

  // 2. Get latest year data for calculations
  const latestYear = historical[0];
  const latestStmt = incomePeriods[0];

  if (!latestYear || !latestStmt) {
    return fallback
  }

  const latestShares = parseNumeric(latestStmt.diluted_average_shares);
  const currentYearRevenue = parseNumeric(estimates.current_year_revenue_avg)
  const currentYearEarnings = parseNumeric(estimates.current_year_earnings_avg)
  const nextYearRevenue = parseNumeric(estimates.next_year_revenue_avg)
  const nextYearEarnings = parseNumeric(estimates.next_year_earnings_avg)
  const currentYearAnalystCount = parseNumeric(estimates.current_year_analyst_count)

  // 3. Create current year estimate (2025E)
  const currentYearEstimate: FinancialYearData = {
    year: latestYear.year + 1,
    isEstimate: true,

    // Revenue - from analyst estimates
    revenue: currentYearRevenue,
    revenueGrowth: calculateGrowth(currentYearRevenue, latestYear.revenue),

    // Gross Profit - N/A (not estimated)
    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    // EBIT - N/A (not estimated)
    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    // Net Income - CALCULATED from EPS × Shares
    netIncome:
      latestShares !== null && currentYearEarnings !== null
        ? currentYearEarnings * latestShares
        : null,
    netMargin:
      latestShares !== null && currentYearEarnings !== null && currentYearRevenue !== null
        ? (currentYearEarnings * latestShares) / currentYearRevenue * 100
        : null,
    netIncomeGrowth:
      latestShares !== null && currentYearEarnings !== null
        ? calculateGrowth(currentYearEarnings * latestShares, latestYear.netIncome)
        : null,

    // EPS - from analyst estimates
    eps: currentYearEarnings,
    epsGrowth: calculateGrowth(currentYearEarnings, latestYear.eps),

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
    revenue: nextYearRevenue,
    revenueGrowth: calculateGrowth(nextYearRevenue, currentYearRevenue),

    // Gross Profit - N/A
    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    // EBIT - N/A
    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    // Net Income - CALCULATED
    netIncome:
      latestShares !== null && nextYearEarnings !== null
        ? nextYearEarnings * latestShares
        : null,
    netMargin:
      latestShares !== null && nextYearEarnings !== null && nextYearRevenue !== null
        ? (nextYearEarnings * latestShares) / nextYearRevenue * 100
        : null,
    netIncomeGrowth:
      latestShares !== null && nextYearEarnings !== null && currentYearEarnings !== null
        ? calculateGrowth(nextYearEarnings * latestShares, currentYearEarnings * latestShares)
        : null,

    // EPS
    eps: nextYearEarnings,
    epsGrowth: calculateGrowth(nextYearEarnings, currentYearEarnings),

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
  if (latestStmt?.period_date) {
    const date = new Date(latestStmt.period_date);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    fiscalYearEnd = `${month}-${day}`;
  }

  return {
    symbol: incomeData?.symbol ?? '',
    years: allYears,
    fiscalYearEnd,
    analystCount: currentYearAnalystCount,
    lastUpdated: new Date().toISOString(),
  };
}
