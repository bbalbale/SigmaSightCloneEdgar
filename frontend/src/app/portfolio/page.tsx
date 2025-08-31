"use client"

import React from 'react'
import Link from 'next/link'
import { ChatInput } from '../components/ChatInput'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'
import { ThemeToggle } from '../components/ThemeToggle'

// Mock data matching the v0 reference design exactly
const portfolioSummaryMetrics = [
  { title: 'Long Exposure', value: '1.1M', subValue: '91.7%', description: 'Notional exposure', positive: true },
  { title: 'Short Exposure', value: '(567K)', subValue: '47.3%', description: 'Notional exposure', positive: false },
  { title: 'Gross Exposure', value: '1.7M', subValue: '141.7%', description: 'Notional total', positive: true },
  { title: 'Net Exposure', value: '574K', subValue: '47.8%', description: 'Notional net', positive: true },
  { title: 'Total P&L', value: '+285,000', subValue: '23.8%', description: 'Equity: +1,200,000', positive: true }
]

const longPositions = [
  { symbol: 'AAPL', quantity: 100, price: 150.25, marketValue: 15025, pnl: 2500, positive: true },
  { symbol: 'MSFT', quantity: 150, price: 330.50, marketValue: 49575, pnl: 5200, positive: true },
  { symbol: 'GOOGL', quantity: 50, price: 2800.00, marketValue: 140000, pnl: 8500, positive: true },
  { symbol: 'NVDA', quantity: 75, price: 450.25, marketValue: 33769, pnl: 3200, positive: true },
  { symbol: 'AMZN', quantity: 80, price: 3200.00, marketValue: 256000, pnl: 12000, positive: true },
  { symbol: 'TSLA', quantity: 60, price: 850.75, marketValue: 51045, pnl: 4500, positive: true },
  { symbol: 'AMD', quantity: 200, price: 120.50, marketValue: 24100, pnl: 2800, positive: true },
  { symbol: 'CRM', quantity: 40, price: 220.25, marketValue: 8810, pnl: 1200, positive: true },
  { symbol: 'NET', quantity: 120, price: 75.50, marketValue: 9060, pnl: 800, positive: true },
  { symbol: 'SHOP', quantity: 25, price: 65.75, marketValue: 1644, pnl: 200, positive: true },
  { symbol: 'SQ', quantity: 150, price: 68.25, marketValue: 10238, pnl: 900, positive: true },
  { symbol: 'PYPL', quantity: 100, price: 58.50, marketValue: 5850, pnl: 600, positive: true },
  { symbol: 'ABNB', quantity: 45, price: 138.75, marketValue: 6244, pnl: 750, positive: true },
  { symbol: 'UBER', quantity: 200, price: 45.25, marketValue: 9050, pnl: 1100, positive: true },
  { symbol: 'PINS', quantity: 300, price: 28.75, marketValue: 8625, pnl: 950, positive: true },
  { symbol: 'TWTR', quantity: 180, price: 42.25, marketValue: 7605, pnl: 680, positive: true },
  { symbol: 'SNAP', quantity: 500, price: 10.75, marketValue: 5375, pnl: 425, positive: true },
  { symbol: 'SPOT', quantity: 35, price: 145.25, marketValue: 5084, pnl: 600, positive: true },
  { symbol: 'ZM', quantity: 35, price: 70.25, marketValue: 2459, pnl: 300, positive: true },
  { symbol: 'DOCU', quantity: 45, price: 60.00, marketValue: 2700, pnl: 600, positive: true }
]

const shortPositions = [
  { symbol: 'WDAY', quantity: 50, price: 200.25, marketValue: 10013, pnl: 1500, positive: true },
  { symbol: 'SNOW', quantity: 30, price: 180.50, marketValue: 5415, pnl: 800, positive: true },
  { symbol: 'OKTA', quantity: 25, price: 90.25, marketValue: 2256, pnl: 400, positive: true },
  { symbol: 'PTON', quantity: 100, price: 8.50, marketValue: 850, pnl: 200, positive: true },
  { symbol: 'NFLX', quantity: 20, price: 400.00, marketValue: 8000, pnl: 1000, positive: true },
  { symbol: 'DIS', quantity: 60, price: 95.25, marketValue: 5715, pnl: 750, positive: true },
  { symbol: 'ROKU', quantity: 80, price: 52.75, marketValue: 4220, pnl: 450, positive: true },
  { symbol: 'PLTR', quantity: 150, price: 15.25, marketValue: 2288, pnl: 300, positive: true },
  { symbol: 'COIN', quantity: 25, price: 78.50, marketValue: 1963, pnl: 200, positive: true },
  { symbol: 'UPST', quantity: 40, price: 25.75, marketValue: 1030, pnl: 150, positive: true },
  { symbol: 'HOOD', quantity: 100, price: 11.25, marketValue: 1125, pnl: 100, positive: true },
  { symbol: 'DKNG', quantity: 75, price: 18.50, marketValue: 1388, pnl: 120, positive: true },
  { symbol: 'CRWD', quantity: 20, price: 175.25, marketValue: 3505, pnl: 400, positive: true },
  { symbol: 'MU', quantity: 100, price: 68.25, marketValue: 6825, pnl: 750, positive: true },
  { symbol: 'INTC', quantity: 200, price: 32.50, marketValue: 6500, pnl: 600, positive: true },
  { symbol: 'QCOM', quantity: 40, price: 125.75, marketValue: 5030, pnl: 500, positive: true },
  { symbol: 'AVGO', quantity: 15, price: 580.25, marketValue: 8704, pnl: 850, positive: true },
  { symbol: 'MRVL', quantity: 60, price: 52.75, marketValue: 3165, pnl: 350, positive: true },
  { symbol: 'LYFT', quantity: 75, price: 12.50, marketValue: 938, pnl: 150, positive: true },
  { symbol: 'JOW', quantity: 90, price: 35.25, marketValue: 3173, pnl: 400, positive: true },
  { symbol: 'SQ', quantity: 150, price: 68.25, marketValue: 10238, pnl: 900, positive: true },
  { symbol: 'NFLX', quantity: 20, price: 400.00, marketValue: 8000, pnl: 1000, positive: true },
  { symbol: 'PTON', quantity: 100, price: 8.50, marketValue: 850, pnl: 200, positive: true },
  { symbol: 'COIN', quantity: 25, price: 78.50, marketValue: 1963, pnl: 200, positive: true }
]

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

      {/* Portfolio Header */}
      <section className={`py-6 px-4 transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className={`text-2xl font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Demo Portfolio</h2>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>Live positions and performance metrics - 39 total positions</p>
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
            <ChatInput placeholder="What are my biggest risks? How correlated are my positions?" className="flex-1" />
          </div>
        </div>
      </section>

      {/* Portfolio Summary Metrics Cards */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            {portfolioSummaryMetrics.map((metric, index) => (
              <Card key={index} className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
              }`}>
                <CardContent className="p-4">
                  <div className={`text-xs mb-2 transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                  }`}>{metric.title}</div>
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
                  {longPositions.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {longPositions.slice(0, 15).map((position, index) => (
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
                            position.positive ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {position.positive ? '+' : ''}{formatNumber(position.pnl)}
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
                  {shortPositions.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {shortPositions.slice(0, 19).map((position, index) => (
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
                            position.positive ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {position.positive ? '+' : ''}{formatNumber(position.pnl)}
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