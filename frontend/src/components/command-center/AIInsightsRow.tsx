"use client";

import React, { useState } from "react";
import { useTheme } from "@/contexts/ThemeContext";
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
  theme: "dark" | "light";
  onDismiss: (id: string) => void;
  onExpand: () => void;
  isExpanded: boolean;
}

function getSeverityStyles(
  severity: InsightSeverity,
  theme: "dark" | "light"
) {
  const styles = {
    critical: {
      bg: theme === "dark" ? "bg-red-900/20" : "bg-red-50",
      border: theme === "dark" ? "border-red-700/50" : "border-red-300",
      text: theme === "dark" ? "text-red-400" : "text-red-600",
      badge: theme === "dark" ? "bg-red-900/40 text-red-400" : "bg-red-100 text-red-700",
    },
    warning: {
      bg: theme === "dark" ? "bg-amber-900/20" : "bg-amber-50",
      border: theme === "dark" ? "border-amber-700/50" : "border-amber-300",
      text: theme === "dark" ? "text-amber-400" : "text-amber-600",
      badge: theme === "dark" ? "bg-amber-900/40 text-amber-400" : "bg-amber-100 text-amber-700",
    },
    elevated: {
      bg: theme === "dark" ? "bg-orange-900/20" : "bg-orange-50",
      border: theme === "dark" ? "border-orange-700/50" : "border-orange-300",
      text: theme === "dark" ? "text-orange-400" : "text-orange-600",
      badge: theme === "dark" ? "bg-orange-900/40 text-orange-400" : "bg-orange-100 text-orange-700",
    },
    normal: {
      bg: theme === "dark" ? "bg-primary/50" : "bg-white",
      border: theme === "dark" ? "border-primary/50" : "border-slate-300",
      text: theme === "dark" ? "text-primary" : "text-slate-700",
      badge: theme === "dark" ? "bg-slate-800 text-secondary" : "bg-slate-100 text-slate-700",
    },
    info: {
      bg: theme === "dark" ? "bg-blue-900/20" : "bg-blue-50",
      border: theme === "dark" ? "border-blue-700/50" : "border-blue-300",
      text: theme === "dark" ? "text-blue-400" : "text-blue-600",
      badge: theme === "dark" ? "bg-blue-900/40 text-blue-400" : "bg-blue-100 text-blue-700",
    },
  };

  return styles[severity] || styles.normal;
}

