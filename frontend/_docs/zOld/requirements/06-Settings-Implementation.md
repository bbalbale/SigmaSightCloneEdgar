# Settings Page Implementation Guide

**Purpose**: Step-by-step guide to create the Settings page  
**Route**: `/settings`  
**Features**: User settings, portfolio settings, data export  
**Last Updated**: September 29, 2025

---

## Overview

This page provides settings management with three tabs:
- **User Settings**: Profile, email, password
- **Portfolio Settings**: Name, currency, preferences
- **Export**: Download portfolio data (CSV, JSON)

---

## Service Dependencies

### Services Used (Already Exist)
```typescript
import { apiClient } from '@/services/apiClient'      // HTTP client
import { authManager } from '@/services/authManager'  // Auth management
import { useAuth } from '@/app/providers'             // Auth context
```

### API Endpoints Used

#### User Endpoints
```
GET  /auth/me                              # Get user info
PATCH /auth/me                             # Update user info
POST /auth/change-password                 # Change password
```

#### Portfolio Endpoints
```
GET  /data/portfolio/{id}/complete         # Get portfolio details
PATCH /data/portfolio/{id}                 # Update portfolio
```

#### Export Endpoints
```
POST /data/portfolio/{id}/export           # Export data
GET  /data/positions/details?format=csv    # Export positions
```

---

## Implementation Steps

### Step 1: Create UI Components

#### Component A: User Settings Form

**File**: `src/components/settings/UserSettingsForm.tsx`

```typescript
// src/components/settings/UserSettingsForm.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/services/apiClient'
import { useAuth } from '@/app/providers'

interface User {
  id: string
  email: string
  full_name: string
}

interface UserSettingsFormProps {
  user: User | null
}

export function UserSettingsForm({ user }: UserSettingsFormProps) {
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const { refreshSession } = useAuth()
  
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    
    try {
      await apiClient.patch('/api/v1/auth/me', {
        full_name: fullName
      })
      
      await refreshSession()  // Refresh user data
      setMessage('Profile updated successfully')
    } catch (error) {
      console.error('Failed to update profile:', error)
      setMessage('Failed to update profile')
    } finally {
      setLoading(false)
    }
  }
  
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (newPassword !== confirmPassword) {
      setMessage('Passwords do not match')
      return
    }
    
    setLoading(true)
    setMessage('')
    
    try {
      await apiClient.post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setMessage('Password changed successfully')
    } catch (error) {
      console.error('Failed to change password:', error)
      setMessage('Failed to change password')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={user?.email || ''}
                disabled
                className="bg-gray-50"
              />
              <p className="text-xs text-gray-500 mt-1">
                Email cannot be changed
              </p>
            </div>
            
            <div>
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
              />
            </div>
            
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : 'Save Profile'}
            </Button>
          </form>
        </CardContent>
      </Card>
      
      {/* Password Change */}
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </div>
            
            <div>
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
              />
            </div>
            
            <div>
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
              />
            </div>
            
            <Button type="submit" disabled={loading}>
              {loading ? 'Changing...' : 'Change Password'}
            </Button>
          </form>
        </CardContent>
      </Card>
      
      {/* Status Message */}
      {message && (
        <div className={`p-4 rounded ${
          message.includes('success') 
            ? 'bg-green-50 text-green-800' 
            : 'bg-red-50 text-red-800'
        }`}>
          {message}
        </div>
      )}
    </div>
  )
}
```

