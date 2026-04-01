from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Float, case
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
import os
import re
import json
from urllib.parse import unquote
import time

from database import engine, SessionLocal
from models import *
from schemas import *
from core.dependencies import get_db, get_user_by_email, get_system_settings, check_and_reset_daily_limit
from core.utils import extract_category_from_text, start_cache_cleanup, extract_category_from_url, init_db, trigger_webhook_async
from auth import get_password_hash, verify_password, create_access_token, verify_token, SECRET_KEY, ALGORITHM

router = APIRouter()

async def root():
    """Fast root endpoint with minimal processing"""
    return {"status": "ok", "service": "akbpo-api", "version": "1.0"}

