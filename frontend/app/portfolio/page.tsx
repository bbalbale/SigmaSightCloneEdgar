"use client"

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ChatInput } from '../components/ChatInput'
import { openChatSheet, sendChatMessage } from '@/components/chat/ChatInterface'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'
import { ThemeToggle } from '../components/ThemeToggle'
import { loadPortfolioData, PortfolioType } from '@/services/portfolioService'
import { positionApiService } from '@/services/positionApiService'
import { portfolioResolver } from '@/services/portfolioResolver'
import { FactorExposureCards } from '@/components/portfolio/FactorExposureCards'
import type { FactorExposure } from '@/types/analytics'

const formatNumber = (num: number) => {
  if (Math.abs(num) >= 1000) {
    return `$${(num / 1000).toFixed(1)}K`
  }
  return `$${num.toFixed(2)}`
}

const formatPrice = (price: number) => {
  return `$${price.toFixed(2)}`
}

function PortfolioPageContent() {
  const { theme } = useTheme()
  const searchParams = useSearchParams()
  const portfolioType = searchParams?.get('type') as PortfolioType | null
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiErrors, setApiErrors] = useState<{overview?: any, positions?: any, factorExposures?: any}>({})
  const [retryCount, setRetryCount] = useState(0)
  const [portfolioSummaryMetrics, setPortfolioSummaryMetrics] = useState<any[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [shortPositionsState, setShortPositionsState] = useState<any[]>([])
  const [portfolioName, setPortfolioName] = useState('Loading...')
  const [dataLoaded, setDataLoaded] = useState(false)
  const [factorExposures, setFactorExposures] = useState<FactorExposure[] | null>(null)
  
  useEffect(() => {
    const abortController = new AbortController();
    
    const loadData = async () => {
      if (!portfolioType) {
        // No portfolio type specified - show error
        setError('Please select a portfolio type')
        setPortfolioSummaryMetrics([])
        setPositions([])
        setShortPositionsState([])
        setPortfolioName('No Portfolio Selected')
        setDataLoaded(false)
        return
      }

      setLoading(true)
      setError(null)
      
      try {
        // Phase 3: Enable API positions
        const USE_API_POSITIONS = true // Feature flag for Phase 3
        const data = await loadPortfolioData(portfolioType, abortController.signal)
        
        if (data) {
          console.log('Loaded portfolio data:', data)
          console.log('Portfolio name from backend:', data.portfolioInfo?.name)
          
          // Handle API errors from individual endpoints
          if (data.errors) {
            setApiErrors(data.errors)
            
            // Show position error if positions failed but overview succeeded
            if (data.errors.positions && !data.errors.overview) {
              console.error('Position API failed:', data.errors.positions)
            }
            // Log factor exposures error if it failed
            if (data.errors.factorExposures) {
              console.error('Factor exposures API failed:', data.errors.factorExposures)
            }
          } else {
            setApiErrors({})
          }
          
          // Update all state with real data
          setPortfolioSummaryMetrics(data.exposures || [])
          setPositions(data.positions.filter(p => p.type === 'LONG' || !p.type))
          setShortPositionsState(data.positions.filter(p => p.type === 'SHORT'))
          setFactorExposures(data.factorExposures || null)
          
          // Use descriptive name if backend returns generic "Demo Portfolio"
          if (data.portfolioInfo?.name === 'Demo Portfolio' && portfolioType === 'individual') {
            setPortfolioName('Demo Individual Investor Portfolio')
          } else {
            setPortfolioName(data.portfolioInfo?.name || 'Portfolio')
          }
          
          setDataLoaded(true)
          setError(null)
          setRetryCount(0)
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error('Failed to load portfolio:', err)
          const errorMessage = err.message || 'Failed to load portfolio data'
          setError(errorMessage)
          
          // No fallback - show error state
          if (!dataLoaded) {
            setPortfolioSummaryMetrics([])
            setPositions([])
            setShortPositionsState([])
            setPortfolioName('Portfolio Unavailable')
          }
        }
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
    
    return () => {
      abortController.abort()
    }
  }, [portfolioType, retryCount])
  
  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
  }
  
  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header - Theme Aware */}
      <header className={`border-b transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link href="/landing" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <div className="text-emerald-400 text-xl font-bold">$</div>
              <h1 className={`text-xl font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>SigmaSight</h1>
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {(error || apiErrors.positions) && !loading && (
        <div className={`px-4 py-3 border-b transition-colors duration-300 ${
          theme === 'dark' ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'
        }`}>
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`text-sm ${theme === 'dark' ? 'text-red-400' : 'text-red-600'}`}>
                ⚠️ {error || (apiErrors.positions && 'Position data unavailable')}
              </span>
              {dataLoaded && (
                <span className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-gray-500'}`}>
                  (partial data available)
                </span>
              )}
            </div>
            <Button 
              onClick={handleRetry}
              size="sm"
              variant="outline"
              className={`text-xs ${
                theme === 'dark' 
                  ? 'border-red-700 text-red-400 hover:bg-red-900/30' 
                  : 'border-red-300 text-red-600 hover:bg-red-100'
              }`}
            >
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Portfolio Header */}
      <section className={`py-6 px-4 transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className={`text-2xl font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              } ${loading ? 'animate-pulse' : ''}`}>
                {loading && !dataLoaded ? (
                  <span className="inline-block bg-slate-700 rounded h-8 w-64"></span>
                ) : (
                  portfolioName
                )}
              </h2>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                {loading && !dataLoaded ? (
                  <span className="inline-block bg-slate-700 rounded h-4 w-48 mt-1"></span>
                ) : (
                  `Live positions and performance metrics - ${positions.length + shortPositionsState.length} total positions`
                )}
              </p>
            </div>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-white border-slate-600 bg-slate-700 hover:bg-slate-600' 
                  : 'text-gray-900 border-gray-300 bg-white hover:bg-gray-50'
              }`}>Daily</Button>
              <Button variant="ghost" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}>Weekly</Button>
              <Button variant="ghost" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}>Monthly</Button>
              <Button variant="ghost" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}>YTD</Button>
            </div>
          </div>
          
          {/* Chat Input */}
          <div className="mt-6 flex items-center gap-4">
            <h3 className={`text-lg font-semibold whitespace-nowrap transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>Ask SigmaSight</h3>
            <ChatInput 
              placeholder="What are my biggest risks? How correlated are my positions?" 
              className="flex-1"
              onFocus={() => openChatSheet()}
              onSubmit={(message) => {
                sendChatMessage(message)
              }}
            />
          </div>
        </div>
      </section>

      {/* Loading State */}
      {loading && (
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              Loading portfolio data...
            </p>
          </div>
        </section>
      )}
      
      {/* Error State */}
      {error && (
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg text-red-500`}>
              {error}
            </p>
          </div>
        </section>
      )}
      
      {/* Portfolio Summary Metrics Cards */}
      {!loading && !error && (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            {portfolioSummaryMetrics.map((metric, index) => (
              <Card key={index} className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
              }`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className={`text-xs transition-colors duration-300 ${
                      theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                    }`}>{metric.title}</div>
                  </div>
                  <div className={`text-xl font-bold mb-1 ${
                    metric.positive ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {metric.value}
                  </div>
                  <div className={`text-sm mb-1 transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
                  }`}>{metric.subValue}</div>
                  <div className={`text-xs transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
                  }`}>{metric.description}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
      )}

      {/* Factor Exposure Cards */}
      {!loading && !error && (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <FactorExposureCards 
            factors={factorExposures}
            loading={loading}
            error={apiErrors?.factorExposures}
          />
        </div>
      </section>
      )}

      {/* Filter & Sort Bar */}
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <div className={`flex items-center justify-between text-sm transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zM3 16a1 1 0 011-1h4a1 1 0 110 2H4a1 1 0 01-1-1z"/>
              </svg>
              <span>Filter & Sort:</span>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700' 
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}>Tags</Button>
              <Button variant="outline" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700' 
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}>Exposure</Button>
              <Button variant="outline" size="sm" className={`transition-colors duration-300 ${
                theme === 'dark' 
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700' 
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}>Desc</Button>
            </div>
          </div>
        </div>
      </section>

      {/* Position Cards */}
      <section className="flex-1 px-4 pb-6">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Long Positions Column */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>Long Positions</h3>
                <Badge variant="secondary" className={`transition-colors duration-300 ${
                  theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                }`}>
                  {positions.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {positions.map((position, index) => (
                  <Card key={index} className={`transition-colors cursor-pointer ${
                    theme === 'dark' 
                      ? 'bg-slate-800 border-slate-700 hover:bg-slate-750' 
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className={`font-semibold text-sm transition-colors duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{position.symbol}</div>
                          <div className={`text-xs transition-colors duration-300 ${
                            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                          }`}>
                            {position.symbol === 'AAPL' ? 'Apple Inc.' :
                             position.symbol === 'MSFT' ? 'Microsoft Corporation' :
                             position.symbol === 'GOOGL' ? 'Alphabet Inc.' :
                             position.symbol === 'NVDA' ? 'NVIDIA Corporation' :
                             position.symbol === 'AMZN' ? 'Amazon.com, Inc.' :
                             position.symbol === 'META' ? 'Meta Platforms Inc.' :
                             'Technology Company'}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-medium transition-colors duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{formatNumber(position.marketValue)}</div>
                          <div className={`text-sm font-medium ${
                            position.pnl === 0 ? 'text-slate-400' : position.positive ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {position.pnl === 0 ? '—' : `${position.positive ? '+' : ''}${formatNumber(position.pnl)}`}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Short Positions Column */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>Short Positions</h3>
                <Badge variant="secondary" className={`transition-colors duration-300 ${
                  theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                }`}>
                  {shortPositionsState.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {shortPositionsState.map((position, index) => (
                  <Card key={index} className={`transition-colors cursor-pointer ${
                    theme === 'dark' 
                      ? 'bg-slate-800 border-slate-700 hover:bg-slate-750' 
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className={`font-semibold text-sm transition-colors duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>{position.symbol}</div>
                          <div className={`text-xs transition-colors duration-300 ${
                            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                          }`}>
                            {position.symbol === 'WISH' ? 'ContextLogic Inc.' :
                             position.symbol === 'NKLA' ? 'Nikola Corporation' :
                             position.symbol === 'CLOV' ? 'Clover Health' :
                             position.symbol === 'HOOD' ? 'Robinhood Markets' :
                             position.symbol === 'SPCE' ? 'Virgin Galactic' :
                             'Growth Company'}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-medium transition-colors duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>-{formatNumber(position.marketValue)}</div>
                          <div className={`text-sm font-medium ${
                            position.pnl === 0 ? 'text-slate-400' : position.positive ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {position.pnl === 0 ? '—' : `${position.positive ? '+' : ''}${formatNumber(position.pnl)}`}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom Navigation */}
      <footer className={`border-t px-4 py-3 transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-center justify-center gap-8">
            <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
              theme === 'dark' 
                ? 'text-slate-300 hover:text-white' 
                : 'text-gray-600 hover:text-gray-900'
            }`}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>
              </svg>
              <span className="text-xs">Home</span>
            </Button>
            <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
              theme === 'dark' 
                ? 'text-slate-400 hover:text-white' 
                : 'text-gray-600 hover:text-gray-900'
            }`}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12a1 1 0 112 0V8a1 1 0 11-2 0v4zM6 8a6 6 0 1112 0c0 .55-.24 1.08-.67 1.44L15 12v1a1 1 0 01-1 1H6a1 1 0 01-1-1v-1l-2.33-2.56A1.99 1.99 0 013 8z"/>
              </svg>
              <span className="text-xs">History</span>
            </Button>
            <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
              theme === 'dark' 
                ? 'text-slate-400 hover:text-white' 
                : 'text-gray-600 hover:text-gray-900'
            }`}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12a1 1 0 112 0V8a1 1 0 11-2 0v4zM6 8a6 6 0 1112 0c0 .55-.24 1.08-.67 1.44L15 12v1a1 1 0 01-1 1H6a1 1 0 01-1-1v-1l-2.33-2.56A1.99 1.99 0 013 8z"/>
              </svg>
              <span className="text-xs">Risk Analytics</span>
            </Button>
            <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
              theme === 'dark' 
                ? 'text-slate-400 hover:text-white' 
                : 'text-gray-600 hover:text-gray-900'
            }`}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
              </svg>
              <span className="text-xs">Performance</span>
            </Button>
            <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
              theme === 'dark' 
                ? 'text-slate-400 hover:text-white' 
                : 'text-gray-600 hover:text-gray-900'
            }`}>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd"/>
              </svg>
              <span className="text-xs">Tags</span>
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function PortfolioPage() {
  return (
    <ThemeProvider>
      <PortfolioPageContent />
    </ThemeProvider>
  )
}