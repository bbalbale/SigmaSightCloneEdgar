'use client'

import { useTheme } from '@/contexts/ThemeContext'
import { ReactNode, CSSProperties } from 'react'

interface ThemedCardProps {
  children: ReactNode
  className?: string
  style?: CSSProperties
  hover?: boolean
}

/**
 * Theme-aware card component that automatically adapts:
 * - Padding (16px Bloomberg, 24px Modern Premium)
 * - Border radius (8px Bloomberg, 12px Modern Premium)
 * - Borders (Bloomberg) vs Shadows (Modern Premium)
 */
export function ThemedCard({ children, className = '', style = {}, hover = false }: ThemedCardProps) {
  const cardStyle: CSSProperties = {
    padding: 'var(--card-padding)',
    borderRadius: 'var(--border-radius)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    transition: 'all 0.2s ease',
    ...style,
  }

  const hoverStyle = hover ? {
    onMouseEnter: (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'
      e.currentTarget.style.borderColor = 'var(--border-accent)'
    },
    onMouseLeave: (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'
      e.currentTarget.style.borderColor = 'var(--border-primary)'
    },
  } : {}

  return (
    <div
      className={className}
      style={cardStyle}
      {...hoverStyle}
    >
      {children}
    </div>
  )
}

/**
 * Lightweight wrapper - just padding and radius (no borders/shadows)
 * Use when the component handles its own background/borders
 */
export function ThemedBox({ children, className = '', style = {} }: ThemedCardProps) {
  return (
    <div
      className={className}
      style={{
        padding: 'var(--card-padding)',
        borderRadius: 'var(--border-radius)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}
