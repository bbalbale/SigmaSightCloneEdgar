# Test User Creation - Implementation Plan

**Last Updated:** 2025-10-13
**Status:** Planning Phase
**Owner:** Frontend + Backend Teams

---

## 📋 Executive Summary

Two approaches for implementing test user creation with portfolio upload:

1. **File-Based Approach (Quick Testing)** - 2.5 hours, local dev only
2. **Backend API Approach (Production Ready)** - 5-6 hours, full-featured

Both approaches reuse existing `seed_demo_portfolios.py` logic. File-based enables immediate testing; API provides long-term solution.

---

# Option 1: File-Based Approach (Quick Testing)

## 🎯 Overview
Frontend generates JSON file → User places in `backend/test_users/` → User runs Python script → Database populated

**Best For:** Immediate local testing needs
**Timeline:** 2.5 hours
**Deployment:** Local development only

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│   Frontend  │ ───> │  JSON File   │ ───> │   Python    │ ───> │ Database │
│    Form     │      │   Download   │      │   Script    │      │          │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────┘
```

---

## 📝 Implementation Details

### **1. JSON File Structure**

```json
{
  "email": "test.user@example.com",
  "full_name": "Test User",
  "username": "test.user",
  "password": "password123",
  "strategy": "Test portfolio for development",
  "portfolio": {
    "name": "Test User Portfolio",
    "description": "Uploaded test portfolio",
    "total_value": 100000,  // USER-PROVIDED: Total equity value of the portfolio
    "positions": [
      {
        "symbol": "AAPL",
        "quantity": 100,
        "entry_price": 150.00,
        "entry_date": "2024-01-15",
        "tags": ["Tech", "Growth"]
      },
      {
        "symbol": "GOOGL",
        "quantity": 50,
        "entry_price": 140.00,
        "entry_date": "2024-01-20",
        "tags": ["Tech"]
      }
    ]
  }
}
```

### **2. Portfolio CSV Format**

User uploads CSV with this structure:

```csv
symbol,quantity,entry_price,entry_date,tags
AAPL,100,150.00,2024-01-15,"Tech,Growth"
GOOGL,50,140.00,2024-01-20,Tech
MSFT,75,380.00,2024-02-01,"Tech,Core Holdings"
```

### **3. Frontend Changes**

**File:** `frontend/src/containers/TestUserCreationContainer.tsx`

```typescript
// Add utility to parse CSV
const parsePortfolioCSV = (file: File): Promise<Position[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const csv = e.target?.result as string
      const lines = csv.split('\n')
      const headers = lines[0].split(',')

      const positions = lines.slice(1)
        .filter(line => line.trim())
        .map(line => {
          const values = line.split(',')
          return {
            symbol: values[0].trim(),
            quantity: parseFloat(values[1]),
            entry_price: parseFloat(values[2]),
            entry_date: values[3].trim(),
            tags: values[4] ? values[4].replace(/"/g, '').split(',').map(t => t.trim()) : []
          }
        })

      resolve(positions)
    }
    reader.onerror = reject
    reader.readAsText(file)
  })
}

// Add state for equity value
const [equityValue, setEquityValue] = useState<number>(0)

