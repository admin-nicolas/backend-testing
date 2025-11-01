"""
Script to drop and recreate all tables.
WARNING: This will delete all existing data!
"""
from database import engine, Base
from models import Lead

def reset_database():
    try:
        print("WARNING: This will delete all existing data!")
        confirm = input("Type 'yes' to continue: ")
        
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            return False
        
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✓ Database reset successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    reset_database()
