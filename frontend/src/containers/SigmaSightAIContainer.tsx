/**
 * SigmaSight AI Container
 *
 * Dedicated page for AI-powered portfolio insights.
 * Uses the new card-based approach with preloading instead of modals.
 */

'use client'

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useAIInsights } from '@/hooks/useAIInsights'
import { AIInsightsRow } from '@/components/command-center/AIInsightsRow'
import { ClaudeChatInterface } from '@/components/claude-insights/ClaudeChatInterface'
import { Sparkles } from 'lucide-react'

export function SigmaSightAIContainer() {
  const { theme } = useTheme()
  const {
    insights,
    loading,
    error,
    generatingInsight,
    handleGenerateInsight,
    handleDismissInsight
  } = useAIInsights()

  if (error && !loading) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div className="rounded-lg p-8 text-center transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)'
            }}>
              <h2 className="font-semibold mb-2 transition-colors duration-300" style={{
                fontSize: 'var(--text-xl)',
                color: 'var(--text-primary)'
              }}>
                Error Loading Insights
              </h2>
              <p className="transition-colors duration-300" style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-secondary)'
              }}>
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">
      {/* Page Description */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto">
          <p className="text-sm text-muted-foreground">
            AI-powered analysis of your portfolio
          </p>
        </div>
      </div>

      {/* Split Layout: Insights Left, Chat Right */}
      <section className="px-4 py-8">
        <div className="container mx-auto max-w-7xl">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column: Daily Summary Analysis */}
            <div className="rounded-lg border transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              {/* Header */}
              <div className="p-4 border-b flex items-center justify-between transition-colors duration-300" style={{
                borderColor: 'var(--border-primary)'
              }}>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-semibold" style={{
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-display)'
                  }}>
                    Daily Summary Analysis
                  </h3>
                </div>
                <button
                  onClick={handleGenerateInsight}
                  disabled={generatingInsight}
                  className="text-sm font-semibold px-4 py-2 rounded transition-colors"
                  style={
                    generatingInsight
                      ? {
                          backgroundColor: 'var(--bg-tertiary)',
                          color: 'var(--text-tertiary)',
                          cursor: 'not-allowed',
                        }
                      : {
                          backgroundColor: 'var(--color-accent)',
                          color: '#000000',
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!generatingInsight) {
                      e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!generatingInsight) {
                      e.currentTarget.style.backgroundColor = 'var(--color-accent)';
                    }
                  }}
                >
                  {generatingInsight ? "Generating..." : "Generate"}
                </button>
              </div>
              {/* Content */}
              <div className="p-4 space-y-4 min-h-[700px] max-h-[900px] overflow-y-auto transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-secondary)'
              }}>
                <AIInsightsRow
                  insights={insights}
                  loading={loading}
                  onGenerateInsight={handleGenerateInsight}
                  onDismissInsight={handleDismissInsight}
                  generatingInsight={generatingInsight}
                />
              </div>
            </div>

            {/* Right Column: Claude Chat */}
            <div>
              <ClaudeChatInterface />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
