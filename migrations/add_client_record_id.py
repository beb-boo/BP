"""
Database Migration: client_record_id on blood_pressure_records
===============================================================
Idempotency key for offline-first BP entry (PWA Sprint 3, PWA_SPEC §7.3).
Clients send a UUID per submission; retries return the existing record
instead of creating duplicates.

Usage:
    python3 -m migrations.add_client_record_id
    python3 -m migrations.add_client_record_id --rollback

Note: This is a manual migration since Alembic is not configured.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def get_database_url():
    """Get database URL from environment"""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "blood_db")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")

    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return "sqlite:///./blood_pressure.db"


def migrate():
    """Add client_record_id column + partial unique index."""
    database_url = get_database_url()
    is_sqlite = "sqlite" in database_url
    print("Connecting to database...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(blood_pressure_records)"))
            column_exists = "client_record_id" in [row[1] for row in result.fetchall()]
        else:
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'blood_pressure_records'
                  AND column_name = 'client_record_id'
            """))
            column_exists = result.fetchone() is not None

        if column_exists:
            print("Column 'client_record_id' already exists. Skipping column add.")
        else:
            print("Adding 'client_record_id' column to blood_pressure_records...")
            # Stored as 36-char string — works on both SQLite and PG; the
            # app generates/validates UUIDs, no native uuid type needed.
            conn.execute(text(
                "ALTER TABLE blood_pressure_records "
                "ADD COLUMN client_record_id VARCHAR(36) NULL"
            ))

        # Partial unique index (both SQLite and PG support WHERE clauses).
        print("Ensuring partial unique index on client_record_id...")
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_bp_records_client_record_id "
            "ON blood_pressure_records (client_record_id) "
            "WHERE client_record_id IS NOT NULL"
        ))

        conn.commit()
        print("Migration completed successfully!")


def rollback():
    """Remove index and column."""
    database_url = get_database_url()
    is_sqlite = "sqlite" in database_url
    print("Connecting to database for rollback...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        print("Dropping index...")
        conn.execute(text("DROP INDEX IF EXISTS uq_bp_records_client_record_id"))

        if is_sqlite:
            print("SQLite does not support DROP COLUMN directly.")
            print("'client_record_id' column is left in place (harmless).")
        else:
            print("Removing 'client_record_id' column...")
            conn.execute(text(
                "ALTER TABLE blood_pressure_records "
                "DROP COLUMN IF EXISTS client_record_id"
            ))

        conn.commit()
        print("Rollback completed successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database migration for client_record_id idempotency key")
    parser.add_argument("--rollback", action="store_true",
                        help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
