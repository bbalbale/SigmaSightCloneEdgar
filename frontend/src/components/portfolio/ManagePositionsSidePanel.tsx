'use client'

import React, { useState, useEffect } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import positionManagementService, { PositionType, InvestmentClass } from '@/services/positionManagementService'
import { apiClient } from '@/services/apiClient'

interface ManagePositionsSidePanelProps {
  portfolioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete?: () => void
}

interface PositionLot {
  id: string
  quantity: number
  avg_cost: number
  entry_date: string
}

interface PositionFormData {
  id?: string // Temp ID for UI
  action: 'buy' | 'sell'
  symbol: string
  // Buy fields
  investment_class: InvestmentClass | ''
  position_type: PositionType | ''
  quantity: string
  avg_cost: string
  entry_date: string
  notes: string
  // Sell fields
  lot_id?: string
  sell_quantity: string
  sale_price: string
  sale_date: string
}

interface ValidationState {
  isValidating: boolean
  isValid: boolean | null
  message: string
  existingLots?: PositionLot[]
  hasTags?: boolean
}

const emptyFormData = (): PositionFormData => ({
  action: 'buy',
  symbol: '',
  investment_class: '',
  position_type: '',
  quantity: '',
  avg_cost: '',
  entry_date: new Date().toISOString().split('T')[0],
  notes: '',
  sell_quantity: '',
  sale_price: '',
  sale_date: new Date().toISOString().split('T')[0],
})

