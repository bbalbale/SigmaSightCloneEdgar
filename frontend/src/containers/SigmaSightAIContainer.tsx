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
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column: AI Insights */}
            <div className="space-y-4">
              <div className="mb-4">
                <h2 className="text-xl font-semibold transition-colors duration-300" style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>
                  Generated Insights
                </h2>
                <p className="text-sm mt-1 transition-colors duration-300 text-secondary">
                  Pre-generated portfolio analysis cards
                </p>
              </div>
              <AIInsightsRow
                insights={insights}
                loading={loading}
                onGenerateInsight={handleGenerateInsight}
                onDismissInsight={handleDismissInsight}
                generatingInsight={generatingInsight}
              />
            </div>

            {/* Right Column: Claude Chat */}
            <div className="space-y-4">
              <div className="mb-4">
                <h2 className="text-xl font-semibold transition-colors duration-300" style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>
                  Ask SigmaSight AI
                </h2>
                <p className="text-sm mt-1 transition-colors duration-300 text-secondary">
                  Chat with SigmaSight AI about your portfolio using real-time analytics
                </p>
              </div>
              <ClaudeChatInterface />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
