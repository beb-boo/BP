"""Migration: bring payments table up to the current model schema.

This migration is idempotent and supports both SQLite and PostgreSQL.
It safely upgrades legacy payment tables by adding all columns required by
the current Payment model and backfilling plan_amount from amount where
possible.

Usage:
    python -m migrations.add_payment_fields
    DATABASE_URL=postgresql://... python -m migrations.add_payment_fields
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


PAYMENT_COLUMNS = {
    "trans_ref_hash": "VARCHAR",
    "plan_amount": "FLOAT",
    "sending_bank": "VARCHAR",
    "sender_name_encrypted": "VARCHAR",
    "receiver_name": "VARCHAR",
    "trans_date": "VARCHAR",
    "trans_time": "VARCHAR",
    "error_code": "VARCHAR",
    "error_message": "VARCHAR",
    "verification_response": "TEXT",
}

POSTGRES_PAYMENT_COLUMNS = {
    "trans_ref_hash": "VARCHAR",
    "plan_amount": "DOUBLE PRECISION",
    "sending_bank": "VARCHAR",
    "sender_name_encrypted": "VARCHAR",
    "receiver_name": "VARCHAR",
    "trans_date": "VARCHAR",
    "trans_time": "VARCHAR",
    "error_code": "VARCHAR",
    "error_message": "VARCHAR",
    "verification_response": "TEXT",
}


def _sqlite_db_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return "blood_pressure.db"


def _create_payments_table_sqlite(cursor):
    print("Creating 'payments' table with current schema...")
    cursor.execute("""
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            trans_ref VARCHAR,
            trans_ref_hash VARCHAR,
            amount FLOAT,
            plan_type VARCHAR,
            plan_amount FLOAT,
            sending_bank VARCHAR,
            sender_name_encrypted VARCHAR,
            receiver_name VARCHAR,
            trans_date VARCHAR,
            trans_time VARCHAR,
            status VARCHAR DEFAULT 'pending',
            error_code VARCHAR,
            error_message VARCHAR,
            verification_response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            verified_at DATETIME
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_payments_trans_ref ON payments (trans_ref)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)")


def migrate_sqlite(db_path: str = "blood_pressure.db"):
    import sqlite3

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
        payments_exists = cursor.fetchone() is not None

        if not payments_exists:
            _create_payments_table_sqlite(cursor)
            conn.commit()
            print("Migration successful: Created 'payments' table with current schema.")
            return

        cursor.execute("PRAGMA table_info(payments)")
        columns = {row[1] for row in cursor.fetchall()}

        changed = False
        for column_name, column_type in PAYMENT_COLUMNS.items():
            if column_name in columns:
                continue
            print(f"Adding '{column_name}' column to payments...")
            cursor.execute(f"ALTER TABLE payments ADD COLUMN {column_name} {column_type}")
            changed = True

        print("Ensuring payment indexes exist...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_payments_trans_ref ON payments (trans_ref)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)")

        if "plan_amount" in PAYMENT_COLUMNS:
            cursor.execute(
                "UPDATE payments SET plan_amount = amount WHERE plan_amount IS NULL AND amount IS NOT NULL"
            )

        conn.commit()
        if changed:
            print("Migration successful: Updated 'payments' table to current schema.")
        else:
            print("'payments' table already matches current schema.")
    except sqlite3.Error as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()


def _create_payments_table_postgres(conn):
    from sqlalchemy import text

    print("Creating 'payments' table with current schema...")
    conn.execute(text("""
        CREATE TABLE payments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            trans_ref VARCHAR,
            trans_ref_hash VARCHAR,
            amount DOUBLE PRECISION,
            plan_type VARCHAR,
            plan_amount DOUBLE PRECISION,
            sending_bank VARCHAR,
            sender_name_encrypted VARCHAR,
            receiver_name VARCHAR,
            trans_date VARCHAR,
            trans_time VARCHAR,
            status VARCHAR DEFAULT 'pending',
            error_code VARCHAR,
            error_message VARCHAR,
            verification_response TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            verified_at TIMESTAMP
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_trans_ref ON payments (trans_ref)"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)"))


def migrate_postgres(database_url: str):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    engine = create_engine(database_url)

    with engine.connect() as conn:
        try:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='payments')"
            ))
            payments_exists = result.scalar()

            if not payments_exists:
                _create_payments_table_postgres(conn)
                conn.commit()
                print("Migration successful: Created 'payments' table with current schema.")
                return

            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='payments'"
            ))
            columns = {row[0] for row in result.fetchall()}

            changed = False
            for column_name, column_type in POSTGRES_PAYMENT_COLUMNS.items():
                if column_name in columns:
                    continue
                print(f"Adding '{column_name}' column to payments...")
                conn.execute(text(f"ALTER TABLE payments ADD COLUMN {column_name} {column_type}"))
                changed = True

            print("Ensuring payment indexes exist...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_trans_ref ON payments (trans_ref)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_trans_ref_hash ON payments (trans_ref_hash)"))
            conn.execute(text(
                "UPDATE payments SET plan_amount = amount WHERE plan_amount IS NULL AND amount IS NOT NULL"
            ))
            conn.commit()

            if changed:
                print("Migration successful: Updated 'payments' table to current schema.")
            else:
                print("'payments' table already matches current schema.")
        except SQLAlchemyError as e:
            print(f"Migration error: {e}")


def migrate():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")
    if database_url.startswith("postgresql"):
        migrate_postgres(database_url)
        return
    migrate_sqlite(_sqlite_db_path(database_url))


if __name__ == "__main__":
    migrate()