import os


def _get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")


def _sqlite_db_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return "blood_pressure.db"


def migrate_sqlite(db_path: str):
    import sqlite3

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking 'users' table schema...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]

        if "language" not in columns:
            print("Adding 'language' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'th'")
            conn.commit()
            print("Migration successful: Added 'language' column.")
        else:
            print("'language' column already exists.")

        cursor.execute("PRAGMA table_info(payments)")
        if not cursor.fetchall():
            print("'payments' table missing. It should be created by app restart or payment migration.")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_audit_logs'")
        if not cursor.fetchone():
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
        else:
            print("'admin_audit_logs' table already exists.")

    except sqlite3.Error as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()


def migrate_postgres(database_url: str):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    engine = create_engine(database_url)

    with engine.connect() as conn:
        try:
            print("Checking 'users' table schema...")
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='language')"
            ))
            if not result.scalar():
                print("Adding 'language' column to 'users' table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'th'"))
                conn.commit()
                print("Migration successful: Added 'language' column.")
            else:
                print("'language' column already exists.")

            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='payments')"
            ))
            if not result.scalar():
                print("'payments' table missing. It should be created by app bootstrap or payment migration.")

            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='admin_audit_logs')"
            ))
            if not result.scalar():
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
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_id ON admin_audit_logs (id)"))
                conn.commit()
                print("Migration successful: Created 'admin_audit_logs' table.")
            else:
                print("'admin_audit_logs' table already exists.")
        except SQLAlchemyError as e:
            print(f"Migration error: {e}")


def migrate():
    database_url = _get_database_url()
    if database_url.startswith("postgresql"):
        migrate_postgres(database_url)
        return
    migrate_sqlite(_sqlite_db_path(database_url))

if __name__ == "__main__":
    migrate()
