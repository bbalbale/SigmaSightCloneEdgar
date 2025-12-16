'use client'

import React from 'react'
import { useHomePageData } from '@/hooks/useHomePageData'
import { ReturnsRow } from '@/components/home/ReturnsRow'
import { ExposuresRow } from '@/components/home/ExposuresRow'
import { VolatilityRow } from '@/components/home/VolatilityRow'
import { HomeAIChatRow } from '@/components/home/HomeAIChatRow'
import { LoadingCard } from '@/components/home/MetricCard'

export function HomeContainer() {
  const { returns, exposures, volatility, loading, error, refetch } = useHomePageData()

  if (error && !loading) {
    return (
      <div
        className="min-h-screen transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div
              className="text-center transition-colors duration-300"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--border-radius)',
                padding: 'var(--card-padding)',
              }}
            >
              <h2
                className="text-xl font-semibold mb-2"
                style={{ color: 'var(--color-error)' }}
              >
                Error Loading Data
              </h2>
              <p className="text-secondary mb-4">{error}</p>
              <button
                onClick={refetch}
                className="px-4 py-2 rounded font-medium transition-colors"
                style={{
                  backgroundColor: 'var(--color-accent)',
                  color: 'var(--bg-primary)',
                }}
              >
                Try Again
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Header */}
      <section className="px-4 pt-8 pb-4">
        <div className="container mx-auto">
          <h1
            className="text-2xl font-bold mb-2"
            style={{ color: 'var(--text-primary)' }}
          >
            Portfolio Overview
          </h1>
          <p className="text-sm text-secondary">
            Key metrics and AI-powered insights for your portfolio
          </p>
        </div>
      </section>

      {/* Returns Row */}
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: 'var(--text-primary)' }}
          >
            Returns
          </h2>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <LoadingCard key={i} />
              ))}
            </div>
          ) : (
            <ReturnsRow returns={returns} />
          )}
        </div>
      </section>

      {/* Exposures Row */}
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: 'var(--text-primary)' }}
          >
            Exposures
          </h2>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {[...Array(6)].map((_, i) => (
                <LoadingCard key={i} />
              ))}
            </div>
          ) : (
            <ExposuresRow exposures={exposures} />
          )}
        </div>
      </section>

      {/* Volatility Row */}
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: 'var(--text-primary)' }}
          >
            Volatility
          </h2>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <LoadingCard key={i} />
              ))}
            </div>
          ) : (
            <VolatilityRow volatility={volatility} />
          )}
        </div>
      </section>

      {/* AI Chat Row */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: 'var(--text-primary)' }}
          >
            AI Assistant
          </h2>
          <HomeAIChatRow />
        </div>
      </section>
    </div>
  )
}
