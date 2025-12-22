"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, Loader2, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { adminAuthService } from '@/services/adminAuthService'
import { useAdminStore } from '@/stores/adminStore'

export function AdminLoginForm() {
  const router = useRouter()
  const { setAdmin, setLoading, setError: setStoreError } = useAdminStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setStoreError(null)
    setIsLoading(true)
    setLoading(true)

    try {
      const response = await adminAuthService.login({ email, password })

      // Update store with admin data
      setAdmin({
        id: response.admin_id,
        email: response.email,
        full_name: response.full_name,
        role: response.role as 'admin' | 'super_admin',
        is_active: true,
        created_at: new Date().toISOString(),
        last_login_at: new Date().toISOString()
      })

      // Redirect to admin dashboard
      router.push('/admin')
    } catch (err: any) {
      console.error('Admin login error:', err)
      const errorMessage = err?.message || 'Failed to login. Please check your credentials.'
      setError(errorMessage)
      setStoreError(errorMessage)
    } finally {
      setIsLoading(false)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-md space-y-8 px-4">
        <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
          <CardHeader className="space-y-1 text-center">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center">
                <ShieldCheck className="w-10 h-10 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold text-white">Admin Dashboard</CardTitle>
            <CardDescription className="text-slate-400">
              Sign in with your admin credentials
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-slate-300"
                >
                  Email address
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@sigmasight.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                  autoComplete="email"
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-slate-300"
                >
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required
                  autoComplete="current-password"
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 text-sm text-red-400 bg-red-900/30 border border-red-800 rounded-md">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in to Admin'
                )}
              </Button>

              <div className="text-center pt-4">
                <Button
                  type="button"
                  variant="ghost"
                  className="text-slate-400 hover:text-white hover:bg-slate-700"
                  onClick={() => router.push('/login')}
                >
                  Back to User Login
                </Button>
              </div>
            </CardContent>
          </form>
        </Card>

        <p className="text-center text-xs text-slate-500">
          Admin access is restricted to authorized personnel only.
        </p>
      </div>
    </div>
  )
}
