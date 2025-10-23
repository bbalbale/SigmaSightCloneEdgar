/**
 * InsightsList Component
 *
 * Displays a list of AI insights with:
 * - Loading state with skeletons
 * - Error state with retry
 * - Empty state when no insights
 * - List of InsightCard components
 * - Load more button for pagination
 */

'use client'

import React from 'react'
import { useInsights } from '@/hooks/useInsights'
import { InsightCard } from './InsightCard'
import { AIInsight, InsightType } from '@/services/insightsApi'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface InsightsListProps {
  onSelectInsight: (insight: AIInsight) => void
  filterType?: InsightType
  daysBack?: number
}

export function InsightsList({
  onSelectInsight,
  filterType,
  daysBack = 30
}: InsightsListProps) {
  const { insights, loading, error, total, hasMore, refresh } = useInsights({
    insightType: filterType,
    daysBack,
    limit: 20,
  })

  // Loading state
  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border rounded-lg p-6 space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <Skeleton className="h-6 w-6 rounded" />
                <Skeleton className="h-6 w-24" />
              </div>
              <Skeleton className="h-4 w-20" />
            </div>
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-20 w-full" />
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-8 w-28" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription className="flex items-center justify-between">
          <span>Failed to load insights. Please try again.</span>
          <Button variant="outline" size="sm" onClick={() => refresh()}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  // Empty state
  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-16 border rounded-lg bg-muted/30">
        <div className="mb-4 text-6xl">🤖</div>
        <h3 className="text-xl font-semibold mb-2">No insights yet</h3>
        <p className="text-muted-foreground mb-6">
          Generate your first AI-powered portfolio analysis to get started.
        </p>
        <p className="text-sm text-muted-foreground">
          Click the <strong>"Generate Insight"</strong> button above
        </p>
      </div>
    )
  }

  // List with insights
  return (
    <div className="space-y-4">
      {/* Header info */}
      {total > 0 && (
        <div className="text-sm text-muted-foreground mb-2">
          Showing {insights.length} of {total} insights
        </div>
      )}

      {/* Insights list */}
      {insights.map((insight) => (
        <InsightCard
          key={insight.id}
          insight={insight}
          onView={onSelectInsight}
        />
      ))}

      {/* Load more button */}
      {hasMore && (
        <div className="text-center py-6">
          <Button variant="outline" onClick={() => refresh()}>
            Load More Insights
          </Button>
          <p className="text-xs text-muted-foreground mt-2">
            {total - insights.length} more available
          </p>
        </div>
      )}
    </div>
  )
}
