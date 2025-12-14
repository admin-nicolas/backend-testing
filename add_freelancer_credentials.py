#!/usr/bin/env python3
"""
Migration script to add FreelancerCredentials table
Run this script to update your database with the new table
"""

from sqlalchemy import create_engine, text
from database import DATABASE_URL, Base
from models import FreelancerCredentials
import os

def add_freelancer_credentials_table():
    """Add the FreelancerCredentials table to the database"""
    
    print("🔄 Adding FreelancerCredentials table...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    try:
        # Create the new table
        FreelancerCredentials.__table__.create(engine, checkfirst=True)
        print("✅ FreelancerCredentials table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    
    if add_freelancer_credentials_table():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        exit(1)