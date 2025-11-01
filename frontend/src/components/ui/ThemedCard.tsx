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
  const { themeConfig } = useTheme()

  const cardStyle: CSSProperties = {
    padding: 'var(--card-padding)',
    borderRadius: 'var(--border-radius)',
    backgroundColor: 'var(--bg-secondary)',
    // Conditionally apply borders or shadows based on theme
    ...(themeConfig.visual.borderStyle === 'borders' ? {
      border: '1px solid var(--border-primary)',
    } : {
      boxShadow: 'var(--shadow-md)',
    }),
    transition: 'all 0.2s ease',
    ...style,
  }

  const hoverStyle = hover ? {
    onMouseEnter: (e: React.MouseEvent<HTMLDivElement>) => {
      if (themeConfig.visual.borderStyle === 'shadows') {
        e.currentTarget.style.boxShadow = 'var(--shadow-lg)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }
    },
    onMouseLeave: (e: React.MouseEvent<HTMLDivElement>) => {
      if (themeConfig.visual.borderStyle === 'shadows') {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)'
        e.currentTarget.style.transform = 'translateY(0)'
      }
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
