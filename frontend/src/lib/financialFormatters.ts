/**
 * Financial Number Formatting Utilities
 *
 * Provides consistent formatting for financial data display:
 * - Currency (billions, millions)
 * - Percentages (margins, growth rates)
 * - N/A handling for null values
 */

/**
 * Format large currency values with B/M suffixes
 *
 * @param value - Number to format
 * @returns Formatted string (e.g., "$366B", "$5.61B", "$93M")
 *
 * @example
 * formatCurrency(366000000000) → "$366B"
 * formatCurrency(5610000000)   → "$5.61B"
 * formatCurrency(93000000)     → "$93.0M"
 * formatCurrency(null)         → "N/A"
 */
export function formatCurrency(value: number | null): string {
  if (value === null) return 'N/A';

  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1_000_000_000) {
    // Billions
    const billions = absValue / 1_000_000_000;
    if (billions >= 100) {
      return `${sign}$${billions.toFixed(0)}B`;
    } else if (billions >= 10) {
      return `${sign}$${billions.toFixed(1)}B`;
    } else {
      return `${sign}$${billions.toFixed(2)}B`;
    }
  } else if (absValue >= 1_000_000) {
    // Millions
    const millions = absValue / 1_000_000;
    if (millions >= 100) {
      return `${sign}$${millions.toFixed(0)}M`;
    } else {
      return `${sign}$${millions.toFixed(1)}M`;
    }
  } else if (absValue >= 1_000) {
    // Thousands
    const thousands = absValue / 1_000;
    return `${sign}$${thousands.toFixed(1)}K`;
  } else {
    // Less than 1000
    return `${sign}$${absValue.toFixed(2)}`;
  }
}

/**
 * Format EPS values (no suffix, just $)
 *
 * @param value - EPS value
 * @returns Formatted string (e.g., "$6.42", "$5.61")
 *
 * @example
 * formatEPS(6.42)  → "$6.42"
 * formatEPS(5.611) → "$5.61"
 * formatEPS(null)  → "N/A"
 */
export function formatEPS(value: number | null): string {
  if (value === null) return 'N/A';

  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

/**
 * Format percentage values (margins, ratios)
 *
 * @param value - Percentage value (0-100 scale)
 * @returns Formatted string (e.g., "29.8%", "0.7%", "-2.8%")
 *
 * @example
 * formatPercent(29.8)  → "29.8%"
 * formatPercent(0.74)  → "0.7%"
 * formatPercent(-2.8)  → "-2.8%"
 * formatPercent(null)  → "N/A"
 */
export function formatPercent(value: number | null): string {
  if (value === null) return 'N/A';

  const sign = value < 0 ? '-' : '';
  const absValue = Math.abs(value);

  if (absValue >= 10) {
    return `${sign}${absValue.toFixed(1)}%`;
  } else {
    return `${sign}${absValue.toFixed(1)}%`;
  }
}

/**
 * Format growth rate with + prefix for positive values
 *
 * @param value - Growth percentage (0-100 scale)
 * @returns Formatted string with + prefix (e.g., "+33.3%", "-2.8%")
 *
 * @example
 * formatGrowth(33.3)  → "+33.3%"
 * formatGrowth(-2.8)  → "-2.8%"
 * formatGrowth(0.0)   → "0.0%"
 * formatGrowth(null)  → "N/A"
 */
export function formatGrowth(value: number | null): string {
  if (value === null) return 'N/A';

  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  const absValue = Math.abs(value);

  return `${sign}${absValue.toFixed(1)}%`;
}

/**
 * Get color class for growth value
 *
 * @param value - Growth percentage
 * @returns Tailwind color class
 *
 * @example
 * getGrowthColor(10)  → "text-green-600"
 * getGrowthColor(-5)  → "text-red-600"
 * getGrowthColor(0)   → "text-gray-700"
 */
export function getGrowthColor(value: number | null): string {
  if (value === null) return 'text-gray-400';
  if (value > 0) return 'text-green-600';
  if (value < 0) return 'text-red-600';
  return 'text-gray-700';
}

/**
 * Format fiscal year end date for display
 *
 * @param fiscalYearEnd - Date in MM-DD format (e.g., "09-30")
 * @returns Formatted display string (e.g., "September 30")
 *
 * @example
 * formatFiscalYearEnd("09-30") → "September 30"
 * formatFiscalYearEnd("12-31") → "December 31"
 * formatFiscalYearEnd("01-31") → "January 31"
 */
export function formatFiscalYearEnd(fiscalYearEnd: string | null): string | null {
  if (!fiscalYearEnd) return null;

  const [month, day] = fiscalYearEnd.split('-');
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const monthIndex = parseInt(month, 10) - 1;
  const monthName = monthNames[monthIndex];

  return `${monthName} ${parseInt(day, 10)}`;
}

/**
 * Check if fiscal year is calendar year (ends Dec 31)
 *
 * @param fiscalYearEnd - Date in MM-DD format
 * @returns True if calendar year
 */
export function isCalendarYear(fiscalYearEnd: string | null): boolean {
  return fiscalYearEnd === '12-31';
}

/**
 * Format date string for display
 *
 * @param dateString - ISO date string
 * @returns Formatted date (e.g., "Nov 2, 2025")
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return '';

  const date = new Date(dateString);
  const options: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  };

  return date.toLocaleDateString('en-US', options);
}
