'use client'

import React, { useState, useEffect } from 'react'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import positionManagementService, { Position, PositionType, InvestmentClass } from '@/services/positionManagementService'
import { Separator } from '@/components/ui/separator'

interface PositionDetailSheetProps {
  position: Position | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onPositionUpdated?: () => void
}

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '$0.00'
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPercentage(value: number | undefined): string {
  if (value === undefined || value === null) return '0.0%'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function PositionDetailSheet({
  position,
  open,
  onOpenChange,
  onPositionUpdated
}: PositionDetailSheetProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [formData, setFormData] = useState({
    quantity: '',
    avg_cost: '',
    position_type: '' as PositionType,
    investment_class: '' as InvestmentClass,
    notes: '',
    entry_date: '',
    exit_date: '',
    exit_price: ''
  })

  // Initialize form data when position changes
  useEffect(() => {
    if (position) {
      setFormData({
        quantity: position.quantity.toString(),
        avg_cost: position.avg_cost.toString(),
        position_type: position.position_type,
        investment_class: position.investment_class,
        notes: position.notes || '',
        entry_date: position.entry_date || '',
        exit_date: position.exit_date || '',
        exit_price: position.exit_price?.toString() || ''
      })
      setIsEditing(false)
    }
  }, [position])

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    if (!position) return

    setIsSaving(true)
    try {
      const updateData: any = {}

      // Only include changed fields
      if (formData.quantity !== position.quantity.toString()) {
        updateData.quantity = parseFloat(formData.quantity)
      }
      if (formData.avg_cost !== position.avg_cost.toString()) {
        updateData.avg_cost = parseFloat(formData.avg_cost)
      }
      if (formData.position_type !== position.position_type) {
        updateData.position_type = formData.position_type
      }
      if (formData.investment_class !== position.investment_class) {
        updateData.investment_class = formData.investment_class
      }
      if (formData.notes !== (position.notes || '')) {
        updateData.notes = formData.notes
      }
      if (formData.entry_date !== (position.entry_date || '')) {
        updateData.entry_date = formData.entry_date
      }
      if (formData.exit_date !== (position.exit_date || '')) {
        updateData.exit_date = formData.exit_date || undefined
      }
      if (formData.exit_price !== (position.exit_price?.toString() || '')) {
        updateData.exit_price = formData.exit_price ? parseFloat(formData.exit_price) : undefined
      }

      if (Object.keys(updateData).length > 0) {
        await positionManagementService.updatePosition(position.id, updateData)
        onPositionUpdated?.()
        setIsEditing(false)
      } else {
        // No changes
        setIsEditing(false)
      }
    } catch (error) {
      console.error('Failed to update position:', error)
      alert('Failed to update position. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    // Reset form to original values
    if (position) {
      setFormData({
        quantity: position.quantity.toString(),
        avg_cost: position.avg_cost.toString(),
        position_type: position.position_type,
        investment_class: position.investment_class,
        notes: position.notes || '',
        entry_date: position.entry_date || '',
        exit_date: position.exit_date || '',
        exit_price: position.exit_price?.toString() || ''
      })
    }
    setIsEditing(false)
  }

  if (!position) {
    return null
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-2xl flex items-center gap-3">
            <span>{position.symbol}</span>
            <Badge variant="outline" className={
              position.position_type === 'LONG' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
              position.position_type === 'SHORT' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
              'bg-blue-500/10 text-blue-500 border-blue-500/20'
            }>
              {position.position_type}
            </Badge>
            <Badge variant="outline" className={
              position.investment_class === 'PUBLIC' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20' :
              position.investment_class === 'OPTIONS' ? 'bg-purple-500/10 text-purple-500 border-purple-500/20' :
              'bg-amber-500/10 text-amber-500 border-amber-500/20'
            }>
              {position.investment_class}
            </Badge>
          </SheetTitle>
          <SheetDescription>
            Position ID: {position.id}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Performance Summary */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-secondary">Market Value</p>
                <p className="text-lg font-semibold text-primary">{formatCurrency(position.market_value)}</p>
              </div>
              <div>
                <p className="text-xs text-secondary">Unrealized P&L</p>
                <p className={`text-lg font-semibold ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatCurrency(position.unrealized_pnl)} ({formatPercentage(position.unrealized_pnl_percent)})
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Editable Fields */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Position Details</h3>
              {!isEditing ? (
                <Button size="sm" variant="outline" onClick={() => setIsEditing(true)}>
                  Edit
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleCancel} disabled={isSaving}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={isSaving}>
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              )}
            </div>

            <div className="space-y-4">
              {/* Quantity */}
              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity</Label>
                {isEditing ? (
                  <Input
                    id="quantity"
                    type="number"
                    value={formData.quantity}
                    onChange={(e) => handleInputChange('quantity', e.target.value)}
                    step="0.0001"
                  />
                ) : (
                  <p className="text-sm text-primary">{position.quantity.toLocaleString()}</p>
                )}
              </div>

              {/* Average Cost */}
              <div className="space-y-2">
                <Label htmlFor="avg_cost">Average Cost</Label>
                {isEditing ? (
                  <Input
                    id="avg_cost"
                    type="number"
                    value={formData.avg_cost}
                    onChange={(e) => handleInputChange('avg_cost', e.target.value)}
                    step="0.01"
                  />
                ) : (
                  <p className="text-sm text-primary">{formatCurrency(position.avg_cost)}</p>
                )}
              </div>

              {/* Position Type */}
              <div className="space-y-2">
                <Label htmlFor="position_type">Position Type</Label>
                {isEditing ? (
                  <Select
                    value={formData.position_type}
                    onValueChange={(value) => handleInputChange('position_type', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="LONG">LONG</SelectItem>
                      <SelectItem value="SHORT">SHORT</SelectItem>
                      <SelectItem value="LC">Long Call (LC)</SelectItem>
                      <SelectItem value="LP">Long Put (LP)</SelectItem>
                      <SelectItem value="SC">Short Call (SC)</SelectItem>
                      <SelectItem value="SP">Short Put (SP)</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm text-primary">{position.position_type}</p>
                )}
              </div>

              {/* Investment Class */}
              <div className="space-y-2">
                <Label htmlFor="investment_class">Investment Class</Label>
                {isEditing ? (
                  <Select
                    value={formData.investment_class}
                    onValueChange={(value) => handleInputChange('investment_class', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select class" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PUBLIC">PUBLIC</SelectItem>
                      <SelectItem value="OPTIONS">OPTIONS</SelectItem>
                      <SelectItem value="PRIVATE">PRIVATE</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm text-primary">{position.investment_class}</p>
                )}
              </div>

              {/* Entry Date */}
              <div className="space-y-2">
                <Label htmlFor="entry_date">Entry Date</Label>
                {isEditing ? (
                  <Input
                    id="entry_date"
                    type="date"
                    value={formData.entry_date}
                    onChange={(e) => handleInputChange('entry_date', e.target.value)}
                  />
                ) : (
                  <p className="text-sm text-primary">{formatDate(position.entry_date)}</p>
                )}
              </div>

              {/* Exit Date (optional) */}
              <div className="space-y-2">
                <Label htmlFor="exit_date">Exit Date (Optional)</Label>
                {isEditing ? (
                  <Input
                    id="exit_date"
                    type="date"
                    value={formData.exit_date}
                    onChange={(e) => handleInputChange('exit_date', e.target.value)}
                  />
                ) : (
                  <p className="text-sm text-primary">{position.exit_date ? formatDate(position.exit_date) : 'N/A'}</p>
                )}
              </div>

              {/* Exit Price (optional) */}
              <div className="space-y-2">
                <Label htmlFor="exit_price">Exit Price (Optional)</Label>
                {isEditing ? (
                  <Input
                    id="exit_price"
                    type="number"
                    value={formData.exit_price}
                    onChange={(e) => handleInputChange('exit_price', e.target.value)}
                    step="0.01"
                    placeholder="0.00"
                  />
                ) : (
                  <p className="text-sm text-primary">{position.exit_price ? formatCurrency(position.exit_price) : 'N/A'}</p>
                )}
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                {isEditing ? (
                  <Textarea
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => handleInputChange('notes', e.target.value)}
                    rows={4}
                    placeholder="Add notes about this position..."
                  />
                ) : (
                  <p className="text-sm text-primary whitespace-pre-wrap">{position.notes || 'No notes'}</p>
                )}
              </div>
            </div>
          </div>

          <Separator />

          {/* Read-only Metadata */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Metadata</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-secondary">Entry Price</p>
                <p className="text-primary">{formatCurrency(position.entry_price)}</p>
              </div>
              <div>
                <p className="text-xs text-secondary">Current Price</p>
                <p className="text-primary">{formatCurrency(position.current_price)}</p>
              </div>
              <div>
                <p className="text-xs text-secondary">Created At</p>
                <p className="text-primary">{formatDate(position.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-secondary">Last Updated</p>
                <p className="text-primary">{formatDate(position.updated_at)}</p>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
