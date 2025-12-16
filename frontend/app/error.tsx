'use client'

import { useEffect, useMemo } from 'react'

// Generate a unique error code from error details
function generateErrorCode(error: Error): string {
  const errorName = error.name || 'Unknown'
  const messageHash = error.message
    ? error.message.slice(0, 50).replace(/[^a-zA-Z0-9]/g, '').slice(0, 8).toUpperCase()
    : 'NODETAIL'
  const timestamp = Date.now().toString(36).slice(-4).toUpperCase()
  return `ERR-${errorName.slice(0, 3).toUpperCase()}-${messageHash}-${timestamp}`
}

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const errorCode = useMemo(() => generateErrorCode(error), [error])

  useEffect(() => {
    // Log detailed error info with code
    console.error(`[${errorCode}] Application error:`, {
      name: error.name,
      message: error.message,
      stack: error.stack,
      digest: error.digest,
    })
  }, [error, errorCode])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center max-w-lg px-4">
        <h2 className="text-2xl font-bold text-destructive mb-4">Something went wrong!</h2>
        <p className="text-muted-foreground mb-2">
          An error occurred while loading the application.
        </p>
        <div className="bg-muted rounded-md p-3 mb-4 text-left">
          <p className="text-xs font-mono text-muted-foreground mb-1">Error Code:</p>
          <p className="text-sm font-mono font-bold text-destructive">{errorCode}</p>
          {error.message && (
            <>
              <p className="text-xs font-mono text-muted-foreground mt-2 mb-1">Message:</p>
              <p className="text-xs font-mono text-foreground break-words">{error.message}</p>
            </>
          )}
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Check browser console (F12) for full details
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