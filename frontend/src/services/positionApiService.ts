/**
 * Position API Service - Shadow mode fetching for API comparison
 * This service runs in parallel with existing data fetching to compare API vs JSON data
 */

import { authManager } from './authManager'
import { requestManager } from './requestManager'

interface ApiPosition {
  id: string
  portfolio_id: string
  symbol: string
  position_type: 'LONG' | 'SHORT' | 'OPTION'
  quantity: number
  entry_date: string
  entry_price: number
  cost_basis: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
}

interface PositionsApiResponse {
  positions: ApiPosition[]
  summary: {
    total_positions: number
    total_cost_basis: number
    total_market_value: number
    total_unrealized_pnl: number
  }
}

interface ComparisonReport {
  timestamp: Date
  apiCallTime: number
  jsonDataTime: number
  positionCountMatch: boolean
  symbolsMatch: boolean
  pnlDataAvailable: {
    api: boolean
    json: boolean
  }
  differences: string[]
  errors: string[]
}

class PositionApiService {
  private comparisonReports: ComparisonReport[] = []

  /**
   * Fetch positions from the API in shadow mode
   */
  async fetchPositionsFromApi(
    portfolioId: string,
    signal?: AbortSignal
  ): Promise<PositionsApiResponse | null> {
    const startTime = performance.now()
    
    try {
      const token = authManager.getAccessToken()
      if (!token) {
        console.log('dY"S Shadow API: missing auth token, skipping fetch')
        return null
      }

      const response = await requestManager.authenticatedFetch(
        `/api/proxy/api/v1/data/positions/details?portfolio_id=${portfolioId}`,
        token,
        {
          signal,
          maxRetries: 1, // Don't retry much in shadow mode
          timeout: 5000,
        }
      )

      const apiCallTime = performance.now() - startTime

      if (!response.ok) {
        console.log(`📊 Shadow API: positions fetch failed (${response.status}) in ${apiCallTime.toFixed(0)}ms`)
        return null
      }

      const data: PositionsApiResponse = await response.json()
      console.log(`📊 Shadow API: fetched ${data.positions.length} positions in ${apiCallTime.toFixed(0)}ms`)
      
      return data
    } catch (error: any) {
      const apiCallTime = performance.now() - startTime
      if (error.name !== 'AbortError') {
        console.log(`📊 Shadow API: error fetching positions (${apiCallTime.toFixed(0)}ms)`)
      }
      return null
    }
  }

  /**
   * Compare API data with JSON data and generate report
   */
  compareWithJsonData(
    apiData: PositionsApiResponse | null,
    jsonData: any,
    apiCallTime: number
  ): ComparisonReport {
    const report: ComparisonReport = {
      timestamp: new Date(),
      apiCallTime,
      jsonDataTime: 0, // JSON is already loaded
      positionCountMatch: false,
      symbolsMatch: false,
      pnlDataAvailable: {
        api: false,
        json: false
      },
      differences: [],
      errors: []
    }

    // If API call failed
    if (!apiData) {
      report.errors.push('API call failed - no data to compare')
      return report
    }

    // Compare position counts
    const jsonPositions = [...(jsonData.positions || []), ...(jsonData.shortPositions || [])]
    report.positionCountMatch = apiData.positions.length === jsonPositions.length
    
    if (!report.positionCountMatch) {
      report.differences.push(
        `Position count mismatch: API=${apiData.positions.length}, JSON=${jsonPositions.length}`
      )
    }

    // Compare symbols
    const apiSymbols = apiData.positions.map(p => p.symbol).sort()
    const jsonSymbols = jsonPositions.map(p => p.symbol).sort()
    report.symbolsMatch = JSON.stringify(apiSymbols) === JSON.stringify(jsonSymbols)
    
    if (!report.symbolsMatch) {
      const apiOnly = apiSymbols.filter(s => !jsonSymbols.includes(s))
      const jsonOnly = jsonSymbols.filter(s => !apiSymbols.includes(s))
      
      if (apiOnly.length > 0) {
        report.differences.push(`Symbols only in API: ${apiOnly.join(', ')}`)
      }
      if (jsonOnly.length > 0) {
        report.differences.push(`Symbols only in JSON: ${jsonOnly.join(', ')}`)
      }
    }

    // Check P&L data availability
    report.pnlDataAvailable.api = apiData.positions.some(p => p.unrealized_pnl !== 0)
    report.pnlDataAvailable.json = jsonPositions.some(p => p.pnl && p.pnl !== 0)
    
    if (report.pnlDataAvailable.json && !report.pnlDataAvailable.api) {
      report.differences.push('P&L data available in JSON but not in API (all zeros)')
    }

    // Check for position type differences
    const apiLongCount = apiData.positions.filter(p => p.position_type === 'LONG').length
    const apiShortCount = apiData.positions.filter(p => p.position_type === 'SHORT').length
    const jsonLongCount = jsonData.positions?.length || 0
    const jsonShortCount = jsonData.shortPositions?.length || 0
    
    if (apiLongCount !== jsonLongCount || apiShortCount !== jsonShortCount) {
      report.differences.push(
        `Position type mismatch: API (${apiLongCount}L/${apiShortCount}S), JSON (${jsonLongCount}L/${jsonShortCount}S)`
      )
    }

    // Check for field differences on matching positions
    apiData.positions.forEach(apiPos => {
      const jsonPos = jsonPositions.find(p => p.symbol === apiPos.symbol)
      if (jsonPos) {
        if (apiPos.quantity !== jsonPos.quantity) {
          report.differences.push(`${apiPos.symbol}: quantity mismatch (API=${apiPos.quantity}, JSON=${jsonPos.quantity})`)
        }
        if (Math.abs(apiPos.market_value - (jsonPos.marketValue || 0)) > 0.01) {
          report.differences.push(`${apiPos.symbol}: market value mismatch (API=${apiPos.market_value}, JSON=${jsonPos.marketValue})`)
        }
      }
    })

    // Store report
    this.comparisonReports.push(report)
    
    return report
  }

  /**
   * Generate final comparison summary
   */
  generateSummaryReport(): void {
    if (this.comparisonReports.length === 0) {
      console.log('📊 No comparison data collected')
      return
    }

    const lastReport = this.comparisonReports[this.comparisonReports.length - 1]
    
    console.group('📊 API Shadow Mode Report')
    console.log(`Timestamp: ${lastReport.timestamp.toLocaleTimeString()}`)
    console.log(`API Response Time: ${lastReport.apiCallTime.toFixed(0)}ms`)
    
    // Status summary - compact
    const status = []
    if (lastReport.positionCountMatch) status.push('Count ✅')
    else status.push('Count ❌')
    
    if (lastReport.symbolsMatch) status.push('Symbols ✅')
    else status.push('Symbols ❌')
    
    if (lastReport.pnlDataAvailable.api) status.push('API P&L ✅')
    else status.push('API P&L ❌')
    
    console.log(`Status: ${status.join(' | ')}`)
    
    // Differences - show everything as requested
    if (lastReport.differences.length > 0) {
      console.log('Differences Found:')
      lastReport.differences.forEach(diff => console.log(`  - ${diff}`))
    }
    
    // Errors
    if (lastReport.errors.length > 0) {
      console.log('Errors:')
      lastReport.errors.forEach(err => console.log(`  - ${err}`))
    }
    
    console.groupEnd()
  }

  /**
   * Clear comparison reports
   */
  clearReports(): void {
    this.comparisonReports = []
  }
}

export const positionApiService = new PositionApiService()
