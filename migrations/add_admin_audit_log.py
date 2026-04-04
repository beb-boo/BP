"""Migration: Create admin_audit_logs table.

Run this script on production databases where AUTO_CREATE_TABLES is disabled.

Usage:
    python -m migrations.add_admin_audit_log
    # or with custom DB path:
    DATABASE_URL=postgresql://... python -m migrations.add_admin_audit_log
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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_audit_logs'")
        if cursor.fetchone():
            print("'admin_audit_logs' table already exists.")
            return

        print("Creating 'admin_audit_logs' table...")
        cursor.execute("""
            CREATE TABLE admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER NOT NULL REFERENCES users(id),
                action VARCHAR NOT NULL,
                target_user_id INTEGER REFERENCES users(id),
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX ix_admin_audit_logs_id ON admin_audit_logs (id)")
        conn.commit()
        print("Migration successful: Created 'admin_audit_logs' table.")

    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()


def migrate_postgres():
    """Run migration using SQLAlchemy for PostgreSQL."""
    from sqlalchemy import create_engine, text

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return

    engine = create_engine(database_url)

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'admin_audit_logs')"
        ))
        if result.scalar():
            print("'admin_audit_logs' table already exists.")
            return

        print("Creating 'admin_audit_logs' table...")
        conn.execute(text("""
            CREATE TABLE admin_audit_logs (
                id SERIAL PRIMARY KEY,
                admin_user_id INTEGER NOT NULL REFERENCES users(id),
                action VARCHAR NOT NULL,
                target_user_id INTEGER REFERENCES users(id),
                details TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX ix_admin_audit_logs_id ON admin_audit_logs (id)"))
        conn.commit()
        print("Migration successful: Created 'admin_audit_logs' table.")


def migrate():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql"):
        migrate_postgres()
    else:
        # Default to SQLite
        db_path = database_url.replace("sqlite:///", "").replace("./", "") if database_url else "blood_pressure.db"
        migrate_sqlite(db_path)


if __name__ == "__main__":
    migrate()
