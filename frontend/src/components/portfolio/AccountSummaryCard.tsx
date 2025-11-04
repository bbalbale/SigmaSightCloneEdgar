/**
 * AccountSummaryCard Component - November 3, 2025
 * Shows aggregate portfolio summary with progressive disclosure
 * Hides multi-portfolio complexity for users with only 1 portfolio
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAggregateAnalytics, useSelectedPortfolio } from '@/hooks/useMultiPortfolio'
import { formatCurrency, formatPercentage } from '@/lib/formatters'
import { Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface AccountSummaryCardProps {
  /**
   * Show full analytics even for single portfolio users (default: false)
   * When false, uses progressive disclosure to hide complexity
   */
  showFullAnalytics?: boolean
}

export function AccountSummaryCard({ showFullAnalytics = false }: AccountSummaryCardProps) {
  const { analytics, loading, error } = useAggregateAnalytics()
  const { portfolioCount, isAggregateView } = useSelectedPortfolio()

  // Progressive disclosure: Hide for single-portfolio users unless explicitly shown
  const shouldShowMultiPortfolio = portfolioCount > 1 || showFullAnalytics

  // Loading state
  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  // Error state
  if (error || !analytics) {
    return (
      <Card>
        <CardContent className="py-6">
          <p className="text-sm text-muted-foreground text-center">
            {error || 'Unable to load portfolio summary'}
          </p>
        </CardContent>
      </Card>
    )
  }

  const { total_unrealized_pnl, overall_return_pct, net_asset_value, total_value } = analytics
  const displayedTotal = net_asset_value ?? total_value ?? 0

  // Determine P&L trend
  const getTrendIcon = (value: number) => {
    if (value > 0) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (value < 0) return <TrendingDown className="h-4 w-4 text-red-600" />
    return <Minus className="h-4 w-4 text-gray-500" />
  }

  const getTrendColor = (value: number) => {
    if (value > 0) return 'text-green-600'
    if (value < 0) return 'text-red-600'
    return 'text-gray-500'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {shouldShowMultiPortfolio && isAggregateView
            ? `Portfolio Overview (${portfolioCount} Accounts)`
            : 'Portfolio Overview'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Value */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">Net Asset Value</p>
            <p className="text-2xl font-bold">{formatCurrency(displayedTotal)}</p>
          </div>

          {/* Total Positions */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">Positions</p>
            <p className="text-2xl font-bold">{analytics.total_positions}</p>
            {shouldShowMultiPortfolio && (
              <p className="text-xs text-muted-foreground mt-1">
                across {portfolioCount} {portfolioCount === 1 ? 'account' : 'accounts'}
              </p>
            )}
          </div>

          {/* Unrealized P&L */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">Unrealized P&L</p>
            <div className="flex items-center gap-2">
              {getTrendIcon(total_unrealized_pnl)}
              <p className={`text-2xl font-bold ${getTrendColor(total_unrealized_pnl)}`}>
                {formatCurrency(Math.abs(total_unrealized_pnl))}
              </p>
            </div>
          </div>

          {/* Overall Return */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">Overall Return</p>
            <div className="flex items-center gap-2">
              {getTrendIcon(overall_return_pct)}
              <p className={`text-2xl font-bold ${getTrendColor(overall_return_pct)}`}>
                {formatPercentage(overall_return_pct)}
              </p>
            </div>
          </div>
        </div>

        {/* Risk Metrics Row (optional, shown for multi-portfolio or when explicitly enabled) */}
        {shouldShowMultiPortfolio && analytics.risk_metrics && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Portfolio Beta</p>
              <p className="text-xl font-semibold">
                {analytics.risk_metrics.portfolio_beta?.toFixed(2) || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Sharpe Ratio</p>
              <p className="text-xl font-semibold">
                {analytics.risk_metrics.sharpe_ratio?.toFixed(2) || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Volatility</p>
              <p className="text-xl font-semibold">
                {analytics.risk_metrics.volatility
                  ? formatPercentage(analytics.risk_metrics.volatility * 100)
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Max Drawdown</p>
              <p className="text-xl font-semibold text-red-600">
                {analytics.risk_metrics.max_drawdown
                  ? formatPercentage(analytics.risk_metrics.max_drawdown * 100)
                  : 'N/A'}
              </p>
            </div>
          </div>
        )}

        {/* Top Holdings Preview (optional, shown for multi-portfolio or when explicitly enabled) */}
        {shouldShowMultiPortfolio && analytics.top_holdings && analytics.top_holdings.length > 0 && (
          <div className="mt-6 pt-6 border-t">
            <p className="text-sm font-semibold mb-3">Top 3 Holdings</p>
            <div className="space-y-2">
              {analytics.top_holdings.slice(0, 3).map((holding, index) => (
                <div
                  key={holding.symbol}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-4">
                      {index + 1}.
                    </span>
                    <span className="font-medium">{holding.symbol}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">
                      {formatCurrency(holding.net_asset_value ?? holding.total_value)}
                    </span>
                    <span className="text-xs text-muted-foreground w-12 text-right">
                      {formatPercentage(holding.pct_of_total)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
