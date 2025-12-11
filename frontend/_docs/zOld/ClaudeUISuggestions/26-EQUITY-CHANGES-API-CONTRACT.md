# Equity Changes API Contract (Draft v0.1)
**Created**: 2025-11-04  
**Owners**: Backend & Frontend teams  
**Related Plans**: 21-EQUITY-CHANGES-TRACKING-PLAN.md, 25-EQUITY-AND-PNL-EXECUTION-PLAN.md

---

## 1. Purpose
Define the REST contract for capital contribution and withdrawal tracking so frontend and backend can implement Phase 1 consistently. The API must support:
- Recording contributions and withdrawals (with backdated entries allowed)
- Editing/deleting entries within allowed windows
- Returning summaries for the Command Center hero metrics
- Exporting equity change history for download

---

## 2. Data Model (Server Response Shape)
```json
{
  "id": "4c1df1d9-1e6c-463a-9e92-4ef62f884a73",
  "portfolio_id": "d153e5a0-6d73-4d42-a3ad-4194fa2a07e4",
  "change_type": "CONTRIBUTION",
  "amount": 50000.0,
  "change_date": "2025-11-01",
  "notes": "Q4 capital call",
  "created_by_user_id": "b50a0d1a-5ba5-4cad-a656-c576f11b4f12",
  "created_at": "2025-11-01T18:34:12.713Z",
  "updated_at": "2025-11-01T18:34:12.713Z",
  "editable_until": "2025-11-08T18:34:12.713Z",
  "deletable_until": "2025-12-01T18:34:12.713Z",
  "is_deleted": false
}
```

### Field Notes
- `change_type`: enum `CONTRIBUTION` | `WITHDRAWAL`
- `amount`: positive Decimal(16,2); backend enforces withdrawal <= current equity
- `change_date`: `YYYY-MM-DD`, must be <= today (backdating allowed)
- `editable_until`: 7 calendar days after creation (server-calculated)
- `deletable_until`: 30 calendar days after creation (server-calculated)
- `is_deleted`: soft delete flag

---

## 3. Endpoints

### 3.1 Create Equity Change
- **POST** `/api/v1/portfolios/{portfolio_id}/equity-changes`
- **Request**
```json
{
  "change_type": "WITHDRAWAL",
  "amount": 25000.00,
  "change_date": "2025-10-28",
  "notes": "House down payment"
}
```
- **Responses**
  - `201 Created` → returns Equity Change object
  - `400 Bad Request` → validation error (e.g., amount <= 0, future date, withdrawal exceeds balance)
  - `403 Forbidden` → user lacks access to portfolio
  - `404 Not Found` → portfolio does not exist

### 3.2 List Equity Changes
- **GET** `/api/v1/portfolios/{portfolio_id}/equity-changes`
- **Query Parameters**  
  - `page` (default 1), `page_size` (default 25, max 100)
  - `start_date`, `end_date` (optional filters)
  - `include_deleted` (default false)
- **Response**
```json
{
  "items": [ { /* Equity Change */ }, ... ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_items": 12,
    "total_pages": 1
  }
}
```

### 3.3 Get Single Equity Change
- **GET** `/api/v1/portfolios/{portfolio_id}/equity-changes/{equity_change_id}`
- Returns single entry or `404` if not found / soft deleted (unless `include_deleted=true`).

### 3.4 Update Equity Change (within 7 days)
- **PUT** `/api/v1/portfolios/{portfolio_id}/equity-changes/{equity_change_id}`
- **Request**
```json
{
  "amount": 48000.00,
  "change_date": "2025-11-02",
  "notes": "Adjusted wiring amount"
}
```
- Only `amount`, `change_date`, and `notes` are mutable; `change_type` immutable.
- Backend enforces `now <= editable_until` (7-day window). Violations → `400` with error code `EQUITY_006`.

### 3.5 Delete Equity Change (soft delete)
- **DELETE** `/api/v1/portfolios/{portfolio_id}/equity-changes/{equity_change_id}`
- Permitted while `now <= deletable_until` (30-day window). Response `204 No Content`. Outside window → `400` (`EQUITY_007`). Already deleted → `409` (`EQUITY_009`).

