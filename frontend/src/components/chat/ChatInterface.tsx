"use client"

import { useEffect, useRef, useCallback } from 'react'
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle,
  SheetTrigger 
} from '@/components/ui/sheet'
import { ChatInput } from '@/app/components/ChatInput'
import { MessageSquare, AlertCircle, WifiOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chatStore'
import { useStreamStore } from '@/stores/streamStore'
import { useFetchStreaming } from '@/hooks/useFetchStreaming'
import { chatAuthService } from '@/services/chatAuthService'
import { chatService } from '@/services/chatService'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  // Persistent state from chatStore
  const {
    isOpen,
    currentMode,
    currentConversationId,
    setOpen,
    setMode,
    addMessage,
    updateMessage,
    getMessages,
    createConversation,
  } = useChatStore()
  
  // Runtime streaming state from streamStore
  const {
    isStreaming,
    currentRunId,
    streamBuffers,
    messageQueue,
    queueMessage,
    processQueue,
  } = useStreamStore()
  
  // Force re-render when streamBuffers change
  const streamBuffersSize = streamBuffers.size
  
  // Streaming hook
  const { streamMessage, abortStream } = useFetchStreaming()
  
  // Get messages for current conversation
  const messages = getMessages()
  
  // Track current assistant message being streamed
  const currentAssistantMessageId = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const hasInteracted = messages.length > 0
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamBuffers])
  
  // Process message queue when streaming completes
  useEffect(() => {
    if (!isStreaming && messageQueue) {
      const queued = processQueue()
      if (queued) {
        handleSendMessage(queued.message)
      }
    }
  }, [isStreaming, messageQueue])

  const modeColors = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    indigo: 'bg-indigo-500',
    violet: 'bg-violet-500'
  }

  const modeDescriptions: Record<typeof currentMode, string> = {
    green: 'Educational & Detailed',
    blue: 'Concise & Quantitative',
    indigo: 'Strategic & Narrative',
    violet: 'Conservative & Risk-Focused'
  }
  
  // Handle sending messages with streaming
  const handleSendMessage = useCallback(async (text: string) => {
    // Check for mode switch command
    const modeSwitchMatch = text.match(/^\/mode\s+(green|blue|indigo|violet)$/i)
    if (modeSwitchMatch) {
      const newMode = modeSwitchMatch[1].toLowerCase() as typeof currentMode
      setMode(newMode)
      
      // Update backend if conversation exists
      if (currentConversationId) {
        try {
          await chatService.updateConversationMode(currentConversationId, newMode)
        } catch (error) {
          console.error('Failed to update mode on backend:', error)
        }
      }
      
      // Add system message about mode change
      addMessage({
        conversationId: currentConversationId || 'temp',
        role: 'system',
        content: `Mode switched to ${newMode} (${modeDescriptions[newMode]})`,
      })
      return
    }
    
    // Check if we're already streaming - queue if so
    if (isStreaming && currentConversationId) {
      queueMessage(currentConversationId, text)
      return
    }
    
    // Ensure we have a conversation on the backend
    let conversationId = currentConversationId
    
    if (!conversationId) {
      try {
        // Create conversation on backend first
        const backendConversation = await chatService.createConversation(currentMode)
        // Update local store with backend conversation ID
        conversationId = backendConversation.id
        createConversation(currentMode, conversationId)
      } catch (error) {
        console.error('Failed to create conversation:', error)
        // Show error message to user
        addMessage({
          conversationId: 'temp',
          role: 'system',
          content: 'Failed to create conversation. Please check your connection and try again.',
        })
        return
      }
    }
    
    // Add user message to persistent store
    addMessage({
      conversationId,
      role: 'user',
      content: text,
    })
    
    // Create placeholder for assistant message
    const assistantMessageId = `msg_${Date.now()}_assistant`
    currentAssistantMessageId.current = assistantMessageId
    
    addMessage({
      conversationId,
      role: 'assistant',
      content: 'Thinking...', // Show placeholder text while streaming
    })
    
    try {
      // Check authentication
      const isAuthenticated = await chatAuthService.refreshIfNeeded()
      if (!isAuthenticated) {
        updateMessage(assistantMessageId, {
          content: 'Please log in to use the chat assistant.',
          error: {
            message: 'Authentication required',
            error_type: 'AUTH_EXPIRED',
          },
        })
        return
      }
      
      // Start streaming - declare runId first
      let runId: string | null = null
      runId = await streamMessage(conversationId, text, {
        onToken: (token: string, runIdFromEvent?: string) => {
          console.log('ChatInterface onToken received:', token, 'runId:', runIdFromEvent);
          // Use the runId from the event, not the local variable
          const actualRunId = runIdFromEvent || runId || ''
          console.log('All stream buffers:', Array.from(streamBuffers.entries()));
          console.log('Looking for buffer with runId:', actualRunId);
          const buffer = streamBuffers.get(actualRunId)
          console.log('Stream buffer for runId:', actualRunId, buffer);
          if (buffer && currentAssistantMessageId.current) {
            console.log('Updating message with buffer text:', buffer.text);
            updateMessage(currentAssistantMessageId.current, {
              content: buffer.text,
            })
          } else {
            console.log('No buffer or messageId:', { buffer, messageId: currentAssistantMessageId.current });
          }
        },
        onError: (error: any) => {
          console.error('Streaming error:', error)
          if (currentAssistantMessageId.current) {
            updateMessage(currentAssistantMessageId.current, {
              content: error.message || 'An error occurred while processing your request.',
              error: {
                message: error.message,
                error_type: error.error_type,
              },
            })
          }
        },
        onDone: (finalText: string) => {
          if (currentAssistantMessageId.current) {
            updateMessage(currentAssistantMessageId.current, {
              content: finalText || 'No response received.',
              runId,
            })
          }
          currentAssistantMessageId.current = null
        },
      })
    } catch (error: any) {
      console.error('Failed to send message:', error)
      
      // If we get a 422 error, the conversation doesn't exist on backend
      // Clear the local conversation and prompt user to try again
      if (error.detail && conversationId && conversationId.startsWith('conv_')) {
        // Clear the invalid local conversation
        setOpen(false)
        setTimeout(() => {
          // Reset the chat store completely
          const { reset } = useChatStore.getState()
          reset()
          setOpen(true)
        }, 100)
        
        return
      }
      
      if (currentAssistantMessageId.current) {
        updateMessage(currentAssistantMessageId.current, {
          content: 'Failed to send message. Please try again.',
          error: {
            message: error.message || 'Unknown error',
            error_type: 'NETWORK_ERROR',
          },
        })
      }
    }
  }, [currentConversationId, currentMode, createConversation, addMessage, updateMessage, streamMessage, streamBuffers, isStreaming, queueMessage, setMode, modeDescriptions])
  
  // Handle abort
  const handleAbort = useCallback(() => {
    abortStream()
    currentAssistantMessageId.current = null
  }, [abortStream])

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
                            onClick={() => handleSendMessage(suggestion)}
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
                            {message.error ? (
                              <div className="flex items-start gap-2">
                                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                <div className="flex-1">
                                  <p className="text-sm">{message.content || message.error.message}</p>
                                  {message.error.error_type === 'AUTH_EXPIRED' && (
                                    <button 
                                      onClick={() => window.location.href = '/login'}
                                      className="text-xs underline mt-1"
                                    >
                                      Go to login
                                    </button>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                            )}
                            <p className="text-xs mt-1 opacity-70">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      ))}
                      
                      {/* Streaming Indicator */}
                      {isStreaming && currentRunId && (
                        <div className="flex justify-start">
                          <div className="bg-gray-100 rounded-lg px-4 py-2">
                            <div className="flex items-center gap-2">
                              <div className="flex space-x-1">
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                              </div>
                              <button
                                onClick={handleAbort}
                                className="text-xs text-gray-500 hover:text-gray-700"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Message queue indicator */}
                      {messageQueue && (
                        <div className="flex justify-center">
                          <div className="text-xs text-gray-500 bg-gray-50 px-3 py-1 rounded-full">
                            Message queued...
                          </div>
                        </div>
                      )}
                      
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </div>
                
                {/* Input Area in Sheet */}
                <div className="border-t p-4 bg-white">
                  <ChatInput
                    placeholder={isStreaming ? "Please wait..." : "Type your message..."}
                    onSubmit={handleSendMessage}
                    className="w-full"
                    disabled={isStreaming}
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
  // This will be handled by the ChatInterface component when it's mounted
  // For now, just open the chat and queue the message
  const chatStore = useChatStore.getState()
  const streamStore = useStreamStore.getState()
  
  chatStore.setOpen(true)
  
  // If streaming, queue the message
  if (streamStore.isStreaming && chatStore.currentConversationId) {
    streamStore.queueMessage(chatStore.currentConversationId, message)
  }
}