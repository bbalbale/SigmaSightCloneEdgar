import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { OptionPositionCard } from '@/components/positions/OptionPositionCard'

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  price?: number
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}

interface OptionsPositionsProps {
  positions: OptionPosition[]
}

export function OptionsPositions({ positions }: OptionsPositionsProps) {
  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <OptionPositionCard
          key={position.id || `option-${index}`}
          position={position}
        />
      )}
      emptyMessage="No options positions"
    />
  )
}