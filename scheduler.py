"""
Background scheduler for auto-fetch jobs
Runs independently of frontend, works 24/7
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import httpx
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, UserSettings, SystemSettings
import logging
import asyncio

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Webhook URLs
UPWORK_WEBHOOK_URL = os.getenv('UPWORK_WEBHOOK_URL')
FREELANCER_WEBHOOK_URL = os.getenv('FREELANCER_WEBHOOK_URL')

# Initialize scheduler
scheduler = BackgroundScheduler()


def get_db():
    """Get database session"""
    try:
        db = SessionLocal()
        return db
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def check_and_reset_daily_limit(user: User, platform: str, db: Session):
    """Check and reset daily limit if needed"""
    system_settings = db.query(SystemSettings).first()
    if not system_settings:
        system_settings = SystemSettings(
            default_upwork_limit=5,
            default_freelancer_limit=5,
            default_freelancer_plus_limit=3
        )
        db.add(system_settings)
        db.commit()
    
    LIMITS = {
        "upwork": system_settings.default_upwork_limit,
        "freelancer": system_settings.default_freelancer_limit,
    }
    DAILY_LIMIT = LIMITS.get(platform, 5)
    now = datetime.utcnow()
    
    if platform == "upwork":
        count_field = "upwork_fetch_count"
        reset_field = "upwork_last_reset"
    elif platform == "freelancer":
        count_field = "freelancer_fetch_count"
        reset_field = "freelancer_last_reset"
    else:
        return 0, DAILY_LIMIT, False
    
    last_reset = getattr(user, reset_field)
    current_count = getattr(user, count_field) or 0
    
    # Check if it's a new day
    if last_reset:
        if now.date() > last_reset.date():
            # Reset counter
            setattr(user, count_field, 0)
            setattr(user, reset_field, now)
            current_count = 0
            db.commit()
            logger.info(f"[{platform.upper()}] Reset daily limit for user {user.email}")
    else:
        # First time, set reset time
        setattr(user, reset_field, now)
        db.commit()
    
    remaining = DAILY_LIMIT - current_count
    can_fetch = current_count < DAILY_LIMIT
    
    return current_count, DAILY_LIMIT, can_fetch


async def fetch_upwork_for_user(user_id: int, user_email: str, settings: UserSettings):
    """Check and fetch Upwork jobs if interval passed"""
    db = get_db()
    if not db:
        return
    
    try:
        # Get fresh user and settings from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # Get fresh settings
        fresh_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not fresh_settings:
            return
        
        now = datetime.utcnow()
        interval_minutes = fresh_settings.upwork_auto_fetch_interval or 2
        
        # Check if enough time passed since last fetch
        if fresh_settings.upwork_last_auto_fetch:
            time_since_last = (now - fresh_settings.upwork_last_auto_fetch).total_seconds() / 60
            if time_since_last < interval_minutes:
                return  # Not time yet
        else:
            # First time - set the time and wait for next interval
            fresh_settings.upwork_last_auto_fetch = now
            db.commit()
            logger.info(f"[Upwork] Auto-fetch enabled for {user_email}, will fetch in {interval_minutes} min")
            return
        
        # Check daily limit
        current_count, daily_limit, can_fetch = check_and_reset_daily_limit(user, "upwork", db)
        
        if not can_fetch:
            settings.upwork_auto_fetch = False
            db.commit()
            logger.info(f"[Upwork] Limit reached for {user_email}, disabled")
            return
        
        # Trigger webhook
        if not UPWORK_WEBHOOK_URL:
            return
        
        logger.info(f"[Upwork] Fetching for {user_email}")
        
        # Prepare payload and headers with API key
        payload = {
            "user_id": user.id,
            "user_email": user_email,
            "settings": {
                "job_categories": fresh_settings.upwork_job_categories,
                "max_jobs": fresh_settings.upwork_max_jobs,
                "payment_verified": fresh_settings.upwork_payment_verified
            }
        }
        
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("N8N_WEBHOOK_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(UPWORK_WEBHOOK_URL, json=payload, headers=headers)
            
            if response.status_code == 200:
                fresh_settings.upwork_last_auto_fetch = now
                user.upwork_fetch_count = (user.upwork_fetch_count or 0) + 1
                db.commit()
                
                remaining = daily_limit - user.upwork_fetch_count
                logger.info(f"[Upwork] Success. Remaining: {remaining}/{daily_limit}")
                
                if remaining <= 0:
                    fresh_settings.upwork_auto_fetch = False
                    db.commit()
            else:
                logger.error(f"[Upwork] Failed: {response.status_code}")
    
    except Exception as e:
        logger.error(f"[Upwork] Error: {e}")
    finally:
        if db:
            db.close()


async def fetch_freelancer_for_user(user_id: int, user_email: str, settings: UserSettings):
    """Check and fetch Freelancer jobs if interval passed"""
    db = get_db()
    if not db:
        return
    
    try:
        # Get fresh user and settings from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # Get fresh settings
        fresh_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not fresh_settings:
            return
        
        now = datetime.utcnow()
        interval_minutes = fresh_settings.freelancer_auto_fetch_interval or 3
        
        # Check if enough time passed since last fetch
        if fresh_settings.freelancer_last_auto_fetch:
            time_since_last = (now - fresh_settings.freelancer_last_auto_fetch).total_seconds() / 60
            if time_since_last < interval_minutes:
                return  # Not time yet
        else:
            # First time - set the time and wait for next interval
            fresh_settings.freelancer_last_auto_fetch = now
            db.commit()
            logger.info(f"[Freelancer] Auto-fetch enabled for {user_email}, will fetch in {interval_minutes} min")
            return
        
        # Check daily limit
        current_count, daily_limit, can_fetch = check_and_reset_daily_limit(user, "freelancer", db)
        
        if not can_fetch:
            settings.freelancer_auto_fetch = False
            db.commit()
            logger.info(f"[Freelancer] Limit reached for {user_email}, disabled")
            return
        
        # Trigger webhook
        if not FREELANCER_WEBHOOK_URL:
            return
        
        logger.info(f"[Freelancer] Fetching for {user_email}")
        
        # Prepare payload and headers with API key
        payload = {
            "user_id": user.id,
            "user_email": user_email,
            "settings": {
                "job_category": fresh_settings.freelancer_job_category,
                "max_jobs": fresh_settings.freelancer_max_jobs
            }
        }
        
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("N8N_WEBHOOK_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(FREELANCER_WEBHOOK_URL, json=payload, headers=headers)
            
            if response.status_code == 200:
                fresh_settings.freelancer_last_auto_fetch = now
                user.freelancer_fetch_count = (user.freelancer_fetch_count or 0) + 1
                db.commit()
                
                remaining = daily_limit - user.freelancer_fetch_count
                logger.info(f"[Freelancer] Success. Remaining: {remaining}/{daily_limit}")
                
                if remaining <= 0:
                    fresh_settings.freelancer_auto_fetch = False
                    db.commit()
            else:
                logger.error(f"[Freelancer] Failed: {response.status_code}")
    
    except Exception as e:
        logger.error(f"[Freelancer] Error: {e}")
    finally:
        if db:
            db.close()


def check_and_run_auto_fetch():
    """Check every 1 minute for users with auto-fetch enabled"""
    db = get_db()
    if not db:
        return
    
    try:
        # Get all user settings with auto-fetch enabled
        settings_upwork = db.query(UserSettings).filter(UserSettings.upwork_auto_fetch == True).all()
        settings_freelancer = db.query(UserSettings).filter(UserSettings.freelancer_auto_fetch == True).all()
        
        # Process Upwork users
        for settings in settings_upwork:
            user = db.query(User).filter(User.id == settings.user_id).first()
            if user:
                asyncio.run(fetch_upwork_for_user(user.id, user.email, settings))
        
        # Process Freelancer users
        for settings in settings_freelancer:
            user = db.query(User).filter(User.id == settings.user_id).first()
            if user:
                asyncio.run(fetch_freelancer_for_user(user.id, user.email, settings))
    
    except Exception as e:
        logger.error(f"[Scheduler] Error: {e}")
    finally:
        if db:
            db.close()


def start_scheduler():
    """Start the background scheduler"""
    # Run every 1 minute to check for users who need auto-fetch
    scheduler.add_job(
        check_and_run_auto_fetch,
        trigger=IntervalTrigger(minutes=1),
        id='auto_fetch_checker',
        name='Check and run auto-fetch for all users',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("[Scheduler] Background auto-fetch scheduler started")


def stop_scheduler():
    """Stop the background scheduler"""
    scheduler.shutdown()
    logger.info("[Scheduler] Background auto-fetch scheduler stopped")
