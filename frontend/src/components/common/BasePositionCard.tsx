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
  const { theme } = useTheme()

  // Map semantic color to design token class
  const getSecondaryValueClass = () => {
    if (secondaryValueColor === 'neutral') return 'text-card-neutral'
    if (secondaryValueColor === 'positive') return 'text-card-positive'
    return 'text-card-negative'
  }

  return (
    <Card
      className={`transition-colors ${onClick ? 'cursor-pointer' : ''} ${
        theme === 'dark'
          ? 'bg-card-bg-dark border-card-border-dark hover:bg-card-bg-hover-dark'
          : 'bg-card-bg border-card-border hover:bg-card-bg-hover'
      }`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <div className={`font-semibold text-sm transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
            }`}>
              {primaryText}
            </div>
            <div className={`text-xs transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
            }`}>
              {secondaryText}
            </div>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
            }`}>
              {primaryValue}
            </div>
            <div className={`text-sm font-medium ${getSecondaryValueClass()}`}>
              {secondaryValue}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
