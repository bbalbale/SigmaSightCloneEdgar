/**
 * AccountFilter Component - November 3, 2025
 * Dropdown filter for switching between aggregate view and individual portfolios
 * Uses progressive disclosure to hide for single-portfolio users
 */

'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { usePortfolios } from '@/hooks/useMultiPortfolio'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { Loader2, Building2 } from 'lucide-react'

interface AccountFilterProps {
  /**
   * Show filter even for single portfolio users (default: false)
   * When false, uses progressive disclosure to hide for single portfolio
   */
  showForSinglePortfolio?: boolean

  /**
   * Optional className for styling
   */
  className?: string
}

export function AccountFilter({
  showForSinglePortfolio = false,
  className = ''
}: AccountFilterProps) {
  const { portfolios, loading } = usePortfolios()
  const selectedPortfolioId = usePortfolioStore((state) => state.selectedPortfolioId)
  const setSelectedPortfolio = usePortfolioStore((state) => state.setSelectedPortfolio)

  // Progressive disclosure: Hide for single-portfolio users unless explicitly shown
  if (!showForSinglePortfolio && portfolios.length <= 1) {
    return null
  }

  // Loading state
  if (loading) {
    return (
      <div className={`flex items-center gap-2 text-sm text-muted-foreground ${className}`}>
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading accounts...</span>
      </div>
    )
  }

  // No portfolios available
  if (portfolios.length === 0) {
    return null
  }

  const handleValueChange = (value: string) => {
    if (value === 'aggregate') {
      setSelectedPortfolio(null) // null = aggregate view
    } else {
      setSelectedPortfolio(value)
    }
  }

  // Convert selectedPortfolioId to string for Select component
  const selectValue = selectedPortfolioId === null ? 'aggregate' : selectedPortfolioId

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Building2 className="h-4 w-4 text-muted-foreground" />
      <Select value={selectValue} onValueChange={handleValueChange}>
        <SelectTrigger className="w-[280px]">
          <SelectValue placeholder="Select account" />
        </SelectTrigger>
        <SelectContent>
          {/* Aggregate View Option */}
          <SelectItem value="aggregate">
            <div className="flex flex-col">
              <span className="font-medium">All Accounts</span>
              <span className="text-xs text-muted-foreground">
                View combined data from {portfolios.length}{' '}
                {portfolios.length === 1 ? 'account' : 'accounts'}
              </span>
            </div>
          </SelectItem>

          {/* Individual Portfolio Options */}
          {portfolios
            .filter((p) => p.is_active)
            .map((portfolio) => (
              <SelectItem key={portfolio.id} value={portfolio.id}>
                <div className="flex flex-col">
                  <span className="font-medium">{portfolio.account_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatAccountType(portfolio.account_type)} • {portfolio.position_count}{' '}
                    {portfolio.position_count === 1 ? 'position' : 'positions'}
                  </span>
                </div>
              </SelectItem>
            ))}
        </SelectContent>
      </Select>
    </div>
  )
}

/**
 * Helper: Format account type for display
 */
function formatAccountType(accountType: string): string {
  const typeMap: Record<string, string> = {
    taxable: 'Taxable',
    ira: 'IRA',
    roth_ira: 'Roth IRA',
    '401k': '401(k)',
    trust: 'Trust',
    other: 'Other',
  }
  return typeMap[accountType] || accountType
}
