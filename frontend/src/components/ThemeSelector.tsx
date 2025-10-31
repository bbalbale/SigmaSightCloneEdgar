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
            minWidth: '280px',
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
              Choose Theme
            </h3>
          </div>

          {/* Theme Options */}
          <div className="p-2">
            {(Object.keys(themes) as Array<keyof typeof themes>).map((themeKey) => {
              const themeOption = themes[themeKey]
              const isActive = currentTheme === themeKey

              return (
                <button
                  key={themeKey}
                  onClick={() => {
                    setTheme(themeKey)
                    setIsOpen(false)
                  }}
                  className="w-full text-left px-3 py-2 rounded transition-all"
                  style={{
                    background: isActive ? 'var(--color-accent-subtle)' : 'transparent',
                    borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'var(--bg-tertiary)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent'
                    }
                  }}
                >
                  <div
                    className="font-medium"
                    style={{
                      fontSize: 'var(--text-sm)',
                      color: 'var(--text-primary)',
                      marginBottom: '2px',
                    }}
                  >
                    {themeOption.name}
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-tertiary)',
                    }}
                  >
                    {themeOption.description}
                  </div>

                  {/* Color Preview */}
                  <div className="flex gap-1 mt-2">
                    <div
                      className="w-6 h-6 rounded"
                      style={{ background: themeOption.colors.bgSecondary }}
                      title="Background"
                    />
                    <div
                      className="w-6 h-6 rounded"
                      style={{ background: themeOption.colors.accent }}
                      title="Accent"
                    />
                    <div
                      className="w-6 h-6 rounded"
                      style={{ background: themeOption.colors.success }}
                      title="Success"
                    />
                    <div
                      className="w-6 h-6 rounded"
                      style={{ background: themeOption.colors.error }}
                      title="Error"
                    />
                  </div>
                </button>
              )
            })}
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
              Press <kbd className="px-1 py-0.5 rounded" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>T</kbd> to cycle themes
            </p>
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
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
        title={`Current: ${themeConfig.name}`}
      >
        🎨
      </button>
    </div>
  )
}
