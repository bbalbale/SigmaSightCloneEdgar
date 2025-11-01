'use client'

import { useState } from 'react'
import type { TagItem } from '@/types/strategies'
import { TagBadge } from './TagBadge'
import { TagCreator } from './TagCreator'
import { Card, CardContent } from '@/components/ui/card'
import { Trash } from 'lucide-react'
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
      <Card className="transition-colors themed-card">
        <CardContent className="pt-6">
          <TagCreator onCreate={onCreate} />
        </CardContent>
      </Card>

      {/* Tags List - Wider Box */}
      <Card className="transition-colors themed-card">
        <CardContent className="pt-6">
          {tags.length === 0 ? (
            <div className="text-center py-8 transition-colors duration-300 text-secondary">
              No tags yet. Create one to categorize your strategies.
            </div>
          ) : (
            <div className="space-y-2">
              <h3 className="text-sm font-medium transition-colors duration-300 text-primary">Your Tags</h3>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <div
                    key={tag.id}
                    className="flex items-center gap-2 rounded-lg p-2 pr-3 transition-colors duration-300"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-primary)'
                    }}
                  >
                    <TagBadge tag={tag} draggable={true} />

                    <button
                      onClick={() => setTagToDelete(tag)}
                      className="transition-colors duration-300"
                      style={{
                        color: 'var(--text-secondary)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = 'var(--color-error)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = 'var(--text-secondary)'
                      }}
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
        <AlertDialogContent className="themed-card">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ color: 'var(--text-primary)' }}>
              Archive Tag
            </AlertDialogTitle>
            <AlertDialogDescription className="text-secondary">
              Are you sure you want to archive "{tagToDelete?.name}"? This will remove it from all positions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)'
            }}>
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
