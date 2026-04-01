import asyncio
import logging
from datetime import datetime, timedelta
import random
import json
import time
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("AutoBidder")


from playwright.async_api import async_playwright
from autobidder.api_client import AutoBidderAPIMixin
from autobidder.filtering import AutoBidderFilterMixin
from autobidder.ai_proposal import AutoBidderAIBidMixin
from autobidder.db_utils import AutoBidderDBMixin
from autobidder.scheduler import AutoBidderSchedulerMixin
from autobidder.core import AutoBidderCoreMixin

class AutoBidder(
    AutoBidderSchedulerMixin,
    AutoBidderAPIMixin,
    AutoBidderFilterMixin,
    AutoBidderAIBidMixin,
    AutoBidderDBMixin,
    AutoBidderCoreMixin
):
    _instance = None
    _is_running = False
    _task = None
    _user_last_bid_time = {}
    _user_retry_count = {}
    _user_backoff_until = {}
    
    _settings_cache = {}
    _settings_cache_time = {}
    _bid_history_cache = {}
    _bid_history_cache_time = {}
    _http_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutoBidder, cls).__new__(cls)
        return cls._instance

# Singleton accessor
bidder = AutoBidder()
