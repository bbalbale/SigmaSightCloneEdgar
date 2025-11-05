import { apiClient } from './apiClient'
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api'

export type EquityChangeType = 'CONTRIBUTION' | 'WITHDRAWAL'

export interface EquityChange {
  id: string
  portfolioId: string
  changeType: EquityChangeType
  amount: number
  changeDate: string
  notes?: string | null
  createdByUserId: string
  createdAt: string
  updatedAt: string
  deletedAt?: string | null
  editableUntil: string
  deletableUntil: string
  isDeleted: boolean
}

export interface EquityChangeList {
  items: EquityChange[]
  page: number
  pageSize: number
  totalItems: number
  totalPages: number
}

export interface EquityChangeSummaryPeriod {
  contributions: number
  withdrawals: number
  netFlow: number
}

export interface EquityChangeSummary {
  portfolioId: string
  totalContributions: number
  totalWithdrawals: number
  netFlow: number
  periods: Record<string, EquityChangeSummaryPeriod>
  lastChange?: EquityChange
}

export interface EquityChangeInput {
  changeType: EquityChangeType
  amount: number
  changeDate: string
  notes?: string
}

export interface EquityChangeUpdateInput {
  amount?: number
  changeDate?: string
  notes?: string | null
}

interface EquityChangeApi {
  id: string
  portfolio_id: string
  change_type: EquityChangeType
  amount: number
  change_date: string
  notes?: string | null
  created_by_user_id: string
  created_at: string
  updated_at: string
  deleted_at?: string | null
  editable_until: string
  deletable_until: string
  is_deleted: boolean
}

interface EquityChangeListApi {
  items: EquityChangeApi[]
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

interface EquityChangeSummaryApi {
  portfolio_id: string
  total_contributions: number
  total_withdrawals: number
  net_flow: number
  periods: Record<string, {
    contributions: number
    withdrawals: number
    net_flow: number
  }>
  last_change?: EquityChangeApi
}

const toEquityChange = (payload: EquityChangeApi): EquityChange => ({
  id: payload.id,
  portfolioId: payload.portfolio_id,
  changeType: payload.change_type,
  amount: payload.amount,
  changeDate: payload.change_date,
  notes: payload.notes ?? null,
  createdByUserId: payload.created_by_user_id,
  createdAt: payload.created_at,
  updatedAt: payload.updated_at,
  deletedAt: payload.deleted_at ?? null,
  editableUntil: payload.editable_until,
  deletableUntil: payload.deletable_until,
  isDeleted: payload.is_deleted,
})

const equityChangeService = {
  async list(
    portfolioId: string,
    params: { page?: number; pageSize?: number; startDate?: string; endDate?: string; includeDeleted?: boolean } = {}
  ): Promise<EquityChangeList> {
    const query = new URLSearchParams()
    if (params.page) query.set('page', String(params.page))
    if (params.pageSize) query.set('page_size', String(params.pageSize))
    if (params.startDate) query.set('start_date', params.startDate)
    if (params.endDate) query.set('end_date', params.endDate)
    if (params.includeDeleted) query.set('include_deleted', 'true')

    const endpoint = `${API_ENDPOINTS.EQUITY_CHANGES.LIST(portfolioId)}${query.toString() ? `?${query.toString()}` : ''}`
    const response = await apiClient.get<EquityChangeListApi>(endpoint, {
      ...REQUEST_CONFIGS.STANDARD,
    })

    const data = (response as unknown as { data?: EquityChangeListApi }).data ?? (response as EquityChangeListApi)

    return {
      items: (data.items || []).map(toEquityChange),
      page: data.page,
      pageSize: data.page_size,
      totalItems: data.total_items,
      totalPages: data.total_pages,
    }
  },

  async getSummary(portfolioId: string, params: { startDate?: string; endDate?: string } = {}): Promise<EquityChangeSummary> {
    const query = new URLSearchParams()
    if (params.startDate) query.set('start_date', params.startDate)
    if (params.endDate) query.set('end_date', params.endDate)

    const endpoint = `${API_ENDPOINTS.EQUITY_CHANGES.SUMMARY(portfolioId)}${query.toString() ? `?${query.toString()}` : ''}`
    const response = await apiClient.get<EquityChangeSummaryApi>(endpoint, REQUEST_CONFIGS.STANDARD)
    const data = (response as unknown as { data?: EquityChangeSummaryApi }).data ?? (response as EquityChangeSummaryApi)

    const periods: Record<string, EquityChangeSummaryPeriod> = {}
    Object.entries(data.periods || {}).forEach(([key, value]) => {
      periods[key] = {
        contributions: value?.contributions ?? 0,
        withdrawals: value?.withdrawals ?? 0,
        netFlow:
          (value as any)?.netFlow ?? (value as any)?.net_flow ??
          ((value?.contributions ?? 0) - (value?.withdrawals ?? 0)),
      }
    })

    return {
      portfolioId: data.portfolio_id,
      totalContributions: data.total_contributions,
      totalWithdrawals: data.total_withdrawals,
      netFlow: data.net_flow,
      periods,
      lastChange: data.last_change ? toEquityChange(data.last_change) : undefined,
    }
  },

  async create(portfolioId: string, payload: EquityChangeInput): Promise<EquityChange> {
    const endpoint = API_ENDPOINTS.EQUITY_CHANGES.LIST(portfolioId)
    const response = await apiClient.post<EquityChangeApi>(endpoint, {
      change_type: payload.changeType,
      amount: payload.amount,
      change_date: payload.changeDate,
      notes: payload.notes,
    }, REQUEST_CONFIGS.STANDARD)
    const data = (response as unknown as { data?: EquityChangeApi }).data ?? (response as EquityChangeApi)
    return toEquityChange(data)
  },

  async update(portfolioId: string, changeId: string, payload: EquityChangeUpdateInput): Promise<EquityChange> {
    const endpoint = API_ENDPOINTS.EQUITY_CHANGES.ITEM(portfolioId, changeId)
    const response = await apiClient.put<EquityChangeApi>(endpoint, {
      amount: payload.amount,
      change_date: payload.changeDate,
      notes: payload.notes,
    }, REQUEST_CONFIGS.STANDARD)
    const data = (response as unknown as { data?: EquityChangeApi }).data ?? (response as EquityChangeApi)
    return toEquityChange(data)
  },

  async delete(portfolioId: string, changeId: string): Promise<void> {
    const endpoint = API_ENDPOINTS.EQUITY_CHANGES.ITEM(portfolioId, changeId)
    await apiClient.delete(endpoint, undefined, REQUEST_CONFIGS.STANDARD)
  },

  export(portfolioId: string, params: { startDate?: string; endDate?: string } = {}): string {
    const query = new URLSearchParams()
    if (params.startDate) query.set('start_date', params.startDate)
    if (params.endDate) query.set('end_date', params.endDate)
    query.set('format', 'csv')

    const endpoint = `${API_ENDPOINTS.EQUITY_CHANGES.EXPORT(portfolioId)}?${query.toString()}`
    return apiClient.buildUrl(endpoint)
  },
}

export default equityChangeService
