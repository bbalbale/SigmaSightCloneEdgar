'use client'

import { useRouter } from 'next/navigation'
import { InviteCodeForm } from '@/components/onboarding/InviteCodeForm'

export default function OnboardingInvitePage() {
  const router = useRouter()

  const handleInviteSuccess = () => {
    // After successful invite validation, proceed to portfolio upload
    router.push('/onboarding/upload')
  }

  return <InviteCodeForm onSuccess={handleInviteSuccess} />
}
