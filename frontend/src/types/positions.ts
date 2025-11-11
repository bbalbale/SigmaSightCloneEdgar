import type { PositionTag } from './tags'

export type PositionType = 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
export type InvestmentClass = 'PUBLIC' | 'OPTIONS' | 'PRIVATE'

export interface BasePositionView {
  id?: string
  symbol: string
  marketValue: number
  pnl: number
  positive?: boolean
  quantity?: number
  type?: PositionType
  price?: number
  investmentClass?: InvestmentClass
  investmentSubtype?: string
  accountName?: string
  tags?: PositionTag[]
}

export interface PublicPositionView extends BasePositionView {
  companyName?: string
  sector?: string
  industry?: string
}

export interface OptionPositionView extends BasePositionView {
  strikePrice?: number
  expirationDate?: string
  underlyingSymbol?: string
}

export interface PrivatePositionView extends BasePositionView {
  name?: string
}

export type PositionView =
  | PublicPositionView
  | OptionPositionView
  | PrivatePositionView
