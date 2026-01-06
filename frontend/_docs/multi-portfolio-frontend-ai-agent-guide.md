# Multi-Portfolio Frontend Implementation Guide

**Purpose**: Concise reference for AI agents implementing multi-portfolio frontend features.

**Last Updated**: 2025-12-10

---

## Quick Reference

### Account Types (9 supported)
```typescript
type AccountType =
  | 'taxable'   // Standard brokerage
  | 'ira'       // Traditional IRA
  | 'roth_ira'  // Roth IRA
  | '401k'      // 401(k)
  | '403b'      // 403(b)
  | '529'       // Education savings
  | 'hsa'       // Health Savings Account
  | 'trust'     // Trust account
  | 'other';    // Other
```

### Key Endpoints

| Action | Method | Endpoint |
|--------|--------|----------|
| List portfolios | GET | `/api/v1/portfolios` |
| Create portfolio | POST | `/api/v1/portfolios` |
| Get portfolio | GET | `/api/v1/portfolios/{id}` |
| Update portfolio | PUT | `/api/v1/portfolios/{id}` |
| Delete portfolio | DELETE | `/api/v1/portfolios/{id}` |
| Create with CSV | POST | `/api/v1/onboarding/create-portfolio` |
| Trigger calculations | POST | `/api/v1/portfolios/{id}/calculate` |
| Poll batch status | GET | `/api/v1/portfolios/{id}/batch-status/{run_id}` |
| Aggregate overview | GET | `/api/v1/analytics/aggregate/overview` |
| Aggregate beta | GET | `/api/v1/analytics/aggregate/beta` |
| Aggregate volatility | GET | `/api/v1/analytics/aggregate/volatility` |
| Aggregate factors | GET | `/api/v1/analytics/aggregate/factor-exposures` |

---

## User Flow 1: First Portfolio (Onboarding)

### Sequence
```
Register → Login → Upload CSV → Trigger Calculations → Poll Status → Dashboard
```

### API Calls

**1. Register** (unauthenticated)
```typescript
POST /api/v1/onboarding/register
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"
}
// Returns: { user_id, email, full_name, message, next_step }
```

**2. Login**
```typescript
POST /api/v1/auth/login
{ "username": "user@example.com", "password": "SecurePass123" }
// Returns: { access_token, token_type }
// Store token in localStorage as 'access_token'
```

**3. Create Portfolio with CSV** (authenticated)
```typescript
POST /api/v1/onboarding/create-portfolio
Content-Type: multipart/form-data

FormData:
  portfolio_name: "My Investment Account"
  account_name: "Schwab Taxable"        // Must be unique per user
  account_type: "taxable"
  equity_balance: 150000.00
  description: "Main brokerage account" // Optional
  csv_file: [File]

// Returns:
{
  "portfolio_id": "uuid",
  "portfolio_name": "My Investment Account",
  "account_name": "Schwab Taxable",
  "account_type": "taxable",
  "equity_balance": 150000.00,
  "positions_imported": 25,
  "positions_failed": 0,
  "total_positions": 25,
  "message": "Portfolio created...",
  "next_step": { "action": "calculate", "endpoint": "..." }
}
```

**4. Trigger Calculations**
```typescript
POST /api/v1/portfolios/{portfolio_id}/calculate
// Returns:
{
  "portfolio_id": "uuid",
  "batch_run_id": "uuid",
  "status": "started",
  "message": "Batch calculations started..."
}
```

**5. Poll Status** (every 3 seconds)
```typescript
GET /api/v1/portfolios/{portfolio_id}/batch-status/{batch_run_id}
// Returns:
{
  "status": "running" | "completed" | "idle",
  "batch_run_id": "uuid",
  "portfolio_id": "uuid",
  "elapsed_seconds": 45
}
// When status === "completed", redirect to dashboard
```

### Frontend State Machine
```
idle → uploading → processing → completed → dashboard
                 ↘ validation_error → (show errors, retry)
                 ↘ processing_error → (show error, retry)
```

---

## User Flow 2: Adding Additional Portfolio

### When to Show "Add Portfolio"
```typescript
const portfolios = await apiClient.get('/api/v1/portfolios');
const canAddMore = true; // No limit on portfolios
```

