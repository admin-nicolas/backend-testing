"""
Script to initialize the database and create tables.
Run this separately to test database connection.
"""
from database import engine, Base
from models import Lead

def init_database():
    try:
        print("Connecting to database...")
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    init_database()
