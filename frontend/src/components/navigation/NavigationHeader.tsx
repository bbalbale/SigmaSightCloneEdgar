'use client'

import React from 'react'
import { NavigationDropdown } from './NavigationDropdown'
import { ThemeToggle } from '@/components/app/ThemeToggle'

export function NavigationHeader() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="text-emerald-400 text-xl font-bold">$</div>
            <h1 className="text-lg font-semibold">SigmaSight</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <NavigationDropdown />
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}