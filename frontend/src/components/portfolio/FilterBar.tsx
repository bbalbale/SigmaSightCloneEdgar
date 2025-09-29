import React from 'react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/contexts/ThemeContext'

interface FilterBarProps {
  onFilterChange?: (filter: string) => void
  onSortChange?: (sort: string) => void
}

export function FilterBar({ onFilterChange, onSortChange }: FilterBarProps) {
  const { theme } = useTheme()

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className={`flex items-center justify-between text-sm transition-colors duration-300 ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zM3 16a1 1 0 011-1h4a1 1 0 110 2H4a1 1 0 01-1-1z"/>
            </svg>
            <span>Filter & Sort:</span>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onFilterChange?.('tags')}
              className={`transition-colors duration-300 ${
                theme === 'dark'
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700'
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}
            >
              Tags
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onFilterChange?.('exposure')}
              className={`transition-colors duration-300 ${
                theme === 'dark'
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700'
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}
            >
              Exposure
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSortChange?.('desc')}
              className={`transition-colors duration-300 ${
                theme === 'dark'
                  ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700'
                  : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
              }`}
            >
              Desc
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}