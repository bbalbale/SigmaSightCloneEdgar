'use client'

import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { TagBadge } from '@/components/organize/TagBadge'
import { TagCreator } from '@/components/organize/TagCreator'
import { Button } from '@/components/ui/button'
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

export interface Tag {
  id: string
  name: string
  color: string
}

interface ViewAllTagsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  tags: Tag[]
  onCreate: (name: string, color: string) => Promise<void>
  onDelete: (tagId: string) => Promise<void>
}

export function ViewAllTagsModal({
  open,
  onOpenChange,
  tags,
  onCreate,
  onDelete
}: ViewAllTagsModalProps) {
  const [showCreator, setShowCreator] = useState(false)
  const [deleteTagId, setDeleteTagId] = useState<string | null>(null)

  const handleCreate = async (name: string, color: string) => {
    await onCreate(name, color)
    setShowCreator(false)
  }

  const handleDeleteConfirm = async () => {
    if (deleteTagId) {
      await onDelete(deleteTagId)
      setDeleteTagId(null)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>All Tags</DialogTitle>
            <DialogDescription>
              Drag tags to apply them to positions. Click the trash icon to delete a tag.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {/* Tag Creator */}
            {showCreator ? (
              <div className="mb-4">
                <TagCreator
                  onCreate={handleCreate}
                  onCancel={() => setShowCreator(false)}
                />
              </div>
            ) : (
              <Button
                onClick={() => setShowCreator(true)}
                variant="outline"
                className="mb-4 w-full"
              >
                + Create New Tag
              </Button>
            )}

            {/* Tags Grid */}
            {tags.length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {tags.map(tag => (
                  <div
                    key={tag.id}
                    className="flex items-center justify-between p-3 rounded-lg transition-colors duration-300"
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-primary)'
                    }}
                  >
                    <TagBadge
                      tag={tag}
                      draggable={true}
                      size="md"
                    />
                    <button
                      onClick={() => setDeleteTagId(tag.id)}
                      className="ml-2 p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
                      title={`Delete ${tag.name}`}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ color: 'var(--color-error)' }}
                      >
                        <path d="M3 6h18" />
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No tags created yet. Create your first tag above.
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteTagId !== null} onOpenChange={(open) => !open && setDeleteTagId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Tag</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this tag? This will remove it from all positions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
