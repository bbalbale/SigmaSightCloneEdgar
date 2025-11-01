'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, Check, X } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'

const PRESET_COLORS = [
  { name: 'Core Holding', color: '#3B82F6' },    // blue
  { name: 'High Conviction', color: '#10B981' }, // green
  { name: 'Speculative', color: '#F59E0B' },    // yellow
  { name: 'Hedge', color: '#8B5CF6' },          // purple
  { name: 'Tech', color: '#6366F1' },           // indigo
  { name: 'Finance', color: '#EC4899' },        // pink
  { name: 'Custom 1', color: '#EF4444' },       // red
  { name: 'Custom 2', color: '#14B8A6' },       // teal
]

interface TagCreatorProps {
  onCreate: (name: string, color: string) => Promise<void>
}

export function TagCreator({ onCreate }: TagCreatorProps) {
  const { theme } = useTheme()
  const [isCreating, setIsCreating] = useState(false)
  const [name, setName] = useState('')
  const [selectedColor, setSelectedColor] = useState(PRESET_COLORS[0].color)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleCreate = async () => {
    if (!name.trim()) {
      alert('Tag name is required')
      return
    }

    setIsSubmitting(true)

    try {
      await onCreate(name.trim(), selectedColor)
      setName('')
      setSelectedColor(PRESET_COLORS[0].color)
      setIsCreating(false)
    } catch (error) {
      console.error('Failed to create tag:', error)
      alert('Failed to create tag')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    setName('')
    setSelectedColor(PRESET_COLORS[0].color)
    setIsCreating(false)
  }

  if (!isCreating) {
    return (
      <Button
        onClick={() => setIsCreating(true)}
        size="sm"
        variant="outline"
      >
        <Plus className="h-4 w-4 mr-2" />
        New Tag
      </Button>
    )
  }

  return (
    <div className={`rounded-lg p-4 space-y-3 transition-colors ${
      theme === 'dark'
        ? 'bg-slate-700 border border-slate-600'
        : 'bg-white border border-gray-300'
    }`}>
      <Input
        placeholder="Create a new tag..."
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isSubmitting}
        maxLength={50}
        autoFocus
        className={theme === 'dark' ? 'bg-slate-800 border-slate-600 text-white' : ''}
      />

      <div className="flex items-center gap-2">
        <div className={`text-sm transition-colors ${
          theme === 'dark' ? 'text-primary' : 'text-secondary'
        }`}>Color:</div>
        <div className="flex gap-2 flex-wrap">
          {PRESET_COLORS.map((preset) => (
            <button
              key={preset.color}
              onClick={() => setSelectedColor(preset.color)}
              className={`
                w-8 h-8 rounded transition-all
                ${selectedColor === preset.color
                  ? theme === 'dark'
                    ? 'ring-2 ring-offset-2 ring-slate-500 ring-offset-slate-700'
                    : 'ring-2 ring-offset-2 ring-gray-400'
                  : ''
                }
              `}
              style={{ backgroundColor: preset.color }}
              title={preset.name}
              disabled={isSubmitting}
            />
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleCreate}
          size="sm"
          disabled={isSubmitting || !name.trim()}
          className={`transition-colors ${
            theme === 'dark'
              ? 'bg-primary hover:bg-slate-800 text-white'
              : 'bg-black hover:bg-gray-800 text-white'
          }`}
        >
          <Check className="h-4 w-4 mr-1" />
          {isSubmitting ? 'Creating...' : 'Add'}
        </Button>
        <Button
          onClick={handleCancel}
          size="sm"
          variant="ghost"
          disabled={isSubmitting}
          className={theme === 'dark' ? 'hover:bg-slate-600' : ''}
        >
          <X className="h-4 w-4 mr-1" />
          Cancel
        </Button>
      </div>
    </div>
  )
}
