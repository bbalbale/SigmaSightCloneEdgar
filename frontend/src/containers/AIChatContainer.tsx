'use client'

import React from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '../../app/providers'
import { useTheme } from '@/contexts/ThemeContext'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { ChatConversationPane } from '@/components/chat/ChatConversationPane'
import { cn } from '@/lib/utils'

export function AIChatContainer() {
  const searchParams = useSearchParams()
  const initialMessage = searchParams.get('message')
  const { user, loading } = useAuth()
  const portfolioId = usePortfolioStore((state) => state.portfolioId)
  const portfolioName = usePortfolioStore((state) => state.portfolioName)
  const { theme } = useTheme()

  // Comprehensive logging for debugging message flow
  React.useEffect(() => {
    console.log('[AIChatContainer] Component mounted/updated with:', {
      hasSearchParams: !!searchParams,
      initialMessage,
      searchParamsString: searchParams.toString(),
      user: user?.fullName,
      portfolioId
    })
  }, [searchParams, initialMessage, user, portfolioId])

  if (loading) {
    return (
      <div
        className={cn(
          'min-h-screen flex items-center justify-center px-4',
          theme === 'dark' ? 'bg-slate-950' : 'bg-gray-50'
        )}
      >
        <div className="text-sm text-gray-500">Loading AI chat experience…</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const portfolioLabel =
    portfolioName ??
    (portfolioId ? `Portfolio ${portfolioId.slice(0, 8)}…` : 'Portfolio unavailable')

  return (
    <div
      className={cn(
        'min-h-screen py-10 px-4 transition-colors duration-300',
        theme === 'dark' ? 'bg-slate-950' : 'bg-gray-50'
      )}
    >
      <div className="container mx-auto max-w-5xl flex flex-col gap-8">
        <header className="flex flex-col gap-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <p className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-gray-600')}>
                Signed in as {user.fullName}
              </p>
              <h1 className={cn('text-2xl font-semibold', theme === 'dark' ? 'text-white' : 'text-gray-900')}>
                AI Portfolio Assistant
              </h1>
            </div>
            <div
              className={cn(
                'text-xs px-3 py-1 rounded-full border',
                theme === 'dark'
                  ? 'border-slate-700 text-slate-300 bg-slate-900/60'
                  : 'border-gray-200 text-gray-600 bg-white'
              )}
            >
              {portfolioLabel}
            </div>
          </div>
          <p className={cn('text-sm max-w-3xl', theme === 'dark' ? 'text-slate-300' : 'text-gray-600')}>
            Ask SigmaSight for diagnostics, factor exposure breakdowns, or risk mitigation ideas. Responses
            reuse the same authenticated streaming pipeline as the dashboard chat bar.
          </p>
          {!portfolioId && (
            <div
              className={cn(
                'text-xs px-3 py-2 rounded-lg border',
                theme === 'dark'
                  ? 'border-red-700 bg-red-900/40 text-red-200'
                  : 'border-red-200 bg-red-50 text-red-700'
              )}
            >
              Portfolio context is still loading. Conversations may be limited until your portfolio ID is resolved.
            </div>
          )}
        </header>

        <ChatConversationPane
          variant="inline"
          isActive
          title="Conversation"
          subtitle="Responses include real-time portfolio context and risk analytics."
          className="min-h-[560px]"
          initialMessage={initialMessage || undefined}
        />
      </div>
    </div>
  )
}
