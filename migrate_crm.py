"""
Migration script to add ClosedDeal table to the database
"""
from database import engine, Base
from models import ClosedDeal
import sys

def migrate():
    try:
        print("🔄 Creating ClosedDeal table...")
        Base.metadata.create_all(bind=engine, tables=[ClosedDeal.__table__])
        print("✅ ClosedDeal table created successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
