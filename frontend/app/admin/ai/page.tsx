'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useAdminStore } from '@/stores/adminStore'
import {
  adminApiService,
  AIMetricsSummary,
  AILatencyPercentiles,
  AITokenUsage,
  AIErrorBreakdown,
  AIToolUsage,
  AIModelUsage
} from '@/services/adminApiService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ArrowLeft,
  Activity,
  AlertCircle,
  Clock,
  Zap,
  Wrench,
  Cpu,
  Loader2,
  TrendingUp,
  TrendingDown,
  BarChart3
} from 'lucide-react'

export default function AIMetricsPage() {
  const router = useRouter()
  const { admin } = useAdminStore()
  const [metrics, setMetrics] = useState<AIMetricsSummary | null>(null)
  const [latency, setLatency] = useState<AILatencyPercentiles | null>(null)
  const [tokens, setTokens] = useState<AITokenUsage | null>(null)
  const [errors, setErrors] = useState<AIErrorBreakdown | null>(null)
  const [tools, setTools] = useState<AIToolUsage | null>(null)
  const [models, setModels] = useState<AIModelUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [metricsData, latencyData, tokensData, errorsData, toolsData, modelsData] = await Promise.all([
          adminApiService.getAIMetrics(days),
          adminApiService.getAILatency(days),
          adminApiService.getAITokens(days),
          adminApiService.getAIErrors(days),
          adminApiService.getAITools(days),
          adminApiService.getAIModels(days)
        ])
        setMetrics(metricsData)
        setLatency(latencyData)
        setTokens(tokensData)
        setErrors(errorsData)
        setTools(toolsData)
        setModels(modelsData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [days])

  // Format large numbers
  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return 'N/A'
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toLocaleString()
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/admin')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                  <Activity className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-white">AI Performance Metrics</h1>
                  <p className="text-xs text-slate-400">Latency, tokens, errors, and usage</p>
                </div>
              </div>
            </div>

            {/* Period Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">Period:</span>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="bg-slate-700 border-slate-600 text-white text-sm rounded px-3 py-1.5"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            <span className="ml-3 text-slate-400">Loading AI metrics...</span>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                      <Zap className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {formatNumber(metrics?.total_requests)}
                      </p>
                      <p className="text-sm text-slate-400">Total Requests</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center">
                      <Clock className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {metrics?.avg_latency_ms ? `${Math.round(metrics.avg_latency_ms)}ms` : 'N/A'}
                      </p>
                      <p className="text-sm text-slate-400">Avg Latency</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${
                      metrics?.error_rate && metrics.error_rate > 5 ? 'bg-red-500' : 'bg-green-500'
                    } rounded-lg flex items-center justify-center`}>
                      <AlertCircle className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {metrics?.error_rate?.toFixed(1) || 0}%
                      </p>
                      <p className="text-sm text-slate-400">Error Rate</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
                      <Wrench className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {metrics?.tool_usage_rate?.toFixed(1) || 0}%
                      </p>
                      <p className="text-sm text-slate-400">Tool Usage</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Latency Percentiles */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-orange-400" />
                    Latency Percentiles
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Response time distribution ({latency?.sample_count || 0} samples)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {[
                      { label: 'P50 (Median)', value: latency?.percentiles.p50 },
                      { label: 'P75', value: latency?.percentiles.p75 },
                      { label: 'P90', value: latency?.percentiles.p90 },
                      { label: 'P95', value: latency?.percentiles.p95 },
                      { label: 'P99', value: latency?.percentiles.p99 }
                    ].map((item) => (
                      <div key={item.label} className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">{item.label}</span>
                        <span className="text-sm font-mono text-white">
                          {item.value ? `${Math.round(item.value)}ms` : 'N/A'}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-700">
                    <p className="text-xs text-slate-500 mb-2">Time to First Token</p>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">P50</span>
                      <span className="text-sm font-mono text-white">
                        {latency?.first_token.p50 ? `${Math.round(latency.first_token.p50)}ms` : 'N/A'}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Token Usage */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                    Token Usage
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Daily input/output token consumption
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Avg Input Tokens</span>
                      <span className="text-sm font-mono text-white">
                        {formatNumber(metrics?.avg_input_tokens)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Avg Output Tokens</span>
                      <span className="text-sm font-mono text-white">
                        {formatNumber(metrics?.avg_output_tokens)}
                      </span>
                    </div>
                  </div>

                  {tokens?.daily_usage && tokens.daily_usage.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-700">
                      <p className="text-xs text-slate-500 mb-3">Recent Daily Usage</p>
                      <div className="space-y-2">
                        {tokens.daily_usage.slice(0, 5).map((day) => (
                          <div key={day.date} className="flex items-center justify-between text-xs">
                            <span className="text-slate-400">
                              {new Date(day.date).toLocaleDateString()}
                            </span>
                            <span className="text-slate-300">
                              {formatNumber(day.total_tokens)} tokens ({day.request_count} req)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Tool Usage */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-purple-400" />
                    Tool Usage
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    {tools?.total_tool_calls || 0} total tool calls
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {tools?.tools && tools.tools.length > 0 ? (
                    <div className="space-y-3">
                      {tools.tools.slice(0, 8).map((tool) => (
                        <div key={tool.tool_name} className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm text-white font-mono">
                                {tool.tool_name}
                              </span>
                              <span className="text-xs text-slate-400">
                                {tool.count} ({tool.percentage.toFixed(1)}%)
                              </span>
                            </div>
                            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-purple-500 transition-all"
                                style={{ width: `${tool.percentage}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-center py-4">No tool usage data</p>
                  )}
                </CardContent>
              </Card>

              {/* Model Usage */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-green-400" />
                    Model Usage
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    {models?.total_requests || 0} total requests
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {models?.models && models.models.length > 0 ? (
                    <div className="space-y-3">
                      {models.models.map((model) => (
                        <div key={model.model} className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm text-white font-mono">
                                {model.model}
                              </span>
                              <span className="text-xs text-slate-400">
                                {model.count} ({model.percentage.toFixed(1)}%)
                              </span>
                            </div>
                            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-green-500 transition-all"
                                style={{ width: `${model.percentage}%` }}
                              />
                            </div>
                            {model.avg_latency_ms && (
                              <p className="text-xs text-slate-500 mt-1">
                                Avg latency: {Math.round(model.avg_latency_ms)}ms
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-center py-4">No model usage data</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Errors Section */}
            <Card className="bg-slate-800/50 border-slate-700 mt-6">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  Error Breakdown
                </CardTitle>
                <CardDescription className="text-slate-400">
                  {errors?.total_errors || 0} total errors
                </CardDescription>
              </CardHeader>
              <CardContent>
                {errors?.errors && errors.errors.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {errors.errors.map((err) => (
                      <div
                        key={err.error_type}
                        className="p-3 bg-red-900/20 border border-red-800/50 rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-mono text-red-400">
                            {err.error_type}
                          </span>
                          <span className="text-sm font-bold text-white">
                            {err.count}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">
                          {err.percentage.toFixed(1)}% of all errors
                        </p>
                        {err.samples.length > 0 && (
                          <p className="text-xs text-slate-500 mt-1 truncate">
                            {err.samples[0]}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-green-400 text-center py-4">
                    No errors recorded in this period
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}
