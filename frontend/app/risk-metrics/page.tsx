'use client'

import { RiskMetricsContainer } from '@/containers/RiskMetricsContainer'

/**
 * Risk Metrics Page
 *
 * Thin page wrapper following standard architecture pattern:
 * Page (thin wrapper) → Container (business logic) → Hooks (data fetching) → Services (API calls)
 *
 * All business logic, data fetching, and component orchestration
 * is handled in RiskMetricsContainer.
 */
export default function RiskMetricsPage() {
  return <RiskMetricsContainer />
}
