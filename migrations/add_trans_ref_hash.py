"""Migration: Add trans_ref_hash column to payments table.

Run this script on databases created before payment_service.py introduced
duplicate-detection via hashed transaction references.

Usage:
    python -m migrations.add_trans_ref_hash
    # or with custom DB:
    DATABASE_URL=postgresql://... python -m migrations.add_trans_ref_hash
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def migrate_sqlite(db_path: str = "blood_pressure.db"):
    import sqlite3

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(payments)")
        columns = [row[1] for row in cursor.fetchall()]

        if "trans_ref_hash" in columns:
            print("Column 'trans_ref_hash' already exists in payments. Nothing to do.")
            return

        print("Adding 'trans_ref_hash' column to payments...")
        cursor.execute("ALTER TABLE payments ADD COLUMN trans_ref_hash VARCHAR")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)")
        conn.commit()
        print("Migration successful: Added 'trans_ref_hash' to payments.")

    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()


def migrate_postgres():
    from sqlalchemy import create_engine, text

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return

    engine = create_engine(database_url)

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name='payments' AND column_name='trans_ref_hash')"
        ))
        if result.scalar():
            print("Column 'trans_ref_hash' already exists in payments. Nothing to do.")
            return

        print("Adding 'trans_ref_hash' column to payments...")
        conn.execute(text("ALTER TABLE payments ADD COLUMN trans_ref_hash VARCHAR"))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)"
        ))
        conn.commit()
        print("Migration successful: Added 'trans_ref_hash' to payments.")


def migrate():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql"):
        migrate_postgres()
    else:
        db_path = database_url.replace("sqlite:///", "").replace("./", "") if database_url else "blood_pressure.db"
        migrate_sqlite(db_path)


if __name__ == "__main__":
    migrate()
