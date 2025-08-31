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
    <div className={`${className.includes('flex-1') ? '' : className.includes('max-w-none') ? 'w-full' : 'max-w-lg mx-auto'} ${className}`}>
      <input
        type="text"
        placeholder={placeholder}
        className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-400 border-gray-300 bg-white text-gray-900 placeholder:text-gray-500"
      />
    </div>
  )
}