import sqlite3
import os

DB_PATH = "blood_pressure.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Checking 'users' table schema...")
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "language" not in columns:
            print("Adding 'language' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'th'")
            conn.commit()
            print("Migration successful: Added 'language' column.")
        else:
            print("'language' column already exists.")
            
        # Check Payment Table just in case (optional, SQLAlchemy handles this usually)
        cursor.execute("PRAGMA table_info(payments)")
        if not cursor.fetchall():
            print("'payments' table missing. It should be created by app restart.")

    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
