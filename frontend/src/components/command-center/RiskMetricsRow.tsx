"use client";

import React, { CSSProperties } from "react";

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
}

function RiskCard({ label, children }: RiskCardProps) {
  return (
    <div
      className="border-r transition-all duration-300"
      style={{
        padding: 'var(--card-padding)',
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)',
      }}
    >
      {/* Label */}
      <div
        className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary"
      >
        {label}
      </div>

      {children}
    </div>
  );
}

function LoadingCard() {
  return (
    <div
      className="animate-pulse transition-colors duration-300 themed-card"
    >
      <div
        className="h-3 rounded w-24 mb-2"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
      <div
        className="h-8 rounded w-20 mb-1"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
      <div
        className="h-3 rounded w-16"
        style={{ backgroundColor: 'var(--bg-tertiary)' }}
      ></div>
    </div>
  );
}

export function RiskMetricsRow({ metrics, loading }: RiskMetricsRowProps) {
  if (loading) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2 className="text-lg font-semibold mb-4 text-primary">
            Risk Metrics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <LoadingCard key={i} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  // Determine beta interpretation
  const getBetaInterpretation = (beta: number | null) => {
    if (beta === null) return { text: "N/A", colorVar: "var(--text-secondary)" };
    if (beta > 1.2)
      return {
        text: "High risk",
        colorVar: "var(--color-warning)",
      };
    if (beta >= 0.8)
      return {
        text: "Moderate risk",
        colorVar: "var(--color-info)",
      };
    return {
      text: "Low risk",
      colorVar: "var(--color-success)",
    };
  };

  // Determine correlation interpretation
  const getCorrelationInterpretation = (corr: number | null) => {
    if (corr === null) return { text: "N/A", colorVar: "var(--text-secondary)" };
    if (corr > 0.8)
      return {
        text: "Highly correlated",
        colorVar: "var(--color-warning)",
      };
    if (corr >= 0.5)
      return {
        text: "Diversified",
        colorVar: "var(--color-success)",
      };
    return {
      text: "Uncorrelated",
      colorVar: "var(--color-info)",
    };
  };

  const beta1yInterp = getBetaInterpretation(metrics.portfolioBeta1y);
  const corrInterp = getCorrelationInterpretation(metrics.spCorrelation);

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <h2
          className="text-lg font-semibold mb-3 transition-colors duration-300"
          style={{ color: 'var(--color-accent)' }}
        >
          Risk Metrics
        </h2>

        <div
          className="overflow-hidden themed-card transition-colors duration-300"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5">
            {/* Portfolio Beta */}
            <RiskCard label="Portfolio Beta">
              {metrics.portfolioBeta1y !== null ||
              metrics.portfolioBeta90d !== null ? (
                <div className="space-y-0.5">
                  {metrics.portfolioBeta1y !== null && (
                    <div
                      className="text-xs font-medium text-tertiary"
                    >
                      <span
                        className="text-2xl font-bold tabular-nums"
                        style={{ color: 'var(--color-accent)' }}
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
                      <span className="text-xl font-bold tabular-nums text-primary">
                        {metrics.portfolioBeta90d.toFixed(2)}
                      </span>
                      <span className="ml-1">90d</span>
                    </div>
                  )}
                  <div
                    className="text-[10px] font-semibold"
                    style={{ color: beta1yInterp.colorVar }}
                  >
                    {beta1yInterp.text}
                  </div>
                </div>
              ) : (
                <>
                  <div
                    className="text-2xl font-bold tabular-nums mb-0.5"
                    style={{ color: 'var(--color-accent)' }}
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
            <RiskCard label="Top Sector">
              {metrics.topSector ? (
                <>
                  <div
                    className="text-xl font-bold mb-0.5"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    {metrics.topSector.name}
                  </div>
                  <div
                    className="text-xs font-medium tabular-nums mb-0.5 text-primary"
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
            <RiskCard label="Largest Position">
              {metrics.largestPosition ? (
                <>
                  <div
                    className="text-xl font-bold mb-0.5"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    {metrics.largestPosition.symbol}
                  </div>
                  <div
                    className="text-xs font-medium tabular-nums mb-0.5 text-primary"
                  >
                    {metrics.largestPosition.weight.toFixed(1)}%
                  </div>
                  <div
                    className="text-[10px] font-semibold"
                    style={{
                      color: metrics.largestPosition.weight > 20
                        ? 'var(--color-warning)'
                        : 'var(--color-success)'
                    }}
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
            <RiskCard label="S&P 500 Correlation">
              <div
                className="text-2xl font-bold tabular-nums mb-0.5"
                style={{ color: 'var(--color-accent)' }}
              >
                {metrics.spCorrelation !== null
                  ? metrics.spCorrelation.toFixed(2)
                  : "—"}
              </div>
              <div className="text-[10px] font-semibold" style={{ color: corrInterp.colorVar }}>
                {corrInterp.text}
              </div>
            </RiskCard>

            {/* Stress Test */}
            <RiskCard label="Stress Test">
              <div
                className="text-xs font-medium mb-1 text-tertiary"
              >
                ±1% Market:
              </div>
              {metrics.stressTest ? (
                <div className="flex items-baseline gap-1.5">
                  <span
                    className="text-lg font-bold tabular-nums"
                    style={{ color: 'var(--color-success)' }}
                  >
                    {formatCurrency(metrics.stressTest.up)}
                  </span>
                  <span className="text-xs text-tertiary">
                    /
                  </span>
                  <span
                    className="text-lg font-bold tabular-nums"
                    style={{ color: 'var(--color-error)' }}
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
