'use client'

import { SignIn } from '@clerk/nextjs'
import { dark } from '@clerk/themes'

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-md px-4">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-foreground">
            Welcome to SigmaSight
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            AI-powered portfolio risk analytics
          </p>
        </div>
        <SignIn
          fallbackRedirectUrl="/command-center"
          appearance={{
            baseTheme: dark,
            elements: {
              formButtonPrimary:
                'bg-primary hover:bg-primary/90 text-primary-foreground',
              card: 'bg-card border border-border shadow-lg',
              headerTitle: 'text-foreground',
              headerSubtitle: 'text-muted-foreground',
              socialButtonsBlockButton:
                'bg-muted hover:bg-muted/80 text-foreground border border-border',
              formFieldLabel: 'text-foreground',
              formFieldInput:
                'bg-background border-border text-foreground placeholder:text-muted-foreground',
              footerActionLink: 'text-primary hover:text-primary/80',
              identityPreviewText: 'text-foreground',
              identityPreviewEditButton: 'text-primary',
            },
          }}
        />
      </div>
    </div>
  )
}
