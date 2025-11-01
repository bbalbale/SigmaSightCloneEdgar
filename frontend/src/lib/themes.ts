/**
 * Theme System - Multiple Visual Presets
 *
 * Each theme includes:
 * - Color palette (backgrounds, accents, text)
 * - Typography scale (keeping smaller fonts for density)
 * - Shadows/borders style
 * - Spacing adjustments
 */

export type ThemePreset = 'bloomberg-classic' | 'modern-premium'

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

    // Semantic
    success: string
    error: string
    warning: string
    info: string

    // Accents
    accent: string
    accentHover: string
    accentSubtle: string
  }

  // Typography (keeping smaller for density)
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
    borderStyle: 'borders' | 'shadows' | 'hybrid'
    shadowSm: string
    shadowMd: string
    shadowLg: string
    cardPadding: string
  }
}

export const themes: Record<ThemePreset, Theme> = {
  'bloomberg-classic': {
    name: 'Bloomberg Classic',
    description: 'High density, familiar blue, borders (power user style)',

    colors: {
      bgPrimary: '#020617',
      bgSecondary: '#0f172a',
      bgTertiary: '#1e293b',
      bgElevated: '#1e293b',

      borderPrimary: '#334155',
      borderSecondary: '#475569',
      borderAccent: '#2563eb',

      textPrimary: '#f8fafc',
      textSecondary: '#94a3b8',
      textTertiary: '#64748b',

      success: '#34d399',
      error: '#f87171',
      warning: '#fbbf24',
      info: '#60a5fa',

      accent: '#2563eb',
      accentHover: '#1d4ed8',
      accentSubtle: 'rgba(37, 99, 235, 0.1)',
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
      borderRadius: '0.5rem',
      borderStyle: 'borders',
      shadowSm: 'none',
      shadowMd: 'none',
      shadowLg: 'none',
      cardPadding: '1rem',    // 16px - compact
    },
  },

  'modern-premium': {
    name: 'Modern Premium',
    description: 'Stripe-inspired, generous spacing, soft shadows (for focused analysis)',

    colors: {
      bgPrimary: '#0A0E27',
      bgSecondary: '#161B33',
      bgTertiary: '#1F2544',
      bgElevated: '#252B4A',

      borderPrimary: '#2D3149',
      borderSecondary: '#3A3F5C',
      borderAccent: '#635BFF',

      textPrimary: '#F7F7F8',
      textSecondary: '#A5A6B0',
      textTertiary: '#7A7B88',

      success: '#00D9B1',
      error: '#FF5C5C',
      warning: '#FFB800',
      info: '#635BFF',

      accent: '#635BFF',      // Stripe purple
      accentHover: '#7C75FF',
      accentSubtle: 'rgba(99, 91, 255, 0.1)',
    },

    typography: {
      fontDisplay: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      fontBody: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      fontMono: "'JetBrains Mono', 'SF Mono', 'Consolas', monospace",

      textXs: '0.6875rem',    // 11px - same density as Bloomberg
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
      borderRadius: '0.75rem',  // 12px - rounder corners
      borderStyle: 'shadows',   // soft shadows, no borders
      shadowSm: '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.4)',
      shadowMd: '0 4px 6px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.5)',
      shadowLg: '0 10px 15px rgba(0, 0, 0, 0.5), 0 4px 6px rgba(0, 0, 0, 0.6)',
      cardPadding: '1.5rem',    // 24px - generous breathing room
    },
  },
}

export const defaultTheme: ThemePreset = 'bloomberg-classic'