export function ManagePositionsSidePanel({
  portfolioId,
  open,
  onOpenChange,
  onComplete
}: ManagePositionsSidePanelProps) {
  const [positions, setPositions] = useState<PositionFormData[]>([emptyFormData()])
  const [validations, setValidations] = useState<Map<string, ValidationState>>(new Map())
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errors, setErrors] = useState<Map<string, string>>(new Map())

  // Reset form when panel closes
  useEffect(() => {
    if (!open) {
      setPositions([emptyFormData()])
      setValidations(new Map())
      setErrors(new Map())
    }
  }, [open])

  const addAnotherPosition = () => {
    setPositions([...positions, { ...emptyFormData(), id: `temp-${Date.now()}` }])
  }

  const removePosition = (index: number) => {
    if (positions.length === 1) return // Keep at least one
    setPositions(positions.filter((_, i) => i !== index))
  }

  const updatePosition = (index: number, field: keyof PositionFormData, value: any) => {
    const updated = [...positions]
    updated[index] = { ...updated[index], [field]: value }
    setPositions(updated)

    // Clear error for this field
    const key = `${index}-${field}`
    if (errors.has(key)) {
      const newErrors = new Map(errors)
      newErrors.delete(key)
      setErrors(newErrors)
    }
  }

  // Symbol validation with duplicate detection
  const validateSymbol = async (index: number, symbol: string) => {
    if (!symbol || symbol.length < 1) {
      setValidations(new Map(validations.set(symbol, {
        isValidating: false,
        isValid: null,
        message: ''
      })))
      return
    }

    setValidations(new Map(validations.set(symbol, {
      isValidating: true,
      isValid: null,
      message: 'Validating symbol...'
    })))

    try {
      // Validate symbol exists
      const validation = await positionManagementService.validateSymbol(symbol)

      if (!validation.is_valid) {
        setValidations(new Map(validations.set(symbol, {
          isValidating: false,
          isValid: false,
          message: validation.message
        })))
        return
      }

      // Check for existing positions (duplicates)
      const duplicateCheck = await positionManagementService.checkDuplicatePositions(
        portfolioId,
        symbol,
        positions[index].position_type as PositionType || undefined
      )

      if (duplicateCheck.has_duplicates) {
        // Get lot details
        const lots: PositionLot[] = duplicateCheck.existing_positions.map(p => ({
          id: p.id,
          quantity: p.quantity,
          avg_cost: p.avg_cost,
          entry_date: p.entry_date || ''
        }))

        setValidations(new Map(validations.set(symbol, {
          isValidating: false,
          isValid: true,
          message: positions[index].action === 'buy'
            ? `You own ${duplicateCheck.total_count} lot(s) of ${symbol}. Adding as new lot.`
            : `Select lot to sell:`,
          existingLots: lots,
          hasTags: true // Assume tags exist for tag inheritance
        })))
      } else {
        setValidations(new Map(validations.set(symbol, {
          isValidating: false,
          isValid: true,
          message: `✓ ${symbol} validated`
        })))
      }
    } catch (error: any) {
      setValidations(new Map(validations.set(symbol, {
        isValidating: false,
        isValid: false,
        message: error.message || 'Validation failed'
      })))
    }
  }

  const handleSymbolBlur = (index: number, symbol: string) => {
    if (symbol && symbol.length > 0) {
      validateSymbol(index, symbol.toUpperCase())
    }
  }

  const validateForm = (): boolean => {
    const newErrors = new Map<string, string>()

    positions.forEach((pos, index) => {
      // Symbol required
      if (!pos.symbol.trim()) {
        newErrors.set(`${index}-symbol`, 'Symbol is required')
      }

      // Check symbol validation
      const validation = validations.get(pos.symbol)
      if (!validation?.isValid) {
        newErrors.set(`${index}-symbol`, 'Invalid or unvalidated symbol')
      }

      if (pos.action === 'buy') {
        // Buy validations
        if (!pos.investment_class) {
          newErrors.set(`${index}-investment_class`, 'Investment class is required')
        }
        if (!pos.position_type) {
          newErrors.set(`${index}-position_type`, 'Position type is required')
        }
        if (!pos.quantity || parseFloat(pos.quantity) <= 0) {
          newErrors.set(`${index}-quantity`, 'Quantity must be greater than 0')
        }
        if (!pos.avg_cost || parseFloat(pos.avg_cost) <= 0) {
          newErrors.set(`${index}-avg_cost`, 'Average cost must be greater than 0')
        }
        if (!pos.entry_date) {
          newErrors.set(`${index}-entry_date`, 'Entry date is required')
        }
      } else {
        // Sell validations
        const validation = validations.get(pos.symbol)
        if (validation?.existingLots && validation.existingLots.length > 1 && !pos.lot_id) {
          newErrors.set(`${index}-lot_id`, 'Please select which lot to sell')
        }
        if (!pos.sell_quantity || parseFloat(pos.sell_quantity) <= 0) {
          newErrors.set(`${index}-sell_quantity`, 'Quantity must be greater than 0')
        }
        if (!pos.sale_price || parseFloat(pos.sale_price) <= 0) {
          newErrors.set(`${index}-sale_price`, 'Sale price must be greater than 0')
        }
        if (!pos.sale_date) {
          newErrors.set(`${index}-sale_date`, 'Sale date is required')
        }
      }
    })

    setErrors(newErrors)
    return newErrors.size === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)

    try {
      // Separate buys and sells
      const buys = positions.filter(p => p.action === 'buy')
      const sells = positions.filter(p => p.action === 'sell')

      // Handle buys
      if (buys.length > 0) {
        const buyData = buys.map(p => ({
          symbol: p.symbol.toUpperCase(),
          quantity: parseFloat(p.quantity),
          avg_cost: parseFloat(p.avg_cost),
          position_type: p.position_type as PositionType,
          investment_class: p.investment_class as InvestmentClass,
          entry_date: p.entry_date,
          notes: p.notes.trim() || undefined
        }))

        if (buyData.length === 1) {
          await positionManagementService.createPosition({
            portfolio_id: portfolioId,
            ...buyData[0]
          })
        } else {
          await positionManagementService.bulkCreatePositions(portfolioId, buyData)
        }
      }

      // Handle sells
      for (const sell of sells) {
        const validation = validations.get(sell.symbol)
        const lotId = sell.lot_id || validation?.existingLots?.[0]?.id

        if (!lotId) {
          throw new Error(`No position found to sell for ${sell.symbol}`)
        }

        // Update position with exit data
        await positionManagementService.updatePosition(lotId, {
          exit_price: parseFloat(sell.sale_price),
          exit_date: sell.sale_date,
          quantity: parseFloat(sell.sell_quantity) // Update quantity for partial sells
        })

        // If partial sell, create logic would be handled by backend
        // For now, we're updating the existing position
      }

      // Success - close panel and refresh
      onOpenChange(false)
      onComplete?.()

      // Reset form
      setPositions([emptyFormData()])
      setValidations(new Map())
      setErrors(new Map())
    } catch (error: any) {
      console.error('Failed to process positions:', error)
      const newErrors = new Map(errors)
      newErrors.set('general', error.message || 'Failed to process positions')
      setErrors(newErrors)
    } finally {
      setIsSubmitting(false)
    }
  }

  const getError = (index: number, field: string) => {
    return errors.get(`${index}-${field}`)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[90vw] sm:w-[500px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Manage Positions</SheetTitle>
          <SheetDescription>
            Buy new positions or sell existing ones. All changes will be saved together.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          {/* General Error */}
          {errors.has('general') && (
            <Alert variant="destructive">
              <AlertDescription>{errors.get('general')}</AlertDescription>
            </Alert>
          )}

          {/* Position Forms */}
          {positions.map((position, index) => {
            const validation = validations.get(position.symbol)

            return (
              <div key={position.id || index} className="space-y-4 p-4 border rounded-lg themed-card">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-primary">
                    Position {index + 1}
                  </h4>
                  {positions.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removePosition(index)}
                      disabled={isSubmitting}
                    >
                      Remove
                    </Button>
                  )}
                </div>

                {/* Action: Buy or Sell */}
                <div className="space-y-2">
                  <Label>Action *</Label>
                  <Select
                    value={position.action}
                    onValueChange={(value: 'buy' | 'sell') => updatePosition(index, 'action', value)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="buy">Buy / Add Position</SelectItem>
                      <SelectItem value="sell">Sell Position</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Symbol */}
                <div className="space-y-2">
                  <Label htmlFor={`symbol-${index}`}>Symbol *</Label>
                  <div className="flex gap-2">
                    <Input
                      id={`symbol-${index}`}
                      value={position.symbol}
                      onChange={(e) => updatePosition(index, 'symbol', e.target.value.toUpperCase())}
                      onBlur={(e) => handleSymbolBlur(index, e.target.value)}
                      placeholder="AAPL"
                      className={getError(index, 'symbol') ? 'border-red-500' : ''}
                      disabled={isSubmitting}
                    />
                    {validation?.isValidating && (
                      <div className="flex items-center text-xs text-secondary">
                        Validating...
                      </div>
                    )}
                  </div>
                  {getError(index, 'symbol') && (
                    <p className="text-xs text-red-500">{getError(index, 'symbol')}</p>
                  )}
                  {validation?.message && (
                    <p className={`text-xs ${validation.isValid ? 'text-green-600' : 'text-red-500'}`}>
                      {validation.message}
                    </p>
                  )}
                </div>

                {/* Buy Fields */}
                {position.action === 'buy' && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      {/* Investment Class */}
                      <div className="space-y-2">
                        <Label htmlFor={`investment_class-${index}`}>Investment Class *</Label>
                        <Select
                          value={position.investment_class}
                          onValueChange={(value) => updatePosition(index, 'investment_class', value)}
                          disabled={isSubmitting}
                        >
                          <SelectTrigger className={getError(index, 'investment_class') ? 'border-red-500' : ''}>
                            <SelectValue placeholder="Select" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="PUBLIC">PUBLIC</SelectItem>
                            <SelectItem value="OPTIONS">OPTIONS</SelectItem>
                            <SelectItem value="PRIVATE">PRIVATE</SelectItem>
                          </SelectContent>
                        </Select>
                        {getError(index, 'investment_class') && (
                          <p className="text-xs text-red-500">{getError(index, 'investment_class')}</p>
                        )}
                      </div>

                      {/* Position Type */}
                      <div className="space-y-2">
                        <Label htmlFor={`position_type-${index}`}>Position Type *</Label>
                        <Select
                          value={position.position_type}
                          onValueChange={(value) => updatePosition(index, 'position_type', value)}
                          disabled={isSubmitting}
                        >
                          <SelectTrigger className={getError(index, 'position_type') ? 'border-red-500' : ''}>
                            <SelectValue placeholder="Select" />
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
                        {getError(index, 'position_type') && (
                          <p className="text-xs text-red-500">{getError(index, 'position_type')}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      {/* Quantity */}
                      <div className="space-y-2">
                        <Label htmlFor={`quantity-${index}`}>Quantity *</Label>
                        <Input
                          id={`quantity-${index}`}
                          type="number"
                          value={position.quantity}
                          onChange={(e) => updatePosition(index, 'quantity', e.target.value)}
                          placeholder="100"
                          step="0.0001"
                          className={getError(index, 'quantity') ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        {getError(index, 'quantity') && (
                          <p className="text-xs text-red-500">{getError(index, 'quantity')}</p>
                        )}
                      </div>

                      {/* Average Cost */}
                      <div className="space-y-2">
                        <Label htmlFor={`avg_cost-${index}`}>Average Cost *</Label>
                        <Input
                          id={`avg_cost-${index}`}
                          type="number"
                          value={position.avg_cost}
                          onChange={(e) => updatePosition(index, 'avg_cost', e.target.value)}
                          placeholder="150.00"
                          step="0.01"
                          className={getError(index, 'avg_cost') ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        {getError(index, 'avg_cost') && (
                          <p className="text-xs text-red-500">{getError(index, 'avg_cost')}</p>
                        )}
                      </div>
                    </div>

                    {/* Entry Date */}
                    <div className="space-y-2">
                      <Label htmlFor={`entry_date-${index}`}>Entry Date *</Label>
                      <Input
                        id={`entry_date-${index}`}
                        type="date"
                        value={position.entry_date}
                        onChange={(e) => updatePosition(index, 'entry_date', e.target.value)}
                        className={getError(index, 'entry_date') ? 'border-red-500' : ''}
                        disabled={isSubmitting}
                      />
                      {getError(index, 'entry_date') && (
                        <p className="text-xs text-red-500">{getError(index, 'entry_date')}</p>
                      )}
                    </div>

                    {/* Notes */}
                    <div className="space-y-2">
                      <Label htmlFor={`notes-${index}`}>Notes (Optional)</Label>
                      <Input
                        id={`notes-${index}`}
                        value={position.notes}
                        onChange={(e) => updatePosition(index, 'notes', e.target.value)}
                        placeholder="Add any notes..."
                        disabled={isSubmitting}
                      />
                    </div>
                  </>
                )}

                {/* Sell Fields */}
                {position.action === 'sell' && validation?.existingLots && (
                  <>
                    {/* Lot Selection (if multiple) */}
                    {validation.existingLots.length > 1 && (
                      <div className="space-y-2">
                        <Label htmlFor={`lot-${index}`}>Select Lot *</Label>
                        <Select
                          value={position.lot_id}
                          onValueChange={(value) => updatePosition(index, 'lot_id', value)}
                          disabled={isSubmitting}
                        >
                          <SelectTrigger className={getError(index, 'lot_id') ? 'border-red-500' : ''}>
                            <SelectValue placeholder="Select lot" />
                          </SelectTrigger>
                          <SelectContent>
                            {validation.existingLots.map((lot) => (
                              <SelectItem key={lot.id} value={lot.id}>
                                {lot.quantity} shares @ ${lot.avg_cost.toFixed(2)} (Entry: {new Date(lot.entry_date).toLocaleDateString()})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {getError(index, 'lot_id') && (
                          <p className="text-xs text-red-500">{getError(index, 'lot_id')}</p>
                        )}
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      {/* Quantity to Sell */}
                      <div className="space-y-2">
                        <Label htmlFor={`sell_quantity-${index}`}>Quantity *</Label>
                        <Input
                          id={`sell_quantity-${index}`}
                          type="number"
                          value={position.sell_quantity}
                          onChange={(e) => updatePosition(index, 'sell_quantity', e.target.value)}
                          placeholder="100"
                          step="0.0001"
                          className={getError(index, 'sell_quantity') ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        {getError(index, 'sell_quantity') && (
                          <p className="text-xs text-red-500">{getError(index, 'sell_quantity')}</p>
                        )}
                      </div>

                      {/* Sale Price */}
                      <div className="space-y-2">
                        <Label htmlFor={`sale_price-${index}`}>Sale Price *</Label>
                        <Input
                          id={`sale_price-${index}`}
                          type="number"
                          value={position.sale_price}
                          onChange={(e) => updatePosition(index, 'sale_price', e.target.value)}
                          placeholder="160.00"
                          step="0.01"
                          className={getError(index, 'sale_price') ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        {getError(index, 'sale_price') && (
                          <p className="text-xs text-red-500">{getError(index, 'sale_price')}</p>
                        )}
                      </div>
                    </div>

                    {/* Sale Date */}
                    <div className="space-y-2">
                      <Label htmlFor={`sale_date-${index}`}>Sale Date *</Label>
                      <Input
                        id={`sale_date-${index}`}
                        type="date"
                        value={position.sale_date}
                        onChange={(e) => updatePosition(index, 'sale_date', e.target.value)}
                        className={getError(index, 'sale_date') ? 'border-red-500' : ''}
                        disabled={isSubmitting}
                      />
                      {getError(index, 'sale_date') && (
                        <p className="text-xs text-red-500">{getError(index, 'sale_date')}</p>
                      )}
                    </div>
                  </>
                )}

                {index < positions.length - 1 && <Separator className="my-4" />}
              </div>
            )
          })}

          {/* Add Another Button */}
          <Button
            variant="outline"
            onClick={addAnotherPosition}
            disabled={isSubmitting}
            className="w-full"
          >
            + Add Another Position
          </Button>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? 'Processing...' : `Save All (${positions.length})`}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
