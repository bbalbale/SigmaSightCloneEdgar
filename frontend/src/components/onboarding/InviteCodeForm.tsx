'use client'

import React, { useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Key, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { apiClient } from '@/services/apiClient'

interface InviteCodeFormProps {
  onSuccess: () => void
}

export function InviteCodeForm({ onSuccess }: InviteCodeFormProps) {
  const { getToken } = useAuth()
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!code.trim()) {
      setError('Please enter an invite code')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Get fresh Clerk token using custom template with 1-hour lifetime
      const token = await getToken({ template: 'sigmasight-session' })
      if (!token) {
        setError('Authentication error. Please refresh and try again.')
        setLoading(false)
        return
      }

      await apiClient.post(
        '/api/v1/onboarding/validate-invite',
        { invite_code: code.trim() },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      setSuccess(true)
      setLoading(false)
      // User will click "Continue" button to proceed
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message.includes('Invalid')
            ? 'Invalid invite code. Please check and try again.'
            : err.message
          : 'Failed to validate invite code'

      setError(errorMessage)
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-zinc-700 bg-zinc-900">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800">
            <Key className="h-6 w-6 text-zinc-100" />
          </div>
          <CardTitle className="text-2xl text-zinc-100">
            Enter Your Invite Code
          </CardTitle>
          <CardDescription className="text-zinc-400">
            SigmaSight is currently in private beta. Enter your invite code to get started.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="text"
                placeholder="Enter invite code"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value)
                  setError(null)
                }}
                disabled={loading || success}
                className="bg-zinc-800 border-zinc-600 text-zinc-100 placeholder:text-zinc-500"
              />
            </div>

            {success ? (
              <Button
                type="button"
                onClick={onSuccess}
                className="w-full bg-green-600 hover:bg-green-700 text-white"
              >
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Continue to Portfolio Upload
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-zinc-100 hover:bg-zinc-200 text-zinc-900"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Validating...
                  </>
                ) : (
                  'Continue'
                )}
              </Button>
            )}

            {error && (
              <Alert variant="destructive" className="border-red-500/50 bg-red-950">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {success && (
              <Alert className="border-green-500/50 bg-green-950">
                <CheckCircle2 className="h-4 w-4 text-green-400" />
                <AlertDescription className="text-green-200">
                  Invite code validated! Proceeding to portfolio setup...
                </AlertDescription>
              </Alert>
            )}
          </form>

          <p className="mt-6 text-center text-sm text-zinc-500">
            Don&apos;t have an invite code?{' '}
            <a
              href="mailto:support@sigmasight.io"
              className="text-zinc-400 hover:text-zinc-100 underline"
            >
              Request access
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
