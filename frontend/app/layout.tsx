import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '@/styles/globals.css'
import { Providers } from './providers'
import { ConditionalNavigationHeader } from '@/components/navigation/ConditionalNavigationHeader'
import { ThemeProvider } from '@/contexts/ThemeContext'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
})

export const metadata: Metadata = {
  title: 'SigmaSight - Portfolio Risk Analytics',
  description: 'AI-driven institutional grade portfolio analysis in plain English',
  keywords: ['portfolio', 'risk', 'analytics', 'finance', 'investment'],
  authors: [{ name: 'SigmaSight Team' }],
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.variable} font-sans antialiased h-full bg-background text-foreground`}>
        <ThemeProvider>
          <Providers>
            <div className="flex min-h-screen flex-col">
              <ConditionalNavigationHeader />
              <main className="flex-1">
                {children}
              </main>
            </div>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  )
}
