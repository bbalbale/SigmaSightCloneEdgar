'use client'

import { PhaseListItem, PhaseListItemProps } from './PhaseListItem'
import { PhaseDetail, ActivityLogEntry } from '@/services/onboardingService'

/**
 * Default phase definitions for display when no backend data is available.
 * Phase 7.4: Updated to match backend 9-phase architecture (2026-01-11)
 *
 * Phase execution order:
 * - Phases 1, 1_5, 1_75: Run first (market data, factors, symbol metrics)
 * - Phases 0, 2, 3, 4, 5, 6: Run per-date (profiles, fundamentals, P&L, market values, tags, analytics)
 */
const DEFAULT_PHASES: Array<{ phase_id: string; phase_name: string }> = [
  { phase_id: 'phase_1', phase_name: 'Market Data Collection' },
  { phase_id: 'phase_1_5', phase_name: 'Factor Analysis' },
  { phase_id: 'phase_1_75', phase_name: 'Symbol Metrics' },
  { phase_id: 'phase_0', phase_name: 'Company Profile Sync' },
  { phase_id: 'phase_2', phase_name: 'Fundamental Data Collection' },
  { phase_id: 'phase_3', phase_name: 'P&L Calculation & Snapshots' },
  { phase_id: 'phase_4', phase_name: 'Position Market Value Updates' },
  { phase_id: 'phase_5', phase_name: 'Sector Tag Restoration' },
  { phase_id: 'phase_6', phase_name: 'Risk Analytics' },
]

export interface PhaseListProps {
  phases: PhaseDetail[] | null
  currentPhase?: string | null
  activityLog?: ActivityLogEntry[]
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
 * Check if a phase has any warning-level entries in the activity log
 * Per design doc Section 9.5: "Warning phase status - Map from activity log"
 */
function phaseHasWarning(phaseName: string, activityLog: ActivityLogEntry[]): boolean {
  // Check if any warning entries mention this phase name
  return activityLog.some(
    (entry) => entry.level === 'warning' && entry.message.toLowerCase().includes(phaseName.toLowerCase())
  )
}

/**
 * List of all batch processing phases with their current status
 */
export function PhaseList({ phases, currentPhase, activityLog = [] }: PhaseListProps) {
  // If we have backend phase data, use it
  if (phases && phases.length > 0) {
    return (
      <div className="space-y-2">
        {phases.map((phase) => (
          <PhaseListItem
            key={phase.phase_id}
            {...mapPhaseToItemProps(phase, phaseHasWarning(phase.phase_name, activityLog))}
          />
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
