'use client'

import React from 'react'
import { useResearchStore } from '@/stores/researchStore'
import { useTheme } from '@/contexts/ThemeContext'

/**
 * Debug component to visualize correlation matrix state
 * Remove this after debugging is complete
 */
export function CorrelationDebugger() {
  const { theme } = useTheme()
  const correlationMatrix = useResearchStore((state) => state.correlationMatrix)
  const loading = useResearchStore((state) => state.correlationMatrixLoading)
  const error = useResearchStore((state) => state.correlationMatrixError)

  return (
    <div className={`fixed bottom-4 right-4 p-4 rounded shadow-lg border max-w-md ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
    }`}>
      <h4 className="font-bold mb-2 text-sm">🔍 Correlation Matrix Debug</h4>

      <div className="space-y-2 text-xs">
        <div>
          <strong>Loading:</strong> {loading ? '✅ Yes' : '❌ No'}
        </div>

        <div>
          <strong>Error:</strong> {error || '✅ None'}
        </div>

        <div>
          <strong>Matrix Available:</strong> {correlationMatrix ? '✅ Yes' : '❌ No'}
        </div>

        {correlationMatrix && (
          <>
            <div>
              <strong>Symbols Count:</strong> {correlationMatrix.position_symbols?.length || 0}
            </div>

            <div>
              <strong>Matrix Rows:</strong> {correlationMatrix.correlation_matrix?.length || 0}
            </div>

            <div className="max-h-32 overflow-y-auto">
              <strong>Symbols:</strong>
              <div className="mt-1 text-[10px] font-mono">
                {correlationMatrix.position_symbols?.join(', ') || 'None'}
              </div>
            </div>

            {correlationMatrix.data_quality && (
              <div>
                <strong>Data Quality:</strong>
                <div className="ml-2 text-[10px]">
                  - Coverage: {correlationMatrix.data_quality.coverage_percent}%
                  <br />
                  - Valid Pairs: {correlationMatrix.data_quality.valid_pairs}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-600">
        <button
          onClick={() => console.log('Correlation Matrix State:', correlationMatrix)}
          className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Log Full State to Console
        </button>
      </div>
    </div>
  )
}
