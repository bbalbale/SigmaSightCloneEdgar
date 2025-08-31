"use client"

import React from 'react'

interface ChatInputProps {
  placeholder?: string
  className?: string
}

export function ChatInput({ 
  placeholder = "What are my biggest risks? How correlated are my positions?",
  className = ""
}: ChatInputProps) {
  return (
    <div className={`max-w-lg mx-auto ${className}`}>
      <input
        type="text"
        placeholder={placeholder}
        className="w-full px-4 py-3 border border-blue-200 rounded-lg text-foreground placeholder:text-blue-400 bg-background focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  )
}