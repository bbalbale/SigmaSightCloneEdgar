"use client"

import React, { useCallback } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useChatStore } from '@/stores/chatStore'
import { useStreamStore } from '@/stores/streamStore'
import { ChatConversationPane } from '@/components/chat/ChatConversationPane'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const { isOpen, setOpen } = useChatStore()

  const handleConversationReset = useCallback(() => {
    setOpen(false)

    setTimeout(() => {
      useChatStore.getState().reset()
      useStreamStore.getState().reset()
      setOpen(true)
    }, 100)
  }, [setOpen])

  return (
    <Sheet open={isOpen} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button id="chat-sheet-trigger" className="hidden" aria-label="Open chat" />
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:w-[400px] md:w-[500px] p-0 flex flex-col">
        <ChatConversationPane
          variant="sheet"
          isActive={isOpen}
          title="Portfolio Assistant"
          subtitle="Streaming SigmaSight insights in real time"
          onConversationReset={handleConversationReset}
          className={cn('h-full', className)}
        />
      </SheetContent>
    </Sheet>
  )
}

export function openChatSheet() {
  useChatStore.getState().setOpen(true)
}

export function sendChatMessage(message: string) {
  const trimmed = message.trim()
  if (!trimmed) {
    return
  }

  if (typeof window !== 'undefined') {
    sessionStorage.setItem('pendingChatMessage', trimmed)
  }

  useChatStore.getState().setOpen(true)
}
