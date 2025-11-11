import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'

interface PositionListProps<T> {
  items: T[]
  renderItem: (item: T, index: number) => React.ReactNode
  emptyMessage?: string
}

export function PositionList<T>({
  items,
  renderItem,
  emptyMessage = 'No positions'
}: PositionListProps<T>) {
  if (items.length === 0) {
    return (
      <div className="p-3 rounded-lg transition-colors duration-300" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--text-secondary)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-primary)'
      }}>
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map(renderItem)}
    </div>
  )
}
