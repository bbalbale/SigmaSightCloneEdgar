/**
 * Formatting utilities for displaying financial data
 */

/**
 * Format a number as currency with K suffix for thousands
 */
export function formatNumber(num: number | string | null | undefined): string {
  const n = Number(num)
  if (isNaN(n) || num == null) return '$0.00'
  if (Math.abs(n) >= 1000) {
    return `$${(n / 1000).toFixed(1)}K`
  }
  return `$${n.toFixed(2)}`
}

/**
 * Format a price value as currency
 */
export function formatPrice(price: number | string | null | undefined): string {
  const p = Number(price)
  if (isNaN(p) || price == null) return '$0.00'
  return `$${p.toFixed(2)}`
}

/**
 * Format a percentage value
 */
export function formatPercentage(value: number | string | null | undefined, decimals: number = 2): string {
  const v = Number(value)
  if (isNaN(v) || value == null) return '0.00%'
  return `${v.toFixed(decimals)}%`
}

/**
 * Format large numbers with commas
 */
export function formatWithCommas(num: number | string): string {
  const n = Number(num)
  if (isNaN(n)) return '0'
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * Format currency with full precision
 */
export function formatCurrency(amount: number | string | null | undefined, decimals: number = 2): string {
  const a = Number(amount)
  if (isNaN(a) || amount == null) return '$0.00'
  return `$${formatWithCommas(Number(a.toFixed(decimals)))}`
}