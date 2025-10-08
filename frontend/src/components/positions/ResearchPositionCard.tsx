// src/components/positions/ResearchPositionCard.tsx
'use client'

import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { TagBadge } from '@/components/organize/TagBadge'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'
import type { EnhancedPosition } from '@/services/positionResearchService'

interface ResearchPositionCardProps {
  position: EnhancedPosition
  onClick?: () => void
}

export function ResearchPositionCard({ position, onClick }: ResearchPositionCardProps) {
  const { theme } = useTheme()

  return (
    <div className="space-y-3">
      {/* Main Position Card */}
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={position.company_name || position.symbol}
        primaryValue={formatCurrency(position.market_value)}
        secondaryValue={`${formatNumber(position.percent_of_equity, 1)}% of portfolio`}
        secondaryValueColor="neutral"
        onClick={onClick}
      />

      {/* Tags Row */}
      {position.tags && position.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {position.tags.map(tag => (
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      )}

      {/* Research Data - Compact Grid */}
      <div className={`text-xs space-y-1.5 px-2 py-2 rounded-md transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800/50' : 'bg-gray-50'
      }`}>
        {/* Sector & Industry */}
        {(position.sector || position.industry) && (
          <div className={`flex justify-between transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            <span className="font-medium">Sector:</span>
            <span>{position.sector || '-'} • {position.industry || '-'}</span>
          </div>
        )}

        {/* Price & Targets */}
        <div className={`space-y-1 transition-colors duration-300 ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
          <div className="flex justify-between">
            <span className="font-medium">Current:</span>
            <span>{formatCurrency(position.current_price)}</span>
          </div>
          {position.user_target_eoy && (
            <div className="flex justify-between">
              <span className="font-medium">Target EOY:</span>
              <span className={position.target_return_eoy && position.target_return_eoy >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatCurrency(position.user_target_eoy)} ({position.target_return_eoy ? `${position.target_return_eoy >= 0 ? '+' : ''}${formatNumber(position.target_return_eoy, 1)}%` : '-'})
              </span>
            </div>
          )}
          {position.user_target_next_year && (
            <div className="flex justify-between">
              <span className="font-medium">Target Next Yr:</span>
              <span className={position.target_return_next_year && position.target_return_next_year >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatCurrency(position.user_target_next_year)} ({position.target_return_next_year ? `${position.target_return_next_year >= 0 ? '+' : ''}${formatNumber(position.target_return_next_year, 1)}%` : '-'})
              </span>
            </div>
          )}
          {position.target_mean_price && (
            <div className="flex justify-between">
              <span className="font-medium">Analyst Target:</span>
              <span>{formatCurrency(position.target_mean_price)}</span>
            </div>
          )}
        </div>

        {/* EPS & Revenue */}
        {(position.current_year_earnings_avg || position.next_year_earnings_avg) && (
          <div className={`space-y-1 pt-1 border-t transition-colors duration-300 ${
            theme === 'dark' ? 'border-slate-700 text-slate-400' : 'border-gray-200 text-gray-600'
          }`}>
            {position.current_year_earnings_avg && (
              <div className="flex justify-between">
                <span className="font-medium">EPS This Yr:</span>
                <span>{formatCurrency(position.current_year_earnings_avg)}</span>
              </div>
            )}
            {position.next_year_earnings_avg && (
              <div className="flex justify-between">
                <span className="font-medium">EPS Next Yr:</span>
                <span>{formatCurrency(position.next_year_earnings_avg)}</span>
              </div>
            )}
            {position.current_year_revenue_avg && (
              <div className="flex justify-between">
                <span className="font-medium">Rev This Yr:</span>
                <span>${(position.current_year_revenue_avg / 1e9).toFixed(2)}B</span>
              </div>
            )}
            {position.next_year_revenue_avg && (
              <div className="flex justify-between">
                <span className="font-medium">Rev Next Yr:</span>
                <span>${(position.next_year_revenue_avg / 1e9).toFixed(2)}B</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
