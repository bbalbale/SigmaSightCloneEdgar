'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { themes, defaultTheme, type ThemePreset, type Theme } from '@/lib/themes'

interface ThemeContextType {
  // New API (for theme system)
  currentTheme: ThemePreset
  themeConfig: Theme  // The full theme object
  setTheme: (preset: ThemePreset) => void
  cycleTheme: () => void

  // Legacy API (for backward compatibility with existing components)
  // Old components expect theme to be 'dark' | 'light' string
  theme: 'dark' | 'light'  // Always 'dark' since all themes are dark mode
  toggleTheme: () => void  // Maps to cycleTheme
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<ThemePreset>(defaultTheme)

  // Load theme from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('sigmasight-theme') as ThemePreset
    if (stored && themes[stored]) {
      setCurrentTheme(stored)
    }
  }, [])

  // Apply theme CSS variables when theme changes
  useEffect(() => {
    const theme = themes[currentTheme]
    const root = document.documentElement

    // Apply our custom theme variables
    root.style.setProperty('--bg-primary', theme.colors.bgPrimary)
    root.style.setProperty('--bg-secondary', theme.colors.bgSecondary)
    root.style.setProperty('--bg-tertiary', theme.colors.bgTertiary)
    root.style.setProperty('--bg-elevated', theme.colors.bgElevated)

    root.style.setProperty('--border-primary', theme.colors.borderPrimary)
    root.style.setProperty('--border-secondary', theme.colors.borderSecondary)
    root.style.setProperty('--border-accent', theme.colors.borderAccent)

    root.style.setProperty('--text-primary', theme.colors.textPrimary)
    root.style.setProperty('--text-secondary', theme.colors.textSecondary)
    root.style.setProperty('--text-tertiary', theme.colors.textTertiary)

    root.style.setProperty('--color-success', theme.colors.success)
    root.style.setProperty('--color-error', theme.colors.error)
    root.style.setProperty('--color-warning', theme.colors.warning)
    root.style.setProperty('--color-info', theme.colors.info)

    root.style.setProperty('--color-accent', theme.colors.accent)
    root.style.setProperty('--color-accent-hover', theme.colors.accentHover)
    root.style.setProperty('--color-accent-subtle', theme.colors.accentSubtle)

    // IMPORTANT: Also update shadcn/ui variables so dropdowns work
    // Convert hex to HSL for shadcn (it expects HSL format)
    root.style.setProperty('--background', theme.colors.bgPrimary)
    root.style.setProperty('--foreground', theme.colors.textPrimary)
    root.style.setProperty('--card', theme.colors.bgSecondary)
    root.style.setProperty('--card-foreground', theme.colors.textPrimary)
    root.style.setProperty('--popover', theme.colors.bgElevated)
    root.style.setProperty('--popover-foreground', theme.colors.textPrimary)
    root.style.setProperty('--muted', theme.colors.bgTertiary)
    root.style.setProperty('--muted-foreground', theme.colors.textSecondary)
    root.style.setProperty('--border', theme.colors.borderPrimary)
    root.style.setProperty('--input', theme.colors.borderPrimary)
    root.style.setProperty('--ring', theme.colors.accent)

    // Add dark class to html element for shadcn components
    root.classList.add('dark')
    root.classList.remove('light')

    // Apply typography variables
    root.style.setProperty('--font-display', theme.typography.fontDisplay)
    root.style.setProperty('--font-body', theme.typography.fontBody)
    root.style.setProperty('--font-mono', theme.typography.fontMono)

    root.style.setProperty('--text-xs', theme.typography.textXs)
    root.style.setProperty('--text-sm', theme.typography.textSm)
    root.style.setProperty('--text-base', theme.typography.textBase)
    root.style.setProperty('--text-lg', theme.typography.textLg)
    root.style.setProperty('--text-xl', theme.typography.textXl)
    root.style.setProperty('--text-2xl', theme.typography.text2xl)
    root.style.setProperty('--text-3xl', theme.typography.text3xl)

    root.style.setProperty('--tracking-tight', theme.typography.trackingTight)
    root.style.setProperty('--tracking-normal', theme.typography.trackingNormal)
    root.style.setProperty('--tracking-wide', theme.typography.trackingWide)

    // Apply visual variables
    root.style.setProperty('--border-radius', theme.visual.borderRadius)
    root.style.setProperty('--shadow-sm', theme.visual.shadowSm)
    root.style.setProperty('--shadow-md', theme.visual.shadowMd)
    root.style.setProperty('--shadow-lg', theme.visual.shadowLg)
    root.style.setProperty('--card-padding', theme.visual.cardPadding)

    // Store in localStorage
    localStorage.setItem('sigmasight-theme', currentTheme)
  }, [currentTheme])

  const setTheme = (preset: ThemePreset) => {
    setCurrentTheme(preset)
  }

  const cycleTheme = () => {
    const presets: ThemePreset[] = ['bloomberg-classic', 'midnight-premium', 'carbon-professional', 'moonlight-elegant']
    const currentIndex = presets.indexOf(currentTheme)
    const nextIndex = (currentIndex + 1) % presets.length
    setCurrentTheme(presets[nextIndex])
  }

  return (
    <ThemeContext.Provider
      value={{
        // New API
        currentTheme,
        themeConfig: themes[currentTheme],
        setTheme,
        cycleTheme,
        // Legacy API (for backward compatibility)
        theme: 'dark',  // All our themes are dark mode
        toggleTheme: cycleTheme,
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
