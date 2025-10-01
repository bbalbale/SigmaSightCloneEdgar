import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { StockPositionCard } from '@/components/positions/StockPositionCard'

interface Position {
  id?: string
  symbol: string
  name?: string
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_class?: string
  investment_subtype?: string
  price?: number
}

interface PublicPositionsProps {
  positions: Position[]
}

export function PublicPositions({ positions }: PublicPositionsProps) {
  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <StockPositionCard
          key={position.id || `public-${index}`}
          position={{
            ...position,
            // Ensure negative display for shorts
            marketValue: position.type === 'SHORT' ? -Math.abs(position.marketValue) : position.marketValue
          }}
        />
      )}
      emptyMessage="No positions"
    />
  )
}