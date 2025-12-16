/**
 * CopilotSheet Component - Slide-out panel for AI copilot
 *
 * A sheet/drawer that contains the CopilotPanel component.
 * For use on non-AI pages where the copilot should be accessible but not always visible.
 */

'use client'

import React from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription
} from '@/components/ui/sheet'
import { CopilotPanel } from './CopilotPanel'
import { PageHint } from '@/hooks/useCopilot'
import { Sparkles } from 'lucide-react'

export interface CopilotSheetProps {
  /**
   * Whether the sheet is open
   */
  open: boolean

  /**
   * Callback when the sheet open state changes
   */
  onOpenChange: (open: boolean) => void

  /**
   * Page hint for context-aware behavior
   */
  pageHint?: PageHint

  /**
   * Callback when an insight is ready
   */
  onInsightReady?: (insight: string) => void
}

/**
 * CopilotSheet - Slide-out panel containing the copilot
 *
 * @example
 * ```tsx
 * function MyPage() {
 *   const [isOpen, setIsOpen] = useState(false)
 *
 *   return (
 *     <>
 *       <button onClick={() => setIsOpen(true)}>Open Copilot</button>
 *       <CopilotSheet
 *         open={isOpen}
 *         onOpenChange={setIsOpen}
 *         pageHint="portfolio"
 *       />
 *     </>
 *   )
 * }
 * ```
 */
export function CopilotSheet({
  open,
  onOpenChange,
  pageHint,
  onInsightReady
}: CopilotSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg p-0 flex flex-col"
        style={{
          backgroundColor: 'var(--bg-primary)'
        }}
      >
        {/* Accessible header (hidden visually but available to screen readers) */}
        <SheetHeader className="sr-only">
          <SheetTitle>SigmaSight AI Copilot</SheetTitle>
          <SheetDescription>
            Chat with SigmaSight AI about your portfolio
          </SheetDescription>
        </SheetHeader>

        {/* Custom visible header */}
        <div
          className="flex items-center gap-2 p-4 border-b"
          style={{
            borderColor: 'var(--border-primary)',
            backgroundColor: 'var(--bg-primary)'
          }}
        >
          <Sparkles className="h-5 w-5" style={{ color: 'var(--color-accent)' }} />
          <h2
            className="font-semibold text-lg"
            style={{
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}
          >
            SigmaSight AI
          </h2>
        </div>

        {/* Chat panel */}
        <div className="flex-1 overflow-hidden">
          <CopilotPanel
            variant="compact"
            showHeader={false}
            pageHint={pageHint}
            onInsightReady={onInsightReady}
            className="h-full border-0 rounded-none"
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default CopilotSheet
