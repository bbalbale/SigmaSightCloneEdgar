"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface PortfolioSelectionDialogProps {
  trigger: React.ReactNode
}

const portfolioTypes = [
  {
    id: 'individual',
    title: 'Individual',
    description: 'Personal investment portfolio with stocks, bonds, and ETFs',
    features: ['Basic risk analysis', 'Portfolio tracking', 'Simple reporting']
  },
  {
    id: 'high-net-worth',
    title: 'High Net Worth',
    description: 'Complex portfolios with private investments and alternatives',
    features: ['Advanced analytics', 'Private equity tracking', 'Tax optimization']
  },
  {
    id: 'hedge-fund',
    title: 'Hedge Fund Style',
    description: 'Long/short strategies with derivatives and complex instruments',
    features: ['Options analysis', 'Risk attribution', 'Performance attribution']
  }
]

export function PortfolioSelectionDialog({ trigger }: PortfolioSelectionDialogProps) {
  const [open, setOpen] = useState(false)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const router = useRouter()

  const handlePortfolioSelect = (portfolioType: string) => {
    setSelectedType(portfolioType)
    setOpen(false)
    
    // Navigate to portfolio page with type parameter
    router.push(`/portfolio?type=${portfolioType}`)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Select Your Portfolio Type</DialogTitle>
          <DialogDescription>
            Choose the portfolio type that best matches your investment approach. This will customize the analytics and features available to you.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          {portfolioTypes.map((type) => (
            <Card 
              key={type.id}
              className="cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => handlePortfolioSelect(type.id)}
            >
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{type.title}</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      handlePortfolioSelect(type.id)
                    }}
                  >
                    Select
                  </Button>
                </div>
                <p className="text-gray-600 text-sm mb-3">{type.description}</p>
                <div className="flex flex-wrap gap-2">
                  {type.features.map((feature, index) => (
                    <span 
                      key={index}
                      className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-md"
                    >
                      {feature}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}