'use client'

import { useState } from 'react'
import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'
import { TagCreator } from './TagCreator'
import { Card, CardContent } from '@/components/ui/card'
import { Trash } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

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
  const [tagToDelete, setTagToDelete] = useState<TagItem | null>(null)

  const confirmDelete = async () => {
    if (!tagToDelete) return

    try {
      await onDelete(tagToDelete.id)
      setTagToDelete(null)
    } catch (error) {
      console.error('Failed to delete tag:', error)
      // Could add toast notification here
    }
  }

  return (
    <div className="space-y-4">
      {/* Tag Creator - Thin Box */}
      <Card className={`transition-colors ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardContent className="pt-6">
          <TagCreator onCreate={onCreate} />
        </CardContent>
      </Card>

      {/* Tags List - Wider Box */}
      <Card className={`transition-colors ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardContent className="pt-6">
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
                      onClick={() => setTagToDelete(tag)}
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

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!tagToDelete} onOpenChange={(open) => !open && setTagToDelete(null)}>
        <AlertDialogContent className={theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'}>
          <AlertDialogHeader>
            <AlertDialogTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
              Archive Tag
            </AlertDialogTitle>
            <AlertDialogDescription className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Are you sure you want to archive "{tagToDelete?.name}"? This will remove it from all positions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className={theme === 'dark' ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : ''}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
