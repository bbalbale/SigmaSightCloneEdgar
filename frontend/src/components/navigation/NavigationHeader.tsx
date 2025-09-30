'use client'

import React from 'react'
import { NavigationDropdown } from './NavigationDropdown'

export function NavigationHeader() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold">SigmaSight</h1>
        </div>
        <NavigationDropdown />
      </div>
    </header>
  )
}