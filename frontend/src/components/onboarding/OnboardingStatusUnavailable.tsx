'use client'

import { AlertTriangle, RefreshCw, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export interface OnboardingStatusUnavailableProps {
  onRefresh: () => void
  onViewPortfolio: () => void
}

/**
 * Screen shown when status endpoint returns not_found mid-run
 *
 * This can happen due to server restart, network issues, etc.
 * Shown after 3 consecutive not_found responses.
 */
export function OnboardingStatusUnavailable({
  onRefresh,
  onViewPortfolio,
}: OnboardingStatusUnavailableProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-slate-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto rounded-full p-4 bg-gray-100 dark:bg-gray-800 w-fit mb-4">
              <AlertTriangle className="h-10 w-10 text-gray-500" />
            </div>
            <CardTitle className="text-xl">Status Unavailable</CardTitle>
            <CardDescription className="text-base">
              Unable to fetch status updates.
              <br />
              Your portfolio setup is still running in the background.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={onRefresh} variant="outline" className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Refresh Status
              </Button>
              <Button onClick={onViewPortfolio} className="gap-2">
                View Portfolio
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingStatusUnavailable
