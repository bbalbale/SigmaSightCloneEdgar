'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Menu,
  ChevronRight,
  Sparkles,
  TrendingUp,
  Command,
  Search,
  Home
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const navigationItems = [
  { href: '/home', label: 'Home', icon: Home },
  { href: '/command-center', label: 'Command Center', icon: Command },
  { href: '/risk-metrics', label: 'Risk Metrics', icon: TrendingUp },
  { href: '/research-and-analyze', label: 'Research & Analyze', icon: Search },
  { href: '/sigmasight-ai', label: 'SigmaSight AI', icon: Sparkles },
]

export function NavigationDropdown() {
  const pathname = usePathname()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Menu className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="start">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          All Pages
        </DropdownMenuLabel>
        {navigationItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href

          return (
            <DropdownMenuItem key={item.href} asChild>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center justify-between cursor-pointer",
                  isActive && "bg-accent"
                )}
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                {isActive && (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </Link>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}