"""
Database Migration: push_subscriptions table + users.notification_preferences
==============================================================================
Adds Web Push subscription storage (PWA Sprint 2) and the JSONB
notification preferences column on users (PWA_SPEC D3).

Usage:
    python3 -m migrations.add_push_subscriptions
    python3 -m migrations.add_push_subscriptions --rollback

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


def _column_exists(conn, is_sqlite: bool, table: str, column: str) -> bool:
    if is_sqlite:
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        return column in [row[1] for row in result.fetchall()]
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def _table_exists(conn, is_sqlite: bool, table: str) -> bool:
    if is_sqlite:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:t"
        ), {"t": table})
    else:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name=:t"
        ), {"t": table})
    return result.fetchone() is not None


def migrate():
    """Create push_subscriptions and add users.notification_preferences."""
    database_url = get_database_url()
    is_sqlite = "sqlite" in database_url
    print("Connecting to database...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # 1. push_subscriptions table
        if _table_exists(conn, is_sqlite, "push_subscriptions"):
            print("Table 'push_subscriptions' already exists. Skipping.")
        else:
            print("Creating 'push_subscriptions' table...")
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE push_subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        endpoint VARCHAR(500) NOT NULL UNIQUE,
                        p256dh VARCHAR(255) NOT NULL,
                        auth VARCHAR(255) NOT NULL,
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used_at TIMESTAMP,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE push_subscriptions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        endpoint VARCHAR(500) NOT NULL UNIQUE,
                        p256dh VARCHAR(255) NOT NULL,
                        auth VARCHAR(255) NOT NULL,
                        user_agent VARCHAR(500),
                        created_at TIMESTAMPTZ DEFAULT now(),
                        last_used_at TIMESTAMPTZ,
                        is_active BOOLEAN NOT NULL DEFAULT true
                    )
                """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user_id "
                "ON push_subscriptions (user_id)"
            ))

        # 2. users.notification_preferences (JSONB on PG, TEXT on SQLite)
        if _column_exists(conn, is_sqlite, "users", "notification_preferences"):
            print("Column 'notification_preferences' already exists. Skipping.")
        else:
            print("Adding 'notification_preferences' column to users...")
            if is_sqlite:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN notification_preferences "
                    "TEXT NOT NULL DEFAULT '{}'"
                ))
            else:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN notification_preferences "
                    "JSONB NOT NULL DEFAULT '{}'::jsonb"
                ))

        conn.commit()
        print("Migration completed successfully!")


def rollback():
    """Drop push_subscriptions and remove notification_preferences."""
    database_url = get_database_url()
    is_sqlite = "sqlite" in database_url
    print("Connecting to database for rollback...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        print("Dropping 'push_subscriptions' table...")
        conn.execute(text("DROP TABLE IF EXISTS push_subscriptions"))

        if is_sqlite:
            print("SQLite does not support DROP COLUMN directly.")
            print("'notification_preferences' column is left in place (harmless).")
        else:
            print("Removing 'notification_preferences' column from users...")
            conn.execute(text(
                "ALTER TABLE users DROP COLUMN IF EXISTS notification_preferences"
            ))

        conn.commit()
        print("Rollback completed successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database migration for push subscriptions")
    parser.add_argument("--rollback", action="store_true",
                        help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
