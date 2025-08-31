"use client"

import React from 'react'
import { Header } from '@/components/Header'
import { ChatInput } from '@/components/ChatInput'

export default function PortfolioPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <Header />

      {/* Chat Section */}
      <section className="py-24 px-4">
        <div className="container mx-auto text-center">
          <ChatInput className="mb-8" />
        </div>
      </section>

      {/* Portfolio Content Area - Empty for now */}
      <section className="flex-1 py-16 px-4">
        <div className="container mx-auto">
          <div className="text-center text-muted-foreground">
            {/* This area will be populated with portfolio content */}
          </div>
        </div>
      </section>
    </div>
  )
}