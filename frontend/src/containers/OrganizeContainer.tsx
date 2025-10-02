'use client'

import { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { usePositions } from '@/hooks/usePositions'
import { useStrategies } from '@/hooks/useStrategies'
import { useTags } from '@/hooks/useTags'
import { usePositionSelection } from '@/hooks/usePositionSelection'
import { PositionSelectionGrid } from '@/components/organize/PositionSelectionGrid'
import { CombinePositionsButton } from '@/components/organize/CombinePositionsButton'
import { CombineModal } from '@/components/organize/CombineModal'
import { TagList } from '@/components/organize/TagList'
import strategiesApi from '@/services/strategiesApi'
import tagsApi from '@/services/tagsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'

export function OrganizeContainer() {
  const { theme } = useTheme()
  const portfolioId = usePortfolioStore(state => state.portfolioId)

  // Data hooks
  const { positions, loading: positionsLoading } = usePositions()
  const { strategies, loading: strategiesLoading, refresh: refreshStrategies } = useStrategies({
    includePositions: true,
    includeTags: true
  })
  const { tags, loading: tagsLoading, refresh: refreshTags } = useTags()

  // Selection state
  const {
    selectedIds,
    selectedCount,
    isSelected,
    toggleSelection,
    clearSelection
  } = usePositionSelection()

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  // State for drag-drop combination
  const [dragDropPositions, setDragDropPositions] = useState<string[]>([])

  // Loading state
  const isLoading = positionsLoading || strategiesLoading || tagsLoading

  // Get position IDs to combine (either from selection or drag-drop)
  const positionsToCombine = dragDropPositions.length > 0 ? dragDropPositions : selectedIds

  // Handlers
  const handleCombineClick = () => {
    if (selectedCount < 2) {
      alert('Please select at least 2 positions to combine')
      return
    }
    setDragDropPositions([]) // Clear any drag-drop state
    setIsModalOpen(true)
  }

  const handleDropPosition = (droppedStrategyId: string, targetStrategyId: string) => {
    // Find the strategies by ID
    const droppedStrategy = strategies.find(s => s.id === droppedStrategyId)
    const targetStrategy = strategies.find(s => s.id === targetStrategyId)

    // Extract position IDs from the strategies
    const positionIds: string[] = []

    if (droppedStrategy?.positions) {
      positionIds.push(...droppedStrategy.positions.map((p: any) => p.id))
    }
    if (targetStrategy?.positions) {
      positionIds.push(...targetStrategy.positions.map((p: any) => p.id))
    }

    // Set the position IDs to combine
    setDragDropPositions(positionIds)
    // Open the modal
    setIsModalOpen(true)
  }

  const handleCombineConfirm = async (data: { name: string; type: string; description: string }) => {
    if (!portfolioId) {
      throw new Error('Portfolio ID not available')
    }

    try {
      await strategiesApi.combine({
        portfolio_id: portfolioId,
        position_ids: positionsToCombine,
        strategy_name: data.name,  // Backend expects strategy_name not name
        strategy_type: 'custom'  // User-created combinations are custom strategies
      })

      // Refresh data
      await refreshStrategies()
      clearSelection()
      setDragDropPositions([])
      setIsModalOpen(false)

      alert('Combination created successfully!')
    } catch (error) {
      console.error('Failed to create combination:', error)
      throw error
    }
  }

  const handleModalClose = () => {
    setIsModalOpen(false)
    setDragDropPositions([]) // Clear drag-drop state on cancel
  }

  const handleEditStrategy = (strategy: any) => {
    // TODO: Implement edit modal
    console.log('Edit strategy:', strategy)
    alert('Edit functionality coming soon')
  }

  const handleDeleteStrategy = async (strategyId: string) => {
    if (!confirm('Delete this combination? Positions will remain individual.')) {
      return
    }

    try {
      await strategiesApi.delete(strategyId)
      await refreshStrategies()
      alert('Combination deleted successfully')
    } catch (error) {
      console.error('Failed to delete combination:', error)
      alert('Failed to delete combination')
    }
  }

  const handleCreateTag = async (name: string, color: string) => {
    try {
      await tagsApi.create(name, color)
      await refreshTags()
    } catch (error) {
      console.error('Failed to create tag:', error)
      throw error
    }
  }

  const handleDeleteTag = async (tagId: string) => {
    try {
      // Archive tag (soft delete)
      await tagsApi.delete(tagId)
      await refreshTags()
    } catch (error) {
      console.error('Failed to delete tag:', error)
      throw error
    }
  }

  const handleDropTag = async (targetId: string, tagId: string) => {
    try {
      // Check if target is a position or strategy
      const position = positions.find(p => p.id === targetId)

      if (position) {
        // Target is a position - use its strategy_id for tagging
        if (!position.strategy_id) {
          alert('Position does not have an associated strategy. Please create a strategy first.')
          return
        }
        await strategiesApi.addStrategyTags(position.strategy_id, [tagId])
      } else {
        // Target is a strategy - use the strategy id directly
        await strategiesApi.addStrategyTags(targetId, [tagId])
      }

      await refreshStrategies()
    } catch (error) {
      console.error('Failed to apply tag:', error)
      alert('Failed to apply tag')
    }
  }

  if (isLoading) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              Loading portfolio organization...
            </p>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      <section className="px-4 py-8">
        <div className="container mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className={`text-3xl font-bold mb-2 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>Portfolio Organization</h1>
            <p className={`${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Group positions into strategies and organize with tags
            </p>
          </div>

      {/* Tag Management Section */}
      <TagList
        tags={tags}
        onCreate={handleCreateTag}
        onDelete={handleDeleteTag}
      />

      {/* Four-Quadrant Position Grid */}
      <PositionSelectionGrid
        positions={positions}
        strategies={strategies}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={toggleSelection}
        onDropTag={handleDropTag}
        onDropPosition={handleDropPosition}
        onEditStrategy={handleEditStrategy}
        onDeleteStrategy={handleDeleteStrategy}
      />

      {/* Combine Button (appears when 2+ selected) */}
      <CombinePositionsButton
        selectedCount={selectedCount}
        onClick={handleCombineClick}
        onClear={clearSelection}
      />

      {/* Combine Modal */}
      <CombineModal
        open={isModalOpen}
        onClose={handleModalClose}
        onConfirm={handleCombineConfirm}
        selectedCount={positionsToCombine.length}
      />
        </div>
      </section>
    </div>
  )
}
