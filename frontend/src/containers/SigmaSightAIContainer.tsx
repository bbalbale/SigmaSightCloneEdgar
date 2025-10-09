'use client'

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'

export function SigmaSightAIContainer() {
  const { theme } = useTheme()

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            SigmaSight AI
          </h1>
          <p className={`transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            AI-powered portfolio insights and analysis
          </p>
        </div>
      </section>

      {/* Main Content Area */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className={`rounded-lg p-8 transition-colors duration-300 ${
            theme === 'dark' ? 'bg-slate-800' : 'bg-white'
          }`}>
            <p className={`text-center transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-600'
            }`}>
              Content coming soon...
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
