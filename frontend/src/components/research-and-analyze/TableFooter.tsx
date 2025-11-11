'use client'

import React from 'react'
import { formatFiscalYearEnd, isCalendarYear, formatDate } from '@/lib/financialFormatters'

interface TableFooterProps {
  fiscalYearEnd: string | null
  analystCount: number | null
  lastUpdated: string | null
}

/**
 * TableFooter Component
 *
 * Displays contextual notes below the financial summary table:
 * - Fiscal year end (e.g., "Fiscal year ends September 30")
 * - Analyst estimate info (e.g., "Forward estimates based on 34 analysts")
 * - Last updated timestamp
 *
 * Example:
 * ┌────────────────────────────────────────────────────────────────┐
 * │ Note: Fiscal year ends September 30 (not calendar year)       │
 * │ Forward estimates based on 34 analysts · Updated Nov 2, 2025  │
 * └────────────────────────────────────────────────────────────────┘
 */
export function TableFooter({
  fiscalYearEnd,
  analystCount,
  lastUpdated
}: TableFooterProps) {
  const isCalYear = fiscalYearEnd ? isCalendarYear(fiscalYearEnd) : false
  const formattedFiscalYearEnd = fiscalYearEnd ? formatFiscalYearEnd(fiscalYearEnd) : null

  return (
    <div className="space-y-2 pt-2">
      {/* Fiscal Year Note */}
      {formattedFiscalYearEnd && (
        <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
          {isCalYear ? (
            <span>
              <strong>Fiscal Year:</strong> Calendar year (ends December 31)
            </span>
          ) : (
            <span>
              <strong>Note:</strong> Fiscal year ends {formattedFiscalYearEnd} (not calendar year)
            </span>
          )}
        </div>
      )}

      {/* Analyst & Update Info */}
      <div className="flex items-center gap-3 text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
        {analystCount !== null && analystCount > 0 && (
          <span>
            Forward estimates based on {analystCount} analyst{analystCount !== 1 ? 's' : ''}
          </span>
        )}
        {lastUpdated && (
          <>
            {analystCount !== null && analystCount > 0 && (
              <span style={{ color: 'var(--text-tertiary)' }}>·</span>
            )}
            <span>
              Updated {formatDate(lastUpdated)}
            </span>
          </>
        )}
      </div>

      {/* Data Source Note */}
      <div className="text-xs italic transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
        Historical data from income statements and cash flows. Forward estimates from analyst consensus.
      </div>
    </div>
  )
}
