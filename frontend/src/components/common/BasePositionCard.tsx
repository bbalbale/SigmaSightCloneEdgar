import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

interface BasePositionCardProps {
  primaryText: string
  secondaryText: string
  primaryValue: string
  secondaryValue: string
  secondaryValueColor: 'positive' | 'negative' | 'neutral'
  onClick?: () => void
}

export function BasePositionCard({
  primaryText,
  secondaryText,
  primaryValue,
  secondaryValue,
  secondaryValueColor,
  onClick
}: BasePositionCardProps) {
  // Map semantic color to CSS variable
  const getSecondaryValueColor = () => {
    if (secondaryValueColor === 'neutral') return 'var(--text-primary)'
    if (secondaryValueColor === 'positive') return 'var(--color-success)'
    return 'var(--color-error)'
  }

  return (
    <Card
      className={`transition-all duration-200 ${onClick ? 'cursor-pointer' : ''}`}
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <div className="font-semibold transition-colors duration-300" style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--text-primary)'
            }}>
              {primaryText}
            </div>
            <div className="transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              {secondaryText}
            </div>
          </div>
          <div className="text-right">
            <div className="font-medium transition-colors duration-300" style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--text-primary)'
            }}>
              {primaryValue}
            </div>
            <div className="font-medium" style={{
              fontSize: 'var(--text-sm)',
              color: getSecondaryValueColor()
            }}>
              {secondaryValue}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
