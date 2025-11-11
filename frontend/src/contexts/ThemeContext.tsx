'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { themes, defaultTheme, type ThemeMode, type Theme } from '@/lib/themes'

interface ThemeContextType {
  theme: ThemeMode  // 'light' | 'dark'
  themeConfig: Theme  // The full theme object
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

// Helper function to convert hex to HSL format for Tailwind/ShadCN
function hexToHSL(hex: string): string {
  // Remove # if present
  hex = hex.replace('#', '')

  // Convert to RGB
  const r = parseInt(hex.substring(0, 2), 16) / 255
  const g = parseInt(hex.substring(2, 4), 16) / 255
  const b = parseInt(hex.substring(4, 6), 16) / 255

  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0, s = 0, l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)

    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }

  h = Math.round(h * 360)
  s = Math.round(s * 100)
  l = Math.round(l * 100)

  // Return in Tailwind format: "h s% l%"
  return `${h} ${s}% ${l}%`
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>(defaultTheme)

  // Load theme from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('sigmasight-theme-mode') as ThemeMode
    if (stored && (stored === 'light' || stored === 'dark')) {
      setTheme(stored)
    }
  }, [])

  // Apply theme CSS variables when theme changes
  useEffect(() => {
    const themeConfig = themes[theme]
    const root = document.documentElement

    // Apply our custom theme variables
    root.style.setProperty('--bg-primary', themeConfig.colors.bgPrimary)
    root.style.setProperty('--bg-secondary', themeConfig.colors.bgSecondary)
    root.style.setProperty('--bg-tertiary', themeConfig.colors.bgTertiary)
    root.style.setProperty('--bg-elevated', themeConfig.colors.bgElevated)

    root.style.setProperty('--border-primary', themeConfig.colors.borderPrimary)
    root.style.setProperty('--border-secondary', themeConfig.colors.borderSecondary)
    root.style.setProperty('--border-accent', themeConfig.colors.borderAccent)

    root.style.setProperty('--text-primary', themeConfig.colors.textPrimary)
    root.style.setProperty('--text-secondary', themeConfig.colors.textSecondary)
    root.style.setProperty('--text-tertiary', themeConfig.colors.textTertiary)

    root.style.setProperty('--color-success', themeConfig.colors.success)
    root.style.setProperty('--color-error', themeConfig.colors.error)
    root.style.setProperty('--color-warning', themeConfig.colors.warning)
    root.style.setProperty('--color-info', themeConfig.colors.info)

    root.style.setProperty('--color-accent', themeConfig.colors.accent)
    root.style.setProperty('--color-accent-hover', themeConfig.colors.accentHover)
    root.style.setProperty('--color-accent-subtle', themeConfig.colors.accentSubtle)

    // IMPORTANT: Also update shadcn/ui variables so dropdowns work
    // Convert hex colors to HSL format for Tailwind compatibility
    root.style.setProperty('--background', hexToHSL(themeConfig.colors.bgPrimary))
    root.style.setProperty('--foreground', hexToHSL(themeConfig.colors.textPrimary))
    root.style.setProperty('--card', hexToHSL(themeConfig.colors.bgSecondary))
    root.style.setProperty('--card-foreground', hexToHSL(themeConfig.colors.textPrimary))
    root.style.setProperty('--popover', hexToHSL(themeConfig.colors.bgElevated))
    root.style.setProperty('--popover-foreground', hexToHSL(themeConfig.colors.textPrimary))
    root.style.setProperty('--muted', hexToHSL(themeConfig.colors.bgTertiary))
    root.style.setProperty('--muted-foreground', hexToHSL(themeConfig.colors.textSecondary))
    root.style.setProperty('--border', hexToHSL(themeConfig.colors.borderPrimary))
    root.style.setProperty('--input', hexToHSL(themeConfig.colors.borderPrimary))
    root.style.setProperty('--ring', hexToHSL(themeConfig.colors.accent))

    // Apply light/dark class to html element
    if (theme === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }

    // Apply typography variables
    root.style.setProperty('--font-display', themeConfig.typography.fontDisplay)
    root.style.setProperty('--font-body', themeConfig.typography.fontBody)
    root.style.setProperty('--font-mono', themeConfig.typography.fontMono)

    root.style.setProperty('--text-xs', themeConfig.typography.textXs)
    root.style.setProperty('--text-sm', themeConfig.typography.textSm)
    root.style.setProperty('--text-base', themeConfig.typography.textBase)
    root.style.setProperty('--text-lg', themeConfig.typography.textLg)
    root.style.setProperty('--text-xl', themeConfig.typography.textXl)
    root.style.setProperty('--text-2xl', themeConfig.typography.text2xl)
    root.style.setProperty('--text-3xl', themeConfig.typography.text3xl)

    root.style.setProperty('--tracking-tight', themeConfig.typography.trackingTight)
    root.style.setProperty('--tracking-normal', themeConfig.typography.trackingNormal)
    root.style.setProperty('--tracking-wide', themeConfig.typography.trackingWide)

    // Apply visual variables
    root.style.setProperty('--border-radius', themeConfig.visual.borderRadius)
    root.style.setProperty('--card-padding', themeConfig.visual.cardPadding)
    root.style.setProperty('--card-gap', themeConfig.visual.cardGap)

    // Store in localStorage
    localStorage.setItem('sigmasight-theme-mode', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        themeConfig: themes[theme],
        toggleTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
