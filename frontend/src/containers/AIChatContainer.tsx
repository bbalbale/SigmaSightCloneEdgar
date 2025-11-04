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
  const currentPortfolio = usePortfolioStore((state) => {
    const id = state.portfolioId
    if (!id) return null
    return state.portfolios.find((p) => p.id === id) ?? null
  })
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
      <div className="min-h-screen flex items-center justify-center px-4 transition-colors duration-300" style={{
        backgroundColor: 'var(--bg-primary)'
      }}>
        <div className="text-sm text-tertiary">Loading AI chat experience…</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const portfolioLabel =
    currentPortfolio?.account_name ??
    (portfolioId ? `Portfolio ${portfolioId.slice(0, 8)}…` : 'Portfolio unavailable')

  return (
    <div className="min-h-screen py-10 px-4 transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-primary)'
    }}>
      <div className="container mx-auto max-w-5xl flex flex-col gap-8">
        <header className="flex flex-col gap-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <p className="text-sm text-secondary">
                Signed in as {user.fullName}
              </p>
              <h1 className="font-semibold transition-colors duration-300" style={{
                fontSize: 'var(--text-2xl)',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-display)'
              }}>
                AI Portfolio Assistant
              </h1>
            </div>
            <div className="text-xs px-3 py-1 rounded-full transition-colors duration-300" style={{
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              backgroundColor: 'var(--bg-secondary)'
            }}>
              {portfolioLabel}
            </div>
          </div>
          <p className="text-sm max-w-3xl text-secondary">
            Ask SigmaSight for diagnostics, factor exposure breakdowns, or risk mitigation ideas. Responses
            reuse the same authenticated streaming pipeline as the dashboard chat bar.
          </p>
          {!portfolioId && (
            <div className="text-xs px-3 py-2 rounded-lg transition-colors duration-300" style={{
              border: '1px solid var(--color-error)',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--color-error)'
            }}>
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
