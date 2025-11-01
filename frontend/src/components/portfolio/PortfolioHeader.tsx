import React from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ChatInput } from "@/components/app/ChatInput"

interface PortfolioHeaderProps {
  portfolioName: string
  loading: boolean
  dataLoaded: boolean
  positionsCount: number
  showAskSigmaSight?: boolean
}

export function PortfolioHeader({
  portfolioName,
  loading,
  dataLoaded,
  positionsCount,
  showAskSigmaSight = true
}: PortfolioHeaderProps) {
  const router = useRouter()

  const handleSubmit = (message: string) => {
    const trimmed = message.trim()
    if (!trimmed) {
      return
    }

    // Navigate to AI chat with message as URL parameter
    const encodedMessage = encodeURIComponent(trimmed)
    router.push(`/ai-chat?message=${encodedMessage}`)
  }

  return (
    <section className="py-4 px-4 transition-colors duration-300 bg-primary">
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`font-semibold transition-colors duration-300 ${loading ? "animate-pulse" : ""}`} style={{
              fontSize: 'var(--text-lg)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}>
              {loading && !dataLoaded ? (
                <span className="inline-block bg-slate-700 rounded h-6 w-64"></span>
              ) : (
                portfolioName
              )}
            </h2>
            <p className="transition-colors duration-300 text-secondary">
              {loading && !dataLoaded ? (
                <span className="inline-block bg-slate-700 rounded h-4 w-48 mt-1"></span>
              ) : (
                `Live positions and performance metrics - ${positionsCount} total positions`
              )}
            </p>
          </div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="transition-colors duration-300"
              style={{
                color: 'var(--text-primary)',
                borderColor: 'var(--border-primary)',
                backgroundColor: 'var(--bg-secondary)'
              }}
            >
              Daily
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="transition-colors duration-300"
              style={{
                color: 'var(--text-secondary)'
              }}
            >
              Weekly
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="transition-colors duration-300"
              style={{
                color: 'var(--text-secondary)'
              }}
            >
              Monthly
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="transition-colors duration-300"
              style={{
                color: 'var(--text-secondary)'
              }}
            >
              YTD
            </Button>
          </div>
        </div>

        {showAskSigmaSight && (
          <div className="mt-6 flex items-center gap-4">
            <h3 className="font-semibold whitespace-nowrap transition-colors duration-300" style={{
              fontSize: 'var(--text-lg)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}>
              Ask SigmaSight
            </h3>
            <ChatInput
              placeholder="What are my biggest risks? How correlated are my positions?"
              className="flex-1"
              onSubmit={handleSubmit}
            />
          </div>
        )}
      </div>
    </section>
  )
}
