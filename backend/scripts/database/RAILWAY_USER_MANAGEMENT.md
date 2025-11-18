# Railway User Management Guide

Two simple scripts for managing users on Railway:
1. **`list_users.py`** - View users (safe, read-only)
2. **`delete_users.py`** - Delete users (destructive)

---

## 1. View Users (Safe - Read Only)

### List All Users
```bash
cd backend
railway run python scripts/database/list_users.py
```

**Example Output:**
```
================================================================================
DATABASE USER SUMMARY
================================================================================
Total Users: 5
  - Demo Users: 3
  - Test Users: 2
================================================================================

================================================================================
DEMO USERS (3):
================================================================================

📧 demo_individual@sigmasight.com
   ID: 123e4567-e89b-12d3-a456-426614174000
   Name: Demo Individual
   Portfolios: 1
   Created: 2025-01-15 10:30:00

📧 demo_hnw@sigmasight.com
   ID: 223e4567-e89b-12d3-a456-426614174001
   Name: Demo HNW
   Portfolios: 1
   Created: 2025-01-15 10:30:00

📧 demo_hedgefundstyle@sigmasight.com
   ID: 323e4567-e89b-12d3-a456-426614174002
   Name: Demo Hedge Fund
   Portfolios: 1
   Created: 2025-01-15 10:30:00

================================================================================
TEST USERS (2):
================================================================================

📧 test@example.com
   ID: 423e4567-e89b-12d3-a456-426614174003
   Name: Test User
   Portfolios: 2
   Created: 2025-01-16 14:20:00

📧 another_test@example.com
   ID: 523e4567-e89b-12d3-a456-426614174004
   Name: Another Test
   Portfolios: 0
   Created: 2025-01-16 15:45:00

================================================================================
Total: 5 user(s)
================================================================================
```

### Quick Summary Only
```bash
railway run python scripts/database/list_users.py --summary
```

**Example Output:**
```
================================================================================
DATABASE USER SUMMARY
================================================================================
Total Users: 5
  - Demo Users: 3
  - Test Users: 2
================================================================================
```

---

## 2. Delete Users (Destructive - Use Carefully)

⚠️ **ALWAYS run `list_users.py` first to see what users exist!**

⚠️ **Each user must be identified and deleted individually - no bulk deletion**

### Delete a Specific User
```bash
cd backend
railway run python scripts/database/delete_users.py --email test@example.com
```

**Example Output:**
```
================================================================================
USER TO DELETE:
================================================================================
Email: test@example.com
ID: 423e4567-e89b-12d3-a456-426614174003
Name: Test User
Portfolios: 2
Created: 2025-01-16 14:20:00
================================================================================

⚠️  This will permanently delete:
   - The user account
   - 2 portfolio(s)
   - All positions, calculations, and related data

Type 'DELETE' to confirm deletion: DELETE

✅ Successfully deleted user: test@example.com
   - Deleted 2 portfolio(s) and all associated data
```

### Skip Confirmation (Use with Caution!)
```bash
# Delete specific user without confirmation
railway run python scripts/database/delete_users.py --email test@example.com --confirm
```

---

## Recommended Workflow

### Step 1: See what's in the database
```bash
cd backend
railway run python scripts/database/list_users.py
```

### Step 2: Delete specific users as needed (one at a time)
```bash
# Delete first user
railway run python scripts/database/delete_users.py --email test1@example.com

# Delete second user
railway run python scripts/database/delete_users.py --email test2@example.com

# Continue for each user you want to remove...
```

### Step 3: Verify deletion
```bash
railway run python scripts/database/list_users.py
```

---

## Important Notes

### Individual Deletion Only
Each user must be explicitly identified by email and deleted individually. There is no bulk deletion to prevent accidental data loss.

### Cascading Deletes
When you delete a user, the database automatically deletes:
- All portfolios owned by that user
- All positions in those portfolios
- All calculations, target prices, tags, and other related data

### Confirmation Requirements
By default, the delete script requires explicit confirmation:
- **Single user**: Type `DELETE` to confirm
- **All test users**: Type `DELETE ALL` to confirm
- Use `--confirm` flag to skip prompts (automation only)

### Railway Context
The `railway run` command automatically uses your Railway database connection. No need to change environment variables or connection strings.

---

## Quick Reference

| Command | What It Does |
|---------|-------------|
| `railway run python scripts/database/list_users.py` | View all users (safe) |
| `railway run python scripts/database/list_users.py --summary` | Show counts only (safe) |
| `railway run python scripts/database/delete_users.py --email <email>` | Delete one user |
| `railway run python scripts/database/delete_users.py --email <email> --confirm` | Delete without prompt |

---

## If Something Goes Wrong

If you accidentally delete a demo user or need to restore the database to a clean state:

```bash
cd backend
railway run npm run trigger:railway:fix
```

This triggers the Railway data fix workflow which reseeds demo data and repairs any data quality issues.
