import asyncio
import logging
from datetime import datetime, timedelta
import random
import json
import time
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("AutoBidder")

class AutoBidderDBMixin:
    async def _get_cached_bid_history(self, user_id: int) -> set:
        """PERFORMANCE: Get cached bid history to avoid repeated DB queries"""
        now = time.time()
        cache_ttl = 300  # 5 minutes cache
        
        # Check if cache is valid
        if (user_id in self._bid_history_cache and 
            now - self._bid_history_cache_time.get(user_id, 0) < cache_ttl):
            return self._bid_history_cache[user_id]
        
        # Fetch from database
        try:
            from database import SessionLocal
            from models import BidHistory
            
            db = SessionLocal()
            try:
                # Fetch all project IDs user has bid on (much faster than checking one by one)
                bid_history_ids = db.query(BidHistory.project_id).filter(
                    BidHistory.user_id == user_id
                ).all()
                
                # Convert to set for O(1) lookup
                bid_history_set = {str(pid[0]) for pid in bid_history_ids}
                
                # Cache it
                self._bid_history_cache[user_id] = bid_history_set
                self._bid_history_cache_time[user_id] = now
                
                logger.info(f"📦 User {user_id}: Cached {len(bid_history_set)} bid history entries")
                return bid_history_set
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Error fetching bid history cache for User {user_id}: {e}")
            return set()

    def _invalidate_bid_history_cache(self, user_id: int):
        """PERFORMANCE: Invalidate cache when new bid is placed"""
        if user_id in self._bid_history_cache:
            del self._bid_history_cache[user_id]
        if user_id in self._bid_history_cache_time:
            del self._bid_history_cache_time[user_id]

    async def _cleanup_old_bid_history(self, user_id: int, days_to_keep: int = 7):
        """Clean up old bid history entries to prevent database bloat"""
        try:
            from database import SessionLocal
            from models import BidHistory
            from datetime import datetime, timedelta
            
            db = SessionLocal()
            try:
                # Delete bid history older than specified days
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                deleted_count = db.query(BidHistory).filter(
                    BidHistory.user_id == user_id,
                    BidHistory.created_at < cutoff_date
                ).delete()
                
                if deleted_count > 0:
                    db.commit()
                    logger.info(f"🧹 User {user_id}: Cleaned up {deleted_count} old bid history entries (>{days_to_keep} days)")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up bid history for User {user_id}: {e}")

    async def _has_bid_history(self, user_id: int, project_id: str) -> bool:
        """PERFORMANCE: Check if user has already attempted to bid on this project (using cache)"""
        # This method is now deprecated in favor of batch checking in _run_bid_cycle
        # Kept for backward compatibility
        try:
            bid_history_set = await self._get_cached_bid_history(user_id)
            return project_id in bid_history_set
        except Exception as e:
            logger.error(f"❌ Error checking bid history for User {user_id}, Project {project_id}: {e}")
            return False  # If we can't check, allow bidding (fail-safe)

    async def _check_daily_bid_limit(self, user_id: int, settings: Dict) -> bool:
        """Check if user has reached their daily bid limit"""
        daily_limit = settings.get("daily_bids", 10)
        
        try:
            from database import SessionLocal
            from models import BidHistory
            from datetime import datetime, timedelta
            
            db = SessionLocal()
            try:
                # Get today's date range
                today = datetime.now().date()
                start_of_day = datetime.combine(today, datetime.min.time())
                end_of_day = datetime.combine(today, datetime.max.time())
                
                # Count successful bids placed today
                today_bids = db.query(BidHistory).filter(
                    BidHistory.user_id == user_id,
                    BidHistory.status == "success",
                    BidHistory.created_at >= start_of_day,
                    BidHistory.created_at <= end_of_day
                ).count()
                
                logger.info(f"📊 User {user_id}: Daily bid count: {today_bids}/{daily_limit}")
                
                if today_bids >= daily_limit:
                    logger.error(f"🚫 User {user_id}: Daily bid limit reached ({today_bids}/{daily_limit})! Disabling auto-bidding...")
                    await self._disable_user_autobidding(user_id)
                    return False
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error checking daily bid limit for User {user_id}: {e}")
            return True  # Allow bidding if we can't check (fail-safe)

    async def _mark_credentials_expired(self, user_id: int):
        """Mark user credentials as expired in database"""
        try:
            from database import SessionLocal
            from models import FreelancerCredentials
            
            db = SessionLocal()
            try:
                credentials = db.query(FreelancerCredentials).filter(
                    FreelancerCredentials.user_id == user_id
                ).first()
                
                if credentials:
                    credentials.is_validated = False
                    db.commit()
                    logger.info(f"🔐 User {user_id}: Marked credentials as expired in database")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Failed to update credential status: {e}")

    async def _disable_user_autobidding(self, user_id: int):
        """Disable auto-bidding for user who hit bid limit"""
        try:
            from database import SessionLocal
            from models import AutoBidSettings as DBAutoBidSettings
            
            db = SessionLocal()
            try:
                db_settings = db.query(DBAutoBidSettings).filter(
                    DBAutoBidSettings.user_id == user_id
                ).first()
                
                if db_settings:
                    db_settings.enabled = False
                    db.commit()
                    logger.info(f"🚫 User {user_id}: Auto-bidding disabled due to bid limit reached")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Failed to disable auto-bidding: {e}")

    async def _save_bid_history(self, bid_data: Dict):
        """PERFORMANCE: Save bid attempt to database and invalidate cache"""
        try:
            from database import SessionLocal
            from models import BidHistory
            
            db = SessionLocal()
            try:
                history = BidHistory(
                    user_id=bid_data.get("user_id", 1),
                    project_id=bid_data.get("project_id"),
                    project_title=bid_data.get("project_title"),
                    project_url=bid_data.get("project_url"),
                    bid_amount=bid_data.get("bid_amount", 0),
                    proposal_text=bid_data.get("proposal_text"),
                    status=bid_data.get("status", "pending"),
                    error_message=bid_data.get("error_message")
                )
                
                db.add(history)
                db.commit()
                logger.info("✅ Saved to bid history database")
                
                # PERFORMANCE: Invalidate cache after saving
                user_id = bid_data.get("user_id", 1)
                self._invalidate_bid_history_cache(user_id)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to save bid history: {e}")

