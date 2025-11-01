import React from 'react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'

interface PositionSectionHeaderProps {
  title: string
  count: number
}

export function PositionSectionHeader({ title, count }: PositionSectionHeaderProps) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <h3 className="font-semibold transition-colors duration-300" style={{
        fontSize: 'var(--text-lg)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-display)'
      }}>
        {title}
      </h3>
      <Badge variant="secondary" className="transition-colors duration-300" style={{
        backgroundColor: 'var(--bg-secondary)',
        color: 'var(--text-primary)'
      }}>
        {count}
      </Badge>
    </div>
  )
}
