/**
 * GenerateInsightModal Component
 *
 * Modal dialog for generating new AI insights with:
 * - Insight type selection (6 types)
 * - Optional focus area input
 * - Custom question textarea (for custom type)
 * - Cost and time estimate display
 * - Loading state during generation
 * - Success callback on completion
 */

'use client'

import React, { useState } from 'react'
import { useGenerateInsight } from '@/hooks/useInsights'
import { InsightType } from '@/services/insightsApi'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Loader2 } from 'lucide-react'

interface GenerateInsightModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (insightId: string) => void
}

const insightTypes = [
  {
    value: 'daily_summary' as InsightType,
    label: 'Daily Summary',
    description: 'Comprehensive portfolio review with key metrics and trends'
  },
  {
    value: 'volatility_analysis' as InsightType,
    label: 'Volatility Analysis',
    description: 'Analyze volatility patterns and risk factors'
  },
  {
    value: 'concentration_risk' as InsightType,
    label: 'Concentration Risk',
    description: 'Evaluate concentration and diversification levels'
  },
  {
    value: 'hedge_quality' as InsightType,
    label: 'Hedge Quality',
    description: 'Assess effectiveness of hedging strategies'
  },
  {
    value: 'factor_exposure' as InsightType,
    label: 'Factor Exposure',
    description: 'Review factor exposures and systematic risk'
  },
  {
    value: 'custom' as InsightType,
    label: 'Custom Question',
    description: 'Ask a specific question about your portfolio'
  },
]

export function GenerateInsightModal({
  open,
  onOpenChange,
  onSuccess
}: GenerateInsightModalProps) {
  const [insightType, setInsightType] = useState<InsightType>('daily_summary')
  const [focusArea, setFocusArea] = useState('')
  const [userQuestion, setUserQuestion] = useState('')

  const { generate, generating, error } = useGenerateInsight()

  const handleGenerate = async () => {
    try {
      const result = await generate(
        insightType,
        focusArea || undefined,
        insightType === 'custom' ? userQuestion : undefined
      )

      if (result) {
        // Show success notification
        console.log(`Insight generated! Cost: $${result.performance.cost_usd.toFixed(4)}`)

        // Close modal
        onOpenChange(false)

        // Call success callback
        onSuccess(result.id)

        // Reset form
        setInsightType('daily_summary')
        setFocusArea('')
        setUserQuestion('')
      }
    } catch (error) {
      console.error('Failed to generate insight:', error)
      // Error is already set in the hook
    }
  }

  const selectedType = insightTypes.find(t => t.value === insightType)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>Generate AI Insight</DialogTitle>
          <DialogDescription>
            Claude Sonnet 4 will analyze your portfolio data and provide detailed insights.
            <br />
            <span className="text-xs mt-1 block">
              Cost: ~$0.02 | Time: 25-30 seconds
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Insight Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="insight-type">Analysis Type</Label>
            <Select
              value={insightType}
              onValueChange={(value) => setInsightType(value as InsightType)}
            >
              <SelectTrigger id="insight-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {insightTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="py-1">
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {type.description}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedType && (
              <p className="text-xs text-muted-foreground">
                {selectedType.description}
              </p>
            )}
          </div>

          {/* Focus Area (Optional, not for custom) */}
          {insightType !== 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="focus-area">
                Focus Area <span className="text-muted-foreground text-xs">(optional)</span>
              </Label>
              <Input
                id="focus-area"
                placeholder="e.g., tech exposure, options risk, healthcare sector"
                value={focusArea}
                onChange={(e) => setFocusArea(e.target.value)}
                disabled={generating}
              />
              <p className="text-xs text-muted-foreground">
                Narrow the analysis to a specific area of your portfolio
              </p>
            </div>
          )}

          {/* Custom Question (only for custom type) */}
          {insightType === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="user-question">
                Your Question <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="user-question"
                placeholder="e.g., Why is my portfolio underperforming the market? How can I reduce my exposure to tech volatility?"
                rows={4}
                value={userQuestion}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setUserQuestion(e.target.value)}
                disabled={generating}
              />
              <p className="text-xs text-muted-foreground">
                Ask any question about your portfolio - be specific for better insights
              </p>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error.message || 'Failed to generate insight. Please try again.'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={generating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generating || (insightType === 'custom' && !userQuestion.trim())}
          >
            {generating && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {generating ? 'Generating...' : 'Generate Insight'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
