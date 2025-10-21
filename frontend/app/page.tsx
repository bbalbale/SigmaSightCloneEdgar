import { redirect } from 'next/navigation'

export default function RootPage() {
  // Redirect to dashboard page as the main app entry point
  redirect('/dashboard')
}