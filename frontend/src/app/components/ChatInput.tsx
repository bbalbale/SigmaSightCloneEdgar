"use client"

import { useState } from 'react'

interface ChatInputProps {
  placeholder?: string
  className?: string
}

export function ChatInput({ placeholder = "Ask a question...", className = "" }: ChatInputProps) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim()) {
      // Handle chat submission here
      console.log('Chat message:', message)
      setMessage('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={placeholder}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Send
        </button>
      </div>
    </form>
  )
}