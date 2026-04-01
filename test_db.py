import os
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("❌ Error: DATABASE_URL not found in .env file")
    exit(1)

print(f"🔄 Attempting to connect using DATABASE_URL from .env...")
try:
    # Parse URL just to safely print connection details without showing the password
    parsed = urlparse(db_url)
    print(f"📡 Connecting to Host: {parsed.hostname}")
    print(f"🔌 Port: {parsed.port}")
    print(f"👤 User: {parsed.username}")
    print(f"🗄️ Database: {parsed.path.lstrip('/')}")
    
    # Try connecting
    conn = psycopg2.connect(db_url)
    print("\n✅ SUCCESS! Database connection established perfectly!")
    
    # Run a quick test query
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"📊 PostgreSQL Version: {version}")
    
    cur.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print("\n❌ CONNECTION FAILED!")
    print(f"Error Details:\n{e}")
    if "password authentication failed" in str(e).lower():
        print("\n💡 TIP: The password in your DATABASE_URL is incorrect or your database user doesn't have access.")
        print("💡 TIP: Also ensure that your current IP address is whitelisted in your Supabase dashboard > Database > Network restrictions if using the direct IPv4 connection.")
    elif "could not connect to server" in str(e).lower():
        print("\n💡 TIP: The server host might be incorrect, or if you're using the Direct IPv4 Connection, your IP address might not be allowed (whitelisted) in Supabase.")
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
