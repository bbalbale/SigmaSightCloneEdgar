"use client"

import React from 'react'
import { Header } from './Header'
import { ChatInput } from './ChatInput'

export function BasicDemoPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <Header />

      {/* Hero Section */}
      <section className="py-24 px-4">
        <div className="container mx-auto text-center">
          <h1 className="text-4xl font-normal mb-6 text-foreground max-w-4xl mx-auto leading-tight">
            Do you know the risks in your portfolio?
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-3xl mx-auto">
            Get AI driven institutional grade portfolio analysis in plain English
          </p>
          <ChatInput className="mb-8" />
          <div className="flex justify-center space-x-4">
            <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
              Try it for free
            </button>
            <button className="px-6 py-3 border border-border text-foreground rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors font-medium">
              Choose Your Plan
            </button>
          </div>
        </div>
      </section>

      {/* Quick Actions Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal mb-4 text-foreground">
              Quick Actions
            </h2>
            <p className="text-base text-muted-foreground">
              Try these common portfolio analysis tasks
            </p>
          </div>
          <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-6xl mx-auto">
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                What are my biggest risks?
              </div>
              <div className="text-xs text-muted-foreground">
                Identify concentration, correlation, and sector risks in your portfolio
              </div>
            </div>
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                How correlated are my positions?
              </div>
              <div className="text-xs text-muted-foreground">
                See which positions move together and hidden dependencies
              </div>
            </div>
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                What if tech drops 20%?
              </div>
              <div className="text-xs text-muted-foreground">
                Stress test your portfolio against market scenarios
              </div>
            </div>
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                Show me my factor exposures
              </div>
              <div className="text-xs text-muted-foreground">
                Understand your exposure to growth, value, momentum, and more
              </div>
            </div>
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                Try with demo portfolio
              </div>
              <div className="text-xs text-muted-foreground">
                See SigmaSight in action with a sample portfolio
              </div>
            </div>
            <div className="p-4 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-sm font-medium mb-1 text-card-foreground">
                How does this work?
              </div>
              <div className="text-xs text-muted-foreground">
                Learn about AI-powered portfolio analysis
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 px-4 bg-muted/50">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal mb-4 text-foreground">
              Powerful Analytics Tools
            </h2>
            <p className="text-base text-muted-foreground">
              Professional-grade tools for comprehensive portfolio analysis
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="p-6 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-lg font-medium mb-3 text-card-foreground">
                Risk Metrics
              </div>
              <div className="text-sm text-muted-foreground">
                Comprehensive risk analysis with VaR, CVaR, and advanced stress testing capabilities
              </div>
            </div>
            <div className="p-6 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-lg font-medium mb-3 text-card-foreground">
                Portfolio Analytics
              </div>
              <div className="text-sm text-muted-foreground">
                Deep portfolio analysis with performance attribution and factor exposure insights
              </div>
            </div>
            <div className="p-6 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
              <div className="text-lg font-medium mb-3 text-card-foreground">
                Real-time Monitoring
              </div>
              <div className="text-sm text-muted-foreground">
                Live market data integration with automated alerts and risk threshold monitoring
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal mb-4 text-foreground">
              Choose Your Experience Level
            </h2>
            <p className="text-base text-muted-foreground">
              Tailored portfolio analytics for every type of investor
            </p>
          </div>
          <div className="grid md:grid-cols-3 lg:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {/* Basic Plan */}
            <div className="flex flex-col p-6 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer h-[520px]">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-card-foreground mb-2">Basic</h3>
                <p className="text-sm text-muted-foreground mb-2">Simple Portfolios</p>
                <p className="text-sm text-muted-foreground mb-6 h-10">Traditional stock and bond portfolios with basic risk analysis</p>
                <div className="text-3xl font-normal text-foreground mb-2 h-12 flex items-center justify-center">$5<span className="text-lg text-muted-foreground">/month</span></div>
              </div>
              <ul className="space-y-3 mb-8 text-sm flex-grow">
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Portfolio risk analysis
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Basic metrics & reporting
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Email support
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Single portfolio
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Community support
                </li>
              </ul>
              <button className="w-full px-6 py-3 border-2 border-primary text-foreground rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors font-semibold mt-auto">
                Get Started
              </button>
            </div>

            {/* Standard Plan */}
            <div className="flex flex-col p-6 bg-card border-2 border-primary rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer h-[520px]">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-card-foreground mb-2">Standard</h3>
                <p className="text-sm text-muted-foreground mb-2">Multi-Asset Portfolios</p>
                <p className="text-sm text-muted-foreground mb-6 h-10">Private funds, RSUs, employee stock options, and complex holdings</p>
                <div className="text-3xl font-normal text-foreground mb-2 h-12 flex items-center justify-center">$9<span className="text-lg text-muted-foreground">/month</span></div>
              </div>
              <ul className="space-y-3 mb-8 text-sm flex-grow">
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Everything in Basic
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Advanced risk analytics
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Factor exposure analysis
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Up to 10 portfolios
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Priority support
                </li>
              </ul>
              <button className="w-full px-6 py-3 bg-primary text-primary-foreground border-2 border-primary rounded-lg hover:bg-primary/90 transition-colors font-semibold mt-auto">
                Get Started
              </button>
            </div>

            {/* Professional Plan */}
            <div className="flex flex-col p-6 bg-card border border-border rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer h-[520px]">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-card-foreground mb-2">Professional</h3>
                <p className="text-sm text-muted-foreground mb-2">Advanced Strategies</p>
                <p className="text-sm text-muted-foreground mb-6 h-10">Most comprehensive analytics with long/short portfolio analysis</p>
                <div className="text-3xl font-normal text-foreground mb-2 h-12 flex items-center justify-center">$29<span className="text-lg text-muted-foreground">/month</span></div>
              </div>
              <ul className="space-y-3 mb-8 text-sm flex-grow">
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Everything in Standard
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Stress testing & scenarios
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Options & derivatives modeling
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Unlimited portfolios
                </li>
                <li className="flex items-center text-card-foreground h-6">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Dedicated support
                </li>
              </ul>
              <button className="w-full px-6 py-3 border-2 border-primary text-foreground rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors font-semibold mt-auto">
                Get Started
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 bg-card border-t border-border">
        <div className="container mx-auto">
          <div className="flex justify-between items-center">
            <div className="text-xl font-bold text-primary">
              SigmaSight
            </div>
            <div className="text-sm text-muted-foreground">
              © 2024 SigmaSight. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}