function InsightCard({ insight, theme, onDismiss, onExpand, isExpanded }: InsightCardProps) {
  const styles = getSeverityStyles(insight.severity, theme);
  const createdDate = new Date(insight.created_at).toLocaleDateString();

  return (
    <div
      className={`border transition-all duration-200 ${styles.border} ${styles.bg} hover:shadow-md`}
    >
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${styles.badge}`}
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
              className={`text-lg font-bold mb-1 ${
                theme === "dark" ? "text-orange-400" : "text-slate-900"
              }`}
            >
              {insight.title}
            </h3>
          </div>
          <button
            onClick={() => onDismiss(insight.id)}
            className={`ml-2 text-xs font-medium px-2 py-1 rounded transition-colors ${
              theme === "dark"
                ? "text-tertiary hover:text-primary hover:bg-slate-800"
                : "text-tertiary hover:text-slate-700 hover:bg-slate-100"
            }`}
          >
            Dismiss
          </button>
        </div>

        {/* Summary */}
        <p
          className={`text-sm mb-3 ${
            theme === "dark" ? "text-primary" : "text-slate-700"
          }`}
        >
          {insight.summary}
        </p>

        {/* Key Findings */}
        {insight.key_findings.length > 0 && (
          <div className="mb-3">
            <div
              className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-tertiary"
            >
              Key Findings
            </div>
            <ul className="space-y-1">
              {insight.key_findings.slice(0, isExpanded ? undefined : 3).map((finding, idx) => (
                <li
                  key={idx}
                  className={`text-xs ${
                    theme === "dark" ? "text-secondary" : "text-slate-600"
                  }`}
                >
                  • {finding}
                </li>
              ))}
            </ul>
            {!isExpanded && insight.key_findings.length > 3 && (
              <button
                onClick={onExpand}
                className={`text-xs font-medium mt-1 ${
                  theme === "dark" ? "text-blue-400 hover:text-blue-300" : "text-blue-600 hover:text-blue-700"
                }`}
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
              className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-tertiary"
            >
              Recommendations
            </div>
            <ul className="space-y-1">
              {insight.recommendations.map((rec, idx) => (
                <li
                  key={idx}
                  className={`text-xs ${
                    theme === "dark" ? "text-secondary" : "text-slate-600"
                  }`}
                >
                  • {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Footer metadata */}
        <div className="flex items-center justify-between pt-2 border-t border-opacity-30">
          <div
            className={`text-[10px] ${
              theme === "dark" ? "text-slate-600" : "text-secondary"
            }`}
          >
            Generated {createdDate} • ${insight.performance.cost_usd.toFixed(3)} • {(insight.performance.generation_time_ms / 1000).toFixed(1)}s
          </div>
          {!isExpanded && (
            <button
              onClick={onExpand}
              className={`text-xs font-medium ${
                theme === "dark" ? "text-blue-400 hover:text-blue-300" : "text-blue-600 hover:text-blue-700"
              }`}
            >
              View full analysis
            </button>
          )}
          {isExpanded && (
            <button
              onClick={onExpand}
              className={`text-xs font-medium ${
                theme === "dark" ? "text-tertiary hover:text-primary" : "text-tertiary hover:text-slate-700"
              }`}
            >
              Collapse
            </button>
          )}
        </div>

        {/* Full Analysis (expanded only) */}
        {isExpanded && (
          <div className={`mt-3 pt-3 border-t ${theme === "dark" ? "border-primary/50" : "border-slate-300"}`}>
            <div
              className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-tertiary"
            >
              Full Analysis
            </div>
            <div
              className={`text-sm whitespace-pre-wrap ${
                theme === "dark" ? "text-primary" : "text-slate-700"
              }`}
            >
              {insight.full_analysis}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingCard({ theme }: { theme: "dark" | "light" }) {
  return (
    <div
      className={`rounded-lg border p-4 animate-pulse transition-colors duration-300 ${
        theme === "dark"
          ? "bg-primary border-primary"
          : "bg-slate-50 border-slate-200"
      }`}
    >
      <div
        className={`h-3 rounded w-24 mb-2 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
      ></div>
      <div
        className={`h-6 rounded w-48 mb-3 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
      ></div>
      <div
        className={`h-4 rounded w-full mb-2 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
      ></div>
      <div
        className={`h-4 rounded w-3/4 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
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
  const { theme } = useTheme();
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
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2
            className={`text-sm font-semibold uppercase tracking-wider mb-2 ${
              theme === "dark" ? "text-secondary" : "text-slate-600"
            }`}
          >
            AI Insights
          </h2>
          <div className="grid grid-cols-1 gap-4">
            <LoadingCard theme={theme} />
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-2">
          <h2
            className={`text-sm font-semibold uppercase tracking-wider ${
              theme === "dark" ? "text-secondary" : "text-slate-600"
            }`}
          >
            AI Insights
          </h2>
          <button
            onClick={onGenerateInsight}
            disabled={generatingInsight}
            className={`text-xs font-medium px-3 py-1.5 rounded transition-colors ${
              generatingInsight
                ? theme === "dark"
                  ? "bg-slate-800 text-slate-600 cursor-not-allowed"
                  : "bg-slate-200 text-secondary cursor-not-allowed"
                : theme === "dark"
                ? "bg-orange-900/40 text-orange-400 hover:bg-orange-900/60"
                : "bg-orange-100 text-orange-700 hover:bg-orange-200"
            }`}
          >
            {generatingInsight ? "Generating..." : "Generate Daily Summary"}
          </button>
        </div>

        {activeInsights.length === 0 ? (
          <div
            className={`border p-8 text-center transition-colors duration-300 ${
              theme === "dark"
                ? "bg-primary/30 border-primary/50"
                : "bg-white border-slate-300"
            }`}
          >
            <p
              className={`text-sm mb-3 ${
                theme === "dark" ? "text-secondary" : "text-slate-600"
              }`}
            >
              No AI insights yet. Generate your first daily summary to get started.
            </p>
            <button
              onClick={onGenerateInsight}
              disabled={generatingInsight}
              className={`text-sm font-medium px-4 py-2 rounded transition-colors ${
                generatingInsight
                  ? theme === "dark"
                    ? "bg-slate-800 text-slate-600 cursor-not-allowed"
                    : "bg-slate-200 text-secondary cursor-not-allowed"
                  : theme === "dark"
                  ? "bg-orange-900/40 text-orange-400 hover:bg-orange-900/60"
                  : "bg-orange-100 text-orange-700 hover:bg-orange-200"
              }`}
            >
              {generatingInsight ? "Generating Insight..." : "Generate Daily Summary"}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {activeInsights.map((insight) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                theme={theme}
                onDismiss={onDismissInsight}
                onExpand={() => toggleExpanded(insight.id)}
                isExpanded={expandedIds.has(insight.id)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
