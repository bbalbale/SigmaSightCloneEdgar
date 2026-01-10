'use client'

import { PhaseListItem, PhaseListItemProps } from './PhaseListItem'
import { PhaseDetail } from '@/services/onboardingService'

/**
 * Default phase definitions for display when no backend data is available
 */
const DEFAULT_PHASES: Array<{ phase_id: string; phase_name: string }> = [
  { phase_id: 'phase_1', phase_name: 'Market Data Collection' },
  { phase_id: 'phase_1.5', phase_name: 'Factor Analysis' },
  { phase_id: 'phase_1.75', phase_name: 'Symbol Metrics' },
  { phase_id: 'phase_2', phase_name: 'Portfolio Snapshots' },
  { phase_id: 'phase_2.5', phase_name: 'Position Values' },
  { phase_id: 'phase_3', phase_name: 'Position Betas' },
  { phase_id: 'phase_4', phase_name: 'Factor Exposures' },
  { phase_id: 'phase_5', phase_name: 'Volatility Analysis' },
  { phase_id: 'phase_6', phase_name: 'Correlations' },
]

export interface PhaseListProps {
  phases: PhaseDetail[] | null
  currentPhase?: string | null
}

/**
 * Map backend phase detail to PhaseListItem props
 */
function mapPhaseToItemProps(
  phase: PhaseDetail,
  hasWarning: boolean = false
): PhaseListItemProps {
  let status: PhaseListItemProps['status'] = phase.status

  // Show warning status if phase has warning-level log entries
  if (phase.status === 'completed' && hasWarning) {
    status = 'warning'
  }

  return {
    phaseId: phase.phase_id,
    phaseName: phase.phase_name,
    status,
    current: phase.current,
    total: phase.total,
    unit: phase.unit,
    durationSeconds: phase.duration_seconds,
  }
}

/**
 * List of all batch processing phases with their current status
 */
export function PhaseList({ phases, currentPhase }: PhaseListProps) {
  // If we have backend phase data, use it
  if (phases && phases.length > 0) {
    return (
      <div className="space-y-2">
        {phases.map((phase) => (
          <PhaseListItem key={phase.phase_id} {...mapPhaseToItemProps(phase)} />
        ))}
      </div>
    )
  }

  // Otherwise show default phases with pending status
  return (
    <div className="space-y-2">
      {DEFAULT_PHASES.map((phase) => (
        <PhaseListItem
          key={phase.phase_id}
          phaseId={phase.phase_id}
          phaseName={phase.phase_name}
          status={currentPhase === phase.phase_id ? 'running' : 'pending'}
        />
      ))}
    </div>
  )
}

export default PhaseList
