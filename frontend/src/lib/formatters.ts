/**
 * Formatting utilities for displaying financial data
 */

/**
 * Format a number as currency with K suffix for thousands
 */
export function formatNumber(num: number): string {
  if (Math.abs(num) >= 1000) {
    return `$${(num / 1000).toFixed(1)}K`
  }
  return `$${num.toFixed(2)}`
}

/**
 * Format a price value as currency
 */
export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

/**
 * Format a percentage value
 */
export function formatPercentage(value: number, decimals: number = 2): string {
  return `${value.toFixed(decimals)}%`
}

/**
 * Format large numbers with commas
 */
export function formatWithCommas(num: number): string {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * Format currency with full precision
 */
export function formatCurrency(amount: number, decimals: number = 2): string {
  return `$${formatWithCommas(Number(amount.toFixed(decimals)))}`
}