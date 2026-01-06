import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ClerkProvider } from '@clerk/nextjs'
import '@/styles/globals.css'
import '@/styles/theme-utilities.css'
import { Providers } from './providers'
import { ConditionalNavigationHeader } from '@/components/navigation/ConditionalNavigationHeader'
import { BottomNavigation } from '@/components/navigation/BottomNavigation'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
})

export const metadata: Metadata = {
  title: 'SigmaSight - Portfolio Risk Analytics',
  description: 'AI-driven institutional grade portfolio analysis in plain English',
  keywords: ['portfolio', 'risk', 'analytics', 'finance', 'investment'],
  authors: [{ name: 'SigmaSight Team' }],
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en" className="h-full dark">
        <body className={`${inter.variable} font-sans antialiased h-full bg-background text-foreground`}>
          <Providers>
            <div className="flex min-h-screen flex-col">
              <ConditionalNavigationHeader />
              <main className="flex-1 pb-16 md:pb-0">
                {children}
              </main>
              <BottomNavigation className="md:hidden" />
            </div>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  )
}
