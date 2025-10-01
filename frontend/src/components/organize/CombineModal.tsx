'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface CombineModalProps {
  open: boolean
  onClose: () => void
  onConfirm: (data: { name: string; type: string; description: string }) => void
  selectedCount: number
}

export function CombineModal({
  open,
  onClose,
  onConfirm,
  selectedCount
}: CombineModalProps) {
  const [name, setName] = useState('')
  const [type, setType] = useState<'LONG' | 'SHORT'>('LONG')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      alert('Strategy name is required')
      return
    }

    setIsSubmitting(true)

    try {
      await onConfirm({
        name: name.trim(),
        type,
        description: description.trim()
      })

      // Reset form
      setName('')
      setType('LONG')
      setDescription('')
    } catch (error) {
      console.error('Failed to create strategy:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setName('')
      setType('LONG')
      setDescription('')
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create a Combined Position</DialogTitle>
          <DialogDescription>
            Select a name and whether it should be long or short.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {/* Name field */}
            <div className="space-y-2">
              <label htmlFor="strategy-name" className="text-sm font-medium text-gray-700">
                Name *
              </label>
              <Input
                id="strategy-name"
                placeholder="e.g. Tech Pairs Trade"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={isSubmitting}
              />
            </div>

            {/* Type field */}
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">Type *</div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="strategy-type"
                    value="LONG"
                    checked={type === 'LONG'}
                    onChange={(e) => setType('LONG')}
                    disabled={isSubmitting}
                    className="cursor-pointer"
                  />
                  <span>Long</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="strategy-type"
                    value="SHORT"
                    checked={type === 'SHORT'}
                    onChange={(e) => setType('SHORT')}
                    disabled={isSubmitting}
                    className="cursor-pointer"
                  />
                  <span>Short</span>
                </label>
              </div>
            </div>

            {/* Description field */}
            <div className="space-y-2">
              <label htmlFor="strategy-description" className="text-sm font-medium text-gray-700">
                Description (optional)
              </label>
              <textarea
                id="strategy-description"
                placeholder="Add notes about this strategy..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isSubmitting}
                className="w-full min-h-[80px] px-3 py-2 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                maxLength={500}
              />
              <p className="text-xs text-gray-500">
                {description.length}/500 characters
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-black hover:bg-gray-800 text-white"
            >
              {isSubmitting ? 'Creating...' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
