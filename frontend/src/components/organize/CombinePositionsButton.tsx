'use client'

import { Button } from '@/components/ui/button'
import { Layers } from 'lucide-react'

interface CombinePositionsButtonProps {
  selectedCount: number
  onClick: () => void
  onClear: () => void
}

export function CombinePositionsButton({
  selectedCount,
  onClick,
  onClear
}: CombinePositionsButtonProps) {
  if (selectedCount < 2) {
    return null
  }

  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
      <div className="bg-white border border-gray-300 rounded-lg shadow-lg px-4 py-3 flex items-center gap-3">
        <span className="text-sm text-gray-600">
          {selectedCount} positions selected
        </span>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClear}
          >
            Clear
          </Button>

          <Button
            size="sm"
            onClick={onClick}
            className="bg-black hover:bg-gray-800 text-white"
          >
            <Layers className="h-4 w-4 mr-2" />
            Combine {selectedCount} items
          </Button>
        </div>
      </div>
    </div>
  )
}
