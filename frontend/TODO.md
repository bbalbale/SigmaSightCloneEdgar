# Frontend TODO: Portfolio Data Integration (Revised)

> **Last Updated**: 2025-08-31
> **Critical Context**: Backend is only 23% implemented - most endpoints return TODO stubs
> **Revised Strategy**: Create minimal backend bridge endpoint + use existing working endpoints

## 🚨 Reality Check

### What Actually Works in Backend
- ✅ `/api/v1/auth/login` - Authentication
- ✅ `/api/v1/data/portfolios` - List portfolios  
- ✅ `/api/v1/data/portfolio/{id}/complete` - Full portfolio data
- ✅ `/api/v1/data/positions/details` - Position details
- ❌ **77% of endpoints** - Return `{"message": "TODO: Implement..."}`

### Why Previous Attempts Failed
1. **Sonnet tried**: Building file server in Next.js → Path resolution nightmares
2. **Opus assumed**: Using existing backend APIs → Most don't exist
3. **Root cause**: Documentation claimed "100% complete" but reality is 23%

## 🎯 Pragmatic Solution: Two-Path Strategy

### Path A: Create ONE Backend Bridge Endpoint (Recommended)
**Time**: 1 hour | **Complexity**: Low | **Success Rate**: High

```python
# backend/app/api/v1/data/demo.py (NEW FILE)
from fastapi import APIRouter, HTTPException
import json
import csv
from pathlib import Path

router = APIRouter()

@router.get("/demo/{portfolio_type}")
async def get_demo_portfolio(portfolio_type: str):
    """
    Temporary bridge endpoint that reads from report files
    Maps: individual | high-net-worth | hedge-fund
    """
    folder_map = {
        'individual': 'demo-individual-investor-portfolio_2025-08-23',
        'high-net-worth': 'demo-high-net-worth-portfolio_2025-08-23',
        'hedge-fund': 'demo-hedge-fund-style-investor-portfolio_2025-08-23'
    }
    
    if portfolio_type not in folder_map:
        raise HTTPException(status_code=404, detail="Portfolio type not found")
    
    folder_name = folder_map[portfolio_type]
    base_path = Path(__file__).parent.parent.parent.parent.parent / "reports" / folder_name
    
    # Read JSON for exposures
    json_path = base_path / "portfolio_report.json"
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Read CSV for positions
    csv_path = base_path / "portfolio_report.csv"
    positions = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        positions = list(reader)
    
    return {
        "portfolio_info": json_data["portfolio_info"],
        "exposures": json_data["calculation_engines"]["position_exposures"]["data"],
        "snapshot": json_data["calculation_engines"]["portfolio_snapshot"]["data"],
        "positions": positions
    }
```

**Frontend Integration**:
```typescript
// Simple, clean, no file path issues
const response = await fetch(`http://localhost:8000/api/v1/data/demo/${portfolioType}`)
const data = await response.json()
```

### Path B: Use Existing Working Endpoints (Complex)
**Time**: 3-4 hours | **Complexity**: High | **Success Rate**: Medium

Problems with this approach:
- Need to map portfolio types → UUID database IDs
- Must handle authentication (JWT tokens)
- Data structure doesn't match UI needs well
- Requires multiple API calls to assemble full picture

## 📋 Revised Implementation Plan

### Phase 1: Backend Bridge (30 minutes)
- [ ] Create `/api/v1/data/demo.py` endpoint
- [ ] Test with curl/Postman
- [ ] Add to backend router
- [ ] Verify CORS allows frontend access

### Phase 2: Frontend Integration (2 hours)
- [ ] Update PortfolioSelectionDialog to pass type in URL
- [ ] Create simple data service to fetch from bridge endpoint
- [ ] Transform data to match existing UI structure
- [ ] Replace dummy data in portfolio page

### Phase 3: Testing (30 minutes)
- [ ] Test all three portfolio types
- [ ] Verify data displays correctly
- [ ] Handle loading and error states

## 🚀 Immediate Action Items

### Step 1: Create Backend Bridge Endpoint
```bash
cd backend
# Create new file: app/api/v1/data/demo.py
# Add router to app/api/v1/data/__init__.py
uvicorn app.main:app --reload
```

### Step 2: Test Backend Endpoint
```bash
curl http://localhost:8000/api/v1/data/demo/individual
curl http://localhost:8000/api/v1/data/demo/high-net-worth
curl http://localhost:8000/api/v1/data/demo/hedge-fund
```

### Step 3: Update Frontend
```typescript
// src/services/portfolioDataService.ts
export async function loadPortfolioData(portfolioType: string) {
  const response = await fetch(`http://localhost:8000/api/v1/data/demo/${portfolioType}`)
  if (!response.ok) throw new Error('Failed to load portfolio')
  
  const data = await response.json()
  
  // Transform to UI format
  return {
    exposures: transformExposures(data.exposures),
    positions: transformPositions(data.positions),
    info: data.portfolio_info
  }
}
```

## ✅ Success Criteria
- [ ] Portfolio selection dialog navigates with type parameter
- [ ] Backend bridge endpoint returns data for all 3 portfolios
- [ ] Frontend displays real data instead of dummy data
- [ ] No file path resolution issues
- [ ] Single endpoint to maintain (easy to swap later)

## 🎯 Why This Will Work
1. **Python handles file paths better** than Node.js on Windows
2. **Single endpoint** to debug (not distributed logic)
3. **Backend already has** the file access it needs
4. **When backend improves**, swap implementation inside endpoint
5. **LLM agents** can use same endpoint

## ⚠️ What NOT To Do
- ❌ Don't build file servers in Next.js
- ❌ Don't try to use non-existent backend endpoints
- ❌ Don't parse CSVs in the frontend
- ❌ Don't hardcode absolute Windows paths
- ❌ Don't create complex multi-endpoint orchestration

## 📊 Risk Assessment
- **Path resolution issues**: Eliminated (Python backend handles it)
- **CORS problems**: Minimal (backend already configured)
- **Data transformation**: Simple (one place, Python)
- **Future migration**: Easy (change endpoint implementation)
- **LLM compatibility**: Built-in (same API for all consumers)

---

**Note**: This approach acknowledges the backend's incomplete state and works around it pragmatically. When the backend is fully implemented, we can swap the bridge endpoint's internals without changing the frontend.