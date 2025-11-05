'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import equityChangeService, { type EquityChange, type EquityChangeSummary, type EquityChangeType } from '@/services/equityChangeService'
import { format } from 'date-fns'

interface ManageEquitySidePanelProps {
  portfolioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete?: () => void
}

interface EquityFormState {
  changeType: EquityChangeType
  amount: string
  changeDate: string
  notes: string
}

const createEmptyForm = (): EquityFormState => ({
  changeType: 'CONTRIBUTION',
  amount: '',
  changeDate: new Date().toISOString().split('T')[0],
  notes: '',
})

const currencyFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

function formatCurrency(value: number): string {
  return currencyFormatter.format(value)
}

function formatSignedCurrency(value: number): string {
  const formatted = formatCurrency(Math.abs(value))
  return value >= 0 ? `+${formatted}` : `-${formatted}`
}

function formatHumanDate(value: string): string {
  try {
    return format(new Date(value), 'MMM d, yyyy')
  } catch {
    return value
  }
}

function canEdit(change: EquityChange): boolean {
  return new Date(change.editableUntil).getTime() > Date.now()
}

function canDelete(change: EquityChange): boolean {
  return new Date(change.deletableUntil).getTime() > Date.now()
}

export function ManageEquitySidePanel({ portfolioId, open, onOpenChange, onComplete }: ManageEquitySidePanelProps) {
  const [form, setForm] = useState<EquityFormState>(createEmptyForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [loadingData, setLoadingData] = useState(false)
  const [summary, setSummary] = useState<EquityChangeSummary | null>(null)
  const [recentChanges, setRecentChanges] = useState<EquityChange[]>([])

  useEffect(() => {
    if (!open) {
      setForm(createEmptyForm())
      setError(null)
      setSuccessMessage(null)
      return
    }

    let isCancelled = false
    const loadData = async () => {
      setLoadingData(true)
      try {
        const [summaryResponse, listResponse] = await Promise.all([
          equityChangeService.getSummary(portfolioId),
          equityChangeService.list(portfolioId, { page: 1, pageSize: 10 }),
        ])
        if (!isCancelled) {
          setSummary(summaryResponse)
          setRecentChanges(listResponse.items)
        }
      } catch (err) {
        console.error('Failed to load equity changes:', err)
        if (!isCancelled) {
          setError('Failed to load equity change history. Please try again.')
        }
      } finally {
        if (!isCancelled) {
          setLoadingData(false)
        }
      }
    }

    loadData()

    return () => {
      isCancelled = true
    }
  }, [open, portfolioId])

  const resetForm = () => {
    setForm(createEmptyForm())
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSuccessMessage(null)

    const amountValue = parseFloat(form.amount)
    if (!Number.isFinite(amountValue) || amountValue <= 0) {
      setError('Amount must be a positive number.')
      return
    }

    if (!form.changeDate) {
      setError('Please select a change date.')
      return
    }

    setIsSubmitting(true)
    try {
      await equityChangeService.create(portfolioId, {
        changeType: form.changeType,
        amount: amountValue,
        changeDate: form.changeDate,
        notes: form.notes?.trim() || undefined,
      })

      setSuccessMessage(`${form.changeType === 'CONTRIBUTION' ? 'Contribution' : 'Withdrawal'} recorded successfully.`)
      resetForm()

      const [summaryResponse, listResponse] = await Promise.all([
        equityChangeService.getSummary(portfolioId),
        equityChangeService.list(portfolioId, { page: 1, pageSize: 10 }),
      ])
      setSummary(summaryResponse)
      setRecentChanges(listResponse.items)

      onComplete?.()
    } catch (err: any) {
      console.error('Failed to record equity change:', err)
      setError(err?.message || 'Failed to record equity change.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (change: EquityChange) => {
    if (!canDelete(change)) return
    try {
      await equityChangeService.delete(portfolioId, change.id)
      const listResponse = await equityChangeService.list(portfolioId, { page: 1, pageSize: 10 })
      setRecentChanges(listResponse.items)
      const summaryResponse = await equityChangeService.getSummary(portfolioId)
      setSummary(summaryResponse)
      onComplete?.()
    } catch (err) {
      console.error('Failed to delete equity change:', err)
      setError('Unable to delete this entry. It may be outside the deletion window.')
    }
  }

  const netFlow30d = useMemo(() => summary?.periods?.['30d']?.netFlow ?? 0, [summary])
  const totalNetFlow = summary ? summary.netFlow ?? 0 : 0

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[90vw] sm:w-[520px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Manage Equity</SheetTitle>
          <SheetDescription>
            Record capital contributions or withdrawals and review recent activity.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {successMessage && (
            <Alert>
              <AlertDescription>{successMessage}</AlertDescription>
            </Alert>
          )}

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-secondary uppercase tracking-wide">
              Record Equity Change
            </h3>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="equity-type">Type *</Label>
                  <Select
                    value={form.changeType}
                    onValueChange={(value) => setForm((prev) => ({ ...prev, changeType: value as EquityChangeType }))}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="equity-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CONTRIBUTION">Contribution</SelectItem>
                      <SelectItem value="WITHDRAWAL">Withdrawal</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="equity-amount">Amount *</Label>
                  <Input
                    id="equity-amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.amount}
                    onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))}
                    placeholder="50000"
                    disabled={isSubmitting}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="equity-date">Date *</Label>
                <Input
                  id="equity-date"
                  type="date"
                  value={form.changeDate}
                  max={new Date().toISOString().split('T')[0]}
                  onChange={(event) => setForm((prev) => ({ ...prev, changeDate: event.target.value }))}
                  disabled={isSubmitting}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="equity-notes">Notes</Label>
                <Textarea
                  id="equity-notes"
                  value={form.notes}
                  onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
                  placeholder="Optional description"
                  disabled={isSubmitting}
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" disabled={isSubmitting} onClick={resetForm}>
                  Clear
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Record Change'}
                </Button>
              </div>
            </form>
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-secondary uppercase tracking-wide">
              Summary
            </h3>
            {loadingData && !summary ? (
              <p className="text-sm text-secondary">Loading summary…</p>
            ) : summary ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="themed-border p-3">
                  <p className="text-[10px] uppercase tracking-wide text-secondary font-semibold">Net Capital Flow (30d)</p>
                  <p className={`text-xl font-semibold ${netFlow30d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatSignedCurrency(netFlow30d)}
                  </p>
                </div>
                <div className="themed-border p-3">
                  <p className="text-[10px] uppercase tracking-wide text-secondary font-semibold">Net Capital Flow (All Time)</p>
                  <p className={`text-xl font-semibold ${totalNetFlow >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatSignedCurrency(totalNetFlow)}
                  </p>
                </div>
                <div className="themed-border p-3">
                  <p className="text-[10px] uppercase tracking-wide text-secondary font-semibold">Total Contributions</p>
                  <p className="text-xl font-semibold text-accent">
                    {formatCurrency(summary.totalContributions)}
                  </p>
                </div>
                <div className="themed-border p-3">
                  <p className="text-[10px] uppercase tracking-wide text-secondary font-semibold">Total Withdrawals</p>
                  <p className="text-xl font-semibold text-accent">
                    {formatCurrency(summary.totalWithdrawals)}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-secondary">No equity changes recorded yet.</p>
            )}
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-secondary uppercase tracking-wide">
                Recent Activity
              </h3>
              {summary && (
                <a
                  href={equityChangeService.export(portfolioId)}
                  className="text-xs font-medium text-accent hover:underline"
                >
                  Export CSV
                </a>
              )}
            </div>

            {loadingData && recentChanges.length === 0 ? (
              <p className="text-sm text-secondary">Loading activity…</p>
            ) : recentChanges.length === 0 ? (
              <p className="text-sm text-secondary">No recent equity changes.</p>
            ) : (
              <div className="space-y-2">
                {recentChanges.map((change) => (
                  <div key={change.id} className="themed-border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-primary">
                          {change.changeType === 'CONTRIBUTION' ? 'Contribution' : 'Withdrawal'}
                        </p>
                        <p className={`text-xs font-semibold ${change.changeType === 'CONTRIBUTION' ? 'text-emerald-400' : 'text-red-400'}`}>
                          {change.changeType === 'CONTRIBUTION'
                            ? formatCurrency(change.amount)
                            : `-${formatCurrency(change.amount)}`}
                        </p>
                        <p className="text-xs text-secondary">
                          {formatHumanDate(change.changeDate)}
                        </p>
                        {change.notes && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {change.notes}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col gap-2">
                        {canEdit(change) ? (
                          <span className="text-[10px] font-medium text-secondary uppercase">Editable</span>
                        ) : (
                          <span className="text-[10px] text-muted-foreground uppercase">Edit window closed</span>
                        )}
                        {canDelete(change) ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDelete(change)}
                          >
                            Delete
                          </Button>
                        ) : (
                          <span className="text-[10px] text-muted-foreground uppercase">Delete window closed</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}
