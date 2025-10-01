import React from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ChatInput } from "@/components/app/ChatInput"
import { useTheme } from "@/contexts/ThemeContext"

interface PortfolioHeaderProps {
  portfolioName: string
  loading: boolean
  dataLoaded: boolean
  positionsCount: number
}

export function PortfolioHeader({
  portfolioName,
  loading,
  dataLoaded,
  positionsCount
}: PortfolioHeaderProps) {
  const router = useRouter()
  const { theme } = useTheme()

  const handleSubmit = (message: string) => {
    const trimmed = message.trim()
    if (!trimmed) {
      return
    }

    if (typeof window !== "undefined") {
      sessionStorage.setItem("pendingChatMessage", trimmed)
    }

    router.push("/ai-chat")
  }

  const handleFocus = () => {
    router.push("/ai-chat")
  }

  return (
    <section className={`py-6 px-4 transition-colors duration-300 ${
      theme === "dark" ? "bg-slate-900" : "bg-gray-50"
    }`}>
      <div className="container mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className={`text-2xl font-semibold transition-colors duration-300 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            } ${loading ? "animate-pulse" : ""}`}>
              {loading && !dataLoaded ? (
                <span className="inline-block bg-slate-700 rounded h-8 w-64"></span>
              ) : (
                portfolioName
              )}
            </h2>
            <p className={`transition-colors duration-300 ${
              theme === "dark" ? "text-slate-400" : "text-gray-600"
            }`}>
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
              className={`transition-colors duration-300 ${
                theme === "dark"
                  ? "text-white border-slate-600 bg-slate-700 hover:bg-slate-600"
                  : "text-gray-900 border-gray-300 bg-white hover:bg-gray-50"
              }`}
            >
              Daily
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`transition-colors duration-300 ${
                theme === "dark"
                  ? "text-slate-400 hover:text-white hover:bg-slate-800"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              Weekly
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`transition-colors duration-300 ${
                theme === "dark"
                  ? "text-slate-400 hover:text-white hover:bg-slate-800"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              Monthly
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`transition-colors duration-300 ${
                theme === "dark"
                  ? "text-slate-400 hover:text-white hover:bg-slate-800"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              }`}
            >
              YTD
            </Button>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <h3 className={`text-lg font-semibold whitespace-nowrap transition-colors duration-300 ${
            theme === "dark" ? "text-white" : "text-gray-900"
          }`}
          >
            Ask SigmaSight
          </h3>
          <ChatInput
            placeholder="What are my biggest risks? How correlated are my positions?"
            className="flex-1"
            onFocus={handleFocus}
            onSubmit={handleSubmit}
          />
        </div>
      </div>
    </section>
  )
}
