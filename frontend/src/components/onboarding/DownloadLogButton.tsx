'use client'

import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { onboardingService } from '@/services/onboardingService'

export interface DownloadLogButtonProps {
  portfolioId: string
  disabled?: boolean
  variant?: 'default' | 'secondary' | 'outline' | 'ghost'
  className?: string
}

/**
 * Button to download the complete onboarding activity log
 *
 * Only shown on completion and error screens (not during progress).
 */
export function DownloadLogButton({
  portfolioId,
  disabled = false,
  variant = 'outline',
  className,
}: DownloadLogButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async () => {
    if (!portfolioId || isDownloading) return

    setIsDownloading(true)
    setError(null)

    try {
      await onboardingService.downloadLogs(portfolioId, 'txt')
    } catch (err) {
      setError('Failed to download log')
      console.error('Download log error:', err)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <Button
        onClick={handleDownload}
        disabled={disabled || isDownloading}
        variant={variant}
        className={className}
      >
        {isDownloading ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Download className="h-4 w-4 mr-2" />
        )}
        Download Log
      </Button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  )
}

export default DownloadLogButton
