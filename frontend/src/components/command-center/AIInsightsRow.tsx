"use client";

import React, { useState, CSSProperties } from "react";
import { Sparkles } from "lucide-react";
import type { AIInsight, InsightSeverity } from "@/services/insightsApi";

interface AIInsightsRowProps {
  insights: AIInsight[];
  loading: boolean;
  onGenerateInsight: () => void;
  onDismissInsight: (insightId: string) => void;
  generatingInsight: boolean;
}

interface InsightCardProps {
  insight: AIInsight;
  onDismiss: (id: string) => void;
  onExpand: () => void;
  isExpanded: boolean;
}

function getSeverityStyles(severity: InsightSeverity) {
  const styles = {
    critical: {
      bgColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)',
      textColor: 'var(--text-primary)',
      badgeClass: 'text-xs',
      badgeStyle: { backgroundColor: 'rgba(220, 38, 38, 0.2)', color: 'var(--color-error)' },
    },
    warning: {
      bgColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)',
      textColor: 'var(--text-primary)',
      badgeClass: 'text-xs',
      badgeStyle: { backgroundColor: 'rgba(245, 158, 11, 0.2)', color: 'var(--color-warning)' },
    },
    elevated: {
      bgColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)',
      textColor: 'var(--text-primary)',
      badgeClass: 'text-xs',
      badgeStyle: { backgroundColor: 'rgba(251, 146, 60, 0.2)', color: 'var(--color-accent)' },
    },
    normal: {
      bgColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)',
      textColor: 'var(--text-primary)',
      badgeClass: 'text-xs',
      badgeStyle: { backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)' },
    },
    info: {
      bgColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)',
      textColor: 'var(--text-primary)',
      badgeClass: 'text-xs',
      badgeStyle: { backgroundColor: 'rgba(59, 130, 246, 0.2)', color: 'var(--color-info)' },
    },
  };

  return styles[severity] || styles.normal;
}

function InsightCard({ insight, onDismiss, onExpand, isExpanded }: InsightCardProps) {
  const styles = getSeverityStyles(insight.severity);
  const createdDate = new Date(insight.created_at).toLocaleDateString();

  const cardStyle: CSSProperties = {
    borderRadius: 'var(--border-radius)',
    padding: 'calc(var(--card-padding) * 1.5)',
    transition: 'all 0.3s ease',
    backgroundColor: styles.bgColor,
    border: `1px solid ${styles.borderColor}`,
  };

  return (
    <div
      className="transition-all duration-300"
      style={cardStyle}
    >
      {/* Header */}
      <div style={{ paddingBottom: '0.75rem' }}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
                style={styles.badgeStyle}
              >
                {insight.severity}
              </span>
              <span
                className="text-[10px] font-semibold uppercase tracking-wider text-tertiary"
              >
                {insight.insight_type.replace(/_/g, " ")}
              </span>
            </div>
            <h3
              className="text-lg font-bold mb-1"
              style={{ color: 'var(--color-accent)' }}
            >
              {insight.title}
            </h3>
          </div>
          <button
            onClick={() => onDismiss(insight.id)}
            className="ml-2 text-xs font-medium px-2 py-1 rounded transition-colors text-tertiary"
            style={{
              backgroundColor: 'transparent',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)';
              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-tertiary)';
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            Dismiss
          </button>
        </div>

        {/* Summary */}
        <p className="text-sm mb-3 text-primary">
          {insight.summary}
        </p>

        {/* Key Findings */}
        {insight.key_findings.length > 0 && (
          <div className="mb-3">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-2 transition-colors duration-300"
              style={{ color: 'var(--text-secondary)' }}
            >
              Key Findings
            </div>
            <ul className="space-y-2">
              {insight.key_findings.slice(0, isExpanded ? undefined : 3).map((finding, idx) => (
                <li
                  key={idx}
                  className="text-sm transition-colors duration-300"
                  style={{
                    color: 'var(--text-primary)',
                    lineHeight: '1.6'
                  }}
                >
                  • {finding}
                </li>
              ))}
            </ul>
            {!isExpanded && insight.key_findings.length > 3 && (
              <button
                onClick={onExpand}
                className="text-xs font-medium mt-1 transition-colors"
                style={{ color: 'var(--color-info)' }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              >
                Show {insight.key_findings.length - 3} more findings...
              </button>
            )}
          </div>
        )}

        {/* Recommendations */}
        {isExpanded && insight.recommendations.length > 0 && (
          <div className="mb-3">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-2 transition-colors duration-300"
              style={{ color: 'var(--text-secondary)' }}
            >
              Recommendations
            </div>
            <ul className="space-y-2">
              {insight.recommendations.map((rec, idx) => (
                <li
                  key={idx}
                  className="text-sm transition-colors duration-300"
                  style={{
                    color: 'var(--text-primary)',
                    lineHeight: '1.6'
                  }}
                >
                  • {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Footer metadata */}
        <div className="flex items-center justify-between pt-2 border-t border-opacity-30">
          <div className="text-[10px] text-tertiary">
            Generated {createdDate} • ${insight.performance.cost_usd.toFixed(3)} • {(insight.performance.generation_time_ms / 1000).toFixed(1)}s
          </div>
          {!isExpanded && (
            <button
              onClick={onExpand}
              className="text-xs font-medium transition-colors"
              style={{ color: 'var(--color-info)' }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              View full analysis
            </button>
          )}
          {isExpanded && (
            <button
              onClick={onExpand}
              className="text-xs font-medium text-tertiary transition-colors"
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-tertiary)'}
            >
              Collapse
            </button>
          )}
        </div>

        {/* Full Analysis (expanded only) */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--border-primary)' }}>
            <div
              className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-tertiary"
            >
              Full Analysis
            </div>
            <div className="text-sm whitespace-pre-wrap text-primary">
              {insight.full_analysis}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="animate-pulse transition-colors duration-300 themed-card">
      <div
        className="h-3 rounded w-24 mb-2"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
      <div
        className="h-6 rounded w-48 mb-3"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
      <div
        className="h-4 rounded w-full mb-2"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
      <div
        className="h-4 rounded w-3/4"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
    </div>
  );
}

export function AIInsightsRow({
  insights,
  loading,
  onGenerateInsight,
  onDismissInsight,
  generatingInsight,
}: AIInsightsRowProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Filter to only show non-dismissed insights
  const activeInsights = insights.filter((i) => !i.dismissed);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4">
        <LoadingCard />
      </div>
    );
  }

  return (
    <>
      {activeInsights.length === 0 ? (
          <div className="text-center py-16">
            <Sparkles className="h-16 w-16 mx-auto mb-4" style={{ color: 'var(--color-accent)' }} />
            <h3 className="text-lg font-semibold mb-2 transition-colors duration-300" style={{
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}>
              No Insights Yet
            </h3>
            <p className="text-sm transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
              Click Generate to create your first daily summary
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {activeInsights.map((insight) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                onDismiss={onDismissInsight}
                onExpand={() => toggleExpanded(insight.id)}
                isExpanded={expandedIds.has(insight.id)}
              />
            ))}
          </div>
        )}
    </>
  );
}