### Sequence
```
Dashboard → "Add Portfolio" → Upload Form → Same as steps 3-5 above
```

### Validation
- `account_name` must be unique per user
- Backend returns `409 Conflict` if duplicate:
```json
{
  "error_code": "ERR_PORT_001",
  "message": "User already has portfolio with account_name 'Schwab Taxable'"
}
```

### UI Suggestion
Show existing account names to help user choose unique name:
```typescript
const existingNames = portfolios.map(p => p.account_name);
// Display: "Existing accounts: Schwab Taxable, Fidelity IRA"
```

---

## User Flow 3: Portfolio Switching & Aggregate View

### List All Portfolios
```typescript
GET /api/v1/portfolios?include_inactive=false
// Returns:
{
  "portfolios": [
    {
      "id": "uuid-1",
      "account_name": "Schwab Taxable",
      "account_type": "taxable",
      "net_asset_value": 500000.00,
      "position_count": 25,
      "is_active": true
    },
    {
      "id": "uuid-2",
      "account_name": "Fidelity IRA",
      "account_type": "ira",
      "net_asset_value": 300000.00,
      "position_count": 15,
      "is_active": true
    }
  ],
  "total_count": 2,
  "active_count": 2,
  "net_asset_value": 800000.00
}
```

### Progressive Disclosure Pattern
```typescript
const isSinglePortfolio = portfolios.length === 1;

if (isSinglePortfolio) {
  // Hide aggregate UI, show single portfolio view
  // Use existing single-portfolio endpoints
  return <SinglePortfolioView portfolioId={portfolios[0].id} />;
} else {
  // Show portfolio selector + aggregate view
  return <MultiPortfolioView portfolios={portfolios} />;
}
```

### Aggregate Analytics
```typescript
// Get household-level metrics
GET /api/v1/analytics/aggregate/overview
// Returns:
{
  "net_asset_value": 800000.00,
  "portfolio_count": 2,
  "portfolios": [
    { "id": "uuid-1", "account_name": "Schwab Taxable", "value": 500000, "weight": 0.625 },
    { "id": "uuid-2", "account_name": "Fidelity IRA", "value": 300000, "weight": 0.375 }
  ]
}

// Get weighted beta
GET /api/v1/analytics/aggregate/beta
// Returns:
{
  "aggregate_beta": 1.04,
  "portfolios": [
    { "portfolio_id": "uuid-1", "beta": 1.20, "weight": 0.625, "contribution": 0.75 },
    { "portfolio_id": "uuid-2", "beta": 0.80, "weight": 0.375, "contribution": 0.30 }
  ],
  "formula": "Σ(Beta_i × Weight_i)"
}
```

### Filter Specific Portfolios
```typescript
// Aggregate only selected portfolios
GET /api/v1/analytics/aggregate/beta?portfolio_ids=uuid-1&portfolio_ids=uuid-2
```

---

## User Flow 4: Delete Portfolio

### Rules
- Cannot delete last active portfolio
- Soft delete (preserves data, sets `deleted_at`)

### API Call
```typescript
DELETE /api/v1/portfolios/{portfolio_id}
// Success:
{ "success": true, "message": "Portfolio soft deleted successfully", "deleted_at": "..." }

// Error (last portfolio):
{ "detail": "Cannot delete the last active portfolio. Create another portfolio first." }
```

### UI Pattern
```typescript
const canDelete = portfolios.filter(p => p.is_active).length > 1;
// Disable delete button if canDelete === false
// Show tooltip: "You must have at least one portfolio"
```

---

## State Management

### Zustand Store Updates

Current `portfolioStore.ts` stores single `portfolioId`. For multi-portfolio:

```typescript
// Option A: Keep single "active" portfolio (simpler)
interface PortfolioStore {
  portfolioId: string | null;           // Currently selected
  portfolios: Portfolio[];              // All user portfolios
  setPortfolioId: (id: string) => void;
  setPortfolios: (portfolios: Portfolio[]) => void;
  clearPortfolio: () => void;
}

// Option B: Add aggregate mode flag
interface PortfolioStore {
  portfolioId: string | null;           // Selected portfolio (null = aggregate)
  portfolios: Portfolio[];
  viewMode: 'single' | 'aggregate';
  setViewMode: (mode: 'single' | 'aggregate') => void;
}
```

