import { create } from 'zustand'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolCalls?: any[]
}

interface ChatStore {
  // State
  isOpen: boolean
  messages: Message[]
  isStreaming: boolean
  streamingMessage: string
  currentMode: 'green' | 'blue' | 'indigo' | 'violet'
  
  // Actions
  setOpen: (open: boolean) => void
  addMessage: (message: Message) => void
  updateStreamingMessage: (content: string) => void
  setMode: (mode: 'green' | 'blue' | 'indigo' | 'violet') => void
  sendMessage: (text: string) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state
  isOpen: false,
  messages: [],
  isStreaming: false,
  streamingMessage: '',
  currentMode: 'green',
  
  // Actions
  setOpen: (open) => set({ isOpen: open }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  updateStreamingMessage: (content) => set({ streamingMessage: content }),
  
  setMode: (mode) => set({ currentMode: mode }),
  
  sendMessage: (text) => {
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date()
    }
    
    set((state) => ({
      messages: [...state.messages, userMessage],
      isOpen: true // Open chat when message is sent
    }))
    
    // TODO: Connect to backend API
    console.log('Sending message:', text)
    
    // Temporary mock response
    setTimeout(() => {
      const mockResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `This is a mock response to: "${text}". The real OpenAI integration will be connected next.`,
        timestamp: new Date()
      }
      
      get().addMessage(mockResponse)
    }, 1000)
  },
  
  clearMessages: () => set({ messages: [] })
}))