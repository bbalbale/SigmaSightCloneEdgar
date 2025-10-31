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
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div className={`rounded-lg border p-8 text-center transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-900 border-slate-700'
                : 'bg-white border-slate-200'
            }`}>
              <h2 className={`text-xl font-semibold mb-2 ${
                theme === 'dark' ? 'text-slate-50' : 'text-slate-900'
              }`}>
                Error Loading Insights
              </h2>
              <p className={`text-sm ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
              }`}>
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className={`px-4 py-8 border-b transition-colors duration-300 ${
        theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className={`h-8 w-8 transition-colors duration-300 ${
              theme === 'dark' ? 'text-orange-400' : 'text-orange-600'
            }`} />
            <h1 className={`text-3xl font-bold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              AI Insights
            </h1>
          </div>
          <p className={`text-lg transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            AI-powered analysis of your portfolio
          </p>
          <p className={`text-sm mt-1 transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
          }`}>
            Generation time: ~25 seconds • Limit: 10 per day
          </p>
        </div>
      </section>

      {/* Insights Display */}
      <section className="pt-8">
        <AIInsightsRow
          insights={insights}
          loading={loading}
          onGenerateInsight={handleGenerateInsight}
          onDismissInsight={handleDismissInsight}
          generatingInsight={generatingInsight}
        />
      </section>
    </div>
  )
}
