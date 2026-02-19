from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Optimized for Supabase Transaction Pooler (port 6543)
# Transaction pooler is stateless and handles connection pooling server-side
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=False,  # Disable for transaction pooler (server handles this)
    pool_recycle=300,  # Shorter recycle time for transaction pooler
    pool_size=5,  # Smaller pool size (transaction pooler handles scaling)
    max_overflow=10,  # Moderate overflow for transaction pooler
    pool_timeout=10,  # Fast timeout for transaction pooler
    echo=False,  # Disable SQL logging for performance
    future=True,  # Use SQLAlchemy 2.0 style
    connect_args={
        "connect_timeout": 3,  # Very fast connection timeout for pooler
        "application_name": "akbpo_backend",
        "options": "-c statement_timeout=30s"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
