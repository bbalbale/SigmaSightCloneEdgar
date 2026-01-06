'use client'

import React, { useState } from 'react'
import { useUser, useAuth as useClerkAuth } from '@clerk/nextjs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  CreditCard,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ExternalLink,
  Folder,
  MessageSquare,
  Key,
} from 'lucide-react'
import { useUserEntitlements } from '@/hooks/useUserEntitlements'
import { apiClient } from '@/services/apiClient'

interface InviteFormState {
  code: string
  loading: boolean
  error: string | null
  success: boolean
}

export function AccountBillingSettings() {
  const { user: clerkUser } = useUser()
  const { entitlements, loading, error, refetch } = useUserEntitlements()
  const [inviteForm, setInviteForm] = useState<InviteFormState>({
    code: '',
    loading: false,
    error: null,
    success: false,
  })

  // Clerk domain for billing portal (from env)
  const clerkDomain = process.env.NEXT_PUBLIC_CLERK_DOMAIN || 'clerk.accounts.dev'
  const billingPortalUrl = `https://accounts.${clerkDomain}/user/billing`

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!inviteForm.code.trim()) {
      setInviteForm((prev) => ({ ...prev, error: 'Please enter an invite code' }))
      return
    }

    setInviteForm((prev) => ({ ...prev, loading: true, error: null }))

    try {
      await apiClient.post('/api/v1/onboarding/validate-invite', {
        invite_code: inviteForm.code.trim(),
      })

      setInviteForm((prev) => ({ ...prev, loading: false, success: true }))

      // Refetch entitlements to update the UI
      await refetch()
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message.includes('Invalid')
            ? 'Invalid invite code. Please check and try again.'
            : err.message
          : 'Failed to validate invite code'

      setInviteForm((prev) => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }))
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading account info...</span>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Invite Code Section (shown only if not validated) */}
      {entitlements && !entitlements.inviteValidated && (
        <Card className="border-amber-500/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-500">
              <Key className="h-5 w-5" />
              Enter Invite Code
            </CardTitle>
            <CardDescription>
              You need a valid invite code to unlock all features. Enter your code below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleInviteSubmit} className="space-y-4">
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="Enter your invite code"
                  value={inviteForm.code}
                  onChange={(e) =>
                    setInviteForm((prev) => ({
                      ...prev,
                      code: e.target.value,
                      error: null,
                    }))
                  }
                  disabled={inviteForm.loading || inviteForm.success}
                  className="flex-1"
                />
                <Button
                  type="submit"
                  disabled={inviteForm.loading || inviteForm.success}
                >
                  {inviteForm.loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : inviteForm.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    'Validate'
                  )}
                </Button>
              </div>

              {inviteForm.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{inviteForm.error}</AlertDescription>
                </Alert>
              )}

              {inviteForm.success && (
                <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    Invite code validated! You now have full access to SigmaSight.
                  </AlertDescription>
                </Alert>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {/* Subscription & Billing */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Subscription & Billing
          </CardTitle>
          <CardDescription>
            Manage your subscription and view usage
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Plan */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium">Current Plan</h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  variant={entitlements?.tier === 'paid' ? 'default' : 'secondary'}
                  className={
                    entitlements?.tier === 'paid'
                      ? 'bg-gradient-to-r from-purple-500 to-pink-500'
                      : ''
                  }
                >
                  {entitlements?.tier === 'paid' ? (
                    <>
                      <Sparkles className="h-3 w-3 mr-1" />
                      Pro
                    </>
                  ) : (
                    'Free'
                  )}
                </Badge>
              </div>
            </div>
            <Button asChild variant="outline">
              <a href={billingPortalUrl} target="_blank" rel="noopener noreferrer">
                Manage Subscription
                <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </div>

          {/* Usage Stats */}
          {entitlements && (
            <div className="space-y-4 pt-4 border-t">
              <h3 className="text-sm font-medium">Usage This Month</h3>

              {/* Portfolios */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <Folder className="h-4 w-4 text-muted-foreground" />
                    Portfolios
                  </span>
                  <span className="text-muted-foreground">
                    {entitlements.portfolioCount} / {entitlements.portfolioLimit}
                  </span>
                </div>
                <Progress
                  value={(entitlements.portfolioCount / entitlements.portfolioLimit) * 100}
                  className="h-2"
                />
              </div>

              {/* AI Messages */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    AI Messages
                  </span>
                  <span className="text-muted-foreground">
                    {entitlements.aiMessagesUsed} / {entitlements.aiMessagesLimit}
                  </span>
                </div>
                <Progress
                  value={(entitlements.aiMessagesUsed / entitlements.aiMessagesLimit) * 100}
                  className="h-2"
                />
              </div>
            </div>
          )}

          {/* Upgrade Prompt (Free users only) */}
          {entitlements?.shouldShowUpgrade && (
            <Alert className="border-purple-500/50 bg-purple-50 dark:bg-purple-950">
              <Sparkles className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              <AlertDescription className="text-purple-800 dark:text-purple-200">
                <strong>Upgrade to Pro</strong> for 10 portfolios and 1,000 AI messages/month.
                <Button
                  asChild
                  size="sm"
                  className="ml-4 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                >
                  <a href={billingPortalUrl} target="_blank" rel="noopener noreferrer">
                    Upgrade Now
                  </a>
                </Button>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Account Info */}
      {clerkUser && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Account Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Email</span>
              <span>{clerkUser.primaryEmailAddress?.emailAddress}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Account Created</span>
              <span>{clerkUser.createdAt ? new Date(clerkUser.createdAt).toLocaleDateString() : 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Invite Status</span>
              <span>
                {entitlements?.inviteValidated ? (
                  <Badge variant="outline" className="border-green-500 text-green-500">
                    Validated
                  </Badge>
                ) : (
                  <Badge variant="outline" className="border-amber-500 text-amber-500">
                    Pending
                  </Badge>
                )}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
