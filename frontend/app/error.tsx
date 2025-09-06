'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-destructive mb-4">Something went wrong!</h2>
        <p className="text-muted-foreground mb-4">
          An error occurred while loading the application.
        </p>
        <button
          className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md"
          onClick={() => reset()}
        >
          Try again
        </button>
      </div>
    </div>
  )
}