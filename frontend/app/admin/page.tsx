'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useAdminStore } from '@/stores/adminStore'
import { adminAuthService } from '@/services/adminAuthService'
import { adminApiService, DashboardOverview } from '@/services/adminApiService'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  LogOut,
  Users,
  MessageSquare,
  Activity,
  Settings,
  ShieldCheck,
  Clock,
  UserCheck,
  AlertCircle,
  CheckCircle2,
  Loader2,
  TrendingUp,
  Zap
} from 'lucide-react'

export default function AdminDashboardPage() {
  const router = useRouter()
  const { admin, clearAdmin } = useAdminStore()
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const data = await adminApiService.getDashboardOverview()
        setOverview(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }
    fetchOverview()
  }, [])

  const handleLogout = async () => {
    await adminAuthService.logout()
    clearAdmin()
    router.push('/admin/login')
  }

  // Quick stats cards with real data
  const quickStats = [
    {
      title: 'AI Requests',
      value: loading ? '--' : (overview?.ai.requests_today?.toLocaleString() || '0'),
      description: 'Today',
      icon: Zap,
      color: 'bg-purple-500'
    },
    {
      title: 'Avg Latency',
      value: loading ? '--' : (overview?.ai.avg_latency_ms ? `${Math.round(overview.ai.avg_latency_ms)}ms` : 'N/A'),
      description: 'Response time',
      icon: Clock,
      color: 'bg-orange-500'
    },
    {
      title: 'Error Rate',
      value: loading ? '--' : `${(overview?.ai.error_rate || 0).toFixed(1)}%`,
      description: 'AI requests',
      icon: AlertCircle,
      color: overview?.ai.error_rate && overview.ai.error_rate > 5 ? 'bg-red-500' : 'bg-green-500'
    },
    {
      title: 'Last Batch',
      value: loading ? '--' : (overview?.batch.last_run_status || 'N/A'),
      description: overview?.batch.last_run_at
        ? new Date(overview.batch.last_run_at).toLocaleDateString()
        : 'No recent runs',
      icon: overview?.batch.last_run_status === 'completed' ? CheckCircle2 : Settings,
      color: overview?.batch.last_run_status === 'completed' ? 'bg-green-500'
        : overview?.batch.last_run_status === 'failed' ? 'bg-red-500'
        : 'bg-slate-500'
    }
  ]

  // Navigation items for admin sections - NOW ENABLED
  const adminSections = [
    {
      title: 'Onboarding Analytics',
      description: 'Funnel visualization and error tracking',
      icon: TrendingUp,
      href: '/admin/onboarding',
      disabled: false
    },
    {
      title: 'AI Metrics',
      description: 'Performance, latency, token usage, and errors',
      icon: Activity,
      href: '/admin/ai',
      disabled: false
    },
    {
      title: 'Batch Processing',
      description: 'View batch job history and status',
      icon: Settings,
      href: '/admin/batch',
      disabled: false
    },
    {
      title: 'AI Tuning',
      description: 'Review AI responses and add annotations',
      icon: MessageSquare,
      href: '/admin/ai/tuning',
      disabled: true // Frontend not yet implemented
    },
    {
      title: 'User Management',
      description: 'View users and their onboarding journeys',
      icon: UserCheck,
      href: '/admin/users',
      disabled: true // Frontend not yet implemented
    }
  ]

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">Admin Dashboard</h1>
                <p className="text-xs text-slate-400">SigmaSight</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-white">{admin?.full_name}</p>
                <p className="text-xs text-slate-400">{admin?.role === 'super_admin' ? 'Super Admin' : 'Admin'}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-slate-400 hover:text-white hover:bg-slate-700"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">
            Welcome back, {admin?.full_name?.split(' ')[0]}
          </h2>
          <p className="text-slate-400">
            Monitor AI operations, track user onboarding, and analyze batch processing.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-700 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {quickStats.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title} className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                      {loading ? (
                        <Loader2 className="w-6 h-6 text-white animate-spin" />
                      ) : (
                        <Icon className="w-6 h-6 text-white" />
                      )}
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">{stat.value}</p>
                      <p className="text-sm text-slate-400">{stat.title}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">{stat.description}</p>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Admin Sections */}
        <h3 className="text-lg font-semibold text-white mb-4">Admin Sections</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {adminSections.map((section) => {
            const Icon = section.icon
            return (
              <Card
                key={section.title}
                className={`bg-slate-800/50 border-slate-700 transition-all ${
                  section.disabled
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:bg-slate-800 hover:border-slate-600 cursor-pointer'
                }`}
                onClick={() => !section.disabled && router.push(section.href)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-700 rounded-lg flex items-center justify-center">
                      <Icon className="w-5 h-5 text-slate-300" />
                    </div>
                    <div>
                      <CardTitle className="text-white text-base">{section.title}</CardTitle>
                      {section.disabled && (
                        <span className="text-xs text-yellow-500">Coming Soon</span>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-slate-400">
                    {section.description}
                  </CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Implementation Status */}
        <div className="mt-8 p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Implementation Status</h4>
          <div className="flex flex-wrap gap-2">
            <span className="px-2 py-1 bg-green-900/30 border border-green-700 text-green-400 text-xs rounded">
              Phase 1-5: Backend Complete
            </span>
            <span className="px-2 py-1 bg-blue-900/30 border border-blue-700 text-blue-400 text-xs rounded">
              Phase 6: Frontend In Progress
            </span>
            <span className="px-2 py-1 bg-slate-700 text-slate-400 text-xs rounded">
              Phase 7: Aggregation Pending
            </span>
          </div>
        </div>
      </main>
    </div>
  )
}
