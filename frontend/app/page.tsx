import { redirect } from 'next/navigation'

export default function RootPage() {
  // Redirect to command center as the main app entry point
  redirect('/command-center')
}