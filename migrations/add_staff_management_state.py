"""Migration: create staff_management_states table for env-managed staff sync.

This table is intentionally separate from users so deploys remain compatible
even when code ships before migrations are applied.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _sqlite_db_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return "blood_pressure.db"


def migrate_sqlite(db_path: str = "blood_pressure.db"):
    import sqlite3

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='staff_management_states'"
        )
        if cursor.fetchone():
            print("'staff_management_states' table already exists.")
            return

        print("Creating 'staff_management_states' table...")
        cursor.execute(
            """
            CREATE TABLE staff_management_states (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                management_source VARCHAR NOT NULL DEFAULT 'env',
                original_role VARCHAR NOT NULL,
                last_sync_action VARCHAR,
                last_synced_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_staff_management_states_management_source ON staff_management_states (management_source)"
        )
        conn.commit()
        print("Migration successful: Created 'staff_management_states' table.")
    except sqlite3.Error as exc:
        print(f"Migration error: {exc}")
    finally:
        conn.close()


def migrate_postgres(database_url: str):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    engine = create_engine(database_url)
    with engine.connect() as conn:
        try:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='staff_management_states')"
                )
            )
            if result.scalar():
                print("'staff_management_states' table already exists.")
                return

            print("Creating 'staff_management_states' table...")
            conn.execute(
                text(
                    """
                    CREATE TABLE staff_management_states (
                        user_id INTEGER PRIMARY KEY REFERENCES users(id),
                        management_source VARCHAR NOT NULL DEFAULT 'env',
                        original_role VARCHAR NOT NULL,
                        last_sync_action VARCHAR,
                        last_synced_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_staff_management_states_management_source ON staff_management_states (management_source)"
                )
            )
            conn.commit()
            print("Migration successful: Created 'staff_management_states' table.")
        except SQLAlchemyError as exc:
            print(f"Migration error: {exc}")


def migrate():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")
    if database_url.startswith("postgresql"):
        migrate_postgres(database_url)
        return
    migrate_sqlite(_sqlite_db_path(database_url))


if __name__ == "__main__":
    migrate()