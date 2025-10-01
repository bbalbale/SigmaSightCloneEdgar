'use client'

import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'
import { TagCreator } from './TagCreator'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Trash } from 'lucide-react'

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
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold">Portfolio Tagging & Grouping</CardTitle>
            <p className="text-sm text-gray-600 mt-1">
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
          <div className="text-center py-8 text-gray-500">
            No tags yet. Create one to categorize your strategies.
          </div>
        ) : (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-700">Your Tags</h3>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="flex items-center gap-2 bg-gray-50 rounded-lg p-2 pr-3 border border-gray-200"
                >
                  <TagBadge tag={tag} draggable={true} />

                  {tag.usage_count !== undefined && (
                    <span className="text-xs text-gray-500">
                      ({tag.usage_count})
                    </span>
                  )}

                  <button
                    onClick={() => handleDelete(tag.id)}
                    className="text-gray-400 hover:text-red-600 transition-colors"
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