### Portfolio Resolution on Login
```typescript
// After login, fetch all portfolios
const { portfolios } = await apiClient.get('/api/v1/portfolios');

if (portfolios.length === 0) {
  // New user - redirect to onboarding
  router.push('/onboarding/upload');
} else if (portfolios.length === 1) {
  // Single portfolio - auto-select
  setPortfolioId(portfolios[0].id);
  router.push('/portfolio');
} else {
  // Multiple portfolios - show selector or aggregate
  setPortfolios(portfolios);
  router.push('/portfolio'); // With portfolio picker
}
```

---

## Component Patterns

### Portfolio Selector Dropdown
```tsx
<Select value={portfolioId} onValueChange={setPortfolioId}>
  <SelectTrigger>
    <SelectValue placeholder="Select account" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="aggregate">All Accounts (Aggregate)</SelectItem>
    <SelectSeparator />
    {portfolios.map(p => (
      <SelectItem key={p.id} value={p.id}>
        {p.account_name} ({p.account_type}) - ${p.net_asset_value.toLocaleString()}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

### Account Type Badge
```tsx
const accountTypeLabels: Record<string, string> = {
  taxable: 'Taxable',
  ira: 'IRA',
  roth_ira: 'Roth IRA',
  '401k': '401(k)',
  '403b': '403(b)',
  '529': '529',
  hsa: 'HSA',
  trust: 'Trust',
  other: 'Other'
};

<Badge variant="outline">{accountTypeLabels[portfolio.account_type]}</Badge>
```

### Portfolio Weight Chart
```tsx
// Pie chart data from aggregate/breakdown
const chartData = portfolios.map(p => ({
  name: p.account_name,
  value: p.weight * 100,
  fill: getColorForAccountType(p.account_type)
}));
```

---

## Error Handling

### Common Errors

| Error Code | HTTP | Meaning | UI Action |
|------------|------|---------|-----------|
| ERR_PORT_001 | 409 | Duplicate account_name | Show inline error, suggest unique name |
| ERR_PORT_009 | 400 | Invalid account_type | Show dropdown with valid options |
| ERR_CSV_* | 400 | CSV validation failed | Show row-by-row errors |
| 404 | 404 | Portfolio not found | Redirect to portfolio list |

### Example Error Response
```json
{
  "error_code": "ERR_PORT_001",
  "message": "User already has portfolio with account_name 'Schwab Taxable'",
  "details": {
    "field": "account_name",
    "existing_value": "Schwab Taxable"
  }
}
```

---

## Testing Checklist

- [ ] Create first portfolio (new user flow)
- [ ] Create second portfolio (existing user)
- [ ] Verify unique account_name validation
- [ ] Switch between portfolios
- [ ] View aggregate analytics with 2+ portfolios
- [ ] Delete portfolio (non-last)
- [ ] Attempt delete last portfolio (should fail)
- [ ] Single portfolio hides aggregate UI
- [ ] Weekend upload uses Friday's date (handled by backend)

---

## Files to Modify

| File | Changes |
|------|---------|
| `stores/portfolioStore.ts` | Add `portfolios` array, `viewMode` |
| `services/portfolioService.ts` | Add `listPortfolios()`, `deletePortfolio()` |
| `services/analyticsApi.ts` | Add aggregate endpoint methods |
| `hooks/usePortfolios.ts` | New hook for multi-portfolio state |
| `components/navigation/PortfolioSelector.tsx` | New component |
| `app/portfolio/page.tsx` | Add portfolio selector, conditional aggregate view |
| `containers/OnboardingContainer.tsx` | Add account_name, account_type fields |

---

## Related Documentation

- Backend API: `backend/_docs/MULTI_PORTFOLIO_API_REFERENCE.md`
- Onboarding PRD: `frontend/_docs/ONBOARDING_FLOW_PRD.md`
- Services Reference: `frontend/_docs/requirements/07-Services-Reference.md`
