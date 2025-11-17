'use client'

import { useState } from 'react'
import { useRegistration } from '@/hooks/useRegistration'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function RegistrationForm() {
  const { formData, setFormData, isSubmitting, error, handleSubmit } = useRegistration()

  // Field-level errors
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleFieldChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value })
    // Clear field error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors({ ...fieldErrors, [field]: '' })
    }
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!formData.full_name.trim()) {
      errors.full_name = 'Name is required'
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address'
    }

    if (!formData.password) {
      errors.password = 'Password is required'
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters'
    } else {
      // Check for specific password requirements
      const hasUpper = /[A-Z]/.test(formData.password)
      const hasLower = /[a-z]/.test(formData.password)
      const hasDigit = /[0-9]/.test(formData.password)

      if (!hasUpper) {
        errors.password = 'Password must contain at least one uppercase letter'
      } else if (!hasLower) {
        errors.password = 'Password must contain at least one lowercase letter'
      } else if (!hasDigit) {
        errors.password = 'Password must contain at least one number'
      }
    }

    if (!formData.invite_code.trim()) {
      errors.invite_code = 'Invite code is required'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    await handleSubmit()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md space-y-8 px-4 py-8">
        <div className="space-y-2 px-6">
          <h1 className="text-2xl font-bold tracking-tight">Welcome to SigmaSight 🚀</h1>
          <p className="text-muted-foreground">🙏 for being a trusted tester. This is super early stage, and your feedback is 💎 to us!</p>
        </div>

        <Card className="shadow-lg">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl">Create Account</CardTitle>
            <CardDescription>
              Enter your information and invite code to get started
            </CardDescription>
          </CardHeader>

          <form onSubmit={onSubmit}>
            <CardContent className="space-y-4">
              {/* Global error alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Full Name */}
              <div className="space-y-2">
                <label htmlFor="full_name" className="text-sm font-medium leading-none">
                  Full Name
                </label>
                <Input
                  id="full_name"
                  type="text"
                  placeholder="John Doe"
                  value={formData.full_name}
                  onChange={(e) => handleFieldChange('full_name', e.target.value)}
                  disabled={isSubmitting}
                  className={fieldErrors.full_name ? 'border-red-500' : ''}
                />
                {fieldErrors.full_name && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {fieldErrors.full_name}
                  </p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium leading-none">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) => handleFieldChange('email', e.target.value)}
                  disabled={isSubmitting}
                  className={fieldErrors.email ? 'border-red-500' : ''}
                />
                {fieldErrors.email && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {fieldErrors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium leading-none">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Create a secure password"
                  value={formData.password}
                  onChange={(e) => handleFieldChange('password', e.target.value)}
                  disabled={isSubmitting}
                  className={fieldErrors.password ? 'border-red-500' : ''}
                />
                {fieldErrors.password && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {fieldErrors.password}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Must be at least 8 characters with uppercase, lowercase, and a number
                </p>
              </div>

              {/* Invite Code */}
              <div className="space-y-2">
                <label htmlFor="invite_code" className="text-sm font-medium leading-none">
                  Invite Code
                </label>
                <Input
                  id="invite_code"
                  type="text"
                  placeholder="Enter your invite code"
                  value={formData.invite_code}
                  onChange={(e) => handleFieldChange('invite_code', e.target.value)}
                  disabled={isSubmitting}
                  className={fieldErrors.invite_code ? 'border-red-500' : ''}
                />
                {fieldErrors.invite_code && (
                  <p className="text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {fieldErrors.invite_code}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Check your welcome email for your invite code
                </p>
              </div>
            </CardContent>

            <CardFooter>
              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating Account...
                  </>
                ) : (
                  'Create Account →'
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <p className="text-sm text-muted-foreground px-6">
          Already have an account?{' '}
          <a href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  )
}
