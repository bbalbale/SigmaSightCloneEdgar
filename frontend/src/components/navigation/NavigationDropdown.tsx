'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Building2,
  Shield,
  PieChart,
  Bot,
  Settings,
  LogOut,
  Menu,
  User,
  ChevronRight,
  Sparkles,
  Briefcase,
  TrendingUp
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../../app/providers'
import { usePortfolioName } from '@/stores/portfolioStore'
import { cn } from '@/lib/utils'

const navigationItems = [
  { href: '/dashboard', label: 'Dashboard', icon: Home },
  { href: '/portfolio-holdings', label: 'Portfolio Holdings', icon: Briefcase },
  { href: '/risk-metrics', label: 'Risk Metrics', icon: TrendingUp },
  { href: '/public-positions', label: 'Public Positions', icon: Building2 },
  { href: '/private-positions', label: 'Private Positions', icon: Shield },
  { href: '/organize', label: 'Organize', icon: PieChart },
  { href: '/sigmasight-ai', label: 'SigmaSight AI', icon: Sparkles },
  { href: '/ai-chat', label: 'AI Chat', icon: Bot },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function NavigationDropdown() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const portfolioName = usePortfolioName()

  const handleLogout = async () => {
    await logout()
  }

  // Find current page
  const currentPage = navigationItems.find(item => item.href === pathname)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Menu className="h-4 w-4" />
          <span className="hidden sm:inline-block">
            {currentPage ? currentPage.label : 'Menu'}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end">
        {/* User info section */}
        {user && (
          <>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  <p className="text-sm font-medium leading-none">{user.fullName}</p>
                </div>
                <p className="text-xs leading-none text-muted-foreground">
                  {user.email}
                </p>
                {portfolioName && (
                  <p className="text-xs leading-none text-muted-foreground mt-1">
                    Portfolio: {portfolioName}
                  </p>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
          </>
        )}

        {/* Navigation items */}
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Navigation
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

        {/* Logout */}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleLogout}
          className="text-red-600 dark:text-red-400 cursor-pointer"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Logout</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}