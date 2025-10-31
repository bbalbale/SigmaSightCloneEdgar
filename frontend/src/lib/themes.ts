/**
 * Theme System - Multiple Visual Presets
 *
 * Each theme includes:
 * - Color palette (backgrounds, accents, text)
 * - Typography scale (keeping smaller fonts for density)
 * - Shadows/borders style
 * - Spacing adjustments
 */

export type ThemePreset = 'bloomberg-classic' | 'midnight-premium' | 'carbon-professional' | 'moonlight-elegant'

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
    description: 'High density, familiar blue, borders (current style)',

    colors: {
      bgPrimary: '#020617',
      bgSecondary: '#0f172a',
      bgTertiary: '#1e293b',
      bgElevated: '#0f172a',

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
      cardPadding: '1rem',
    },
  },

  'midnight-premium': {
    name: 'Midnight Premium',
    description: 'Modern navy, purple accent, soft shadows (2025 style)',

    colors: {
      bgPrimary: '#0A0E27',
      bgSecondary: '#161B33',
      bgTertiary: '#1F2544',
      bgElevated: '#161B33',

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

      accent: '#635BFF',
      accentHover: '#7C75FF',
      accentSubtle: 'rgba(99, 91, 255, 0.1)',
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
      borderRadius: '0.75rem',
      borderStyle: 'shadows',
      shadowSm: '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.4)',
      shadowMd: '0 4px 6px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.5)',
      shadowLg: '0 10px 15px rgba(0, 0, 0, 0.5), 0 4px 6px rgba(0, 0, 0, 0.6)',
      cardPadding: '1.25rem',
    },
  },

  'carbon-professional': {
    name: 'Carbon Professional',
    description: 'IBM-inspired, clean, high contrast (corporate)',

    colors: {
      bgPrimary: '#161616',
      bgSecondary: '#262626',
      bgTertiary: '#393939',
      bgElevated: '#262626',

      borderPrimary: '#393939',
      borderSecondary: '#525252',
      borderAccent: '#0F62FE',

      textPrimary: '#F4F4F4',
      textSecondary: '#C6C6C6',
      textTertiary: '#8D8D8D',

      success: '#24A148',
      error: '#DA1E28',
      warning: '#F1C21B',
      info: '#0F62FE',

      accent: '#0F62FE',
      accentHover: '#0353E9',
      accentSubtle: 'rgba(15, 98, 254, 0.1)',
    },

    typography: {
      fontDisplay: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      fontBody: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      fontMono: "'IBM Plex Mono', 'JetBrains Mono', monospace",

      textXs: '0.6875rem',    // 11px
      textSm: '0.8125rem',    // 13px
      textBase: '0.875rem',   // 14px
      textLg: '1rem',         // 16px
      textXl: '1.125rem',     // 18px
      text2xl: '1.375rem',    // 22px
      text3xl: '1.75rem',     // 28px

      trackingTight: '-0.01em',
      trackingNormal: '0',
      trackingWide: '0.04em',
    },

    visual: {
      borderRadius: '0.25rem',
      borderStyle: 'hybrid',
      shadowSm: '0 1px 2px rgba(0, 0, 0, 0.5)',
      shadowMd: '0 2px 4px rgba(0, 0, 0, 0.6)',
      shadowLg: '0 4px 8px rgba(0, 0, 0, 0.7)',
      cardPadding: '1rem',
    },
  },

  'moonlight-elegant': {
    name: 'Moonlight Elegant',
    description: 'Deep purple-black, coral accent, easiest on eyes (night mode)',

    colors: {
      bgPrimary: '#1A1A2E',
      bgSecondary: '#16213E',
      bgTertiary: '#0F3460',
      bgElevated: '#16213E',

      borderPrimary: '#2A3A5C',
      borderSecondary: '#3A4A6C',
      borderAccent: '#E94560',

      textPrimary: '#F0F0F5',
      textSecondary: '#B8B8C8',
      textTertiary: '#8888A8',

      success: '#52D4A8',
      error: '#E94560',
      warning: '#FFB84D',
      info: '#5C8EE6',

      accent: '#E94560',
      accentHover: '#FF5A75',
      accentSubtle: 'rgba(233, 69, 96, 0.1)',
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

      trackingTight: '-0.015em',
      trackingNormal: '0',
      trackingWide: '0.05em',
    },

    visual: {
      borderRadius: '0.875rem',
      borderStyle: 'shadows',
      shadowSm: '0 2px 4px rgba(0, 0, 0, 0.4)',
      shadowMd: '0 4px 8px rgba(0, 0, 0, 0.5)',
      shadowLg: '0 8px 16px rgba(0, 0, 0, 0.6)',
      cardPadding: '1.25rem',
    },
  },
}

export const defaultTheme: ThemePreset = 'bloomberg-classic'
