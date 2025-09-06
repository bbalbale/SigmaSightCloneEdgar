import { redirect } from 'next/navigation'

export default function RootPage() {
  // Redirect to portfolio page as the main app entry point
  redirect('/portfolio')
}