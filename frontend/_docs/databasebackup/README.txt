================================================================================
SigmaSight Database Backup System
================================================================================

PURPOSE:
  Backup local Docker PostgreSQL database for Railway restore

LOCATION:
  D:\SigmaSight_Backups\

BACKUP TYPES:
  1. FULL BACKUP (full\ directory)
     - Complete database dump (all 32 tables, all data)
     - Size: ~1.5 MB
     - Use for: Complete database restore to Railway

  2. CRITICAL TABLES (critical\ directory)
     - Core tables only: users, portfolios, positions, position_tags, tags_v2
     - Size: ~44 KB
     - Use for: Selective restore after schema changes

================================================================================
HOW TO CREATE BACKUP
================================================================================

OPTION 1: Run the backup script (easiest)
  Double-click:  backup_local_database.bat

OPTION 2: Manual backup
  Full:
    docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db > full\backup_TIMESTAMP.sql

  Critical:
    docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db -t users -t portfolios -t positions -t position_tags -t tags_v2 > critical\critical_TIMESTAMP.sql

================================================================================
HOW TO RESTORE TO RAILWAY (For AI Agents)
================================================================================

See RESTORE_INSTRUCTIONS.md for complete details.

QUICK RESTORE:
  1. Navigate to backup directory
     cd D:\SigmaSight_Backups\full

  2. Restore to Railway
     type backup_20251008_HHMMSS.sql | railway run psql $DATABASE_URL

VERIFY RESTORE:
  python C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend\scripts\railway\audit_railway_data.py

================================================================================
BACKUP VERIFICATION
================================================================================

Latest backups contain:
  - 32 database tables (CREATE TABLE statements)
  - 32 data sections (COPY public statements)
  - Users, portfolios, positions, tags, and all calculation data

Verified tables include:
  ✓ users
  ✓ portfolios
  ✓ positions
  ✓ position_tags
  ✓ tags_v2
  ✓ company_profiles
  ✓ historical_prices
  ✓ portfolio_snapshots
  ✓ position_greeks
  ✓ position_factor_exposures
  ✓ correlation_calculations
  ✓ ... and 21 more tables

================================================================================
IMPORTANT NOTES
================================================================================

1. ALWAYS backup before running Alembic migrations
2. Full backup includes schema + data
3. Critical backup is data-only for 5 core tables
4. Backups are NOT tracked in git
5. See RESTORE_INSTRUCTIONS.md for Railway restore process
6. Railway database URL: Get via `railway variables --json`

================================================================================
FILES IN THIS DIRECTORY
================================================================================

backup_local_database.bat   - Automated backup script (run this!)
RESTORE_INSTRUCTIONS.md      - Complete restore guide for AI agents
README.txt                   - This file
full\                        - Full database backups (~1.5 MB each)
critical\                    - Critical tables backups (~44 KB each)

================================================================================
DEMO ACCOUNTS (After Restore)
================================================================================

Email: demo_individual@sigmasight.com
Email: demo_hnw@sigmasight.com
Email: demo_hedgefundstyle@sigmasight.com
Password (all): demo12345

================================================================================
CREATED: 2025-10-08
PROJECT: SigmaSight Backend
