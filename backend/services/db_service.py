import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load .env from the backend directory specifically
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(dotenv_path=env_path)

# Fallback to local SQLite if DATABASE_URL is missing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./requify_pro.db")

# Fix for Render/PostgreSQL URLs (replace postgres:// with postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Azure PostgreSQL aggressively drops idle connections. We MUST include pool_recycle and pool_pre_ping.
engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600,      # Recycle connections every hour
    pool_pre_ping=True,     # Ping DB before executing to handle dropped connections safely
    pool_size=20,           # Max connections in the pool
    max_overflow=10         # Max connections allowed above pool_size
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper to ensure tables exist
def init_db():
    Base.metadata.create_all(bind=engine)
