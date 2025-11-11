'use client'

import React, { useState, useEffect } from 'react'
import positionManagementService, { Position, PositionType, InvestmentClass } from '@/services/positionManagementService'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'

interface PositionManagementTableProps {
  portfolioId: string
  positions: Position[]
  onPositionUpdated?: () => void
  onPositionDeleted?: () => void
  onPositionSelected?: (position: Position) => void
}

type SortColumn = 'symbol' | 'quantity' | 'entry_price' | 'current_price' | 'market_value' | 'unrealized_pnl' | 'unrealized_pnl_percent'
type SortDirection = 'asc' | 'desc'

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '$0.00'
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(2)}`
}

function formatPercentage(value: number | undefined): string {
  if (value === undefined || value === null) return '0.0%'
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

function getPositionTypeBadgeColor(type: PositionType): string {
  switch (type) {
    case 'LONG':
      return 'bg-green-500/10 text-green-500 border-green-500/20'
    case 'SHORT':
      return 'bg-red-500/10 text-red-500 border-red-500/20'
    case 'LC':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    case 'LP':
      return 'bg-blue-400/10 text-blue-400 border-blue-400/20'
    case 'SC':
      return 'bg-orange-500/10 text-orange-500 border-orange-500/20'
    case 'SP':
      return 'bg-orange-400/10 text-orange-400 border-orange-400/20'
    default:
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20'
  }
}

function getInvestmentClassBadgeColor(investmentClass: InvestmentClass): string {
  switch (investmentClass) {
    case 'PUBLIC':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    case 'OPTIONS':
      return 'bg-purple-500/10 text-purple-500 border-purple-500/20'
    case 'PRIVATE':
      return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    default:
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20'
  }
}

export function PositionManagementTable({
  portfolioId,
  positions,
  onPositionUpdated,
  onPositionDeleted,
  onPositionSelected
}: PositionManagementTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('symbol')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [selectedPositions, setSelectedPositions] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [positionToDelete, setPositionToDelete] = useState<Position | null>(null)
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getSortedPositions = () => {
    const sorted = [...positions].sort((a, b) => {
      let aValue: number | string = 0
      let bValue: number | string = 0

      switch (sortColumn) {
        case 'symbol':
          aValue = a.symbol
          bValue = b.symbol
          break
        case 'quantity':
          aValue = a.quantity
          bValue = b.quantity
          break
        case 'entry_price':
          aValue = a.entry_price
          bValue = b.entry_price
          break
        case 'current_price':
          aValue = a.current_price || 0
          bValue = b.current_price || 0
          break
        case 'market_value':
          aValue = a.market_value || 0
          bValue = b.market_value || 0
          break
        case 'unrealized_pnl':
          aValue = a.unrealized_pnl || 0
          bValue = b.unrealized_pnl || 0
          break
        case 'unrealized_pnl_percent':
          aValue = a.unrealized_pnl_percent || 0
          bValue = b.unrealized_pnl_percent || 0
          break
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue)
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number)
    })

    return sorted
  }

  const handleSelectPosition = (positionId: string) => {
    setSelectedPositions((prev) => {
      const next = new Set(prev)
      if (next.has(positionId)) {
        next.delete(positionId)
      } else {
        next.add(positionId)
      }
      return next
    })
  }

  const handleSelectAll = () => {
    if (selectedPositions.size === positions.length) {
      setSelectedPositions(new Set())
    } else {
      setSelectedPositions(new Set(positions.map(p => p.id)))
    }
  }

  const handleDeleteClick = (position: Position) => {
    setPositionToDelete(position)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!positionToDelete) return

    setIsDeleting(true)
    try {
      // Check if position is < 5 minutes old - try hard delete first
      const createdAt = new Date(positionToDelete.created_at)
      const now = new Date()
      const ageMinutes = (now.getTime() - createdAt.getTime()) / (1000 * 60)

      if (ageMinutes < 5) {
        try {
          await positionManagementService.hardDeletePosition(positionToDelete.id)
          console.log(`✅ Hard deleted position ${positionToDelete.symbol}`)
        } catch (error) {
          // If hard delete fails, fall back to soft delete
          console.log(`ℹ️ Hard delete failed, falling back to soft delete`)
          await positionManagementService.softDeletePosition(positionToDelete.id)
        }
      } else {
        // Position is old, use soft delete
        await positionManagementService.softDeletePosition(positionToDelete.id)
      }

      onPositionDeleted?.()
      setDeleteDialogOpen(false)
      setPositionToDelete(null)
    } catch (error) {
      console.error('Failed to delete position:', error)
      alert('Failed to delete position. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleBulkDeleteClick = () => {
    if (selectedPositions.size === 0) return
    setBulkDeleteDialogOpen(true)
  }

  const handleBulkDeleteConfirm = async () => {
    if (selectedPositions.size === 0) return

    setIsDeleting(true)
    try {
      await positionManagementService.bulkDeletePositions(Array.from(selectedPositions))
      setSelectedPositions(new Set())
      onPositionDeleted?.()
      setBulkDeleteDialogOpen(false)
    } catch (error) {
      console.error('Failed to bulk delete positions:', error)
      alert('Failed to delete positions. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  const SortableHeader = ({ column, children, align = 'left' }: { column: SortColumn; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`px-3 py-2 text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-opacity-80 transition-colors ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
      style={{
        color: 'var(--color-secondary)',
        borderBottom: '1px solid var(--border-primary)'
      }}
      onClick={() => handleSort(column)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : 'justify-start'}`}>
        <span>{children}</span>
        {sortColumn === column && (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {sortDirection === 'asc' ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            )}
          </svg>
        )}
      </div>
    </th>
  )

  const sortedPositions = getSortedPositions()

  if (positions.length === 0) {
    return (
      <div className="themed-card p-8 text-center">
        <p className="text-secondary">No positions found</p>
      </div>
    )
  }

  return (
    <>
      <div className="themed-card overflow-hidden">
        {/* Bulk Actions Bar */}
        {selectedPositions.size > 0 && (
          <div className="px-4 py-2 flex items-center justify-between" style={{ backgroundColor: 'var(--background-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
            <span className="text-sm text-secondary">
              {selectedPositions.size} position{selectedPositions.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedPositions(new Set())}
              >
                Clear Selection
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleBulkDeleteClick}
                disabled={isDeleting}
              >
                Delete Selected
              </Button>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead style={{ backgroundColor: 'var(--background-secondary)' }}>
              <tr>
                <th className="px-3 py-2 text-left" style={{ borderBottom: '1px solid var(--border-primary)' }}>
                  <input
                    type="checkbox"
                    checked={selectedPositions.size === positions.length && positions.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <SortableHeader column="symbol">Symbol</SortableHeader>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-left" style={{ color: 'var(--color-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
                  Type
                </th>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-left" style={{ color: 'var(--color-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
                  Class
                </th>
                <SortableHeader column="quantity" align="right">Quantity</SortableHeader>
                <SortableHeader column="entry_price" align="right">Entry Price</SortableHeader>
                <SortableHeader column="current_price" align="right">Current Price</SortableHeader>
                <SortableHeader column="market_value" align="right">Market Value</SortableHeader>
                <SortableHeader column="unrealized_pnl" align="right">P&L</SortableHeader>
                <SortableHeader column="unrealized_pnl_percent" align="right">P&L %</SortableHeader>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-right" style={{ color: 'var(--color-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedPositions.map((position, index) => (
                <tr
                  key={position.id}
                  className="hover:bg-opacity-50 transition-colors cursor-pointer"
                  style={{
                    backgroundColor: index % 2 === 0 ? 'transparent' : 'var(--background-secondary)',
                    borderBottom: '1px solid var(--border-secondary)'
                  }}
                  onClick={() => onPositionSelected?.(position)}
                >
                  <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedPositions.has(position.id)}
                      onChange={() => handleSelectPosition(position.id)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-col">
                      <span className="font-semibold" style={{ color: 'var(--color-primary)' }}>{position.symbol}</span>
                      {position.notes && (
                        <span className="text-xs text-secondary truncate max-w-[200px]" title={position.notes}>
                          {position.notes}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <Badge variant="outline" className={getPositionTypeBadgeColor(position.position_type)}>
                      {position.position_type}
                    </Badge>
                  </td>
                  <td className="px-3 py-3">
                    <Badge variant="outline" className={getInvestmentClassBadgeColor(position.investment_class)}>
                      {position.investment_class}
                    </Badge>
                  </td>
                  <td className="px-3 py-3 text-right text-primary">{position.quantity.toLocaleString()}</td>
                  <td className="px-3 py-3 text-right text-secondary">{formatCurrency(position.entry_price)}</td>
                  <td className="px-3 py-3 text-right text-secondary">{formatCurrency(position.current_price)}</td>
                  <td className="px-3 py-3 text-right font-semibold text-primary">{formatCurrency(position.market_value)}</td>
                  <td className="px-3 py-3 text-right font-semibold" style={{ color: (position.unrealized_pnl || 0) >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                    {formatCurrency(position.unrealized_pnl)}
                  </td>
                  <td className="px-3 py-3 text-right font-semibold" style={{ color: (position.unrealized_pnl_percent || 0) >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                    {formatPercentage(position.unrealized_pnl_percent)}
                  </td>
                  <td className="px-3 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation()
                          onPositionSelected?.(position)
                        }}
                        className="h-7 px-2"
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteClick(position)
                        }}
                        className="h-7 px-2 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                        disabled={isDeleting}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Position</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the position <strong>{positionToDelete?.symbol}</strong>?
              {positionToDelete && (
                <div className="mt-2 text-sm">
                  <div>Quantity: {positionToDelete.quantity}</div>
                  <div>Market Value: {formatCurrency(positionToDelete.market_value)}</div>
                </div>
              )}
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} disabled={isDeleting} className="bg-red-500 hover:bg-red-600">
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Bulk Delete Confirmation Dialog */}
      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Multiple Positions</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {selectedPositions.size} position{selectedPositions.size !== 1 ? 's' : ''}?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDeleteConfirm} disabled={isDeleting} className="bg-red-500 hover:bg-red-600">
              {isDeleting ? 'Deleting...' : `Delete ${selectedPositions.size} Position${selectedPositions.size !== 1 ? 's' : ''}`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
