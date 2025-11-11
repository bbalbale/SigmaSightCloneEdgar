/**
 * Bloomberg Terminal Theme System
 *
 * Single theme with light/dark mode support
 * Colors match Bloomberg Terminal aesthetic
 */

export type ThemeMode = 'light' | 'dark'

export interface Theme {
  name: string
  description: string

  // Colors
  colors: {
    // Backgrounds
    bgPrimary: string
    bgSecondary: string
    bgTertiary: string
    bgElevated: string

    // Borders
    borderPrimary: string
    borderSecondary: string
    borderAccent: string

    // Text
    textPrimary: string
    textSecondary: string
    textTertiary: string

    // Semantic (Bloomberg style)
    success: string      // Green for gains
    error: string        // Red for losses
    warning: string      // Orange for warnings
    info: string         // Blue for info

    // Bloomberg accent (orange)
    accent: string
    accentHover: string
    accentSubtle: string
  }

  // Typography (Bloomberg terminal density)
  typography: {
    fontDisplay: string
    fontBody: string
    fontMono: string

    // Sizes (intentionally small for data density)
    textXs: string      // 11px - tertiary info
    textSm: string      // 13px - table cells
    textBase: string    // 14px - body text
    textLg: string      // 16px - section headers
    textXl: string      // 18px - card labels
    text2xl: string     // 22px - hero values
    text3xl: string     // 28px - page titles

    // Letter spacing
    trackingTight: string
    trackingNormal: string
    trackingWide: string
  }

  // Visual style
  visual: {
    borderRadius: string
    cardPadding: string
    cardGap: string      // Gap between cards
  }
}

// Bloomberg theme - Dark mode
const bloombergDark: Theme = {
  name: 'Bloomberg Dark',
  description: 'Bloomberg Terminal dark mode with orange accents',

  colors: {
    bgPrimary: '#000000',           // Pure black (Bloomberg style)
    bgSecondary: '#0a0a0a',         // Slightly lighter black for cards
    bgTertiary: '#1a1a1a',          // Card hover/elevated
    bgElevated: '#1a1a1a',

    borderPrimary: '#333333',       // Subtle borders
    borderSecondary: '#404040',
    borderAccent: '#ff8c00',        // Bloomberg orange

    textPrimary: '#ffffff',         // Pure white text
    textSecondary: '#b0b0b0',       // Gray secondary text
    textTertiary: '#808080',        // Darker gray tertiary

    success: '#00ff00',             // Bloomberg green (gains)
    error: '#ff0000',               // Bloomberg red (losses)
    warning: '#ff8c00',             // Bloomberg orange
    info: '#00bfff',                // Bloomberg blue

    accent: '#ff8c00',              // Bloomberg orange
    accentHover: '#ffa500',         // Lighter orange on hover
    accentSubtle: 'rgba(255, 140, 0, 0.1)',
  },

  typography: {
    fontDisplay: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontBody: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontMono: "'JetBrains Mono', 'SF Mono', 'Consolas', monospace",

    textXs: '0.6875rem',    // 11px
    textSm: '0.8125rem',    // 13px
    textBase: '0.875rem',   // 14px
    textLg: '1rem',         // 16px
    textXl: '1.125rem',     // 18px
    text2xl: '1.375rem',    // 22px
    text3xl: '1.75rem',     // 28px

    trackingTight: '-0.02em',
    trackingNormal: '0',
    trackingWide: '0.05em',
  },

  visual: {
    borderRadius: '0.375rem',  // 6px - subtle rounding
    cardPadding: '1rem',       // 16px - compact
    cardGap: '1rem',           // 16px gap between cards
  },
}

// Bloomberg theme - Light mode
const bloombergLight: Theme = {
  name: 'Bloomberg Light',
  description: 'Bloomberg Terminal light mode with orange accents',

  colors: {
    bgPrimary: '#ffffff',           // White background
    bgSecondary: '#f5f5f5',         // Light gray for cards
    bgTertiary: '#e8e8e8',          // Card hover
    bgElevated: '#e8e8e8',

    borderPrimary: '#d0d0d0',       // Light borders
    borderSecondary: '#b0b0b0',
    borderAccent: '#ff8c00',        // Bloomberg orange

    textPrimary: '#000000',         // Black text
    textSecondary: '#4a4a4a',       // Dark gray secondary
    textTertiary: '#808080',        // Gray tertiary

    success: '#008000',             // Dark green (gains)
    error: '#cc0000',               // Dark red (losses)
    warning: '#ff8c00',             // Bloomberg orange
    info: '#0080ff',                // Blue

    accent: '#ff8c00',              // Bloomberg orange
    accentHover: '#ff7700',         // Darker orange on hover
    accentSubtle: 'rgba(255, 140, 0, 0.1)',
  },

  typography: {
    fontDisplay: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontBody: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontMono: "'JetBrains Mono', 'SF Mono', 'Consolas', monospace",

    textXs: '0.6875rem',    // 11px
    textSm: '0.8125rem',    // 13px
    textBase: '0.875rem',   // 14px
    textLg: '1rem',         // 16px
    textXl: '1.125rem',     // 18px
    text2xl: '1.375rem',    // 22px
    text3xl: '1.75rem',     // 28px

    trackingTight: '-0.02em',
    trackingNormal: '0',
    trackingWide: '0.05em',
  },

  visual: {
    borderRadius: '0.375rem',  // 6px - subtle rounding
    cardPadding: '1rem',       // 16px - compact
    cardGap: '1rem',           // 16px gap between cards
  },
}

export const themes: Record<ThemeMode, Theme> = {
  dark: bloombergDark,
  light: bloombergLight,
}

export const defaultTheme: ThemeMode = 'dark'
