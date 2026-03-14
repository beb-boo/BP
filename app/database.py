
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

import os
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Database setup
# Default to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blood_pressure.db")

# Vercel/Postgres fix: Vercel might give "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
