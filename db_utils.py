"""
Database utilities optimized for Supabase Transaction Pooler
"""

from sqlalchemy import text
from database import engine
import time
from functools import wraps

def with_db_retry(max_retries=3, delay=0.1):
    """Decorator to retry database operations with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                    break
            
            # If all retries failed, raise the last exception
            raise last_exception
        return wrapper
    return decorator

@with_db_retry(max_retries=2, delay=0.05)
def quick_db_check():
    """Fast database connectivity check optimized for transaction pooler"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1

@with_db_retry(max_retries=2, delay=0.05)
def execute_query(query, params=None):
    """Execute a query with retry logic"""
    with engine.connect() as conn:
        if params:
            return conn.execute(text(query), params)
        else:
            return conn.execute(text(query))

def get_connection_info():
    """Get database connection information"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    current_database() as database,
                    current_user as user,
                    inet_server_addr() as server_ip,
                    inet_server_port() as server_port,
                    version() as version
            """))
            return dict(result.fetchone())
    except Exception as e:
        return {"error": str(e)}

def optimize_connection():
    """Optimize connection settings for transaction pooler"""
    try:
        with engine.connect() as conn:
            # Set optimal settings for transaction pooler
            conn.execute(text("SET statement_timeout = '30s'"))
            conn.execute(text("SET lock_timeout = '10s'"))
            conn.execute(text("SET idle_in_transaction_session_timeout = '60s'"))
            conn.commit()
            return True
    except Exception as e:
        print(f"Connection optimization failed: {e}")
        return False