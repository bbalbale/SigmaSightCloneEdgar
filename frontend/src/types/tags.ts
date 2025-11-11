/**
 * Shared tag types for UI components.
 * Keeps tag shape consistent between stores, services, and components.
 */
export interface PositionTag {
  id: string
  name: string
  color: string
  description?: string | null
}

export type TagSize = 'sm' | 'md'
