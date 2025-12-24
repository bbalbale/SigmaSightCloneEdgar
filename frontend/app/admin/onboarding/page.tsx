'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useAdminStore } from '@/stores/adminStore'
import { adminAuthService } from '@/services/adminAuthService'
import {
  adminApiService,
  OnboardingFunnel,
  OnboardingErrors,
  OnboardingDaily
} from '@/services/adminApiService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ArrowLeft,
  TrendingUp,
  AlertCircle,
  Users,
  UserPlus,
  LogIn,
  Briefcase,
  MessageSquare,
  Loader2,
  ChevronDown,
  ArrowRight
} from 'lucide-react'

export default function OnboardingAnalyticsPage() {
  const router = useRouter()
  const { admin } = useAdminStore()
  const [funnel, setFunnel] = useState<OnboardingFunnel | null>(null)
  const [errors, setErrors] = useState<OnboardingErrors | null>(null)
  const [daily, setDaily] = useState<OnboardingDaily | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [funnelData, errorsData, dailyData] = await Promise.all([
          adminApiService.getOnboardingFunnel(days),
          adminApiService.getOnboardingErrors(days),
          adminApiService.getOnboardingDaily(days)
        ])
        setFunnel(funnelData)
        setErrors(errorsData)
        setDaily(dailyData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [days])

  // Funnel step icons
  const stepIcons: Record<string, typeof Users> = {
    register_start: UserPlus,
    register_complete: Users,
    login_success: LogIn,
    portfolio_complete: Briefcase,
    chat_session_start: MessageSquare
  }

  // Get funnel step color based on position
  const getStepColor = (index: number, total: number) => {
    const colors = ['bg-blue-500', 'bg-indigo-500', 'bg-purple-500', 'bg-pink-500', 'bg-rose-500']
    return colors[index % colors.length]
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
                <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-white">Onboarding Analytics</h1>
                  <p className="text-xs text-slate-400">User funnel and error tracking</p>
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
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
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
            <span className="ml-3 text-slate-400">Loading analytics...</span>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                      <UserPlus className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {funnel?.total_started || 0}
                      </p>
                      <p className="text-sm text-slate-400">Started Registration</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
                      <Users className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {funnel?.total_completed || 0}
                      </p>
                      <p className="text-sm text-slate-400">Completed Onboarding</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
                      <TrendingUp className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        {funnel?.overall_conversion_rate?.toFixed(1) || 0}%
                      </p>
                      <p className="text-sm text-slate-400">Overall Conversion</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Funnel Visualization */}
            <Card className="bg-slate-800/50 border-slate-700 mb-8">
              <CardHeader>
                <CardTitle className="text-white">Onboarding Funnel</CardTitle>
                <CardDescription className="text-slate-400">
                  User progression through registration steps
                </CardDescription>
              </CardHeader>
              <CardContent>
                {funnel?.funnel_steps && funnel.funnel_steps.length > 0 ? (
                  <div className="space-y-4">
                    {funnel.funnel_steps.map((step, index) => {
                      const Icon = stepIcons[step.step] || Users
                      const widthPercent = funnel.total_started > 0
                        ? (step.count / funnel.total_started) * 100
                        : 0
                      return (
                        <div key={step.step} className="relative">
                          <div className="flex items-center gap-4 mb-2">
                            <div className={`w-10 h-10 ${getStepColor(index, funnel.funnel_steps.length)} rounded-lg flex items-center justify-center`}>
                              <Icon className="w-5 h-5 text-white" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-white capitalize">
                                  {step.step.replace(/_/g, ' ')}
                                </span>
                                <span className="text-sm text-slate-400">
                                  {step.count} users
                                </span>
                              </div>
                              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${getStepColor(index, funnel.funnel_steps.length)} transition-all duration-500`}
                                  style={{ width: `${widthPercent}%` }}
                                />
                              </div>
                            </div>
                            {step.drop_off_rate !== null && step.drop_off_rate > 0 && (
                              <div className="text-right min-w-[80px]">
                                <span className="text-xs text-red-400">
                                  -{step.drop_off_rate.toFixed(1)}%
                                </span>
                              </div>
                            )}
                          </div>
                          {index < funnel.funnel_steps.length - 1 && (
                            <div className="flex justify-center py-1">
                              <ChevronDown className="w-4 h-4 text-slate-600" />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-slate-400 text-center py-8">
                    No funnel data available for this period
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Error Breakdown */}
            <Card className="bg-slate-800/50 border-slate-700 mb-8">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  Error Breakdown
                </CardTitle>
                <CardDescription className="text-slate-400">
                  {errors?.total_errors || 0} total errors in the last {days} days
                </CardDescription>
              </CardHeader>
              <CardContent>
                {errors?.breakdown && errors.breakdown.length > 0 ? (
                  <div className="space-y-3">
                    {errors.breakdown.map((err) => (
                      <div
                        key={err.error_code}
                        className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono text-red-400">
                              {err.error_code}
                            </span>
                            <span className="text-xs text-slate-500">
                              ({err.percentage.toFixed(1)}%)
                            </span>
                          </div>
                          {err.sample_messages && err.sample_messages.length > 0 && (
                            <p className="text-xs text-slate-400 mt-1 truncate">
                              {err.sample_messages[0]}
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <span className="text-lg font-bold text-white">{err.count}</span>
                          <p className="text-xs text-slate-500">occurrences</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-center py-8">
                    No errors recorded in this period
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Daily Trends */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Daily Activity</CardTitle>
                <CardDescription className="text-slate-400">
                  Event counts by day
                </CardDescription>
              </CardHeader>
              <CardContent>
                {daily?.trends && daily.trends.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-2 px-3 text-slate-400 font-medium">Date</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-medium">Registrations</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-medium">Logins</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-medium">Portfolios</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-medium">Chats</th>
                        </tr>
                      </thead>
                      <tbody>
                        {daily.trends.slice(0, 14).map((day) => (
                          <tr key={day.date} className="border-b border-slate-700/50">
                            <td className="py-2 px-3 text-white">
                              {new Date(day.date).toLocaleDateString()}
                            </td>
                            <td className="text-right py-2 px-3 text-slate-300">
                              {day.events['onboarding.register_complete'] || 0}
                            </td>
                            <td className="text-right py-2 px-3 text-slate-300">
                              {day.events['onboarding.login_success'] || 0}
                            </td>
                            <td className="text-right py-2 px-3 text-slate-300">
                              {day.events['onboarding.portfolio_complete'] || 0}
                            </td>
                            <td className="text-right py-2 px-3 text-slate-300">
                              {day.events['chat.session_start'] || 0}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-slate-400 text-center py-8">
                    No daily data available
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
