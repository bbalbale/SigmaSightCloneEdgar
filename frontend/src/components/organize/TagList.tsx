'use client'

import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'
import { TagCreator } from './TagCreator'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Trash } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'

interface TagListProps {
  tags: TagItem[]
  onCreate: (name: string, color: string) => Promise<void>
  onDelete: (tagId: string) => Promise<void>
}

export function TagList({
  tags,
  onCreate,
  onDelete
}: TagListProps) {
  const { theme } = useTheme()

  const handleDelete = async (tagId: string) => {
    if (!confirm('Archive this tag? It will be removed from all strategies.')) {
      return
    }

    try {
      await onDelete(tagId)
    } catch (error) {
      console.error('Failed to delete tag:', error)
      alert('Failed to delete tag')
    }
  }

  return (
    <Card className={`transition-colors ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className={`text-xl font-bold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>Portfolio Tagging & Grouping</CardTitle>
            <p className={`text-sm mt-1 transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Drag tags, select & combine tickers, or click to rename
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Tag Creator */}
        <TagCreator onCreate={onCreate} />

        {/* Tags List */}
        {tags.length === 0 ? (
          <div className={`text-center py-8 transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
          }`}>
            No tags yet. Create one to categorize your strategies.
          </div>
        ) : (
          <div className="space-y-2">
            <h3 className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
            }`}>Your Tags</h3>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className={`flex items-center gap-2 rounded-lg p-2 pr-3 border transition-colors ${
                    theme === 'dark'
                      ? 'bg-slate-700 border-slate-600'
                      : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <TagBadge tag={tag} draggable={true} />

                  {tag.usage_count !== undefined && (
                    <span className={`text-xs transition-colors duration-300 ${
                      theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                    }`}>
                      ({tag.usage_count})
                    </span>
                  )}

                  <button
                    onClick={() => handleDelete(tag.id)}
                    className={`transition-colors ${
                      theme === 'dark'
                        ? 'text-slate-400 hover:text-red-400'
                        : 'text-gray-400 hover:text-red-600'
                    }`}
                    title="Archive tag"
                  >
                    <Trash className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
