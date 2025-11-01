"use client";

import React from "react";
import { useTheme } from "@/contexts/ThemeContext";

interface RiskMetricsRowProps {
  metrics: {
    portfolioBeta90d: number | null;
    portfolioBeta1y: number | null;
    topSector: { name: string; weight: number; vs_sp: number } | null;
    largestPosition: { symbol: string; weight: number } | null;
    spCorrelation: number | null;
    stressTest: { up: number; down: number } | null;
  };
  loading: boolean;
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
}

interface RiskCardProps {
  label: string;
  children: React.ReactNode;
  theme: "dark" | "light";
}

function RiskCard({ label, children, theme }: RiskCardProps) {
  return (
    <div
      className={`border-r p-3 transition-all duration-200 hover:bg-opacity-50 ${
        theme === "dark"
          ? "bg-primary/50 border-primary/50 hover:bg-slate-800/50"
          : "bg-white border-slate-300 hover:bg-slate-50"
      }`}
    >
      {/* Label */}
      <div
        className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-tertiary"
      >
        {label}
      </div>

      {children}
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
        className={`h-8 rounded w-20 mb-1 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
      ></div>
      <div
        className={`h-3 rounded w-16 ${
          theme === "dark" ? "bg-slate-700" : "bg-slate-300"
        }`}
      ></div>
    </div>
  );
}

export function RiskMetricsRow({ metrics, loading }: RiskMetricsRowProps) {
  const { theme } = useTheme();

  if (loading) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2
            className={`text-lg font-semibold mb-4 ${
              theme === "dark" ? "text-slate-50" : "text-slate-900"
            }`}
          >
            Risk Metrics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <LoadingCard key={i} theme={theme} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  // Determine beta interpretation
  const getBetaInterpretation = (beta: number | null) => {
    if (beta === null) return { text: "N/A", color: "text-secondary" };
    if (beta > 1.2)
      return {
        text: "High risk",
        color: theme === "dark" ? "text-amber-400" : "text-amber-600",
      };
    if (beta >= 0.8)
      return {
        text: "Moderate risk",
        color: theme === "dark" ? "text-blue-400" : "text-blue-600",
      };
    return {
      text: "Low risk",
      color: theme === "dark" ? "text-emerald-400" : "text-emerald-600",
    };
  };

  // Determine correlation interpretation
  const getCorrelationInterpretation = (corr: number | null) => {
    if (corr === null) return { text: "N/A", color: "text-secondary" };
    if (corr > 0.8)
      return {
        text: "Highly correlated",
        color: theme === "dark" ? "text-amber-400" : "text-amber-600",
      };
    if (corr >= 0.5)
      return {
        text: "Diversified",
        color: theme === "dark" ? "text-emerald-400" : "text-emerald-600",
      };
    return {
      text: "Uncorrelated",
      color: theme === "dark" ? "text-blue-400" : "text-blue-600",
    };
  };

  const beta1yInterp = getBetaInterpretation(metrics.portfolioBeta1y);
  const corrInterp = getCorrelationInterpretation(metrics.spCorrelation);

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <h2
          className={`text-sm font-semibold uppercase tracking-wider mb-2 ${
            theme === "dark" ? "text-secondary" : "text-slate-600"
          }`}
        >
          Risk Metrics
        </h2>

        <div
          className={`border overflow-hidden ${
            theme === "dark"
              ? "bg-primary/30 border-primary/50"
              : "bg-white border-slate-300"
          }`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5">
            {/* Portfolio Beta */}
            <RiskCard label="Portfolio Beta" theme={theme}>
              {metrics.portfolioBeta1y !== null ||
              metrics.portfolioBeta90d !== null ? (
                <div className="space-y-0.5">
                  {metrics.portfolioBeta1y !== null && (
                    <div
                      className="text-xs font-medium text-tertiary"
                    >
                      <span
                        className={`text-2xl font-bold tabular-nums ${
                          theme === "dark"
                            ? "text-orange-400"
                            : "text-slate-900"
                        }`}
                      >
                        {metrics.portfolioBeta1y.toFixed(2)}
                      </span>
                      <span className="ml-1">1y</span>
                    </div>
                  )}
                  {metrics.portfolioBeta90d !== null && (
                    <div
                      className="text-xs font-medium text-tertiary"
                    >
                      <span
                        className={`text-xl font-bold tabular-nums ${
                          theme === "dark" ? "text-primary" : "text-slate-700"
                        }`}
                      >
                        {metrics.portfolioBeta90d.toFixed(2)}
                      </span>
                      <span className="ml-1">90d</span>
                    </div>
                  )}
                  <div
                    className={`text-[10px] font-semibold ${beta1yInterp.color}`}
                  >
                    {beta1yInterp.text}
                  </div>
                </div>
              ) : (
                <>
                  <div
                    className={`text-2xl font-bold tabular-nums mb-0.5 ${
                      theme === "dark" ? "text-orange-400" : "text-slate-900"
                    }`}
                  >
                    —
                  </div>
                  <div
                    className="text-xs font-medium text-tertiary"
                  >
                    N/A
                  </div>
                </>
              )}
            </RiskCard>

            {/* Top Sector Concentration */}
            <RiskCard label="Top Sector" theme={theme}>
              {metrics.topSector ? (
                <>
                  <div
                    className={`text-xl font-bold mb-0.5 ${
                      theme === "dark" ? "text-orange-400" : "text-slate-900"
                    }`}
                  >
                    {metrics.topSector.name}
                  </div>
                  <div
                    className={`text-xs font-medium tabular-nums mb-0.5 ${
                      theme === "dark" ? "text-primary" : "text-slate-700"
                    }`}
                  >
                    {metrics.topSector.weight.toFixed(1)}% portfolio
                  </div>
                  <div
                    className="text-[10px] font-semibold tabular-nums text-tertiary"
                  >
                    {metrics.topSector.vs_sp >= 0 ? "+" : ""}
                    {metrics.topSector.vs_sp.toFixed(1)}% vs S&P
                  </div>
                </>
              ) : (
                <div
                  className="text-xs font-medium text-tertiary"
                >
                  No data
                </div>
              )}
            </RiskCard>

            {/* Largest Position */}
            <RiskCard label="Largest Position" theme={theme}>
              {metrics.largestPosition ? (
                <>
                  <div
                    className={`text-xl font-bold mb-0.5 ${
                      theme === "dark" ? "text-orange-400" : "text-slate-900"
                    }`}
                  >
                    {metrics.largestPosition.symbol}
                  </div>
                  <div
                    className={`text-xs font-medium tabular-nums mb-0.5 ${
                      theme === "dark" ? "text-primary" : "text-slate-700"
                    }`}
                  >
                    {metrics.largestPosition.weight.toFixed(1)}%
                  </div>
                  <div
                    className={`text-[10px] font-semibold ${
                      metrics.largestPosition.weight > 20
                        ? theme === "dark"
                          ? "text-amber-400"
                          : "text-amber-600"
                        : theme === "dark"
                          ? "text-emerald-400"
                          : "text-emerald-600"
                    }`}
                  >
                    {metrics.largestPosition.weight > 20
                      ? "High concentration"
                      : "Normal concentration"}
                  </div>
                </>
              ) : (
                <div
                  className="text-xs font-medium text-tertiary"
                >
                  No positions
                </div>
              )}
            </RiskCard>

            {/* S&P 500 Correlation */}
            <RiskCard label="S&P 500 Correlation" theme={theme}>
              <div
                className={`text-2xl font-bold tabular-nums mb-0.5 ${
                  theme === "dark" ? "text-orange-400" : "text-slate-900"
                }`}
              >
                {metrics.spCorrelation !== null
                  ? metrics.spCorrelation.toFixed(2)
                  : "—"}
              </div>
              <div className={`text-[10px] font-semibold ${corrInterp.color}`}>
                {corrInterp.text}
              </div>
            </RiskCard>

            {/* Stress Test */}
            <RiskCard label="Stress Test" theme={theme}>
              <div
                className="text-xs font-medium mb-1 text-tertiary"
              >
                ±1% Market:
              </div>
              {metrics.stressTest ? (
                <div className="flex items-baseline gap-1.5">
                  <span
                    className={`text-lg font-bold tabular-nums ${
                      theme === "dark" ? "text-emerald-400" : "text-emerald-600"
                    }`}
                  >
                    {formatCurrency(metrics.stressTest.up)}
                  </span>
                  <span
                    className={`text-xs ${theme === "dark" ? "text-slate-600" : "text-secondary"}`}
                  >
                    /
                  </span>
                  <span
                    className={`text-lg font-bold tabular-nums ${
                      theme === "dark" ? "text-red-400" : "text-red-600"
                    }`}
                  >
                    {formatCurrency(metrics.stressTest.down)}
                  </span>
                </div>
              ) : (
                <div
                  className="text-xs font-medium text-tertiary"
                >
                  No data
                </div>
              )}
            </RiskCard>
          </div>
        </div>
      </div>
    </section>
  );
}
