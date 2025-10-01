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
  const { theme } = useTheme()

  if (items.length === 0) {
    return (
      <div className={`text-sm p-3 rounded-lg border ${
        theme === 'dark'
          ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
          : 'text-empty-text bg-empty-bg border-empty-border'
      }`}>
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
