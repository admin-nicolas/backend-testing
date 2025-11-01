from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Add posted_time column to leads table
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE leads ADD COLUMN posted_time TIMESTAMP"))
        conn.commit()
        print("Successfully added posted_time column to leads table")
    except Exception as e:
        print(f"Error adding column (may already exist): {e}")
