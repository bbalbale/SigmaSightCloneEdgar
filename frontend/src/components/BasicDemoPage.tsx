"use client"

import React from 'react'

export function BasicDemoPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-xl font-semibold text-primary">
                <div className="w-2 h-2 bg-primary rounded-full mr-2"></div>
                SigmaSight
              </div>
              <nav className="hidden md:flex items-center space-x-6">
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Product
                </a>
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Pricing
                </a>
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Resources
                </a>
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Company
                </a>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <button className="px-4 py-2 text-sm text-foreground hover:text-primary transition-colors font-medium">
                Login
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-24 px-4">
        <div className="container mx-auto text-center">
          <h1 className="text-4xl font-normal mb-6 text-foreground max-w-4xl mx-auto leading-tight">
            Do you know the risks in your portfolio?
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-3xl mx-auto">
            Get AI driven institutional grade portfolio analysis in plain English
          </p>
          <div className="max-w-lg mx-auto mb-8">
            <input
              type="text"
              placeholder="What are my biggest risks? How correlated are my positions?"
              className="w-full px-4 py-3 border border-blue-200 rounded-lg text-foreground placeholder:text-blue-400 bg-background focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
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
          <h2 className="text-3xl font-bold text-center mb-12 text-foreground">
            Powerful Analytics Tools
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 bg-card border border-border rounded-lg">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <div className="w-6 h-6 bg-primary rounded"></div>
              </div>
              <h3 className="text-xl font-semibold mb-3 text-card-foreground">Risk Metrics</h3>
              <p className="text-muted-foreground">
                Comprehensive risk analysis with VaR, CVaR, and advanced stress testing capabilities.
              </p>
            </div>
            <div className="p-6 bg-card border border-border rounded-lg">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <div className="w-6 h-6 bg-primary rounded"></div>
              </div>
              <h3 className="text-xl font-semibold mb-3 text-card-foreground">Portfolio Analytics</h3>
              <p className="text-muted-foreground">
                Deep portfolio analysis with performance attribution and factor exposure insights.
              </p>
            </div>
            <div className="p-6 bg-card border border-border rounded-lg">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <div className="w-6 h-6 bg-primary rounded"></div>
              </div>
              <h3 className="text-xl font-semibold mb-3 text-card-foreground">Real-time Monitoring</h3>
              <p className="text-muted-foreground">
                Live market data integration with automated alerts and risk threshold monitoring.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-normal mb-4 text-foreground">
              Choose Your Experience Level
            </h2>
            <p className="text-lg text-muted-foreground">
              Tailored portfolio analytics for every type of investor
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Basic Plan */}
            <div className="bg-card border border-border rounded-xl p-8 shadow-sm">
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-card-foreground mb-2">Basic</h3>
                <p className="text-sm text-muted-foreground mb-2">Simple Portfolios</p>
                <p className="text-xs text-muted-foreground mb-4">Traditional stock and bond portfolios with basic risk analysis</p>
                <div className="text-xl font-normal text-foreground">Free</div>
              </div>
              <ul className="space-y-2 mb-8 text-sm">
                <li className="text-card-foreground">Portfolio risk analysis</li>
                <li className="text-card-foreground">Basic metrics & reporting</li>
                <li className="text-card-foreground">Email support</li>
              </ul>
              <button className="w-full px-6 py-3 border border-border text-foreground rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors font-semibold">
                Get Started
              </button>
            </div>

            {/* Standard Plan */}
            <div className="bg-card border-2 border-primary rounded-xl p-8 shadow-sm relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <div className="bg-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-semibold">
                  Most Popular
                </div>
              </div>
              <div className="text-center mb-6">
                <h3 className="text-lg font-medium text-card-foreground mb-2">Standard</h3>
                <p className="text-sm text-muted-foreground mb-2">Multi-Asset Portfolios</p>
                <p className="text-xs text-muted-foreground mb-4">Private funds, RSUs, employee stock options, and complex holdings</p>
                <div className="text-xl font-normal text-foreground">$15<span className="text-sm text-muted-foreground">/month</span></div>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Everything in Basic
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Advanced risk analytics
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Factor exposure analysis
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Up to 10 portfolios
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Priority support
                </li>
              </ul>
              <button className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-semibold">
                Start Free Trial
              </button>
            </div>

            {/* Professional Plan */}
            <div className="bg-card border border-border rounded-xl p-8 shadow-sm">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-card-foreground mb-2">Professional</h3>
                <div className="text-4xl font-bold text-foreground mb-1">$29<span className="text-lg text-muted-foreground">/month</span></div>
                <div className="text-muted-foreground">For institutional needs</div>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Everything in Standard
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Stress testing & scenarios
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Options & derivatives modeling
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Unlimited portfolios
                </li>
                <li className="flex items-center text-card-foreground">
                  <div className="w-2 h-2 bg-primary rounded-full mr-3"></div>
                  Dedicated support
                </li>
              </ul>
              <button className="w-full px-6 py-3 border border-border text-foreground rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors font-semibold">
                Contact Sales
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