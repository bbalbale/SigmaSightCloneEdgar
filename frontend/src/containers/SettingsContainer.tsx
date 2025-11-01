'use client'

import React from 'react'
import { useAuth } from '../../app/providers'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { User } from 'lucide-react'

export function SettingsContainer() {
  const { user } = useAuth()

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2">Manage your account settings and preferences</p>
      </div>

      {/* User Profile Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            User Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Full Name</label>
            <p className="text-base mt-1">{user?.fullName || 'N/A'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Email</label>
            <p className="text-base mt-1">{user?.email || 'N/A'}</p>
          </div>
        </CardContent>
      </Card>

      {/* Placeholder for future settings */}
      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
          <CardDescription>Customize your SigmaSight experience</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Additional settings coming soon...</p>
        </CardContent>
      </Card>
    </div>
  )
}
