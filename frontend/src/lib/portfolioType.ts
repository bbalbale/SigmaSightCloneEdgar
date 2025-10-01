// Portfolio type management utilities

export type PortfolioType = 'high-net-worth' | 'individual' | 'hedge-fund'

const PORTFOLIO_TYPE_KEY = 'selected_portfolio_type'

export function getSelectedPortfolioType(): PortfolioType | null {
  if (typeof window === 'undefined') {
    return null
  }
  const stored = localStorage.getItem(PORTFOLIO_TYPE_KEY)
  if (stored && ['high-net-worth', 'individual', 'hedge-fund'].includes(stored)) {
    return stored as PortfolioType
  }
  return null
}

export function setSelectedPortfolioType(type: PortfolioType): void {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.setItem(PORTFOLIO_TYPE_KEY, type)
}

export function clearSelectedPortfolioType(): void {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.removeItem(PORTFOLIO_TYPE_KEY)
}

// Determine portfolio type from email
export function getPortfolioTypeFromEmail(email: string): PortfolioType {
  if (email.includes('hnw')) {
    return 'high-net-worth'
  } else if (email.includes('individual')) {
    return 'individual'
  } else if (email.includes('hedgefund')) {
    return 'hedge-fund'
  }
  // Default to high-net-worth
  return 'high-net-worth'
}