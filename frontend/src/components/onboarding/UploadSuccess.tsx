'use client'

import { useEffect } from 'react'
import { Check, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { ChecklistState } from '@/hooks/usePortfolioUpload'

interface UploadSuccessProps {
  portfolioName: string
  positionsImported: number
  positionsFailed?: number
  checklist: ChecklistState
  onContinue: () => void
  isFromSettings?: boolean
}

const checklistLabels: Record<string, string> = {
  portfolio_created: 'Portfolio created',
  positions_imported: 'Positions imported',
  symbol_extraction: 'Symbols extracted',
  security_enrichment: 'Securities enriched',
  price_bootstrap: 'Price cache ready',
  market_data_collection: 'Market data collected',
  pnl_calculation: 'P&L calculated',
  position_values: 'Position values computed',
  market_beta: 'Market beta analyzed',
  ir_beta: 'Interest rate beta analyzed',
  factor_spread: 'Spread factors computed',
  factor_ridge: 'Ridge factors computed',
  sector_analysis: 'Sector analysis complete',
  volatility: 'Volatility calculated',
  correlations: 'Correlations computed',
}

export function UploadSuccess({ portfolioName, positionsImported, positionsFailed = 0, checklist, onContinue, isFromSettings }: UploadSuccessProps) {
  useEffect(() => {
    // Trigger confetti animation on mount
    // NOTE: Requires canvas-confetti or react-confetti package
    // Installation: npm install canvas-confetti
    // Then uncomment and use:

    /*
    import confetti from 'canvas-confetti';

    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });

    // Trigger again after 200ms for extra celebration
    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 60,
        spread: 55,
        origin: { x: 0 }
      });
      confetti({
        particleCount: 50,
        angle: 120,
        spread: 55,
        origin: { x: 1 }
      });
    }, 200);
    */

    // Temporary fallback: console celebration
    console.log('🎉 Portfolio upload successful!');
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg border-green-200 dark:border-green-900">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="rounded-full bg-green-100 dark:bg-green-900/20 p-3">
                <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-green-900 dark:text-green-100">
                  🎉 Portfolio Ready!
                </CardTitle>
                <CardDescription className="text-green-700 dark:text-green-300">
                  Your portfolio has been successfully uploaded and analyzed
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Summary */}
            <div className="bg-green-50 dark:bg-green-950 rounded-lg p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-green-900 dark:text-green-100">
                  Portfolio Name:
                </span>
                <span className="text-sm text-green-700 dark:text-green-300">
                  {portfolioName}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-green-900 dark:text-green-100">
                  Positions Imported:
                </span>
                <span className="text-sm text-green-700 dark:text-green-300">
                  {positionsImported} {positionsFailed > 0 ? `(${positionsFailed} failed)` : ''}
                </span>
              </div>
            </div>

            {/* Completed Checklist */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Completed tasks:
              </p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(checklistLabels).map(([key, label]) => (
                  <div
                    key={key}
                    className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300"
                  >
                    <Check className="h-3 w-3" />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* What's Next */}
            <div className="border-t pt-4">
              <p className="text-sm font-medium mb-2">What's next?</p>
              <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                <li>• View your portfolio dashboard</li>
                <li>• Explore risk metrics and factor exposures</li>
                <li>• Analyze position correlations</li>
                <li>• Review stress test scenarios</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter>
            <Button
              className="w-full"
              size="lg"
              onClick={onContinue}
            >
              Continue to Dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
