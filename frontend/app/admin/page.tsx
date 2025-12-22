'use client'

import { useRouter } from 'next/navigation'
import { useAdminStore } from '@/stores/adminStore'
import { adminAuthService } from '@/services/adminAuthService'
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
  UserCheck
} from 'lucide-react'

export default function AdminDashboardPage() {
  const router = useRouter()
  const { admin, clearAdmin } = useAdminStore()

  const handleLogout = async () => {
    await adminAuthService.logout()
    clearAdmin()
    router.push('/admin/login')
  }

  // Quick stats cards (placeholder data - will be replaced with real data later)
  const quickStats = [
    {
      title: 'Total Users',
      value: '--',
      description: 'Registered users',
      icon: Users,
      color: 'bg-blue-500'
    },
    {
      title: 'Active Conversations',
      value: '--',
      description: 'Last 24 hours',
      icon: MessageSquare,
      color: 'bg-green-500'
    },
    {
      title: 'AI Requests',
      value: '--',
      description: 'Today',
      icon: Activity,
      color: 'bg-purple-500'
    },
    {
      title: 'Avg Response Time',
      value: '--',
      description: 'Last hour',
      icon: Clock,
      color: 'bg-orange-500'
    }
  ]

  // Navigation items for admin sections
  const adminSections = [
    {
      title: 'User Management',
      description: 'View users and their onboarding journeys',
      icon: UserCheck,
      href: '/admin/users',
      disabled: true
    },
    {
      title: 'AI Tuning',
      description: 'Review AI responses and add annotations',
      icon: MessageSquare,
      href: '/admin/ai/tuning',
      disabled: true
    },
    {
      title: 'Onboarding Analytics',
      description: 'Funnel visualization and error tracking',
      icon: Activity,
      href: '/admin/onboarding',
      disabled: true
    },
    {
      title: 'Batch Processing',
      description: 'View batch job history and status',
      icon: Settings,
      href: '/admin/batch',
      disabled: true
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
            Monitor AI operations, track user onboarding, and tune AI responses.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {quickStats.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title} className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                      <Icon className="w-6 h-6 text-white" />
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {adminSections.map((section) => {
            const Icon = section.icon
            return (
              <Card
                key={section.title}
                className={`bg-slate-800/50 border-slate-700 ${section.disabled ? 'opacity-50' : 'hover:bg-slate-800 cursor-pointer'}`}
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

        {/* Phase 1 Status */}
        <div className="mt-8 p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Implementation Status</h4>
          <div className="flex flex-wrap gap-2">
            <span className="px-2 py-1 bg-green-900/30 border border-green-700 text-green-400 text-xs rounded">
              Phase 1: Admin Auth Complete
            </span>
            <span className="px-2 py-1 bg-slate-700 text-slate-400 text-xs rounded">
              Phase 2: AI Tuning - Pending
            </span>
            <span className="px-2 py-1 bg-slate-700 text-slate-400 text-xs rounded">
              Phase 3-7: Coming Soon
            </span>
          </div>
        </div>
      </main>
    </div>
  )
}
