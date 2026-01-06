'use client'

import React from 'react'
import Link from 'next/link'
import { UserButton, SignedIn, SignedOut } from '@clerk/nextjs'
import { User, Settings, LogOut, ChevronDown } from 'lucide-react'
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
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'
import { dark } from '@clerk/themes'

// Extracted content component for reuse in BottomNavigation (legacy, used for fallback)
export function UserDropdownContent() {
  const { user, logout } = useAuth()
  const { selectedPortfolio, isAggregateView, portfolioCount } = useSelectedPortfolio()

  const handleLogout = async () => {
    await logout()
  }

  return (
    <>
      {/* User info section */}
      {user && (
        <>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">{user.fullName}</p>
              <p className="text-xs leading-none text-muted-foreground">
                {user.email}
              </p>
              {(isAggregateView || selectedPortfolio) && (
                <p className="text-xs leading-none text-muted-foreground mt-1">
                  {isAggregateView
                    ? `All Accounts (${portfolioCount})`
                    : selectedPortfolio?.account_name}
                </p>
              )}
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
        </>
      )}

      {/* Settings */}
      <DropdownMenuItem asChild>
        <Link href="/settings" className="flex items-center cursor-pointer">
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </Link>
      </DropdownMenuItem>

      {/* Logout */}
      <DropdownMenuSeparator />
      <DropdownMenuItem
        onClick={handleLogout}
        className="text-red-600 dark:text-red-400 cursor-pointer"
      >
        <LogOut className="mr-2 h-4 w-4" />
        <span>Logout</span>
      </DropdownMenuItem>
    </>
  )
}

// Main UserDropdown component for desktop top nav - Uses Clerk UserButton
export function UserDropdown() {
  const { selectedPortfolio, isAggregateView, portfolioCount } = useSelectedPortfolio()

  return (
    <div className="flex items-center gap-2">
      {/* Portfolio info badge */}
      {(isAggregateView || selectedPortfolio) && (
        <span className="text-xs text-muted-foreground hidden lg:inline-block">
          {isAggregateView
            ? `All Accounts (${portfolioCount})`
            : selectedPortfolio?.account_name}
        </span>
      )}

      {/* Clerk UserButton - handles user profile, sign-out, etc. */}
      <SignedIn>
        <UserButton
          afterSignOutUrl="/sign-in"
          appearance={{
            baseTheme: dark,
            elements: {
              avatarBox: 'h-8 w-8',
              userButtonTrigger: 'focus:shadow-none',
              userButtonPopoverCard: 'bg-card border border-border shadow-lg',
              userButtonPopoverActionButton: 'text-foreground hover:bg-muted',
              userButtonPopoverActionButtonText: 'text-foreground',
              userButtonPopoverActionButtonIcon: 'text-muted-foreground',
              userButtonPopoverFooter: 'hidden', // Hide Clerk branding
            },
          }}
        >
          {/* Custom menu items */}
          <UserButton.MenuItems>
            <UserButton.Link
              label="Settings"
              labelIcon={<Settings className="h-4 w-4" />}
              href="/settings"
            />
          </UserButton.MenuItems>
        </UserButton>
      </SignedIn>

      {/* Fallback for signed-out state (shouldn't normally show in nav) */}
      <SignedOut>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/sign-in">Sign In</Link>
        </Button>
      </SignedOut>
    </div>
  )
}
