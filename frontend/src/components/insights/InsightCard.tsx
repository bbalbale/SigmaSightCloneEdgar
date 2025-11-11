/**
 * InsightCard Component
 *
 * Displays a preview card for an AI insight with:
 * - Severity badge and icon
 * - Title and summary preview
 * - Timestamp and "new" indicator
 * - Key findings and recommendations count
 * - Click to view full details
 */

'use client'

import React from 'react'
import { AIInsight } from '@/services/insightsApi'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'

interface InsightCardProps {
  insight: AIInsight
  onView: (insight: AIInsight) => void
}

const severityConfig = {
  critical: { label: 'CRITICAL', color: 'bg-red-500 hover:bg-red-600', textColor: 'text-white', icon: '🔴' },
  warning: { label: 'WARNING', color: 'bg-orange-500 hover:bg-orange-600', textColor: 'text-white', icon: '⚠️' },
  elevated: { label: 'ELEVATED', color: 'bg-yellow-500 hover:bg-yellow-600', textColor: 'text-white', icon: '🟡' },
  normal: { label: 'NORMAL', color: 'bg-blue-500 hover:bg-blue-600', textColor: 'text-white', icon: '🔵' },
  info: { label: 'INFO', color: 'bg-primary0 hover:bg-gray-600', textColor: 'text-white', icon: 'ℹ️' },
}

export function InsightCard({ insight, onView }: InsightCardProps) {
  const config = severityConfig[insight.severity]
  const timeAgo = formatDistanceToNow(new Date(insight.created_at), { addSuffix: true })

  return (
    <Card
      className={`cursor-pointer hover:shadow-lg transition-all duration-200 ${
        !insight.viewed ? 'border-l-4 border-l-blue-500' : ''
      }`}
      onClick={() => onView(insight)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xl">{config.icon}</span>
            <Badge className={`${config.color} ${config.textColor}`}>
              {config.label}
            </Badge>
            {!insight.viewed && (
              <Badge variant="outline" className="border-blue-500 text-blue-500">
                New
              </Badge>
            )}
          </div>
          <span className="text-sm text-muted-foreground whitespace-nowrap ml-2">
            {timeAgo}
          </span>
        </div>
        <CardTitle className="mt-2 text-xl">{insight.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-3 mb-4">
          {insight.summary}
        </CardDescription>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>📊 {insight.key_findings.length} findings</span>
            <span>💡 {insight.recommendations.length} recommendations</span>
          </div>
          <Button variant="ghost" size="sm" className="text-xs">
            View Details →
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
