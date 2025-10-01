import React from 'react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'

interface PositionSectionHeaderProps {
  title: string
  count: number
}

export function PositionSectionHeader({ title, count }: PositionSectionHeaderProps) {
  const { theme } = useTheme()

  return (
    <div className="flex items-center gap-2 mb-4">
      <h3 className={`text-lg font-semibold transition-colors duration-300 ${
        theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
      }`}>
        {title}
      </h3>
      <Badge variant="secondary" className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-badge-bg-dark text-badge-text-dark' : 'bg-badge-bg text-badge-text'
      }`}>
        {count}
      </Badge>
    </div>
  )
}
