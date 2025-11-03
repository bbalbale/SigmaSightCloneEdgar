'use client'

import React, { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import positionManagementService, { PositionType, InvestmentClass } from '@/services/positionManagementService'

interface CreatePositionDialogProps {
  portfolioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onPositionCreated?: () => void
}

interface FormData {
  symbol: string
  quantity: string
  avg_cost: string
  position_type: PositionType | ''
  investment_class: InvestmentClass | ''
  entry_date: string
  notes: string
}

interface FormErrors {
  symbol?: string
  quantity?: string
  avg_cost?: string
  position_type?: string
  investment_class?: string
  entry_date?: string
  general?: string
}

export function CreatePositionDialog({
  portfolioId,
  open,
  onOpenChange,
  onPositionCreated
}: CreatePositionDialogProps) {
  const [formData, setFormData] = useState<FormData>({
    symbol: '',
    quantity: '',
    avg_cost: '',
    position_type: '',
    investment_class: '',
    entry_date: new Date().toISOString().split('T')[0], // Today's date
    notes: ''
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isValidatingSymbol, setIsValidatingSymbol] = useState(false)
  const [symbolValidation, setSymbolValidation] = useState<{ valid: boolean; message: string } | null>(null)

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
    // Clear general error
    if (errors.general) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors.general
        return newErrors
      })
    }
  }

  const handleSymbolBlur = async () => {
    if (!formData.symbol) return

    setIsValidatingSymbol(true)
    setSymbolValidation(null)

    try {
      const result = await positionManagementService.validateSymbol(formData.symbol)
      setSymbolValidation({ valid: result.is_valid, message: result.message })

      if (!result.is_valid) {
        setErrors((prev) => ({ ...prev, symbol: result.message }))
      }
    } catch (error) {
      console.error('Symbol validation error:', error)
    } finally {
      setIsValidatingSymbol(false)
    }
  }

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    // Symbol validation
    if (!formData.symbol.trim()) {
      newErrors.symbol = 'Symbol is required'
    } else if (symbolValidation && !symbolValidation.valid) {
      newErrors.symbol = symbolValidation.message
    }

    // Quantity validation
    if (!formData.quantity) {
      newErrors.quantity = 'Quantity is required'
    } else if (parseFloat(formData.quantity) <= 0) {
      newErrors.quantity = 'Quantity must be greater than 0'
    }

    // Average cost validation
    if (!formData.avg_cost) {
      newErrors.avg_cost = 'Average cost is required'
    } else if (parseFloat(formData.avg_cost) <= 0) {
      newErrors.avg_cost = 'Average cost must be greater than 0'
    }

    // Position type validation
    if (!formData.position_type) {
      newErrors.position_type = 'Position type is required'
    }

    // Investment class validation
    if (!formData.investment_class) {
      newErrors.investment_class = 'Investment class is required'
    }

    // Entry date validation
    if (!formData.entry_date) {
      newErrors.entry_date = 'Entry date is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    try {
      // Create position with duplicate check
      await positionManagementService.createPositionWithDuplicateCheck(
        {
          portfolio_id: portfolioId,
          symbol: formData.symbol.trim().toUpperCase(),
          quantity: parseFloat(formData.quantity),
          avg_cost: parseFloat(formData.avg_cost),
          position_type: formData.position_type as PositionType,
          investment_class: formData.investment_class as InvestmentClass,
          entry_date: formData.entry_date,
          notes: formData.notes.trim() || undefined
        },
        false // Don't allow duplicates
      )

      // Reset form and close dialog
      setFormData({
        symbol: '',
        quantity: '',
        avg_cost: '',
        position_type: '',
        investment_class: '',
        entry_date: new Date().toISOString().split('T')[0],
        notes: ''
      })
      setErrors({})
      setSymbolValidation(null)
      onPositionCreated?.()
      onOpenChange(false)
    } catch (error: any) {
      console.error('Failed to create position:', error)

      // Handle duplicate error
      if (error.message && error.message.includes('Duplicate position')) {
        setErrors({ general: error.message })
      } else {
        setErrors({ general: 'Failed to create position. Please try again.' })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    setFormData({
      symbol: '',
      quantity: '',
      avg_cost: '',
      position_type: '',
      investment_class: '',
      entry_date: new Date().toISOString().split('T')[0],
      notes: ''
    })
    setErrors({})
    setSymbolValidation(null)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Position</DialogTitle>
          <DialogDescription>
            Add a new position to your portfolio. All required fields must be filled.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* General Error */}
          {errors.general && (
            <Alert variant="destructive">
              <AlertDescription>{errors.general}</AlertDescription>
            </Alert>
          )}

          {/* Symbol */}
          <div className="space-y-2">
            <Label htmlFor="symbol">Symbol *</Label>
            <div className="flex gap-2">
              <Input
                id="symbol"
                value={formData.symbol}
                onChange={(e) => handleInputChange('symbol', e.target.value.toUpperCase())}
                onBlur={handleSymbolBlur}
                placeholder="AAPL"
                className={errors.symbol ? 'border-red-500' : ''}
              />
              {isValidatingSymbol && (
                <div className="flex items-center text-sm text-secondary">
                  Validating...
                </div>
              )}
            </div>
            {errors.symbol && <p className="text-xs text-red-500">{errors.symbol}</p>}
            {symbolValidation && symbolValidation.valid && (
              <p className="text-xs text-green-500">✓ {symbolValidation.message}</p>
            )}
          </div>

          {/* Quantity */}
          <div className="space-y-2">
            <Label htmlFor="quantity">Quantity *</Label>
            <Input
              id="quantity"
              type="number"
              value={formData.quantity}
              onChange={(e) => handleInputChange('quantity', e.target.value)}
              placeholder="100"
              step="0.0001"
              className={errors.quantity ? 'border-red-500' : ''}
            />
            {errors.quantity && <p className="text-xs text-red-500">{errors.quantity}</p>}
          </div>

          {/* Average Cost */}
          <div className="space-y-2">
            <Label htmlFor="avg_cost">Average Cost *</Label>
            <Input
              id="avg_cost"
              type="number"
              value={formData.avg_cost}
              onChange={(e) => handleInputChange('avg_cost', e.target.value)}
              placeholder="150.00"
              step="0.01"
              className={errors.avg_cost ? 'border-red-500' : ''}
            />
            {errors.avg_cost && <p className="text-xs text-red-500">{errors.avg_cost}</p>}
          </div>

          {/* Position Type */}
          <div className="space-y-2">
            <Label htmlFor="position_type">Position Type *</Label>
            <Select
              value={formData.position_type}
              onValueChange={(value) => handleInputChange('position_type', value)}
            >
              <SelectTrigger className={errors.position_type ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select position type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="LONG">LONG - Buy to Open</SelectItem>
                <SelectItem value="SHORT">SHORT - Sell Short</SelectItem>
                <SelectItem value="LC">Long Call (LC)</SelectItem>
                <SelectItem value="LP">Long Put (LP)</SelectItem>
                <SelectItem value="SC">Short Call (SC)</SelectItem>
                <SelectItem value="SP">Short Put (SP)</SelectItem>
              </SelectContent>
            </Select>
            {errors.position_type && <p className="text-xs text-red-500">{errors.position_type}</p>}
          </div>

          {/* Investment Class */}
          <div className="space-y-2">
            <Label htmlFor="investment_class">Investment Class *</Label>
            <Select
              value={formData.investment_class}
              onValueChange={(value) => handleInputChange('investment_class', value)}
            >
              <SelectTrigger className={errors.investment_class ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select investment class" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PUBLIC">PUBLIC - Stocks & ETFs</SelectItem>
                <SelectItem value="OPTIONS">OPTIONS - Options Contracts</SelectItem>
                <SelectItem value="PRIVATE">PRIVATE - Private Equity & Alternatives</SelectItem>
              </SelectContent>
            </Select>
            {errors.investment_class && <p className="text-xs text-red-500">{errors.investment_class}</p>}
          </div>

          {/* Entry Date */}
          <div className="space-y-2">
            <Label htmlFor="entry_date">Entry Date *</Label>
            <Input
              id="entry_date"
              type="date"
              value={formData.entry_date}
              onChange={(e) => handleInputChange('entry_date', e.target.value)}
              className={errors.entry_date ? 'border-red-500' : ''}
            />
            {errors.entry_date && <p className="text-xs text-red-500">{errors.entry_date}</p>}
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => handleInputChange('notes', e.target.value)}
              placeholder="Add any notes about this position..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || isValidatingSymbol}>
            {isSubmitting ? 'Creating...' : 'Create Position'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