**Key Points**:
- ✅ Uses existing `apiClient` service
- ✅ Profile update with full name
- ✅ Password change with validation
- ✅ Success/error messages
- ✅ Disabled email field (can't change)

#### Component B: Portfolio Settings Form

**File**: `src/components/settings/PortfolioSettingsForm.tsx`

```typescript
// src/components/settings/PortfolioSettingsForm.tsx
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiClient } from '@/services/apiClient'

interface PortfolioSettingsFormProps {
  portfolioId: string
}

export function PortfolioSettingsForm({ portfolioId }: PortfolioSettingsFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [currency, setCurrency] = useState('USD')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  
  useEffect(() => {
    fetchPortfolioDetails()
  }, [portfolioId])
  
  const fetchPortfolioDetails = async () => {
    try {
      const endpoint = `/api/v1/data/portfolio/${portfolioId}/complete`
      const portfolio = await apiClient.get(endpoint)
      
      setName(portfolio.name || '')
      setDescription(portfolio.description || '')
      setCurrency(portfolio.currency || 'USD')
    } catch (error) {
      console.error('Failed to fetch portfolio:', error)
    }
  }
  
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    
    try {
      await apiClient.patch(`/api/v1/data/portfolio/${portfolioId}`, {
        name,
        description,
        currency
      })
      
      setMessage('Portfolio settings updated successfully')
    } catch (error) {
      console.error('Failed to update portfolio:', error)
      setMessage('Failed to update portfolio settings')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div>
              <Label htmlFor="portfolio_name">Portfolio Name</Label>
              <Input
                id="portfolio_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Portfolio"
              />
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Portfolio description"
              />
            </div>
            
            <div>
              <Label htmlFor="currency">Base Currency</Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger id="currency">
                  <SelectValue placeholder="Select currency" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="EUR">EUR</SelectItem>
                  <SelectItem value="GBP">GBP</SelectItem>
                  <SelectItem value="JPY">JPY</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : 'Save Settings'}
            </Button>
          </form>
        </CardContent>
      </Card>
      
      {message && (
        <div className={`p-4 rounded ${
          message.includes('success') 
            ? 'bg-green-50 text-green-800' 
            : 'bg-red-50 text-red-800'
        }`}>
          {message}
        </div>
      )}
    </div>
  )
}
```

**Key Points**:
- ✅ Uses existing `apiClient` service
- ✅ Fetches current portfolio settings
- ✅ Updates name, description, currency
- ✅ Currency dropdown
- ✅ Success/error messages

#### Component C: Export Form

**File**: `src/components/settings/ExportForm.tsx`

```typescript
// src/components/settings/ExportForm.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Download } from 'lucide-react'
import { apiClient } from '@/services/apiClient'

interface ExportFormProps {
  portfolioId: string
}

export function ExportForm({ portfolioId }: ExportFormProps) {
  const [format, setFormat] = useState<'csv' | 'json'>('csv')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  
  const handleExport = async () => {
    setLoading(true)
    setMessage('')
    
    try {
      // Export positions
      const endpoint = `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
      const response = await apiClient.get<{ positions: any[] }>(endpoint)
      
      const positions = response.positions || []
      
      if (format === 'csv') {
        exportAsCSV(positions)
      } else {
        exportAsJSON(positions)
      }
      
      setMessage(`Successfully exported ${positions.length} positions as ${format.toUpperCase()}`)
    } catch (error) {
      console.error('Export failed:', error)
      setMessage('Failed to export portfolio data')
    } finally {
      setLoading(false)
    }
  }
  
  const exportAsCSV = (positions: any[]) => {
    if (positions.length === 0) {
      setMessage('No positions to export')
      return
    }
    
    // Create CSV headers
    const headers = Object.keys(positions[0]).join(',')
    
    // Create CSV rows
    const rows = positions.map(position => 
      Object.values(position).map(value => 
        typeof value === 'string' && value.includes(',') 
          ? `"${value}"` 
          : value
      ).join(',')
    )
    
    // Combine headers and rows
    const csv = [headers, ...rows].join('\n')
    
    // Download file
    downloadFile(csv, `portfolio-${portfolioId}.csv`, 'text/csv')
  }
  
  const exportAsJSON = (positions: any[]) => {
    const json = JSON.stringify(positions, null, 2)
    downloadFile(json, `portfolio-${portfolioId}.json`, 'application/json')
  }
  
  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Export Portfolio Data</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Export Format</Label>
            <RadioGroup value={format} onValueChange={(value) => setFormat(value as 'csv' | 'json')}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="csv" id="csv" />
                <Label htmlFor="csv" className="font-normal cursor-pointer">
                  CSV (Comma-Separated Values)
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="json" id="json" />
                <Label htmlFor="json" className="font-normal cursor-pointer">
                  JSON (JavaScript Object Notation)
                </Label>
              </div>
            </RadioGroup>
          </div>
          
          <div className="border-t pt-4">
            <p className="text-sm text-gray-600 mb-4">
              Export includes all positions with current prices, P&L, and metadata.
            </p>
            <Button onClick={handleExport} disabled={loading}>
              <Download className="h-4 w-4 mr-2" />
              {loading ? 'Exporting...' : `Export as ${format.toUpperCase()}`}
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {message && (
        <div className={`p-4 rounded ${
          message.includes('Success') 
            ? 'bg-green-50 text-green-800' 
            : 'bg-red-50 text-red-800'
        }`}>
          {message}
        </div>
      )}
    </div>
  )
}
```

**Key Points**:
- ✅ Uses existing `apiClient` service
- ✅ CSV and JSON export formats
- ✅ Client-side file generation
- ✅ Automatic download
- ✅ Success/error messages

---

### Step 2: Create Container Component

**File**: `src/containers/SettingsContainer.tsx`

```typescript
// src/containers/SettingsContainer.tsx
'use client'

