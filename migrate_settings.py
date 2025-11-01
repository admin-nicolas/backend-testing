"""
Migration script to add global settings table to the database
"""
from database import engine, Base
from models import GlobalSettings
import sys

def migrate():
    try:
        print("Creating global_settings table...")
        Base.metadata.create_all(bind=engine, tables=[GlobalSettings.__table__])
        print("✓ Global settings table created successfully!")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
