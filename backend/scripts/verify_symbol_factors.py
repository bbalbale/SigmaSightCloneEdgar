"""Verify symbol factors were stored correctly."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from sqlalchemy import create_engine, text

sync_url = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
engine = create_engine(sync_url)

print("=" * 60)
print("VERIFYING SYMBOL FACTOR DATA")
print("=" * 60)

with engine.connect() as conn:
    # Count symbols in universe
    result = conn.execute(text("SELECT COUNT(*) FROM symbol_universe"))
    print(f"\nSymbols in universe: {result.fetchone()[0]}")

    # Count factor exposures
    result = conn.execute(text("SELECT COUNT(*) FROM symbol_factor_exposures"))
    print(f"Total factor exposure records: {result.fetchone()[0]}")

    # Count by method
    result = conn.execute(text("""
        SELECT calculation_method, COUNT(*)
        FROM symbol_factor_exposures
        GROUP BY calculation_method
    """))
    print("\nRecords by calculation method:")
    for row in result.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Count by date
    result = conn.execute(text("""
        SELECT calculation_date, calculation_method, COUNT(DISTINCT symbol) as symbols, COUNT(*) as records
        FROM symbol_factor_exposures
        GROUP BY calculation_date, calculation_method
        ORDER BY calculation_date DESC
        LIMIT 5
    """))
    print("\nRecent calculation dates:")
    for row in result.fetchall():
        print(f"  {row[0]} ({row[1]}): {row[2]} symbols, {row[3]} records")

    # Sample some betas
    result = conn.execute(text("""
        SELECT sfe.symbol, fd.name, sfe.beta_value, sfe.r_squared, sfe.calculation_method
        FROM symbol_factor_exposures sfe
        JOIN factor_definitions fd ON sfe.factor_id = fd.id
        ORDER BY sfe.created_at DESC
        LIMIT 15
    """))
    print("\nSample factor betas (most recent):")
    for row in result.fetchall():
        print(f"  {row[0]:6} | {row[1]:20} | beta={float(row[2]):8.4f} | R2={float(row[3]) if row[3] else 0:.4f} | {row[4]}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
