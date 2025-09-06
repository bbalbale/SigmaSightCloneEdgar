"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { chatAuthService } from '@/services/chatAuthService'
import { AlertCircle, Loader2, User, Building2, TrendingUp } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const demoAccounts = [
    {
      name: 'High Net Worth Portfolio',
      email: 'demo_hnw@sigmasight.com',
      portfolioType: 'high-net-worth',
      icon: TrendingUp,
      description: 'Multi-asset portfolio with advanced analytics'
    },
    {
      name: 'Individual Investor',
      email: 'demo_individual@sigmasight.com',
      portfolioType: 'individual',
      icon: User,
      description: 'Personal investment portfolio'
    },
    {
      name: 'Hedge Fund',
      email: 'demo_hedgefundstyle@sigmasight.com',
      portfolioType: 'hedge-fund',
      icon: Building2,
      description: 'Institutional portfolio with complex strategies'
    }
  ]
  
  const handleFillCredentials = (demoEmail: string) => {
    setEmail(demoEmail)
    setPassword('demo12345')
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const response = await chatAuthService.login(email, password)
      console.log('Login successful:', response.user)
      
      // Determine portfolio type based on email
      let portfolioType = 'high-net-worth' // default
      const account = demoAccounts.find(acc => acc.email === email)
      if (account) {
        portfolioType = account.portfolioType
      }
      
      // Redirect to portfolio page after successful login
      router.push(`/portfolio?type=${portfolioType}`)
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.message || 'Failed to login. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to SigmaSight
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Use demo credentials or your account
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 text-sm text-red-800 bg-red-50 rounded-md">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </div>

        </form>
        
        <div className="mt-8">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">Or use demo account</span>
            </div>
          </div>
          
          <div className="mt-6 space-y-3">
            <p className="text-xs text-center text-gray-500 mb-4">
              All demo accounts use password: <span className="font-mono font-semibold">demo12345</span>
            </p>
            
            {demoAccounts.map((account) => {
              const Icon = account.icon
              return (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => handleFillCredentials(account.email)}
                  className="w-full flex items-start p-3 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-300 transition-colors group"
                >
                  <div className="flex-shrink-0 w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center group-hover:bg-blue-100">
                    <Icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="ml-3 text-left flex-1">
                    <p className="text-sm font-medium text-gray-900">{account.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{account.description}</p>
                    <p className="text-xs font-mono text-blue-600 mt-1">{account.email}</p>
                  </div>
                  <div className="ml-2 text-xs text-gray-400 self-center">
                    Click to fill
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}