import { useState } from 'react'
import { useAuth } from '@/app/providers'
import { UserSettingsForm } from '@/components/settings/UserSettingsForm'
import { PortfolioSettingsForm } from '@/components/settings/PortfolioSettingsForm'
import { ExportForm } from '@/components/settings/ExportForm'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function SettingsContainer() {
  const { user, portfolioId } = useAuth()
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
      
      <Tabs defaultValue="user" className="space-y-6">
        <TabsList>
          <TabsTrigger value="user">User</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
        </TabsList>
        
        <TabsContent value="user" className="space-y-6">
          <UserSettingsForm user={user} />
        </TabsContent>
        
        <TabsContent value="portfolio" className="space-y-6">
          {portfolioId ? (
            <PortfolioSettingsForm portfolioId={portfolioId} />
          ) : (
            <div className="text-center py-8 text-gray-500">
              No portfolio found
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="export" className="space-y-6">
          {portfolioId ? (
            <ExportForm portfolioId={portfolioId} />
          ) : (
            <div className="text-center py-8 text-gray-500">
              No portfolio found
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

**Key Points**:
- ✅ Three-tab layout
- ✅ Conditional rendering based on portfolioId
- ✅ Clean composition
- ✅ ~35 lines total

---

### Step 3: Create Thin Page Route

**File**: `app/settings/page.tsx`

```typescript
// app/settings/page.tsx
'use client'

import { SettingsContainer } from '@/containers/SettingsContainer'

export default function SettingsPage() {
  return <SettingsContainer />
}
```

**Key Points**:
- ✅ Only 8 lines
- ✅ Just imports and renders container
- ✅ No business logic
- ✅ Client component

---

## File Creation Checklist

### Files to Create
- [ ] `src/components/settings/UserSettingsForm.tsx` - User settings
- [ ] `src/components/settings/PortfolioSettingsForm.tsx` - Portfolio settings
- [ ] `src/components/settings/ExportForm.tsx` - Data export
- [ ] `src/containers/SettingsContainer.tsx` - Page container
- [ ] `app/settings/page.tsx` - Thin route wrapper

### Dependencies (Already Exist)
- [x] `src/services/apiClient.ts` - HTTP client
- [x] `src/services/authManager.ts` - Auth management
- [x] `app/providers.tsx` - Auth context
- [x] `src/components/ui/*` - ShadCN UI components

---

## Testing Steps

1. **Create components** in order: Forms → Container → Page
2. **Test user settings** - Update name, change password
3. **Test portfolio settings** - Update name, description, currency
4. **Test export** - Export as CSV and JSON
5. **Test tabs** - Switch between tabs
6. **Test validation** - Password mismatch, required fields
7. **Test errors** - Handle API failures
8. **Test navigation** - Go to `/settings`
9. **Test refresh** - User data updates after save
10. **Test download** - Files download correctly

---

## Common Issues & Solutions

### Issue 1: User data not loading
**Symptom**: Empty form fields  
**Cause**: useAuth() returns null user  
**Solution**: Check authentication, verify user is logged in

### Issue 2: Portfolio settings not saving
**Symptom**: Save button doesn't work  
**Cause**: portfolioId is null  
**Solution**: Check portfolioResolver has loaded ID

### Issue 3: Export downloads empty file
**Symptom**: Downloaded file has no data  
**Cause**: API returns empty positions array  
**Solution**: Check backend has position data

### Issue 4: Password change fails
**Symptom**: Error message shows  
**Cause**: Current password incorrect or validation failed  
**Solution**: Verify current password, check minimum password requirements

---

## Export Format Examples

### CSV Export
```csv
id,symbol,quantity,position_type,current_price,market_value,cost_basis,unrealized_pnl
uuid1,AAPL,100,LONG,150.00,15000.00,14000.00,1000.00
uuid2,GOOGL,50,LONG,2800.00,140000.00,130000.00,10000.00
```

### JSON Export
```json
[
  {
    "id": "uuid1",
    "symbol": "AAPL",
    "quantity": 100,
    "position_type": "LONG",
    "current_price": 150.00,
    "market_value": 15000.00,
    "cost_basis": 14000.00,
    "unrealized_pnl": 1000.00
  },
  {
    "id": "uuid2",
    "symbol": "GOOGL",
    "quantity": 50,
    "position_type": "LONG",
    "current_price": 2800.00,
    "market_value": 140000.00,
    "cost_basis": 130000.00,
    "unrealized_pnl": 10000.00
  }
]
```

---

## Future Enhancements

### Optional Features to Add Later

1. **User Preferences**
   - Theme selection (dark/light)
   - Default currency
   - Notification settings

2. **Portfolio Management**
   - Create additional portfolios
   - Delete portfolio
   - Archive portfolio

3. **Data Import**
   - Import positions from CSV
   - Bulk update positions
   - Import from broker APIs

4. **Export Options**
   - Date range filtering
   - Custom field selection
   - Scheduled exports

5. **Security**
   - Two-factor authentication
   - Session management
   - API key generation

---

## Summary

**Pattern**: Three forms → Container with tabs → Page  
**Services Used**: apiClient, authManager (via useAuth)  
**New Files**: 5 total (3 components, 1 container, 1 page)  
**Features**: User profile, portfolio settings, data export  
**Key Advantage**: Centralized settings management with tab organization
