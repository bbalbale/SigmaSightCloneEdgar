'use client'

import { useTheme } from '@/contexts/ThemeContext'
import { themes } from '@/lib/themes'
import { useState, useEffect } from 'react'

export function ThemeSelector() {
  const { currentTheme, setTheme, themeConfig, cycleTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)

  // Keyboard shortcut: Press 'T' to cycle themes
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === 't' &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA'
      ) {
        cycleTheme()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [cycleTheme])

  // Get the other theme (for 2-theme toggle)
  const otherTheme = currentTheme === 'bloomberg-classic' ? 'modern-premium' : 'bloomberg-classic'
  const otherThemeConfig = themes[otherTheme]

  return (
    <div className="fixed bottom-6 right-6 z-theme-selector">
      {/* Theme Options Panel */}
      {isOpen && (
        <div
          className="absolute bottom-16 right-0 rounded-lg overflow-hidden"
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            boxShadow: 'var(--shadow-lg)',
            minWidth: '320px',
          }}
        >
          {/* Header */}
          <div
            className="px-4 py-3"
            style={{
              borderBottom: '1px solid var(--border-primary)',
              background: 'var(--bg-tertiary)',
            }}
          >
            <h3
              className="font-semibold uppercase"
              style={{
                fontSize: 'var(--text-xs)',
                letterSpacing: 'var(--tracking-wide)',
                color: 'var(--text-secondary)',
              }}
            >
              Visual Themes
            </h3>
          </div>

          {/* Current Theme */}
          <div className="p-3" style={{ background: 'var(--bg-primary)' }}>
            <div
              className="mb-1"
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: 'var(--tracking-wide)',
              }}
            >
              Active
            </div>
            <div className="p-3 rounded" style={{ background: 'var(--color-accent-subtle)', border: '2px solid var(--color-accent)' }}>
              <div
                className="font-semibold"
                style={{
                  fontSize: 'var(--text-base)',
                  color: 'var(--text-primary)',
                  marginBottom: '4px',
                }}
              >
                {themeConfig.name}
              </div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)',
                }}
              >
                {themeConfig.description}
              </div>

              {/* Color Preview */}
              <div className="flex gap-1 mt-3">
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: themeConfig.colors.bgSecondary, border: '1px solid var(--border-primary)' }}
                  title="Background"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: themeConfig.colors.accent }}
                  title="Accent"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: themeConfig.colors.success }}
                  title="Success"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: themeConfig.colors.error }}
                  title="Error"
                />
              </div>
            </div>
          </div>

          {/* Switch to Other Theme */}
          <div className="p-3">
            <button
              onClick={() => {
                setTheme(otherTheme)
                setIsOpen(false)
              }}
              className="w-full text-left p-3 rounded transition-all"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-elevated)'
                e.currentTarget.style.borderColor = 'var(--color-accent)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--bg-tertiary)'
                e.currentTarget.style.borderColor = 'var(--border-primary)'
              }}
            >
              <div
                className="mb-1"
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  letterSpacing: 'var(--tracking-wide)',
                }}
              >
                Switch to
              </div>
              <div
                className="font-semibold"
                style={{
                  fontSize: 'var(--text-base)',
                  color: 'var(--text-primary)',
                  marginBottom: '4px',
                }}
              >
                {otherThemeConfig.name}
              </div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)',
                }}
              >
                {otherThemeConfig.description}
              </div>

              {/* Color Preview */}
              <div className="flex gap-1 mt-3">
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: otherThemeConfig.colors.bgSecondary, border: '1px solid rgba(255,255,255,0.1)' }}
                  title="Background"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: otherThemeConfig.colors.accent }}
                  title="Accent"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: otherThemeConfig.colors.success }}
                  title="Success"
                />
                <div
                  className="w-8 h-8 rounded"
                  style={{ background: otherThemeConfig.colors.error }}
                  title="Error"
                />
              </div>
            </button>
          </div>

          {/* Footer Tip */}
          <div
            className="px-4 py-2 text-center"
            style={{
              borderTop: '1px solid var(--border-primary)',
              background: 'var(--bg-primary)',
            }}
          >
            <p
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-tertiary)',
              }}
            >
              Press <kbd className="px-1 py-0.5 rounded" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>T</kbd> to toggle • Click button to switch
            </p>
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={() => {
          // Single click toggles theme directly
          cycleTheme()
        }}
        onContextMenu={(e) => {
          // Right-click opens the panel
          e.preventDefault()
          setIsOpen(!isOpen)
        }}
        className="rounded-full transition-all"
        style={{
          width: '56px',
          height: '56px',
          background: 'var(--color-accent)',
          color: 'white',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--color-accent-hover)'
          e.currentTarget.style.transform = 'scale(1.05)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'var(--color-accent)'
          e.currentTarget.style.transform = 'scale(1)'
        }}
        title={`${themeConfig.name} (click to toggle, right-click for details)`}
      >
        🎨
      </button>
    </div>
  )
}
