"""
Database Connection Test Script
Tests the database connection with proper isolation level configuration
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection with different configurations"""
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    # Fix the duplicate DATABASE_URL= prefix if present
    if database_url.startswith("DATABASE_URL="):
        database_url = database_url.replace("DATABASE_URL=", "", 1)
        print("⚠️  Fixed duplicate DATABASE_URL= prefix")
    
    print(f"📡 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'database'}")
    print("-" * 60)
    
    # Test 1: Basic connection with proper isolation level
    print("\n🔍 Test 1: Connection with isolation_level='READ COMMITTED'")
    try:
        engine = create_engine(
            database_url,
            poolclass=NullPool,
            isolation_level="READ COMMITTED",  # Proper format with space
            echo=False
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {version[:50]}...")
            
            # Test a simple query
            result = conn.execute(text("SELECT 1 as test;"))
            print(f"✅ Query test passed: {result.fetchone()[0]}")
            
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Test 1 failed: {str(e)}")
    
    # Test 2: Connection without explicit isolation level
    print("\n🔍 Test 2: Connection without isolation_level parameter")
    try:
        engine = create_engine(
            database_url,
            poolclass=NullPool,
            echo=False
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_setting('transaction_isolation');"))
            isolation = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   Default isolation level: {isolation}")
            
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Test 2 failed: {str(e)}")
    
    # Test 3: Connection with AUTOCOMMIT
    print("\n🔍 Test 3: Connection with isolation_level='AUTOCOMMIT'")
    try:
        engine = create_engine(
            database_url,
            poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
            echo=False
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;"))
            print(f"✅ Connected successfully with AUTOCOMMIT!")
            
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Test 3 failed: {str(e)}")
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Database Connection Test")
    print("=" * 60)
    
    success = test_database_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Database connection is working!")
    else:
        print("❌ All connection tests failed")
        print("\n💡 Suggestions:")
        print("   1. Check if DATABASE_URL has duplicate prefix")
        print("   2. Verify database credentials")
        print("   3. Check if IP is whitelisted in Supabase")
        print("   4. Try using the pooler URL instead of direct connection")
    print("=" * 60)
