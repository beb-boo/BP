"""
Database Migration: Add timezone column to users table
======================================================
Run this script to add the timezone column for existing databases.

Usage:
    python3 -m migrations.add_timezone_column

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

    # Try to construct from individual variables
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "blood_db")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")

    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Default to SQLite for development
    return "sqlite:///./blood_pressure.db"

def migrate():
    """Add timezone column to users table"""
    database_url = get_database_url()
    print(f"Connecting to database...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if column already exists
        if "sqlite" in database_url:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = "timezone" in columns
        else:
            # PostgreSQL
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'timezone'
            """))
            column_exists = result.fetchone() is not None

        if column_exists:
            print("Column 'timezone' already exists in users table. Skipping migration.")
            return

        # Add the column
        print("Adding 'timezone' column to users table...")

        if "sqlite" in database_url:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Bangkok'
            """))
        else:
            # PostgreSQL
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Bangkok'
            """))

        conn.commit()
        print("Migration completed successfully!")
        print("Default timezone set to 'Asia/Bangkok' for all existing users.")

def rollback():
    """Remove timezone column (for rollback if needed)"""
    database_url = get_database_url()
    print(f"Connecting to database for rollback...")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        if "sqlite" in database_url:
            print("SQLite does not support DROP COLUMN directly.")
            print("To rollback, you'll need to recreate the table without the timezone column.")
            return

        print("Removing 'timezone' column from users table...")
        conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS timezone"))
        conn.commit()
        print("Rollback completed successfully!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for timezone column")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
