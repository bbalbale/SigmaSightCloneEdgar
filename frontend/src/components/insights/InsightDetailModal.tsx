/**
 * InsightDetailModal Component
 *
 * Full-screen modal displaying complete AI insight with:
 * - Severity badge and metadata
 * - Performance metrics (cost, time, tokens)
 * - Summary section
 * - Key findings list
 * - Detailed analysis (markdown formatted)
 * - Recommendations list
 * - Data limitations notice
 * - Star rating system
 * - Auto-marks as viewed on open
 */

'use client'

import React, { useEffect, useState } from 'react'
import { useInsightDetail, useUpdateInsight, useInsightFeedback } from '@/hooks/useInsights'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Star } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface InsightDetailModalProps {
  insightId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const severityConfig = {
  critical: { label: 'CRITICAL', color: 'bg-red-500 hover:bg-red-600', textColor: 'text-white', icon: '🔴' },
  warning: { label: 'WARNING', color: 'bg-orange-500 hover:bg-orange-600', textColor: 'text-white', icon: '⚠️' },
  elevated: { label: 'ELEVATED', color: 'bg-yellow-500 hover:bg-yellow-600', textColor: 'text-white', icon: '🟡' },
  normal: { label: 'NORMAL', color: 'bg-blue-500 hover:bg-blue-600', textColor: 'text-white', icon: '🔵' },
  info: { label: 'INFO', color: 'bg-gray-500 hover:bg-gray-600', textColor: 'text-white', icon: 'ℹ️' },
}

/**
 * Simple markdown-like text renderer
 * Handles basic formatting without external dependencies
 */
function SimpleMarkdown({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {lines.map((line, idx) => {
        // Headers (##)
        if (line.startsWith('## ')) {
          return (
            <h3 key={idx} className="text-lg font-semibold mt-4 mb-2">
              {line.replace('## ', '')}
            </h3>
          )
        }
        // Headers (#)
        if (line.startsWith('# ')) {
          return (
            <h2 key={idx} className="text-xl font-bold mt-4 mb-2">
              {line.replace('# ', '')}
            </h2>
          )
        }
        // Bold (**text**)
        if (line.includes('**')) {
          const parts = line.split('**')
          return (
            <p key={idx}>
              {parts.map((part, i) => (
                i % 2 === 1 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>
              ))}
            </p>
          )
        }
        // Bullet points (- or *)
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          return (
            <li key={idx} className="ml-4">
              {line.trim().substring(2)}
            </li>
          )
        }
        // Empty line
        if (line.trim() === '') {
          return <div key={idx} className="h-2" />
        }
        // Regular paragraph
        return <p key={idx}>{line}</p>
      })}
    </div>
  )
}

export function InsightDetailModal({
  insightId,
  open,
  onOpenChange
}: InsightDetailModalProps) {
  const { insight, loading, error } = useInsightDetail(insightId)
  const { updateInsight } = useUpdateInsight()
  const { submitFeedback, submitting } = useInsightFeedback()
  const [rating, setRating] = useState(0)

  // Mark as viewed when opened
  useEffect(() => {
    if (insight && !insight.viewed && insightId) {
      updateInsight(insightId, { viewed: true })
        .catch(err => console.error('Failed to mark as viewed:', err))
    }
  }, [insight, insightId, updateInsight])

  // Initialize rating from insight
  useEffect(() => {
    if (insight?.user_rating) {
      setRating(insight.user_rating)
    }
  }, [insight])

  const handleRating = async (newRating: number) => {
    setRating(newRating)
    if (insightId) {
      try {
        await submitFeedback(insightId, newRating)
        console.log(`Rating submitted: ${newRating}/5`)
      } catch (err) {
        console.error('Failed to submit rating:', err)
      }
    }
  }

  // Loading state
  if (loading || !insight) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  // Error state
  if (error) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl">
          <div className="text-center py-8">
            <p className="text-destructive">Failed to load insight details.</p>
            <p className="text-sm text-muted-foreground mt-2">Please try again.</p>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const config = severityConfig[insight.severity]
  const timeAgo = formatDistanceToNow(new Date(insight.created_at), { addSuffix: true })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{config.icon}</span>
            <Badge className={`${config.color} ${config.textColor}`}>
              {config.label}
            </Badge>
            <span className="text-sm text-muted-foreground">{timeAgo}</span>
          </div>
          <DialogTitle className="text-2xl">{insight.title}</DialogTitle>
        </DialogHeader>

        {/* Performance Metrics */}
        <div className="flex items-center gap-6 text-sm text-muted-foreground bg-muted/30 p-3 rounded-md">
          <div className="flex items-center gap-2">
            <span>⚡</span>
            <span>{(insight.performance.generation_time_ms / 1000).toFixed(1)}s</span>
          </div>
          <div className="flex items-center gap-2">
            <span>💰</span>
            <span>${insight.performance.cost_usd.toFixed(4)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span>📊</span>
            <span>{insight.performance.token_count.toLocaleString()} tokens</span>
          </div>
        </div>

        <Separator />

        {/* Summary */}
        <div>
          <h3 className="font-semibold text-lg mb-3">Summary</h3>
          <p className="text-muted-foreground leading-relaxed">{insight.summary}</p>
        </div>

        {/* Key Findings */}
        {insight.key_findings.length > 0 && (
          <div>
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <span>📊</span>
              <span>Key Findings</span>
            </h3>
            <ul className="space-y-3">
              {insight.key_findings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="text-blue-500 font-bold mt-1">•</span>
                  <span className="flex-1">{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <Separator />

        {/* Detailed Analysis */}
        <div>
          <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
            <span>📝</span>
            <span>Detailed Analysis</span>
          </h3>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <SimpleMarkdown content={insight.full_analysis} />
          </div>
        </div>

        {/* Recommendations */}
        {insight.recommendations.length > 0 && (
          <>
            <Separator />
            <div>
              <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                <span>💡</span>
                <span>Recommendations</span>
              </h3>
              <ol className="space-y-4">
                {insight.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="font-bold text-blue-500 text-lg">{idx + 1}.</span>
                    <span className="flex-1 pt-1">{rec}</span>
                  </li>
                ))}
              </ol>
            </div>
          </>
        )}

        {/* Data Limitations */}
        {insight.data_limitations && (
          <>
            <Separator />
            <div className="bg-muted p-4 rounded-lg border border-yellow-500/30">
              <h3 className="font-semibold mb-2 flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                <span>⚠️</span>
                <span>Data Limitations</span>
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {insight.data_limitations}
              </p>
            </div>
          </>
        )}

        <Separator />

        {/* Rating Section */}
        <div>
          <h3 className="font-semibold mb-3">Was this insight helpful?</h3>
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => handleRating(star)}
                disabled={submitting}
                className="hover:scale-110 transition-transform disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={`Rate ${star} stars`}
              >
                <Star
                  className={`h-7 w-7 ${
                    star <= rating
                      ? 'fill-yellow-400 text-yellow-400'
                      : 'text-gray-300 dark:text-gray-600'
                  }`}
                />
              </button>
            ))}
            {rating > 0 && (
              <span className="text-sm text-muted-foreground ml-3">
                {rating}/5 stars
              </span>
            )}
          </div>
          {submitting && (
            <p className="text-xs text-muted-foreground mt-2">Submitting rating...</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
