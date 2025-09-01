"use client"

import { useEffect } from 'react'
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle,
  SheetTrigger 
} from '@/components/ui/sheet'
import { ChatInput } from '@/app/components/ChatInput'
import { MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chatStore'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const {
    isOpen,
    messages,
    isStreaming,
    currentMode,
    setOpen,
    sendMessage,
    setMode
  } = useChatStore()
  
  const hasInteracted = messages.length > 0

  const modeColors = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    indigo: 'bg-indigo-500',
    violet: 'bg-violet-500'
  }

  const modeDescriptions = {
    green: 'Educational & Detailed',
    blue: 'Concise & Quantitative',
    indigo: 'Strategic & Narrative',
    violet: 'Conservative & Risk-Focused'
  }

  return (
    <>
      {/* Sheet Only - No persistent chat bar (ChatInput remains in individual pages) */}
      <Sheet open={isOpen} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          {/* Hidden trigger - will be activated programmatically */}
          <button 
            id="chat-sheet-trigger"
            className="hidden"
            aria-label="Open chat"
          />
        </SheetTrigger>
              
              <SheetContent 
                side="right" 
                className="w-full sm:w-[400px] md:w-[500px] p-0 flex flex-col"
              >
                {/* Header */}
                <SheetHeader className="px-6 py-4 border-b">
                  <div className="flex items-center justify-between">
                    <SheetTitle className="flex items-center gap-2">
                      <MessageSquare className="w-5 h-5" />
                      Portfolio Assistant
                    </SheetTitle>
                    
                    {/* Mode Indicator */}
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        modeColors[currentMode]
                      )} />
                      <span className="text-xs text-gray-500">
                        {modeDescriptions[currentMode]}
                      </span>
                    </div>
                  </div>
                </SheetHeader>
                
                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6">
                  {messages.length === 0 ? (
                    <div className="text-center text-gray-500 mt-8">
                      <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p className="text-sm">Start a conversation about your portfolio</p>
                      
                      {/* Suggested Questions */}
                      <div className="mt-6 space-y-2">
                        <p className="text-xs text-gray-400 mb-3">Try asking:</p>
                        {[
                          "What's my largest position?",
                          "Show me my portfolio performance",
                          "What are my risk exposures?"
                        ].map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => sendMessage(suggestion)}
                            className="block w-full text-left px-4 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {messages.map((message) => (
                        <div
                          key={message.id}
                          className={cn(
                            "flex",
                            message.role === 'user' ? 'justify-end' : 'justify-start'
                          )}
                        >
                          <div
                            className={cn(
                              "max-w-[80%] rounded-lg px-4 py-2",
                              message.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-900'
                            )}
                          >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                            <p className="text-xs mt-1 opacity-70">
                              {message.timestamp.toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      ))}
                      
                      {/* Streaming Indicator */}
                      {isStreaming && (
                        <div className="flex justify-start">
                          <div className="bg-gray-100 rounded-lg px-4 py-2">
                            <div className="flex space-x-1">
                              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Input Area in Sheet */}
                <div className="border-t p-4 bg-white">
                  <ChatInput
                    placeholder="Type your message..."
                    onSubmit={sendMessage}
                    className="w-full"
                  />
                  
                  {/* Mode Selector */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-xs text-gray-500">Mode:</span>
                    <div className="flex gap-1">
                      {(['green', 'blue', 'indigo', 'violet'] as const).map(mode => (
                        <button
                          key={mode}
                          onClick={() => setMode(mode)}
                          className={cn(
                            "w-6 h-6 rounded-full transition-all",
                            modeColors[mode],
                            currentMode === mode 
                              ? 'ring-2 ring-offset-2 ring-gray-400' 
                              : 'opacity-50 hover:opacity-75'
                          )}
                          aria-label={`Switch to ${modeDescriptions[mode]} mode`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
        </SheetContent>
      </Sheet>
    </>
  )
}

// Export a way to open the chat programmatically
export function openChatSheet() {
  useChatStore.getState().setOpen(true)
}

// Export a way to send a message directly
export function sendChatMessage(message: string) {
  useChatStore.getState().sendMessage(message)
}