'use client'

import React from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Sparkles, Folder, MessageSquare, AlertCircle } from 'lucide-react'

interface UpgradePromptProps {
  /**
   * Type of limit reached
   */
  type: 'portfolio' | 'ai_message'

  /**
   * Current usage count
   */
  current: number

  /**
   * Maximum allowed
   */
  limit: number

  /**
   * Whether to show as a blocking alert or inline prompt
   */
  variant?: 'blocking' | 'inline'

  /**
   * Additional CSS classes
   */
  className?: string
}

export function UpgradePrompt({
  type,
  current,
  limit,
  variant = 'inline',
  className = '',
}: UpgradePromptProps) {
  const clerkDomain = process.env.NEXT_PUBLIC_CLERK_DOMAIN || 'clerk.accounts.dev'
  const billingPortalUrl = `https://accounts.${clerkDomain}/user/billing`

  const isAtLimit = current >= limit

  if (!isAtLimit) {
    return null
  }

  const content = {
    portfolio: {
      icon: Folder,
      title: 'Portfolio Limit Reached',
      description: `You've reached your limit of ${limit} portfolios on the Free plan.`,
      action: 'Upgrade to create more portfolios',
    },
    ai_message: {
      icon: MessageSquare,
      title: 'AI Message Limit Reached',
      description: `You've used all ${limit} AI messages this month.`,
      action: 'Upgrade for 1,000 messages/month',
    },
  }

  const config = content[type]
  const Icon = config.icon

  if (variant === 'blocking') {
    return (
      <Alert
        className={`border-amber-500/50 bg-amber-50 dark:bg-amber-950 ${className}`}
      >
        <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <AlertTitle className="text-amber-800 dark:text-amber-200">
          {config.title}
        </AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300">
          <p className="mb-3">{config.description}</p>
          <div className="flex gap-2">
            <Button
              asChild
              size="sm"
              className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
            >
              <a href={billingPortalUrl} target="_blank" rel="noopener noreferrer">
                <Sparkles className="mr-2 h-4 w-4" />
                {config.action}
              </a>
            </Button>
            <Button asChild size="sm" variant="outline">
              <a href="/settings">Manage Usage</a>
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    )
  }

  // Inline variant - more compact
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/50 ${className}`}
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <span className="text-sm text-amber-800 dark:text-amber-200">
          {config.description}
        </span>
      </div>
      <Button
        asChild
        size="sm"
        variant="outline"
        className="border-purple-500 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950"
      >
        <a href={billingPortalUrl} target="_blank" rel="noopener noreferrer">
          <Sparkles className="mr-1 h-3 w-3" />
          Upgrade
        </a>
      </Button>
    </div>
  )
}

/**
 * Hook-friendly wrapper to get limit status
 * Can be used in components to check if user is at limit
 */
export function usePortfolioLimitStatus(
  portfolioCount: number,
  portfolioLimit: number
): { isAtLimit: boolean; canCreate: boolean } {
  return {
    isAtLimit: portfolioCount >= portfolioLimit,
    canCreate: portfolioCount < portfolioLimit,
  }
}

export function useAiMessageLimitStatus(
  messagesUsed: number,
  messagesLimit: number
): { isAtLimit: boolean; canSend: boolean } {
  return {
    isAtLimit: messagesUsed >= messagesLimit,
    canSend: messagesUsed < messagesLimit,
  }
}
