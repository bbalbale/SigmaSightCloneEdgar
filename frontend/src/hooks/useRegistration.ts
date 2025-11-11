'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { onboardingService, RegisterUserData } from '@/services/onboardingService'
import { authManager } from '@/services/authManager'

interface UseRegistrationReturn {
  formData: RegisterUserData
  setFormData: (data: RegisterUserData) => void
  isSubmitting: boolean
  error: string | null
  handleSubmit: () => Promise<void>
}

/**
 * Hook for handling user registration and auto-login
 */
export function useRegistration(): UseRegistrationReturn {
  const router = useRouter()
  const [formData, setFormData] = useState<RegisterUserData>({
    full_name: '',
    email: '',
    password: '',
    invite_code: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError(null)

    try {
      // 1. Register user
      console.log('Step 1: Registering user...')
      const registerResponse = await onboardingService.register(formData)
      console.log('Step 1 SUCCESS: Registration response:', registerResponse)

      // 2. Auto-login with normalized email from registration response
      // IMPORTANT: Use the email from the response, not formData.email, to avoid case sensitivity issues
      console.log('Step 2: Auto-login with email:', registerResponse.email)
      const loginResponse = await onboardingService.login(registerResponse.email, formData.password)
      console.log('Step 2 SUCCESS: Login response:', loginResponse)

      // 3. Store JWT session
      console.log('Step 3: Storing session...')
      authManager.setSession({
        token: loginResponse.access_token,
        email: registerResponse.email,
        tokenType: loginResponse.token_type,
        expiresIn: loginResponse.expires_in
      })
      console.log('Step 3 SUCCESS: Session stored')

      // 4. Navigate to upload page
      console.log('Step 4: Navigating to /onboarding/upload')
      router.push('/onboarding/upload')
    } catch (err: any) {
      console.error('Registration flow error:', err)
      setError(getErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    formData,
    setFormData,
    isSubmitting,
    error,
    handleSubmit,
  }
}

/**
 * Extract user-friendly error message from API error
 */
function getErrorMessage(error: any): string {
  // Handle structured error responses from backend
  if (error?.data?.detail) {
    const detail = error.data.detail

    // If detail has a message property (structured error)
    if (typeof detail === 'object' && detail.message) {
      return detail.message
    }

    // If detail is a string
    if (typeof detail === 'string') {
      return detail
    }
  }

  // Handle status codes with friendly messages
  if (error?.status) {
    switch (error.status) {
      case 401:
        return "That invite code isn't valid. Please check your email and try again."
      case 409:
        return 'An account with this email already exists. Try signing in instead?'
      case 422:
        return 'Please check your information and try again.'
      default:
        return `Registration failed (${error.status}). Please try again.`
    }
  }

  // Network errors
  if (error?.name === 'NetworkError') {
    return 'Connection error. Please check your internet and try again.'
  }

  // Default fallback
  return 'Registration failed. Please try again.'
}