### 3.6 Equity Summary (for Command Center)
- **GET** `/api/v1/portfolios/{portfolio_id}/equity-changes/summary`
- **Response**
```json
{
  "total_contributions": 125000.0,
  "total_withdrawals": 50000.0,
  "net_flow": 75000.0,
  "last_change": {
    "change_type": "CONTRIBUTION",
    "amount": 10000.0,
    "change_date": "2025-11-03"
  },
  "periods": {
    "30d": { "contributions": 25000.0, "withdrawals": 15000.0, "net_flow": 10000.0 },
    "90d": { "contributions": 50000.0, "withdrawals": 20000.0, "net_flow": 30000.0 }
  }
}
```
- Intended to power hero metrics + side panel overview.

### 3.7 Export Equity Changes
- **GET** `/api/v1/portfolios/{portfolio_id}/equity-changes/export`
- **Query Parameters**: `format=csv` (default), optional `start_date`, `end_date`
- Returns `text/csv` attachment (`filename=equity_changes_{portfolio_id}_{timestamp}.csv`).

---

## 4. Validation Rules
- `amount` > 0; backend rejects zero/negative.
- Withdrawals cannot exceed current equity (service performs check at change date).
- `change_date` cannot be in the future (UTC). Backdating allowed to any prior date.
- Edits allowed only within 7 calendar days (based on creation timestamp). Delete permitted within 30 days.
- Notes optional, max length 500 characters (trim server-side).
- Requests must originate from authenticated user with ownership of portfolio.

---

## 5. Error Codes (subset)
| Code | HTTP | Message | Notes |
|------|------|---------|-------|
| `EQUITY_001` | 400 | Amount must be greater than zero | amount <= 0 |
| `EQUITY_002` | 400 | Cannot record equity changes for future dates | change_date > today |
| `EQUITY_003` | 400 | Withdrawal amount cannot exceed current portfolio equity | includes current + pending flows |
| `EQUITY_006` | 400 | Equity changes can only be edited within 7 days of creation | edit window violation |
| `EQUITY_007` | 400 | Equity changes can only be deleted within 30 days of creation | delete window violation |
| `EQUITY_008` | 404 | Equity change not found | invalid id or already soft-deleted |
| `EQUITY_009` | 409 | This equity change has already been deleted | repeat delete |

---

## 6. Summary Calculations
- `net_flow = sum(contributions) - sum(withdrawals)` for requested range.
- Summary endpoint must accept optional `start_date`/`end_date` for future use (default to full history).
- Batch P&L calculator integrates capital flows as:  
  `new_equity = previous_equity + unrealized_pnl + realized_pnl + contributions - withdrawals`
- When backdating a change, calculator should adjust subsequent snapshots automatically (Phase 1 migration script may need to recalc historical equity).

---

## 7. Frontend Integration Notes
- Command Center hook (`useCommandCenterData`) will call:
  - `GET /equity-changes/summary` for hero metrics
  - `GET /equity-changes?page=1&page_size=5` for recent history
  - `POST/PUT/DELETE` from the new `ManageEquitySidePanel`
- Inline sell fix already in place; backend should ensure realized events + equity changes both flow into rollforward before executing Phase 1.
- Export button in side panel can hit `/export` endpoint and offer CSV download (client triggers file save).

---

## 8. Open Questions
- Should export include soft-deleted entries by default? (proposal: no; add `include_deleted=true` to override)
- Do we need bulk upload/import of historical flows? (out of scope for Phase 1)
- Time-zone handling for `change_date`? Current assumption: user-entered local date stored as naive date (UTC midnight). Confirm if we need time zone awareness.

---

## 9. Next Steps
1. Backend: implement migration, model, service, and endpoints adhering to contract.
2. Frontend: scaffold `equityChangeService` using these routes.
3. QA: create Postman collection / integration tests covering create → edit → delete, summary, and export scenarios.
4. Documentation: update API reference (`_docs/reference/API_REFERENCE_V1.4.6.md`) after implementation.

---

*Draft owner: Execution plan to be updated once contract is reviewed and signed off.*
