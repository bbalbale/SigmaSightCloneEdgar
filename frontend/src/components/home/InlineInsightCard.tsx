'use client'

import React, { useState } from 'react'
import { Sparkles, RefreshCw, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'

export type InsightSeverity = 'critical' | 'warning' | 'elevated' | 'normal' | 'info'

export interface InlineInsightCardProps {
  /**
   * Type of row this insight relates to
   */
  rowType: 'returns' | 'exposures' | 'volatility'

  /**
   * Pre-generated insight text (if available)
   */
  insight?: string | null

  /**
   * Severity level for styling
   */
  severity?: InsightSeverity

  /**
   * Whether insight is currently being generated
   */
  loading?: boolean

  /**
   * Callback to generate/refresh insight
   */
  onGenerate?: () => void

  /**
   * Whether generation is available
   */
  canGenerate?: boolean
}

function getSeverityStyles(severity: InsightSeverity) {
  const styles = {
    critical: {
      badgeStyle: { backgroundColor: 'rgba(220, 38, 38, 0.2)', color: 'var(--color-error)' },
    },
    warning: {
      badgeStyle: { backgroundColor: 'rgba(245, 158, 11, 0.2)', color: 'var(--color-warning)' },
    },
    elevated: {
      badgeStyle: { backgroundColor: 'rgba(251, 146, 60, 0.2)', color: 'var(--color-accent)' },
    },
    normal: {
      badgeStyle: { backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)' },
    },
    info: {
      badgeStyle: { backgroundColor: 'rgba(59, 130, 246, 0.2)', color: 'var(--color-info)' },
    },
  }

  return styles[severity] || styles.normal
}

export function InlineInsightCard({
  rowType,
  insight,
  severity = 'info',
  loading = false,
  onGenerate,
  canGenerate = true,
}: InlineInsightCardProps) {
  const [expanded, setExpanded] = useState(false)
  const styles = getSeverityStyles(severity)

  const rowLabels = {
    returns: 'Returns Analysis',
    exposures: 'Exposure Assessment',
    volatility: 'Volatility Context',
  }

  // If no insight and can generate, show placeholder
  if (!insight && !loading) {
    return (
      <div className="themed-border-r p-3 transition-all duration-200 bg-tertiary flex flex-col items-center justify-center min-h-[80px]">
        <Sparkles className="h-5 w-5 mb-2 text-secondary" />
        <div className="text-[10px] font-semibold uppercase tracking-wider mb-1 text-secondary">
          AI Insight
        </div>
        {canGenerate && onGenerate ? (
          <button
            onClick={onGenerate}
            className="text-xs font-medium px-2 py-1 rounded transition-colors hover:opacity-80"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--color-accent)',
            }}
          >
            Generate
          </button>
        ) : (
          <div className="text-xs text-secondary">Coming soon</div>
        )}
      </div>
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="themed-border-r p-3 transition-all duration-200 bg-tertiary flex flex-col items-center justify-center min-h-[80px]">
        <Loader2 className="h-5 w-5 mb-2 text-accent animate-spin" />
        <div className="text-[10px] font-semibold uppercase tracking-wider text-secondary">
          Analyzing...
        </div>
      </div>
    )
  }

  // Show insight
  const truncatedInsight =
    insight && insight.length > 150 ? insight.substring(0, 150) + '...' : insight

  return (
    <div
      className="themed-border-r p-3 transition-all duration-200 bg-tertiary hover:bg-secondary"
      style={{ minHeight: expanded ? 'auto' : '80px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3 w-3" style={{ color: 'var(--color-accent)' }} />
          <span
            className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
            style={styles.badgeStyle}
          >
            {severity}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {onGenerate && canGenerate && (
            <button
              onClick={onGenerate}
              className="p-1 rounded transition-colors hover:bg-secondary"
              title="Refresh insight"
            >
              <RefreshCw className="h-3 w-3 text-secondary" />
            </button>
          )}
          {insight && insight.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 rounded transition-colors hover:bg-secondary"
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? (
                <ChevronUp className="h-3 w-3 text-secondary" />
              ) : (
                <ChevronDown className="h-3 w-3 text-secondary" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Insight Text */}
      <div
        className="text-xs text-primary leading-relaxed"
        style={{ color: 'var(--text-primary)' }}
      >
        {expanded ? insight : truncatedInsight}
      </div>

      {/* Footer */}
      <div className="mt-2 text-[9px] text-tertiary">{rowLabels[rowType]}</div>
    </div>
  )
}
