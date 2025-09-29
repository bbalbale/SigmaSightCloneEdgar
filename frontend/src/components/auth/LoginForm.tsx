"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { chatAuthService } from '@/services/chatAuthService'
import { AlertCircle, Loader2, User, Building2, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

export function LoginForm() {
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
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-lg space-y-8 px-4">
        <Card>
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-2xl font-bold">Sign in to SigmaSight</CardTitle>
            <CardDescription>
              Use demo credentials or your account
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Email address
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
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
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </CardContent>
          </form>

          <CardFooter className="flex flex-col space-y-4">
            <div className="relative w-full">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Or use demo account
                </span>
              </div>
            </div>

            <div className="w-full space-y-3">
              <p className="text-xs text-center text-muted-foreground">
                All demo accounts use password: <span className="font-mono font-semibold">demo12345</span>
              </p>

              {demoAccounts.map((account) => {
                const Icon = account.icon
                return (
                  <Button
                    key={account.email}
                    type="button"
                    variant="outline"
                    className="w-full justify-start h-auto p-4"
                    onClick={() => handleFillCredentials(account.email)}
                  >
                    <div className="flex items-start w-full gap-3">
                      <div className="flex-shrink-0 w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <div className="text-left flex-1 min-w-0">
                        <p className="text-sm font-medium">{account.name}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 break-words">{account.description}</p>
                        <p className="text-xs font-mono text-primary mt-1 break-all">{account.email}</p>
                      </div>
                      <div className="ml-auto pl-2 text-xs text-muted-foreground self-center whitespace-nowrap">
                        Click to fill
                      </div>
                    </div>
                  </Button>
                )
              })}
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}