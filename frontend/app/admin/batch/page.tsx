'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useAdminStore } from '@/stores/adminStore'
import {
  adminApiService,
  BatchHistory,
  BatchHistorySummary,
  BatchRunDetails,
  BatchRun
} from '@/services/adminApiService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ArrowLeft,
  Settings,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Play,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  Timer,
  Download,
  FileText
} from 'lucide-react'

export default function BatchHistoryPage() {
  const router = useRouter()
  const { admin } = useAdminStore()
  const [history, setHistory] = useState<BatchHistory | null>(null)
  const [summary, setSummary] = useState<BatchHistorySummary | null>(null)
  const [selectedRun, setSelectedRun] = useState<BatchRunDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [historyData, summaryData] = await Promise.all([
          adminApiService.getBatchHistory(days, statusFilter || undefined),
          adminApiService.getBatchHistorySummary(days)
        ])
        setHistory(historyData)
        setSummary(summaryData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [days, statusFilter])

  const loadRunDetails = async (batchRunId: string) => {
    setDetailsLoading(true)
    try {
      const details = await adminApiService.getBatchRunDetails(batchRunId)
      setSelectedRun(details)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load run details')
    } finally {
      setDetailsLoading(false)
    }
  }

  const downloadLogs = async (format: 'txt' | 'json' = 'txt') => {
    if (!selectedRun) return
    setDownloadLoading(true)
    try {
      await adminApiService.downloadBatchLogs(selectedRun.batch_run_id, format)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download logs')
    } finally {
      setDownloadLoading(false)
    }
  }

  // Get status icon and color
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'completed':
        return { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500' }
      case 'failed':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500' }
      case 'partial':
        return { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500' }
      case 'running':
        return { icon: Play, color: 'text-blue-400', bg: 'bg-blue-500' }
      default:
        return { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500' }
    }
  }

  // Format duration
  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return 'N/A'
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
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
                <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                  <Settings className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-white">Batch Processing History</h1>
                  <p className="text-xs text-slate-400">Job runs and performance</p>
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white text-sm rounded px-3 py-1.5"
                >
                  <option value="">All</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="partial">Partial</option>
                  <option value="running">Running</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Period:</span>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="bg-slate-700 border-slate-600 text-white text-sm rounded px-3 py-1.5"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={14}>Last 14 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={60}>Last 60 days</option>
                  <option value={90}>Last 90 days</option>
                </select>
              </div>
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
            <span className="ml-3 text-slate-400">Loading batch history...</span>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                      <RefreshCw className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {summary?.total_runs || 0}
                      </p>
                      <p className="text-sm text-slate-400">Total Runs</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${
                      (summary?.success_rate_percent || 0) >= 90 ? 'bg-green-500'
                      : (summary?.success_rate_percent || 0) >= 70 ? 'bg-yellow-500'
                      : 'bg-red-500'
                    } rounded-lg flex items-center justify-center`}>
                      <CheckCircle2 className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {summary?.success_rate_percent?.toFixed(1) || 0}%
                      </p>
                      <p className="text-sm text-slate-400">Success Rate</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center">
                      <Timer className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {formatDuration(summary?.avg_duration_seconds || null)}
                      </p>
                      <p className="text-sm text-slate-400">Avg Duration</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
                      <Clock className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-white capitalize">
                        {summary?.most_recent?.status || 'None'}
                      </p>
                      <p className="text-sm text-slate-400">Last Run Status</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Status Breakdown */}
            <Card className="bg-slate-800/50 border-slate-700 mb-8">
              <CardHeader>
                <CardTitle className="text-white">Status Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4">
                  {[
                    { status: 'completed', label: 'Completed', count: summary?.status_breakdown.completed || 0 },
                    { status: 'failed', label: 'Failed', count: summary?.status_breakdown.failed || 0 },
                    { status: 'partial', label: 'Partial', count: summary?.status_breakdown.partial || 0 },
                    { status: 'running', label: 'Running', count: summary?.status_breakdown.running || 0 }
                  ].map((item) => {
                    const display = getStatusDisplay(item.status)
                    const Icon = display.icon
                    return (
                      <div
                        key={item.status}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-700/50 rounded-lg"
                      >
                        <Icon className={`w-5 h-5 ${display.color}`} />
                        <span className="text-white font-medium">{item.count}</span>
                        <span className="text-slate-400">{item.label}</span>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Run History List */}
              <div className="lg:col-span-2">
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white">Recent Runs</CardTitle>
                    <CardDescription className="text-slate-400">
                      {history?.total_count || 0} runs in the last {days} days
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {history?.runs && history.runs.length > 0 ? (
                      <div className="space-y-2">
                        {history.runs.map((run) => {
                          const display = getStatusDisplay(run.status)
                          const Icon = display.icon
                          const isSelected = selectedRun?.batch_run_id === run.batch_run_id
                          return (
                            <div
                              key={run.id}
                              className={`p-3 rounded-lg cursor-pointer transition-all ${
                                isSelected
                                  ? 'bg-slate-600 border border-blue-500'
                                  : 'bg-slate-700/50 hover:bg-slate-700'
                              }`}
                              onClick={() => loadRunDetails(run.batch_run_id)}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <div className={`w-8 h-8 ${display.bg} rounded flex items-center justify-center`}>
                                    <Icon className="w-4 h-4 text-white" />
                                  </div>
                                  <div>
                                    <p className="text-sm font-mono text-white">
                                      {run.batch_run_id}
                                    </p>
                                    <p className="text-xs text-slate-400">
                                      {run.started_at
                                        ? new Date(run.started_at).toLocaleString()
                                        : 'Unknown start time'}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-4">
                                  <div className="text-right">
                                    <p className="text-sm text-white">
                                      {run.completed_jobs}/{run.total_jobs} jobs
                                    </p>
                                    <p className="text-xs text-slate-400">
                                      {formatDuration(run.duration_seconds)}
                                    </p>
                                  </div>
                                  <ChevronRight className="w-4 h-4 text-slate-400" />
                                </div>
                              </div>
                              {run.has_errors && (
                                <div className="mt-2 flex items-center gap-2 text-xs text-red-400">
                                  <AlertCircle className="w-3 h-3" />
                                  Has errors
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <p className="text-slate-400 text-center py-8">
                        No batch runs found for this period
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Run Details Panel */}
              <div>
                <Card className="bg-slate-800/50 border-slate-700 sticky top-24">
                  <CardHeader>
                    <CardTitle className="text-white">Run Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {detailsLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                      </div>
                    ) : selectedRun ? (
                      <div className="space-y-4">
                        <div>
                          <p className="text-xs text-slate-500 uppercase mb-1">Run ID</p>
                          <p className="text-sm font-mono text-white break-all">
                            {selectedRun.batch_run_id}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-slate-500 uppercase mb-1">Triggered By</p>
                          <p className="text-sm text-white">{selectedRun.triggered_by}</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-xs text-slate-500 uppercase mb-1">Status</p>
                            <p className={`text-sm capitalize ${getStatusDisplay(selectedRun.status).color}`}>
                              {selectedRun.status}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 uppercase mb-1">Duration</p>
                            <p className="text-sm text-white">
                              {formatDuration(selectedRun.duration_seconds)}
                            </p>
                          </div>
                        </div>

                        <div>
                          <p className="text-xs text-slate-500 uppercase mb-1">Jobs</p>
                          <div className="flex items-center gap-2">
                            <span className="text-green-400">{selectedRun.jobs.completed} done</span>
                            <span className="text-slate-500">|</span>
                            <span className="text-red-400">{selectedRun.jobs.failed} failed</span>
                            <span className="text-slate-500">|</span>
                            <span className="text-slate-400">{selectedRun.jobs.total} total</span>
                          </div>
                        </div>

                        {Object.keys(selectedRun.phase_durations).length > 0 && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase mb-2">Phase Durations</p>
                            <div className="space-y-1">
                              {Object.entries(selectedRun.phase_durations).map(([phase, duration]) => (
                                <div key={phase} className="flex items-center justify-between text-xs">
                                  <span className="text-slate-400">{phase.replace(/_/g, ' ')}</span>
                                  <span className="text-white font-mono">
                                    {formatDuration(duration as number)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedRun.error_summary && (
                          <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg">
                            <p className="text-xs text-red-400 uppercase mb-2">Errors</p>
                            <p className="text-sm text-white mb-2">
                              {selectedRun.error_summary.count} error(s)
                            </p>
                            {selectedRun.error_summary.types.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {selectedRun.error_summary.types.map((type) => (
                                  <span
                                    key={type}
                                    className="px-2 py-0.5 bg-red-800/50 text-red-300 text-xs rounded"
                                  >
                                    {type}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Download Logs Section */}
                        <div className="pt-4 border-t border-slate-700">
                          <p className="text-xs text-slate-500 uppercase mb-3">Activity Logs</p>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => downloadLogs('txt')}
                              disabled={downloadLoading}
                              className="flex-1 bg-slate-700 border-slate-600 hover:bg-slate-600 text-white"
                            >
                              {downloadLoading ? (
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              ) : (
                                <FileText className="w-4 h-4 mr-2" />
                              )}
                              TXT
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => downloadLogs('json')}
                              disabled={downloadLoading}
                              className="flex-1 bg-slate-700 border-slate-600 hover:bg-slate-600 text-white"
                            >
                              {downloadLoading ? (
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              ) : (
                                <Download className="w-4 h-4 mr-2" />
                              )}
                              JSON
                            </Button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-400 text-center py-8">
                        Select a run to view details
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
