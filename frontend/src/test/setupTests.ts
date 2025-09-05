// Vitest setup for React + jsdom
import { vi } from 'vitest'

// Ensure timers are modern
vi.useRealTimers()

// No-op: keep console logs visible during test runs for SSE diagnostics
// You can silence selectively if needed.

// Polyfills for jsdom
if (!HTMLElement.prototype.scrollIntoView) {
  // @ts-ignore
  HTMLElement.prototype.scrollIntoView = vi.fn()
}
