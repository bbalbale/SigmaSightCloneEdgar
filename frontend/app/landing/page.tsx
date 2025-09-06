"use client"

import { useState } from "react"
import Link from "next/link"

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedTier, setSelectedTier] = useState<string | null>(null)

  const handleTryFree = () => {
    window.location.href = "/signup"
  }

  const handleQuickStart = () => {
    document.getElementById("user-tiers")?.scrollIntoView({ behavior: "smooth" })
  }

  const handleActionCard = (action: string) => {
    alert(`${action} feature coming soon!`)
  }

  const handleTierSelect = (tier: string) => {
    setSelectedTier(tier)
    document.getElementById(`${tier.toLowerCase()}-section`)?.scrollIntoView({ behavior: "smooth" })
  }

  const userTiers = [
    {
      name: "Basic",
      title: "Simple Portfolios",
      description: "Traditional stock and bond portfolios with basic risk analysis",
      price: "$5/month",
      features: [
        "Portfolio risk analysis",
        "Basic correlation insights",
        "Simple stress testing",
        "Monthly reports",
        "Up to 3 portfolios",
      ],
    },
    {
      name: "Standard",
      title: "Multi-Asset Portfolios",
      description: "Private funds, RSUs, employee stock options, and complex holdings",
      price: "$9/month",
      features: [
        "Everything in Basic",
        "Private fund analysis",
        "RSU & stock option modeling",
        "Alternative investment tracking",
        "Multi-asset correlation analysis",
        "Employee equity planning",
        "Concentration risk alerts",
      ],
      popular: true,
    },
    {
      name: "Professional",
      title: "Advanced Strategies",
      description: "Long/short portfolios and significant options exposure",
      price: "$29/month",
      features: [
        "Everything in Standard",
        "Long/short portfolio analysis",
        "Options Greeks & exposure",
        "Hedge effectiveness tracking",
        "Advanced derivatives modeling",
        "Real-time position monitoring",
        "Custom factor models",
        "Professional support",
      ],
    },
  ]

  return (
    <div className="min-h-screen bg-white text-gray-800">
      {/* Header Navigation */}
      <header className="flex items-center justify-between p-4 lg:px-8 border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="flex items-center gap-8">
          <a href="#" className="flex items-center gap-2 text-gray-800 no-underline">
            <div className="w-8 h-8 flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <defs>
                  <linearGradient id="dotGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#1e40af" stopOpacity={1} />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity={1} />
                  </linearGradient>
                </defs>
                <g transform="translate(50,50)">
                  <circle cx="0" cy="0" r="3" fill="url(#dotGradient)" />
                  <circle cx="-6" cy="0" r="3" fill="url(#dotGradient)" />
                  <circle cx="6" cy="0" r="3" fill="url(#dotGradient)" />
                  <circle cx="-12" cy="0" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="12" cy="0" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="-18" cy="0" r="2" fill="url(#dotGradient)" />
                  <circle cx="18" cy="0" r="2" fill="url(#dotGradient)" />
                  <circle cx="-24" cy="0" r="1.5" fill="url(#dotGradient)" />
                  <circle cx="24" cy="0" r="1.5" fill="url(#dotGradient)" />
                  <circle cx="-30" cy="0" r="1" fill="url(#dotGradient)" />
                  <circle cx="30" cy="0" r="1" fill="url(#dotGradient)" />
                  <circle cx="0" cy="-6" r="3" fill="url(#dotGradient)" />
                  <circle cx="0" cy="6" r="3" fill="url(#dotGradient)" />
                  <circle cx="-6" cy="-6" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="6" cy="-6" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="-6" cy="6" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="6" cy="6" r="2.5" fill="url(#dotGradient)" />
                  <circle cx="-12" cy="-6" r="2" fill="url(#dotGradient)" />
                  <circle cx="12" cy="-6" r="2" fill="url(#dotGradient)" />
                  <circle cx="-12" cy="6" r="2" fill="url(#dotGradient)" />
                  <circle cx="12" cy="6" r="2" fill="url(#dotGradient)" />
                </g>
              </svg>
            </div>
            <span className="text-xl font-semibold text-gray-800">SigmaSight</span>
          </a>
          <nav className="hidden md:block">
            <ul className="flex items-center gap-8 list-none m-0 p-0">
              <li>
                <a href="#product" className="text-sm font-medium text-gray-600 hover:text-gray-800 no-underline">
                  Product
                </a>
              </li>
              <li>
                <a href="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-800 no-underline">
                  Pricing
                </a>
              </li>
              <li>
                <a href="#resources" className="text-sm font-medium text-gray-600 hover:text-gray-800 no-underline">
                  Resources
                </a>
              </li>
              <li>
                <a href="#company" className="text-sm font-medium text-gray-600 hover:text-gray-800 no-underline">
                  Company
                </a>
              </li>
            </ul>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <button className="bg-transparent border border-gray-200 rounded-md px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors cursor-pointer">
              Login
            </button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] p-8">
        <div className="max-w-3xl w-full text-center">
          <h1 className="text-4xl font-normal mb-2 text-gray-800 tracking-tight">
            Do you know the risks in your portfolio?
          </h1>
          <p className="text-lg text-gray-600 mb-12 font-normal">
            Get AI driven institutional grade portfolio analysis in plain English
          </p>

          <div className="relative mb-6 max-w-2xl w-full mx-auto">
            <input
              type="text"
              className="w-full p-4 text-base bg-white border border-gray-200 rounded-lg text-gray-800 outline-none focus:border-blue-600"
              placeholder="What are my biggest risks? How correlated are my positions?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleTryFree()}
              autoFocus
            />
          </div>

          <div className="flex gap-4 justify-center mt-4 flex-col sm:flex-row">
            <button
              onClick={handleTryFree}
              className="bg-blue-600 text-white border-none rounded-lg px-6 py-4 text-base font-medium cursor-pointer hover:bg-blue-700 transition-all"
            >
              Try it for free
            </button>
            <button
              onClick={handleQuickStart}
              className="bg-transparent text-gray-800 border border-gray-200 rounded-lg px-6 py-4 text-base font-medium cursor-pointer hover:bg-gray-50 hover:border-blue-600 transition-all"
            >
              Choose Your Plan
            </button>
          </div>
        </div>
      </main>

      {/* Quick Actions */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal text-gray-800 mb-4">Quick Actions</h2>
            <p className="text-gray-600">Try these common portfolio analysis tasks</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              onClick={() => handleActionCard("Risk Analysis")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">What are my biggest risks?</div>
              <div className="text-xs text-gray-600">
                Identify concentration, correlation, and sector risks in your portfolio
              </div>
            </div>

            <div
              onClick={() => handleActionCard("Correlation Analysis")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">How correlated are my positions?</div>
              <div className="text-xs text-gray-600">See which positions move together and hidden dependencies</div>
            </div>

            <div
              onClick={() => handleActionCard("Stress Testing")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">What if tech drops 20%?</div>
              <div className="text-xs text-gray-600">Stress test your portfolio against market scenarios</div>
            </div>

            <div
              onClick={() => handleActionCard("Factor Analysis")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">Show me my factor exposures</div>
              <div className="text-xs text-gray-600">Understand your exposure to growth, value, momentum, and more</div>
            </div>

            <div
              onClick={() => handleActionCard("Demo Portfolio")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">Try with demo portfolio</div>
              <div className="text-xs text-gray-600">See SigmaSight in action with a sample portfolio</div>
            </div>

            <div
              onClick={() => handleActionCard("Learn More")}
              className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all text-left"
            >
              <div className="text-sm font-medium text-gray-800 mb-2">How does this work?</div>
              <div className="text-xs text-gray-600">Learn about AI-powered portfolio analysis</div>
            </div>
          </div>
        </div>
      </section>

      {/* User Tiers Selection */}
      <section id="user-tiers" className="py-16 bg-white">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-normal text-gray-800 mb-4">Choose Your Experience Level</h2>
            <p className="text-lg text-gray-600">Tailored portfolio analytics for every type of investor</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {userTiers.map((tier) => (
              <div
                key={tier.name}
                className={`relative bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-gray-300 transition-all flex flex-col h-full ${
                  selectedTier === tier.name ? "ring-2 ring-blue-500" : ""
                }`}
                onClick={() => handleTierSelect(tier.name)}
              >
                {tier.popular && (
                  <div className="absolute -top-2 left-4">
                    <span className="bg-gray-800 text-white px-2 py-1 rounded text-xs font-medium">Most Popular</span>
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-800 mb-1">{tier.name}</h3>
                  <p className="text-sm text-gray-600 mb-1">{tier.title}</p>
                  <p className="text-xs text-gray-500 mb-4">{tier.description}</p>
                  <div className="text-xl font-normal text-gray-800">{tier.price}</div>
                </div>

                <ul className="space-y-2 mb-6 text-sm text-gray-600 flex-grow">
                  {tier.features.map((feature, index) => (
                    <li key={index}>{feature}</li>
                  ))}
                </ul>

                <div className="flex gap-2 mt-auto">
                  <Link
                    href="/signup"
                    className="flex-1 py-2 px-4 rounded border border-gray-200 text-gray-800 font-medium hover:bg-gray-50 transition-all text-center no-underline block"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Get Started
                  </Link>
                  <Link
                    href={`/demo/${tier.name.toLowerCase()}`}
                    className="flex-1 py-2 px-4 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 transition-all text-center no-underline block"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View Demo
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Basic Tier Section */}
      <section id="basic-section" className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal text-gray-800 mb-4">Basic: Simple Portfolios</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Professional-grade portfolio analysis for traditional stock and bond portfolios. Perfect for
              straightforward risk management needs.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-800 mb-2">Portfolio Risk Scanner</h3>
              <p className="text-gray-600 text-sm">
                Get instant insights into your portfolio's risk profile with AI-powered analysis
              </p>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-800 mb-2">Correlation Matrix</h3>
              <p className="text-gray-600 text-sm">
                Visualize how your holdings move together and identify hidden dependencies
              </p>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-800 mb-2">Basic Stress Testing</h3>
              <p className="text-gray-600 text-sm">See how your portfolio performs under common market scenarios</p>
            </div>
          </div>

          <div className="text-center">
            <Link
              href="/signup"
              className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 transition-all no-underline"
            >
              View Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Standard Tier Section */}
      <section id="standard-section" className="py-16 bg-white">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal text-gray-800 mb-4">Standard: Multi-Asset Portfolios</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Advanced analytics for complex portfolios including private funds, RSUs, employee stock options, and
              alternative investments.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Private Fund Analysis</h3>
              <p className="text-gray-600 text-sm mb-4">
                Track and analyze private equity, hedge funds, and alternative investments alongside public holdings
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">RSU & Stock Option Modeling</h3>
              <p className="text-gray-600 text-sm mb-4">
                Model vesting schedules, exercise scenarios, and concentration risk from employee equity
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Multi-Asset Risk Assessment</h3>
              <p className="text-gray-600 text-sm mb-4">
                Comprehensive risk analysis across traditional and alternative asset classes
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Concentration Alerts</h3>
              <p className="text-gray-600 text-sm mb-4">
                Monitor and receive alerts when single positions become over-concentrated
              </p>
            </div>
          </div>

          <div className="text-center">
            <Link
              href="/signup"
              className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 transition-all no-underline"
            >
              View Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Professional Tier Section */}
      <section id="professional-section" className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-normal text-gray-800 mb-4">Professional: Advanced Strategies</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Sophisticated analytics for complex investment strategies including long/short portfolios and options
              trading.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Long/Short Analysis</h3>
              <p className="text-gray-600 text-sm mb-4">
                Advanced analytics for long/short equity strategies with net and gross exposure tracking
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Hedge Effectiveness</h3>
              <p className="text-gray-600 text-sm mb-4">
                Measure how well your hedges are protecting against downside risk
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Position Tagging</h3>
              <p className="text-gray-600 text-sm mb-4">
                Advanced position categorization and custom tagging system for complex portfolio organization
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">Factor Analytics</h3>
              <p className="text-gray-600 text-sm mb-4">
                Deep factor exposure analysis with custom factor models and attribution reporting
              </p>
            </div>
          </div>

          <div className="text-center">
            <div className="flex gap-4 justify-center">
              <Link
                href="/signup"
                className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 transition-all no-underline"
              >
                View Demo
              </Link>
              <Link
                href="/signup"
                className="bg-transparent text-gray-800 border border-gray-200 px-6 py-2 rounded font-medium hover:bg-gray-50 transition-all no-underline"
              >
                View Demo
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}