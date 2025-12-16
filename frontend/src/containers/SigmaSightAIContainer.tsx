/**
 * SigmaSight AI Container
 *
 * Dedicated page for AI-powered portfolio insights.
 * Uses the new card-based approach with preloading instead of modals.
 */

'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useAIInsights } from '@/hooks/useAIInsights'
import { AIInsightsRow } from '@/components/command-center/AIInsightsRow'
import { CopilotPanel } from '@/components/copilot'
import { Sparkles } from 'lucide-react'
import { InsightType } from '@/services/insightsApi'

export function SigmaSightAIContainer() {
  const { theme } = useTheme()
  const {
    insights,
    loading,
    loadingMore,
    error,
    generatingInsight,
    hasMore,
    total,
    filters,
    handleGenerateInsight,
    handleDismissInsight,
    handleFeedback,
    loadMore,
    updateFilters,
    refetchInsights
  } = useAIInsights()

  const [generationType, setGenerationType] = useState<InsightType>('daily_summary')
  const [focusArea, setFocusArea] = useState('')
  const [prefillMessage, setPrefillMessage] = useState<string | null>(null)

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
                    Portfolio Insights
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={generationType}
                    onChange={(e) => setGenerationType(e.target.value as InsightType)}
                    className="text-sm px-2 py-1 rounded border"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderColor: 'var(--border-primary)',
                      color: 'var(--text-primary)'
                    }}
                  >
                    <option value="daily_summary">Daily summary</option>
                    <option value="volatility_analysis">Volatility analysis</option>
                    <option value="concentration_risk">Concentration risk</option>
                    <option value="stress_test_review">Stress test review</option>
                    <option value="factor_exposure">Factor exposure</option>
                  </select>
                  <button
                    onClick={() => handleGenerateInsight({ insightType: generationType, focusArea: focusArea || undefined })}
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
              </div>
              {/* Filters */}
              <div className="px-4 pt-4 flex flex-wrap gap-3 text-sm" style={{ color: 'var(--text-primary)' }}>
                <div className="flex flex-col gap-1">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Filter type</span>
                  <select
                    value={filters.insightType || 'all'}
                    onChange={(e) => {
                      const value = e.target.value === 'all' ? undefined : e.target.value as InsightType
                      updateFilters({ insightType: value })
                      setGenerationType(value || 'daily_summary')
                    }}
                    className="px-2 py-1 rounded border"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderColor: 'var(--border-primary)',
                      color: 'var(--text-primary)'
                    }}
                  >
                    <option value="all">All</option>
                    <option value="daily_summary">Daily summary</option>
                    <option value="volatility_analysis">Volatility analysis</option>
                    <option value="concentration_risk">Concentration risk</option>
                    <option value="stress_test_review">Stress test review</option>
                    <option value="factor_exposure">Factor exposure</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Timeframe</span>
                  <select
                    value={filters.daysBack}
                    onChange={(e) => updateFilters({ daysBack: Number(e.target.value) })}
                    className="px-2 py-1 rounded border"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderColor: 'var(--border-primary)',
                      color: 'var(--text-primary)'
                    }}
                  >
                    <option value={7}>Last 7 days</option>
                    <option value={30}>Last 30 days</option>
                    <option value={90}>Last 90 days</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1 flex-1 min-w-[200px]">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Focus area (optional)</span>
                  <input
                    value={focusArea}
                    onChange={(e) => setFocusArea(e.target.value)}
                    placeholder="e.g. tech exposure, top movers"
                    className="px-2 py-1 rounded border"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderColor: 'var(--border-primary)',
                      color: 'var(--text-primary)'
                    }}
                  />
                </div>
                <div className="flex items-end text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {total ? `${total} insights` : ' '} 
                </div>
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
                  onAskInsight={(insight) => setPrefillMessage(`Can you dive deeper into this insight titled "${insight.title}"?\n\nSummary: ${insight.summary}`)}
                  onFeedback={(insightId, rating) => handleFeedback(insightId, rating === 'up' ? 5 : 1)}
                  hasMore={hasMore}
                  loadingMore={loadingMore}
                  onLoadMore={loadMore}
                />
              </div>
            </div>

            {/* Right Column: AI Chat */}
            <div>
              <CopilotPanel
                variant="inline"
                pageHint="ai-chat"
                route="/sigmasight-ai"
                prefillMessage={prefillMessage || undefined}
                onPrefillConsumed={() => setPrefillMessage(null)}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
