# Quick Analytics API Test Page - Rapid Implementation Guide

## 🚀 Ultra-Fast Implementation (2-3 hours)

### Single File Solution
Create ONE file: `app/test-api/page.tsx` that does everything.

### Step 1: Copy-Paste Starter Code (5 minutes)

```tsx
// app/test-api/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

// Test configuration - EDIT THESE VALUES AS NEEDED
const CONFIG = {
  correlationMatrix: { lookbackDays: 90, minOverlap: 30 },
  positionFactorExposures: { limit: 10, offset: 0 }
}

export default function ApiTestPage() {
  const router = useRouter()
  const [token, setToken] = useState<string>('')
  const [portfolioId, setPortfolioId] = useState<string>('')
  const [results, setResults] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  // Check auth on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    if (!storedToken) {
      alert('Please login first!')
      router.push('/login')
      return
    }
    setToken(storedToken)
    
    // Get portfolio ID from auth/me endpoint
    fetch('/api/proxy/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${storedToken}` }
    })
      .then(res => res.json())
      .then(data => setPortfolioId(data.portfolio_id))
      .catch(() => alert('Could not get portfolio ID'))
  }, [router])

  // Generic API caller
  const callApi = async (name: string, endpoint: string) => {
    setLoading(prev => ({ ...prev, [name]: true }))
    try {
      const response = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await response.json()
      setResults(prev => ({ ...prev, [name]: data }))
    } catch (error) {
      setResults(prev => ({ ...prev, [name]: { error: error.message } }))
    }
    setLoading(prev => ({ ...prev, [name]: false }))
  }

  // API endpoints
  const apis = [
    { 
      name: 'Portfolio Overview',
      call: () => callApi('overview', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/overview`)
    },
    {
      name: 'Portfolio Factor Exposures',
      call: () => callApi('factorExposures', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`)
    },
    {
      name: 'Position Factor Exposures',
      call: () => callApi('positionFactors', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/positions/factor-exposures?limit=${CONFIG.positionFactorExposures.limit}`)
    },
    {
      name: 'Stress Test',
      call: () => callApi('stressTest', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/stress-test`)
    },
    {
      name: 'Diversification Score',
      call: () => callApi('diversification', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/diversification-score`)
    },
    {
      name: 'Correlation Matrix',
      call: () => callApi('correlation', `/api/proxy/api/v1/analytics/portfolio/${portfolioId}/correlation-matrix?lookback_days=${CONFIG.correlationMatrix.lookbackDays}`)
    }
  ]

  if (!portfolioId) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Analytics API Test Page</h1>
        <p className="text-gray-600 mb-8">Portfolio ID: {portfolioId}</p>
        
        <button 
          onClick={() => apis.forEach(api => api.call())}
          className="mb-8 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Test All APIs
        </button>

        {apis.map((api, index) => (
          <div key={index} className="mb-8 bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">{api.name}</h2>
              <button
                onClick={api.call}
                disabled={loading[api.name.toLowerCase().replace(/\s+/g, '')]}
                className="px-4 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                {loading[api.name.toLowerCase().replace(/\s+/g, '')] ? 'Loading...' : 'Test'}
              </button>
            </div>
            
            {results[api.name.toLowerCase().replace(/\s+/g, '')] && (
              <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-96 text-xs">
                {JSON.stringify(results[api.name.toLowerCase().replace(/\s+/g, '')], null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Step 2: Add Route (2 minutes)

That's it! The page is now available at `http://localhost:3005/test-api`

### Step 3: Test Flow (5 minutes)

1. Login at `http://localhost:3005/login`
2. Navigate to `http://localhost:3005/test-api`
3. Click "Test All APIs" or test individually

## Even Faster: Minimal Version (30 minutes)

### Super Minimal Test Script

Create `app/api-test/page.tsx`:

```tsx
'use client'
import { useEffect, useState } from 'react'

export default function ApiTest() {
  const [data, setData] = useState<any>({})
  
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    
    // Get portfolio ID then test all endpoints
    fetch('/api/proxy/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(r => r.json())
    .then(async ({ portfolio_id }) => {
      const endpoints = [
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/overview`,
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/factor-exposures`,
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/positions/factor-exposures`,
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/stress-test`,
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/diversification-score`,
        `/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/correlation-matrix`
      ]
      
      for (const endpoint of endpoints) {
        const res = await fetch(endpoint, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const json = await res.json()
        setData(prev => ({ ...prev, [endpoint]: json }))
      }
    })
  }, [])
  
  return <pre>{JSON.stringify(data, null, 2)}</pre>
}
```

## Fastest: Command Line Testing (5 minutes)

### Bash Script Version

Create `test-analytics.sh`:

```bash
#!/bin/bash

# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)

# Get portfolio ID
PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/me | jq -r .portfolio_id)

echo "Testing Analytics APIs for Portfolio: $PORTFOLIO_ID"
echo "================================="

# Test each endpoint
endpoints=(
  "overview"
  "factor-exposures"
  "positions/factor-exposures"
  "stress-test"
  "diversification-score"
  "correlation-matrix"
)

for endpoint in "${endpoints[@]}"; do
  echo -e "\n📊 Testing: $endpoint"
  curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/$endpoint" | jq '.'
  echo "---"
done
```

Run with: `chmod +x test-analytics.sh && ./test-analytics.sh`

## Instant Browser Console Testing (1 minute)

Open browser console after logging in and paste:

```javascript
// Run in browser console after login
const token = localStorage.getItem('access_token');
const testApis = async () => {
  const { portfolio_id } = await fetch('/api/proxy/api/v1/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.json());
  
  const apis = [
    'overview',
    'factor-exposures', 
    'positions/factor-exposures',
    'stress-test',
    'diversification-score',
    'correlation-matrix'
  ];
  
  for (const api of apis) {
    console.log(`\n📊 ${api}:`);
    const data = await fetch(`/api/proxy/api/v1/analytics/portfolio/${portfolio_id}/${api}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
    console.log(data);
  }
};
testApis();
```

## Quick Enhancement Options

### Add Basic Formatting (10 minutes)

Replace the JSON display with formatted cards:

```tsx
// In the results display section
{results.overview && (
  <div className="grid grid-cols-2 gap-4">
    <div className="p-4 bg-blue-50 rounded">
      <div className="text-sm text-gray-600">Total Value</div>
      <div className="text-2xl font-bold">
        ${results.overview.total_value?.toLocaleString()}
      </div>
    </div>
    <div className="p-4 bg-green-50 rounded">
      <div className="text-sm text-gray-600">Total P&L</div>
      <div className="text-2xl font-bold">
        ${results.overview.pnl?.total_pnl?.toLocaleString()}
      </div>
    </div>
  </div>
)}
```

### Add Export Button (5 minutes)

```tsx
const exportResults = () => {
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `api-test-${new Date().toISOString()}.json`
  a.click()
}

// Add button
<button onClick={exportResults} className="px-4 py-2 bg-gray-600 text-white rounded">
  Export Results
</button>
```

### Add Copy cURL (5 minutes)

```tsx
const copyCurl = (endpoint: string) => {
  const curl = `curl -H "Authorization: Bearer ${token}" "${window.location.origin}${endpoint}"`
  navigator.clipboard.writeText(curl)
  alert('Copied to clipboard!')
}

// Add button next to each test
<button onClick={() => copyCurl(`/api/proxy/api/v1/analytics/portfolio/${portfolioId}/overview`)}>
  Copy cURL
</button>
```

## Comparison

| Approach | Time | Complexity | Features |
|----------|------|------------|----------|
| Full TODO | 13-19 hours | High | Everything |
| Single File | 30 mins | Low | Basic UI + JSON |
| Minimal | 10 mins | Minimal | Just JSON |
| Bash Script | 5 mins | None | Terminal only |
| Console | 1 min | None | Browser console |

## Recommended: Start with Single File

1. Copy the single file solution
2. Test it works
3. Add enhancements as needed
4. Total time: 30-60 minutes

The single file solution gives you:
- ✅ Visual UI
- ✅ All 6 endpoints
- ✅ Individual or batch testing
- ✅ Raw JSON display
- ✅ Loading states
- ✅ Error handling
- ✅ No dependencies

Then enhance incrementally:
- Add formatting (10 mins)
- Add export (5 mins)
- Add cURL copy (5 mins)
- Add better visuals (20 mins)

Total: Under 2 hours for a fully functional test page!