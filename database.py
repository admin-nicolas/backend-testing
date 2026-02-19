from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Optimized for Supabase Direct Connection (IPv4)
# Direct connection requires more generous timeouts and connection management
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Enable for direct connection to check connection health
    pool_recycle=3600,  # Longer recycle time for direct connection (1 hour)
    pool_size=5,  # Moderate pool size
    max_overflow=10,  # Allow overflow connections
    pool_timeout=30,  # Longer timeout for direct connection
    echo=False,  # Disable SQL logging for performance
    future=True,  # Use SQLAlchemy 2.0 style
    connect_args={
        "connect_timeout": 10,  # Longer connection timeout for direct connection
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
