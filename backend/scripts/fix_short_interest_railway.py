"""Fix Short Interest factor on Railway database"""
from sqlalchemy import create_engine, text

RAILWAY_DB_URL = "postgresql://postgres:cnNQyUbDSRMlcokGDMRgXsBusLXgQwhb@hopper.proxy.rlwy.net:56725/railway"

def main():
    engine = create_engine(RAILWAY_DB_URL)

    with engine.begin() as conn:
        # Check current status
        result = conn.execute(text(
            "SELECT name, is_active, factor_type FROM factor_definitions WHERE name = 'Short Interest'"
        ))
        row = result.fetchone()

        if row:
            print(f"Before: Short Interest - is_active={row[1]}, factor_type={row[2]}")

            # Update to inactive
            conn.execute(text(
                "UPDATE factor_definitions SET is_active = FALSE, updated_at = NOW() WHERE name = 'Short Interest'"
            ))

            # Verify
            result2 = conn.execute(text(
                "SELECT name, is_active FROM factor_definitions WHERE name = 'Short Interest'"
            ))
            row2 = result2.fetchone()
            print(f"After: Short Interest - is_active={row2[1]}")
            print("Success! Short Interest factor set to inactive on Railway.")
        else:
            print("Error: Short Interest factor not found in Railway database.")

if __name__ == "__main__":
    main()
