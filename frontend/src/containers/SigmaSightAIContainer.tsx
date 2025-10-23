/**
 * SigmaSight AI Container
 *
 * Main container for AI-powered portfolio insights feature.
 *
 * Features:
 * - List of AI-generated insights
 * - Generate new insights modal
 * - View insight details modal
 * - Star rating system
 * - Auto-refresh on new insight generation
 */

'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { Button } from '@/components/ui/button'
import { InsightsList, GenerateInsightModal, InsightDetailModal } from '@/components/insights'
import { AIInsight } from '@/services/insightsApi'
import { Plus, Sparkles } from 'lucide-react'

export function SigmaSightAIContainer() {
  const { theme } = useTheme()

  // Modal state
  const [generateModalOpen, setGenerateModalOpen] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)

  // Handler when user clicks on an insight card
  const handleSelectInsight = (insight: AIInsight) => {
    setSelectedInsightId(insight.id)
    setDetailModalOpen(true)
  }

  // Handler when insight generation succeeds
  const handleGenerateSuccess = (insightId: string) => {
    // Automatically open the newly generated insight
    setSelectedInsightId(insightId)
    setDetailModalOpen(true)

    // Note: InsightsList will auto-refresh via its useInsights hook
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Sparkles className={`h-8 w-8 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
                }`} />
                <h1 className={`text-3xl font-bold transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  SigmaSight AI
                </h1>
              </div>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                AI-powered portfolio insights powered by Claude Sonnet 4
              </p>
              <p className={`text-sm mt-1 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
              }`}>
                Cost: ~$0.02 per insight • Time: 25-30 seconds
              </p>
            </div>
            <Button
              onClick={() => setGenerateModalOpen(true)}
              size="lg"
              className="gap-2"
            >
              <Plus className="h-5 w-5" />
              Generate Insight
            </Button>
          </div>
        </div>
      </section>

      {/* Main Content - Insights List */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <InsightsList onSelectInsight={handleSelectInsight} />
        </div>
      </section>

      {/* Generate Insight Modal */}
      <GenerateInsightModal
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        onSuccess={handleGenerateSuccess}
      />

      {/* Insight Detail Modal */}
      <InsightDetailModal
        insightId={selectedInsightId}
        open={detailModalOpen}
        onOpenChange={setDetailModalOpen}
      />
    </div>
  )
}
