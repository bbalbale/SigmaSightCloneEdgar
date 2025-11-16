'use client'

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Upload, TrendingUp } from 'lucide-react'

/**
 * CTA Banner shown to authenticated users without a portfolio
 *
 * Phase 2.4: Post-Login UX Flow
 * Guides new users to upload their first portfolio after login
 */
export function UploadPortfolioBanner() {
  const router = useRouter()

  const handleUploadClick = () => {
    router.push('/onboarding/upload')
  }

  return (
    <div className="px-4 pt-8 pb-4">
      <div className="container mx-auto">
        <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1 space-y-2">
              <AlertTitle className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                Welcome to SigmaSight!
              </AlertTitle>
              <AlertDescription className="text-blue-800 dark:text-blue-200">
                Get started by uploading your first portfolio. You can import positions from a CSV file or enter them manually.
                Once uploaded, you'll see real-time analytics, risk metrics, and AI-powered insights.
              </AlertDescription>
              <div className="pt-2">
                <Button
                  onClick={handleUploadClick}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Your First Portfolio
                </Button>
              </div>
            </div>
          </div>
        </Alert>
      </div>
    </div>
  )
}
