from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Serverless-optimised for Vercel + Supabase pooler (port 6543)
# Low pool_size prevents connection exhaustion when many Vercel instances run concurrently
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # Drop stale connections before use
    pool_recycle=300,       # 5 min — short recycle suits serverless lifetimes
    pool_size=2,            # 2 per instance; Vercel spins many instances
    max_overflow=5,         # Max 7 total per instance
    pool_timeout=30,        # Wait up to 30s to acquire a connection
    echo=False,
    future=True,
    connect_args={
        "connect_timeout": 10,
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
