'use client'

import React, { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { PositionManagementTable } from '@/components/positions/PositionManagementTable'
import { PositionDetailSheet } from '@/components/positions/PositionDetailSheet'
import { CreatePositionDialog } from '@/components/positions/CreatePositionDialog'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { apiClient } from '@/services/apiClient'
import type { Position } from '@/services/positionManagementService'

interface PositionManagementContainerProps {
  className?: string
}

export function PositionManagementContainer({ className }: PositionManagementContainerProps) {
  const { portfolioId } = usePortfolioStore()
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [detailSheetOpen, setDetailSheetOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Fetch positions from backend
  useEffect(() => {
    if (!portfolioId) {
      setError('No portfolio selected')
      setLoading(false)
      return
    }

    const fetchPositions = async () => {
      setLoading(true)
      setError(null)

      try {
        // Fetch positions using the existing /api/v1/data/positions/details endpoint
        const response = await apiClient.get<{ positions: any[] }>(
          `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
        )

        // Transform the response to match our Position interface
        const transformedPositions: Position[] = response.positions.map((p: any) => ({
          id: p.id || p.position_id,
          portfolio_id: p.portfolio_id,
          symbol: p.symbol,
          position_type: p.position_type,
          investment_class: p.investment_class,
          quantity: p.quantity,
          avg_cost: p.avg_cost || p.cost_basis / p.quantity,
          entry_price: p.entry_price || p.avg_cost || p.cost_basis / p.quantity,
          entry_date: p.entry_date,
          exit_date: p.exit_date,
          exit_price: p.exit_price,
          current_price: p.current_price,
          market_value: p.market_value || p.marketValue,
          unrealized_pnl: p.unrealized_pnl || p.pnl,
          unrealized_pnl_percent: p.unrealized_pnl_percent || (p.pnl / (p.cost_basis || 1)) * 100,
          notes: p.notes,
          deleted_at: p.deleted_at,
          created_at: p.created_at,
          updated_at: p.updated_at
        }))

        // Filter out deleted positions
        const activePositions = transformedPositions.filter(p => !p.deleted_at)

        setPositions(activePositions)
      } catch (err: any) {
        console.error('Failed to fetch positions:', err)
        setError(err.message || 'Failed to load positions')
      } finally {
        setLoading(false)
      }
    }

    fetchPositions()
  }, [portfolioId, refreshTrigger])

  const handlePositionSelected = (position: Position) => {
    setSelectedPosition(position)
    setDetailSheetOpen(true)
  }

  const handlePositionUpdated = () => {
    // Trigger refresh
    setRefreshTrigger(prev => prev + 1)
  }

  const handlePositionDeleted = () => {
    // Close detail sheet if open
    setDetailSheetOpen(false)
    setSelectedPosition(null)
    // Trigger refresh
    setRefreshTrigger(prev => prev + 1)
  }

  const handlePositionCreated = () => {
    // Trigger refresh
    setRefreshTrigger(prev => prev + 1)
  }

  const handleCreateClick = () => {
    setCreateDialogOpen(true)
  }

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1)
  }

  if (!portfolioId) {
    return (
      <div className={className}>
        <Alert>
          <AlertDescription>
            Please select a portfolio to manage positions.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={className}>
        <div className="themed-card p-8">
          <div className="flex flex-col items-center justify-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="text-secondary">Loading positions...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={className}>
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="mt-4">
          <Button onClick={handleRefresh}>Retry</Button>
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      {/* Header Section */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary">Position Management</h1>
            <p className="text-sm text-secondary mt-1">
              {positions.length} position{positions.length !== 1 ? 's' : ''} in your portfolio
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleRefresh} size="sm">
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </Button>
            <Button onClick={handleCreateClick} size="sm">
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Create Position
            </Button>
          </div>
        </div>
      </div>

      {/* Position Management Table */}
      <PositionManagementTable
        portfolioId={portfolioId}
        positions={positions}
        onPositionUpdated={handlePositionUpdated}
        onPositionDeleted={handlePositionDeleted}
        onPositionSelected={handlePositionSelected}
      />

      {/* Position Detail Sheet */}
      <PositionDetailSheet
        position={selectedPosition}
        open={detailSheetOpen}
        onOpenChange={setDetailSheetOpen}
        onPositionUpdated={handlePositionUpdated}
      />

      {/* Create Position Dialog */}
      <CreatePositionDialog
        portfolioId={portfolioId}
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onPositionCreated={handlePositionCreated}
      />
    </div>
  )
}
