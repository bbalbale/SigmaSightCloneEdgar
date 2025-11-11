'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Command, Search, TrendingUp, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { UserDropdown } from './UserDropdown'
import { NavigationDropdown } from './NavigationDropdown'
import { ThemeToggle } from '@/components/app/ThemeToggle'
import { cn } from '@/lib/utils'

const navigationItems = [
  { href: '/command-center', label: 'Command Center', icon: Command },
  { href: '/research-and-analyze', label: 'Research & Analyze', icon: Search },
  { href: '/risk-metrics', label: 'Risk Metrics', icon: TrendingUp },
  { href: '/sigmasight-ai', label: 'SigmaSight AI', icon: Sparkles },
]

export function TopNavigationBar() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 hidden md:flex">
      <div className="container flex h-14 items-center justify-between">
        {/* Left: Logo + Theme Toggle + All Pages Menu */}
        <div className="flex items-center gap-3">
          <div className="text-emerald-400 text-xl font-bold">$</div>
          <h1 className="text-lg font-semibold">SigmaSight</h1>
          <ThemeToggle />
          <NavigationDropdown />
        </div>

        {/* Right: Main Navigation + User Dropdown */}
        <div className="flex items-center gap-1">
          <nav className="flex items-center gap-1">
            {navigationItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href

              return (
                <Button
                  key={item.href}
                  variant={isActive ? 'default' : 'ghost'}
                  asChild
                  className={cn(
                    'gap-2 relative',
                    isActive && 'bg-primary text-primary-foreground font-semibold shadow-sm border-2 border-primary-foreground'
                  )}
                >
                  <Link href={item.href}>
                    <Icon className={cn('h-4 w-4', isActive && 'text-primary-foreground')} />
                    <span className="hidden md:inline-block">{item.label}</span>
                  </Link>
                </Button>
              )
            })}
          </nav>
          <div className="ml-2 pl-2 border-l">
            <UserDropdown />
          </div>
        </div>
      </div>
    </header>
  )
}
