'use client'

import React from 'react'
import { HoldingsTableDesktop } from './HoldingsTableDesktop'
import { HoldingsTableMobile } from './HoldingsTableMobile'

interface HoldingRow {
  id: string
  symbol: string
  quantity: number
  entryPrice: number
  todaysPrice: number
  targetPrice: number | null
  marketValue: number
  weight: number
  pnlToday: number | null
  pnlTotal: number
  returnPct: number
  targetReturn: number | null
  beta: number | null
  positionType: string
  investmentClass: string
  account_name?: string // For aggregate view - which account/portfolio this holding belongs to
  portfolio_id?: string // For grouping in aggregate view
}

interface HoldingsTableProps {
  holdings: HoldingRow[]
  loading: boolean
  onRefresh?: () => void
}

/**
 * HoldingsTable - Responsive Wrapper
 *
 * Renders desktop table on ≥768px, mobile cards on <768px.
 * Uses CSS-based conditional rendering for better performance.
 *
 * Desktop: Full sortable table with 11 columns
 * Mobile: Compact position cards with essential info
 */
export function HoldingsTable({ holdings, loading, onRefresh }: HoldingsTableProps) {
  return (
    <>
      {/* Desktop: Table (hidden on mobile) */}
      <div className="hidden md:block">
        <HoldingsTableDesktop holdings={holdings} loading={loading} onRefresh={onRefresh} />
      </div>

      {/* Mobile: Cards (hidden on desktop) */}
      <div className="md:hidden">
        <HoldingsTableMobile holdings={holdings} loading={loading} />
      </div>
    </>
  )
}
