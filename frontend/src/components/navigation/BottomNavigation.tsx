'use client'

import React, { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Command, Search, TrendingUp, Sparkles, User } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { UserDropdownContent } from './UserDropdown'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/command-center', icon: Command, label: 'Command Center' },
  { href: '/research-and-analyze', icon: Search, label: 'Research' },
  { href: '/risk-metrics', icon: TrendingUp, label: 'Risk' },
  { href: '/sigmasight-ai', icon: Sparkles, label: 'AI' },
]

interface NavItemProps {
  href?: string
  icon: React.ElementType
  label: string
  isActive: boolean
  onClick?: () => void
}

function NavItem({ href, icon: Icon, label, isActive, onClick }: NavItemProps) {
  const [showLabel, setShowLabel] = useState(false)
  const timeoutRef = useRef<NodeJS.Timeout>()

  const handleTouchStart = () => {
    timeoutRef.current = setTimeout(() => {
      setShowLabel(true)
    }, 500) // 500ms long-press
  }

  const handleTouchEnd = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setShowLabel(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const content = (
    <div className="relative">
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-1',
          'h-14 px-3 rounded-lg transition-colors duration-200',
          isActive
            ? 'text-accent font-semibold'
            : 'text-muted-foreground hover:text-foreground'
        )}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onMouseLeave={() => setShowLabel(false)}
      >
        <Icon className={cn('h-6 w-6', isActive && 'text-accent')} />
        {/* Active indicator */}
        {isActive && (
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-8 h-1 rounded-full bg-accent" />
        )}
      </div>

      {/* Tooltip on long-press */}
      {showLabel && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-lg whitespace-nowrap border">
          {label}
        </div>
      )}
    </div>
  )

  if (href) {
    return (
      <Link href={href} className="flex-1 min-w-0">
        {content}
      </Link>
    )
  }

  return (
    <button onClick={onClick} className="flex-1 min-w-0">
      {content}
    </button>
  )
}

export function BottomNavigation({ className }: { className?: string }) {
  const pathname = usePathname()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  // Import UserDropdownContent here to avoid circular dependency
  // We'll need to extract the content from UserDropdown component
  return (
    <nav
      className={cn(
        'fixed bottom-0 left-0 right-0 z-50',
        'border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        className
      )}
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex items-center justify-around h-14">
        {/* 4 Main Navigation Items */}
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <NavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              isActive={isActive}
            />
          )
        })}

        {/* 5th Item: User Dropdown */}
        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <div className="flex-1 min-w-0">
              <NavItem
                icon={User}
                label="Profile"
                isActive={false}
                onClick={() => setDropdownOpen(true)}
              />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-56 mb-2"
            align="end"
            side="top"
          >
            <UserDropdownContent />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  )
}
