/**
 * PortfolioManagement Component - November 3, 2025
 * Manages portfolio CRUD operations in Settings page
 * Uses progressive disclosure to hide for single-portfolio users
 */

'use client'

import React, { useState } from 'react'
import { usePortfolios, usePortfolioMutations } from '@/hooks/useMultiPortfolio'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Building2, Plus, Pencil, Trash2, Loader2 } from 'lucide-react'
import { formatNumber } from '@/lib/formatters'

interface PortfolioManagementProps {
  /**
   * Show component even for single portfolio users (default: false)
   * When false, uses progressive disclosure to hide for single portfolio
   */
  showForSinglePortfolio?: boolean
}

export function PortfolioManagement({ showForSinglePortfolio = false }: PortfolioManagementProps) {
  const { portfolios, loading, refetch } = usePortfolios()
  const { createPortfolio, updatePortfolio, deletePortfolio, creating, updating, deleting, error } =
    usePortfolioMutations()

  // Form state for create/edit
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    account_name: '',
    account_type: 'taxable' as 'taxable' | 'ira' | 'roth_ira' | '401k' | 'trust' | 'other',
    description: '',
  })

  // Progressive disclosure: Hide for single-portfolio users unless explicitly shown
  if (!showForSinglePortfolio && portfolios.length <= 1) {
    return null
  }

  const handleCreatePortfolio = async () => {
    try {
      await createPortfolio(formData)
      setIsCreateDialogOpen(false)
      setFormData({ account_name: '', account_type: 'taxable', description: '' })
      await refetch()
    } catch (err) {
      console.error('Failed to create portfolio:', err)
    }
  }

  const handleEditPortfolio = async () => {
    if (!selectedPortfolioId) return
    try {
      await updatePortfolio(selectedPortfolioId, formData)
      setIsEditDialogOpen(false)
      setSelectedPortfolioId(null)
      setFormData({ account_name: '', account_type: 'taxable', description: '' })
      await refetch()
    } catch (err) {
      console.error('Failed to update portfolio:', err)
    }
  }

  const handleDeletePortfolio = async () => {
    if (!selectedPortfolioId) return
    try {
      await deletePortfolio(selectedPortfolioId)
      setIsDeleteDialogOpen(false)
      setSelectedPortfolioId(null)
      await refetch()
    } catch (err) {
      console.error('Failed to delete portfolio:', err)
    }
  }

  const openEditDialog = (portfolioId: string) => {
    const portfolio = portfolios.find((p) => p.id === portfolioId)
    if (portfolio) {
      setSelectedPortfolioId(portfolioId)
      setFormData({
        account_name: portfolio.account_name,
        account_type: portfolio.account_type as any,
        description: portfolio.description || '',
      })
      setIsEditDialogOpen(true)
    }
  }

  const openDeleteDialog = (portfolioId: string) => {
    setSelectedPortfolioId(portfolioId)
    setIsDeleteDialogOpen(true)
  }

  const formatAccountType = (accountType: string): string => {
    const typeMap: Record<string, string> = {
      taxable: 'Taxable',
      ira: 'IRA',
      roth_ira: 'Roth IRA',
      '401k': '401(k)',
      trust: 'Trust',
      other: 'Other',
    }
    return typeMap[accountType] || accountType
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Portfolio Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Portfolio Management
            </CardTitle>
            <CardDescription>Manage your investment accounts</CardDescription>
          </div>

          {/* Create Portfolio Button */}
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Portfolio
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Portfolio</DialogTitle>
                <DialogDescription>Add a new investment account to track</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="account_name">Account Name *</Label>
                  <Input
                    id="account_name"
                    placeholder="e.g., Growth Portfolio"
                    value={formData.account_name}
                    onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="account_type">Account Type *</Label>
                  <Select
                    value={formData.account_type}
                    onValueChange={(value: any) => setFormData({ ...formData, account_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="taxable">Taxable</SelectItem>
                      <SelectItem value="ira">IRA</SelectItem>
                      <SelectItem value="roth_ira">Roth IRA</SelectItem>
                      <SelectItem value="401k">401(k)</SelectItem>
                      <SelectItem value="trust">Trust</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Optional description..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                  disabled={creating}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreatePortfolio} disabled={creating || !formData.account_name}>
                  {creating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Portfolio'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>

      <CardContent>
        {/* Portfolio List */}
        <div className="space-y-3">
          {portfolios.map((portfolio) => (
            <div
              key={portfolio.id}
              className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium">{portfolio.account_name}</h4>
                  <Badge variant={portfolio.is_active ? 'default' : 'secondary'} className="text-xs">
                    {formatAccountType(portfolio.account_type)}
                  </Badge>
                  {!portfolio.is_active && (
                    <Badge variant="outline" className="text-xs">
                      Inactive
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{formatNumber(portfolio.net_asset_value ?? portfolio.total_value)} Net Asset Value</span>
                  <span>•</span>
                  <span>
                    {portfolio.position_count} {portfolio.position_count === 1 ? 'Position' : 'Positions'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Edit Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEditDialog(portfolio.id)}
                  disabled={updating}
                >
                  <Pencil className="h-4 w-4" />
                </Button>

                {/* Delete Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openDeleteDialog(portfolio.id)}
                  disabled={deleting || portfolios.length === 1}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {portfolios.length === 1 && (
          <p className="text-sm text-muted-foreground mt-4">
            Note: You must have at least one portfolio. Create a new portfolio before deleting this one.
          </p>
        )}
      </CardContent>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Portfolio</DialogTitle>
            <DialogDescription>Update portfolio information</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit_account_name">Account Name *</Label>
              <Input
                id="edit_account_name"
                value={formData.account_name}
                onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_account_type">Account Type *</Label>
              <Select
                value={formData.account_type}
                onValueChange={(value: any) => setFormData({ ...formData, account_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="taxable">Taxable</SelectItem>
                  <SelectItem value="ira">IRA</SelectItem>
                  <SelectItem value="roth_ira">Roth IRA</SelectItem>
                  <SelectItem value="401k">401(k)</SelectItem>
                  <SelectItem value="trust">Trust</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_description">Description</Label>
              <Textarea
                id="edit_description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(false)}
              disabled={updating}
            >
              Cancel
            </Button>
            <Button onClick={handleEditPortfolio} disabled={updating || !formData.account_name}>
              {updating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Updating...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Portfolio</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this portfolio? This action cannot be undone and will remove
              all associated positions and data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeletePortfolio} disabled={deleting} className="bg-destructive">
              {deleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Portfolio'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
