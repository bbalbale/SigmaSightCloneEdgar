'use client'

import { AlertCircle, Download, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { onboardingService } from '@/services/onboardingService'

export interface ValidationError {
  row: number
  symbol?: string
  error_code: string
  message: string
  field?: string
}

interface ValidationErrorsProps {
  errors: ValidationError[]
  onTryAgain: () => void
}

export function ValidationErrors({ errors, onTryAgain }: ValidationErrorsProps) {
  const handleDownloadTemplate = () => {
    onboardingService.downloadTemplate()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg border-red-200 dark:border-red-900">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="rounded-full bg-red-100 dark:bg-red-900/20 p-3">
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-red-900 dark:text-red-100">CSV Validation Failed</CardTitle>
                <CardDescription className="text-red-700 dark:text-red-300">
                  We found some issues with your CSV file. Please fix these issues and try again.
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertTitle>
                ❌ We found {errors.length} {errors.length === 1 ? 'issue' : 'issues'} with your CSV file:
              </AlertTitle>
            </Alert>

            <div className="space-y-2 max-h-96 overflow-y-auto">
              <ul className="space-y-3">
                {errors.map((error, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span className="text-red-600 dark:text-red-400 font-bold">•</span>
                    <div className="flex-1">
                      <span className="font-medium">
                        Row {error.row}
                        {error.symbol && `: ${error.symbol}`}
                      </span>
                      <br />
                      <span className="text-muted-foreground">
                        {error.message}
                        {error.field && (
                          <span className="text-xs ml-1">
                            (field: {error.field})
                          </span>
                        )}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                <strong>Tips for fixing your CSV:</strong>
              </p>
              <ul className="text-sm text-muted-foreground space-y-1 mt-2 ml-4">
                <li>• Make sure all required columns are present (Symbol, Quantity, Entry Price, Entry Date)</li>
                <li>• Check date format is YYYY-MM-DD (e.g., 2024-01-15)</li>
                <li>• Ensure quantities are numeric and non-zero</li>
                <li>• Verify entry prices are positive numbers</li>
                <li>• No duplicate positions (same symbol + entry date)</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleDownloadTemplate}
            >
              <Download className="mr-2 h-4 w-4" />
              Download Template
            </Button>
            <Button
              className="flex-1"
              onClick={onTryAgain}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
