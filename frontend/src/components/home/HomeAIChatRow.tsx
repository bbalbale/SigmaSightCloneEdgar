'use client'

import React from 'react'
import { CopilotPanel } from '@/components/copilot/CopilotPanel'

const HOME_QUICK_PROMPTS = [
  'How is my portfolio performing compared to the market?',
  'What are my biggest risk exposures?',
  'Should I be concerned about my current volatility levels?',
  'Summarize my portfolio positioning',
]

export function HomeAIChatRow() {
  return (
    <div
      className="themed-border overflow-hidden bg-secondary"
      style={{ borderRadius: 'var(--border-radius)' }}
    >
      <CopilotPanel
        variant="compact"
        height="350px"
        showHeader={true}
        pageHint="home"
        quickPrompts={HOME_QUICK_PROMPTS}
      />
    </div>
  )
}