// Update handleSubmit
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  setError(null)
  setIsLoading(true)

  try {
    // Validate equity value
    if (!equityValue || equityValue <= 0) {
      setError('Please enter a valid equity value')
      return
    }

    // Parse CSV
    const positions = await parsePortfolioCSV(portfolioFile)

    // Create JSON structure
    const testUserData = {
      email,
      full_name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      username: email.split('@')[0],
      password,
      strategy: "Test portfolio for development",
      portfolio: {
        name: `${email} Portfolio`,
        description: "Uploaded test portfolio",
        total_value: equityValue,  // USER-PROVIDED: Not calculated from positions
        positions: positions.map(pos => ({
          symbol: pos.symbol,
          quantity: pos.quantity,
          entry_price: pos.entry_price,
          entry_date: pos.entry_date,
          tags: pos.tags
        }))
      }
    }

    // Generate filename with timestamp
    const timestamp = Date.now()
    const filename = `test_user_${timestamp}.json`

    // Download JSON file
    const blob = new Blob([JSON.stringify(testUserData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)

    // Show success with instructions
    setSuccess(true)
    setInstructions(`
      1. Place ${filename} in: backend/test_users/
      2. Run: cd backend && uv run python scripts/load_test_user.py
      3. Login with: ${email} / ${password}
    `)

  } catch (err: any) {
    setError(err?.message || 'Failed to generate test user file')
  } finally {
    setIsLoading(false)
  }
}
```

**Add form field for equity value:**

```typescript
// In the form JSX (add before portfolio file upload):
<div className="space-y-2">
  <label htmlFor="equityValue" className="text-sm font-medium">
    Portfolio Equity Value ($)
  </label>
  <input
    id="equityValue"
    type="number"
    min="0"
    step="0.01"
    value={equityValue}
    onChange={(e) => setEquityValue(parseFloat(e.target.value))}
    className="w-full px-3 py-2 border rounded-md"
    placeholder="100000.00"
    required
  />
  <p className="text-xs text-gray-500">
    Enter the total equity value of the portfolio
  </p>
</div>

// In success state UI:
const [instructions, setInstructions] = useState<string | null>(null)

{success && (
  <Alert>
    <AlertDescription className="whitespace-pre-line">
      <strong>Test User File Downloaded!</strong>
      {instructions}
    </AlertDescription>
  </Alert>
)}
```

### **4. Backend Script**

**File:** `backend/scripts/load_test_user.py`

```python
"""
Load Test User Script - File-Based Approach
Reads JSON files from test_users/ directory and creates users + portfolios
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import get_async_session
from app.core.logging import setup_logging, get_logger
from app.core.auth import get_password_hash
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from sqlalchemy import select

setup_logging()
logger = get_logger(__name__)

async def load_test_users():
    """
    Load test users from JSON files in test_users/ directory
    """
    test_users_dir = Path("test_users")

    if not test_users_dir.exists():
        logger.error("❌ test_users/ directory not found. Please create it.")
        return

    json_files = list(test_users_dir.glob("*.json"))

    if not json_files:
        logger.info("📭 No test user files found in test_users/")
        return

    logger.info(f"📁 Found {len(json_files)} test user file(s) to process")

    async with get_async_session() as db:
        for json_file in json_files:
            try:
                logger.info(f"📄 Processing {json_file.name}...")

                # Load JSON data
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # 1. Check if user already exists
                stmt = select(User).where(User.email == data['email'])
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    logger.warning(f"⚠️  User {data['email']} already exists. Skipping.")
                    json_file.rename(json_file.with_suffix('.skipped'))
                    continue

                # 2. Create user
                user = User(
                    email=data['email'],
                    full_name=data['full_name'],
                    hashed_password=get_password_hash(data['password']),
                    is_active=True,
                    is_admin=False
                )
                db.add(user)
                await db.flush()  # Get user ID

                logger.info(f"✅ Created user: {user.email}")

                # 3. Create portfolio
                portfolio_data = data['portfolio']
                portfolio = Portfolio(
                    user_id=user.id,
                    name=portfolio_data['name'],
                    description=portfolio_data.get('description', ''),
                    equity_balance=Decimal(str(portfolio_data['total_value']))
                )
                db.add(portfolio)
                await db.flush()  # Get portfolio ID

                logger.info(f"✅ Created portfolio: {portfolio.name}")

                # 4. Create positions
                positions_created = 0
                for pos_data in portfolio_data['positions']:
                    position = Position(
                        portfolio_id=portfolio.id,
                        symbol=pos_data['symbol'],
                        position_type=PositionType.LONG,  # Default to LONG
                        quantity=Decimal(str(pos_data['quantity'])),
                        entry_price=Decimal(str(pos_data['entry_price'])),
                        entry_date=date.fromisoformat(pos_data['entry_date']),
                        current_price=Decimal(str(pos_data['entry_price'])),  # Initialize with entry price
                        investment_class='Equity'  # Default
                    )
                    db.add(position)
                    positions_created += 1

                await db.commit()

                logger.info(f"✅ Created {positions_created} positions")
                logger.info(f"🎉 Test user {data['email']} loaded successfully!")

                # Mark file as processed
                json_file.rename(json_file.with_suffix('.processed'))

            except Exception as e:
                await db.rollback()
                logger.error(f"❌ Failed to process {json_file.name}: {e}")
                json_file.rename(json_file.with_suffix('.failed'))
                continue

if __name__ == "__main__":
    logger.info("🚀 Starting Test User Loader...")
    asyncio.run(load_test_users())
    logger.info("✅ Test User Loader completed")
```

### **5. Directory Setup**

**File:** `backend/test_users/README.md`

```markdown
# Test Users Directory

Place test user JSON files here and run:

```bash
cd backend
uv run python scripts/load_test_user.py
```

## File Format

See: `frontend/app/test-user-creation/TEST_USER_CREATION_PLAN.md`

## File Lifecycle

- `*.json` - New files to process
- `*.processed` - Successfully loaded
- `*.skipped` - User already exists
- `*.failed` - Processing error
```

**File:** `backend/test_users/.gitignore`

```
*.json
!.gitignore
!README.md
```

---

## 🔄 User Workflow

1. User fills form at `/test-user-creation`
2. Uploads portfolio CSV file
3. Frontend generates JSON and downloads it
4. User places `test_user_<timestamp>.json` in `backend/test_users/`
5. User runs: `cd backend && uv run python scripts/load_test_user.py`
6. Script creates user + portfolio + positions
7. User logs in with test credentials

---

## ✅ Advantages

- ✅ **Fast to implement** - 2.5 hours
- ✅ **Reuses existing code** - 100% seed logic
- ✅ **No backend API needed** - Just file + script
- ✅ **Simple debugging** - Direct database access
- ✅ **No security concerns** - Local only

## ⚠️ Limitations

- ⚠️ **Manual steps** - User must place file + run script
- ⚠️ **Local only** - Won't work in cloud
- ⚠️ **No real-time feedback** - Errors surface during script run
- ⚠️ **Not user-friendly** - Requires command line

---

## 📊 Estimated Effort

| Task | Time |
|------|------|
| Frontend CSV parser + JSON generator | 30 min |
| Backend load script | 1 hour |
| Directory setup + README | 15 min |
| Testing | 30 min |
| **Total** | **2.5 hours** |

---

# Option 2: Backend API Approach (Production Ready)

## 🎯 Overview
Frontend uploads file directly → Backend API endpoint → Parses + validates → Database populated → Returns result

**Best For:** Production deployment, better UX
**Timeline:** 5-6 hours
**Deployment:** Works everywhere (local, cloud, Railway, etc.)

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│   Frontend  │ ───> │  Backend API │ ───> │  Validation │ ───> │ Database │
│    Form     │      │   Endpoint   │      │  & Parser   │      │          │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────┘
                            │
                            └───> Rate Limiting, Security, Logging
```

---

## 📡 API Endpoint

### **POST /api/v1/test-users/create**

**Request (multipart/form-data):**
```
email: string (required)
password: string (required, min 8 chars)
equity_value: number (required, positive)
portfolio_file: File (required, CSV/JSON/Excel, max 5MB)
```

**Success Response (200):**
```json
{
  "success": true,
  "user_id": "uuid-here",
  "portfolio_id": "uuid-here",
  "message": "Test user created successfully",
  "credentials": {
    "email": "test@example.com",
    "password": "password123"
  },
  "positions_created": 15,
  "total_value": 125000.00
}
```

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Email already exists",
  "details": "test@example.com is already registered"
}
```

---

## 📝 Implementation Details

### **1. API Route Handler**

**File:** `backend/app/api/v1/test_users.py`

```python
"""
Test User API Endpoints
Handles test user creation with portfolio upload
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database import get_async_session
from app.services.test_user_service import TestUserService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/test-users", tags=["test-users"])

@router.post("/create")
async def create_test_user(
    email: str = Form(...),
    password: str = Form(...),
    equity_value: float = Form(...),
    portfolio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Create a test user with portfolio from uploaded file

    Args:
        email: User email (must be unique)
        password: User password (min 8 characters)
        equity_value: Total equity value of the portfolio (user-provided)
        portfolio_file: Portfolio file (CSV, JSON, or Excel)

    Returns:
        Dictionary with user_id, portfolio_id, and credentials

    Raises:
        HTTPException: If validation fails or user exists
    """
    logger.info(f"📥 Test user creation request for: {email}")

    # Validate inputs
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    if equity_value <= 0:
        raise HTTPException(
            status_code=400,
            detail="Equity value must be positive"
        )

    try:
        # Create service instance
        service = TestUserService(db)

        # Parse portfolio file
        positions = await service.parse_portfolio_file(portfolio_file)

        if not positions:
            raise HTTPException(
                status_code=400,
                detail="Portfolio file is empty or invalid"
            )

        # Create user and portfolio
        result = await service.create_test_user(
            email=email,
            password=password,
            equity_value=equity_value,
            positions=positions
        )

        logger.info(f"✅ Test user created: {email}")
        return result

    except ValueError as e:
        # Validation errors
        logger.warning(f"⚠️  Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Unexpected errors
        logger.error(f"❌ Test user creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create test user. Please try again."
        )
```

### **2. Service Layer**

**File:** `backend/app/services/test_user_service.py`

```python
"""
Test User Service
Business logic for test user creation
"""
import csv
import json
import pandas as pd
from io import StringIO, BytesIO
from typing import List, Dict, Any
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.core.auth import get_password_hash
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from fastapi import UploadFile

logger = get_logger(__name__)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_POSITIONS = 100
ALLOWED_EXTENSIONS = {'.csv', '.json', '.xlsx', '.xls'}

class TestUserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def parse_portfolio_file(self, file: UploadFile) -> List[Dict]:
        """
        Parse uploaded portfolio file into position data

        Supports CSV, JSON, and Excel formats
        """
        # Read and validate file
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large (max 5MB)")

        # Check file extension
        from pathlib import Path
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {ext}")

        # Parse based on format
        if ext == '.csv':
            return self._parse_csv(content)
        elif ext == '.json':
            return self._parse_json(content)
        elif ext in ('.xlsx', '.xls'):
            return self._parse_excel(content)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _parse_csv(self, content: bytes) -> List[Dict]:
        """Parse CSV portfolio file"""
        csv_data = StringIO(content.decode('utf-8'))
        reader = csv.DictReader(csv_data)

        positions = []
        for row in reader:
            if not row.get('symbol'):
                continue  # Skip empty rows

            position = {
                "symbol": row["symbol"].strip().upper(),
                "quantity": Decimal(row["quantity"]),
                "entry_price": Decimal(row["entry_price"]),
                "entry_date": date.fromisoformat(row["entry_date"]),
                "tags": [t.strip() for t in row.get("tags", "").split(",")] if row.get("tags") else []
            }

            positions.append(self._validate_position(position))

        return positions

    def _parse_json(self, content: bytes) -> List[Dict]:
        """Parse JSON portfolio file"""
        data = json.loads(content.decode('utf-8'))

        # Handle both direct array and nested structure
        positions_data = data if isinstance(data, list) else data.get("positions", [])

        positions = []
        for pos in positions_data:
            position = {
                "symbol": pos["symbol"].strip().upper(),
                "quantity": Decimal(str(pos["quantity"])),
                "entry_price": Decimal(str(pos["entry_price"])),
                "entry_date": date.fromisoformat(pos["entry_date"]),
                "tags": pos.get("tags", [])
            }

            positions.append(self._validate_position(position))

        return positions

    def _parse_excel(self, content: bytes) -> List[Dict]:
        """Parse Excel portfolio file"""
        df = pd.read_excel(BytesIO(content))

        # Check required columns
        required = ['symbol', 'quantity', 'entry_price', 'entry_date']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        positions = []
        for _, row in df.iterrows():
            if pd.isna(row['symbol']):
                continue  # Skip empty rows

            position = {
                "symbol": str(row["symbol"]).strip().upper(),
                "quantity": Decimal(str(row["quantity"])),
                "entry_price": Decimal(str(row["entry_price"])),
                "entry_date": row["entry_date"].date() if hasattr(row["entry_date"], 'date') else date.fromisoformat(str(row["entry_date"])),
                "tags": [t.strip() for t in str(row.get("tags", "")).split(",")] if pd.notna(row.get("tags")) else []
            }

            positions.append(self._validate_position(position))

        return positions

    def _validate_position(self, pos: Dict) -> Dict:
        """Validate and enrich position data"""
        import re

        # Validate symbol
        if not re.match(r'^[A-Z_]{1,20}$', pos['symbol']):
            raise ValueError(f"Invalid symbol: {pos['symbol']}")

        # Validate quantity (can be negative for shorts)
        if pos['quantity'] == 0:
            raise ValueError(f"Quantity cannot be zero for {pos['symbol']}")

        # Validate price (must be positive)
        if pos['entry_price'] <= 0:
            raise ValueError(f"Price must be positive for {pos['symbol']}")

        # Validate date (not in future)
        if pos['entry_date'] > date.today():
            raise ValueError(f"Entry date cannot be in the future for {pos['symbol']}")

        # Auto-determine position type
        pos['position_type'] = PositionType.SHORT if pos['quantity'] < 0 else PositionType.LONG

        return pos

    async def create_test_user(
        self,
        email: str,
        password: str,
        equity_value: float,
        positions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create test user and portfolio using existing seed logic

        Args:
            email: User email
            password: User password
            equity_value: Total equity value of the portfolio (user-provided)
            positions: List of position dictionaries

        Returns:
            Dictionary with creation results
        """
        # Validate position count
        if len(positions) > MAX_POSITIONS:
            raise ValueError(f"Too many positions (max {MAX_POSITIONS})")

        if len(positions) == 0:
            raise ValueError("Portfolio must have at least 1 position")

        # Validate equity value
        if equity_value <= 0:
            raise ValueError("Equity value must be positive")

        try:
            # Check if user exists
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise ValueError(f"Email already exists: {email}")

            # 1. Create user
            user = User(
                email=email,
                full_name=email.split('@')[0].replace('.', ' ').replace('_', ' ').title(),
                hashed_password=get_password_hash(password),
                is_active=True,
                is_admin=False
            )
            self.db.add(user)
            await self.db.flush()  # Get user ID

            logger.info(f"✅ Created user: {user.email}")

            # 2. Create portfolio
            portfolio = Portfolio(
                user_id=user.id,
                name=f"{user.full_name} Test Portfolio",
                description="Test portfolio created via upload",
                equity_balance=Decimal(str(equity_value))  # USER-PROVIDED: Not calculated
            )
            self.db.add(portfolio)
            await self.db.flush()  # Get portfolio ID

            logger.info(f"✅ Created portfolio: {portfolio.name}")

            # 3. Create positions
            for pos_data in positions:
                position = Position(
                    portfolio_id=portfolio.id,
                    symbol=pos_data['symbol'],
                    position_type=pos_data['position_type'],
                    quantity=abs(pos_data['quantity']),  # Store as positive
                    entry_price=pos_data['entry_price'],
                    entry_date=pos_data['entry_date'],
                    current_price=pos_data['entry_price'],  # Initialize with entry price
                    investment_class='Equity'  # Default
                )
                self.db.add(position)

            # Commit transaction
            await self.db.commit()

            logger.info(f"✅ Created {len(positions)} positions")

            return {
                "success": True,
                "user_id": str(user.id),
                "portfolio_id": str(portfolio.id),
                "message": "Test user created successfully",
                "credentials": {
                    "email": email,
                    "password": password
                },
                "positions_created": len(positions),
                "equity_value": float(equity_value)  # USER-PROVIDED
            }

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"❌ Database integrity error: {e}")
            raise ValueError("Email already exists")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Test user creation failed: {e}")
            raise
```

### **3. Router Integration**

**File:** `backend/app/api/v1/router.py` (update)

```python
from app.api.v1 import test_users

# Add to router includes
api_router.include_router(test_users.router)
```

### **4. Frontend Integration**

**File:** `frontend/src/containers/TestUserCreationContainer.tsx` (update)

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  setError(null)
  setIsLoading(true)

  try {
    // Validate password match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate file
    if (!portfolioFile) {
      setError('Please upload a portfolio file')
      return
    }

    // Create FormData for file upload
    const formData = new FormData()
    formData.append('email', email)
    formData.append('password', password)
    formData.append('equity_value', equityValue.toString())
    formData.append('portfolio_file', portfolioFile)

    // Call backend API
    const response = await fetch('/api/proxy/api/v1/test-users/create', {
      method: 'POST',
      body: formData
    })

    const result = await response.json()

    if (!response.ok) {
      throw new Error(result.detail || result.error || 'Failed to create test user')
    }

    console.log('✅ Test user created:', result)

    setSuccess(true)

    // Redirect to login after 2 seconds
    setTimeout(() => {
      router.push('/login')
    }, 2000)

  } catch (err: any) {
    console.error('❌ Test user creation error:', err)
    setError(err?.message || 'Failed to create test user. Please try again.')
  } finally {
    setIsLoading(false)
  }
}
```

### **5. Security Features**

**Rate Limiting (Optional):**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/create")
@limiter.limit("5/hour")  # Max 5 test users per hour per IP
async def create_test_user(...):
    ...
```

## 🔄 User Workflow

1. User fills form at `/test-user-creation`
2. Uploads portfolio CSV/JSON/Excel file
3. Clicks "Create Test User"
4. Frontend sends request to `/api/v1/test-users/create`
5. Backend validates + creates user + portfolio + positions
6. Returns success response
7. Frontend shows success message
8. User redirected to login automatically

---

## ✅ Advantages

- ✅ **Seamless UX** - No manual steps
- ✅ **Immediate feedback** - Real-time validation
- ✅ **Cloud-ready** - Works in any deployment
- ✅ **Secure** - Rate limiting, validation
- ✅ **Testable** - Unit + integration tests
- ✅ **Auditable** - Full logging
- ✅ **Reusable** - Other services can call API

## ⚠️ Considerations

- ⚠️ **More complex** - More code to maintain
- ⚠️ **Longer implementation** - 5-6 hours
- ⚠️ **Requires testing** - Unit + integration tests
- ⚠️ **API versioning** - Need to maintain API contract

---

## 📊 Estimated Effort

| Task | Time |
|------|------|
| API endpoint | 1 hour |
| Service layer (parsers, validation) | 2 hours |
| Frontend integration | 1 hour |
| Security features | 1 hour |
| Testing (unit + integration) | 1 hour |
| **Total** | **6 hours** |

---

# 📊 Comparison Matrix

| Feature | File-Based | Backend API |
|---------|------------|-------------|
| **Implementation Time** | 2.5 hours | 6 hours |
| **User Experience** | Manual steps | Seamless |
| **Real-time Validation** | ❌ No | ✅ Yes |
| **Cloud Deployment** | ❌ Local only | ✅ Works everywhere |
| **Security** | N/A (local) | ✅ Rate limiting, validation |
| **Error Handling** | Script errors | ✅ Structured API responses |
| **Testing** | Manual | ✅ Automated |
| **Maintenance** | Low | Medium |
| **Production Ready** | ❌ No | ✅ Yes |
| **Immediate Testing** | ✅ Yes | ✅ Yes |

---

# 🎯 Recommendation

## **For Immediate Testing Needs:**
→ **Start with File-Based Approach**
- Get testing capability **today** (2.5 hours)
- No backend API complexity
- Perfect for local development

## **For Long-Term/Production:**
→ **Build Backend API**
- Professional UX
- Cloud-ready
- Secure and maintainable

## **Hybrid Approach:**
1. **Week 1:** Implement file-based (2.5 hours) → Start testing
2. **Week 2:** Build backend API (6 hours) → Deploy to production
3. Both reuse same core logic → Easy transition

---

# 📁 File Structure

## File-Based Approach
```
frontend/
├── src/containers/TestUserCreationContainer.tsx (update)
└── src/utils/csvParser.ts (new)

backend/
├── test_users/ (new directory)
│   ├── .gitignore
│   └── README.md
└── scripts/
    └── load_test_user.py (new)
```

## Backend API Approach
```
frontend/
└── src/containers/TestUserCreationContainer.tsx (update)

backend/
├── app/
│   ├── api/v1/
│   │   ├── test_users.py (new)
│   │   └── router.py (update)
│   │
│   └── services/
│       └── test_user_service.py (new)
│
└── tests/
    └── test_test_user_service.py (new)
```

---

# 📚 Sample Portfolio Files

## CSV Format
```csv
symbol,quantity,entry_price,entry_date,tags
AAPL,100,150.00,2024-01-15,"Tech,Growth"
GOOGL,50,140.00,2024-01-20,Tech
MSFT,75,380.00,2024-02-01,"Tech,Core Holdings"
TSLA,25,250.00,2024-02-05,"Tech,Speculative"
SPY,200,450.00,2024-01-10,"Index,Core"
```

## JSON Format
```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "entry_price": 150.00,
      "entry_date": "2024-01-15",
      "tags": ["Tech", "Growth"]
    },
    {
      "symbol": "GOOGL",
      "quantity": 50,
      "entry_price": 140.00,
      "entry_date": "2024-01-20",
      "tags": ["Tech"]
    }
  ]
}
```

---

# 🧪 Testing Plan

## File-Based Testing
1. Generate test JSON with valid data
2. Place in `backend/test_users/`
3. Run script and verify user created
4. Test login with credentials
5. Verify portfolio data in database

## API Testing
1. Unit tests for parsers (CSV, JSON, Excel)
2. Unit tests for validation
3. Integration test for endpoint
4. Test error cases (invalid file, duplicate email)
5. Test file size limits
6. Test with real frontend form

---

# 🔐 Security Considerations

## File-Based
- ✅ No network exposure
- ✅ Local files only
- ✅ No authentication needed
- ⚠️ Manual password handling

## Backend API
- ✅ Rate limiting (5 test users/hour)
- ✅ File size limits (5MB)
- ✅ Input validation
- ✅ SQL injection protection (SQLAlchemy)
- ✅ No email enumeration (generic errors)
- ⚠️ Consider CAPTCHA for production
- ⚠️ Consider email domain restrictions

---

# 📞 Next Steps

## To Proceed with File-Based:
1. Review this plan
2. Implement frontend JSON generator (30 min)
3. Create backend load script (1 hour)
4. Test with sample portfolio (30 min)
5. Start using for testing

## To Proceed with Backend API:
1. Review this plan
2. Backend team implements API endpoint + service (3 hours)
3. Frontend team updates form submission (1 hour)
4. Write tests (1 hour)
5. Deploy and test

---

**Questions? Contact the team lead or update this document with findings.**
