"use client"

import React from 'react'
import Link from 'next/link'

export function Header() {
  return (
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
            <Link 
              href="/portfolio"
              className="px-4 py-2 text-sm text-foreground hover:text-primary transition-colors font-medium"
            >
              Login
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}