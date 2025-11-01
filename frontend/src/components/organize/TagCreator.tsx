'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, Check, X } from 'lucide-react'

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
  onCancel?: () => void
}

export function TagCreator({ onCreate, onCancel }: TagCreatorProps) {
  // If onCancel is provided (modal mode), start in creating state
  const [isCreating, setIsCreating] = useState(!!onCancel)
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
    if (onCancel) {
      onCancel()
    } else {
      setIsCreating(false)
    }
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
    <div className="rounded-lg p-4 space-y-3 transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-primary)'
    }}>
      <Input
        placeholder="Create a new tag..."
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isSubmitting}
        maxLength={50}
        autoFocus
        className="transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-tertiary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}
      />

      <div className="flex items-center gap-2">
        <div className="text-sm transition-colors duration-300" style={{
          color: 'var(--text-primary)'
        }}>Color:</div>
        <div className="flex gap-2 flex-wrap">
          {PRESET_COLORS.map((preset) => (
            <button
              key={preset.color}
              onClick={() => setSelectedColor(preset.color)}
              className="w-8 h-8 rounded transition-all"
              style={{
                backgroundColor: preset.color,
                ...(selectedColor === preset.color && {
                  boxShadow: '0 0 0 2px var(--bg-secondary), 0 0 0 4px var(--border-primary)'
                })
              }}
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
          className="transition-colors duration-300"
          style={{
            backgroundColor: 'var(--bg-primary)',
            color: 'var(--text-primary)'
          }}
        >
          <Check className="h-4 w-4 mr-1" />
          {isSubmitting ? 'Creating...' : 'Add'}
        </Button>
        <Button
          onClick={handleCancel}
          size="sm"
          variant="ghost"
          disabled={isSubmitting}
          className="transition-colors duration-300"
        >
          <X className="h-4 w-4 mr-1" />
          Cancel
        </Button>
      </div>
    </div>
  )
}
