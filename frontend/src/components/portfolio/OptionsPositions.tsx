import React from 'react'
import { OptionCard } from './OptionCard'
import { useTheme } from '@/contexts/ThemeContext'

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
  const { theme } = useTheme()

  return (
    <div className="space-y-2">
      {positions.map((position, index) => (
        <OptionCard key={position.id || `option-${index}`} position={position} />
      ))}

      {positions.length === 0 && (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800/50 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No options positions
        </div>
      )}
    </div>
  )
}