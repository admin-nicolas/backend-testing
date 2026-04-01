from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Float, case
from typing import List, Optional, Dict, Any
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
from core.dependencies import get_db, get_user_by_email, get_system_settings, check_and_reset_daily_limit, verify_admin, prepare_freelancer_request
from core.utils import extract_category_from_text, start_cache_cleanup, extract_category_from_url, init_db, trigger_webhook_async, _check_db_status
from auth import get_password_hash, verify_password, create_access_token, verify_token, SECRET_KEY, ALGORITHM

router = APIRouter()

@router.post("/api/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    from models import User
    
    # Check if user already exists (case-insensitive)
    existing_user = db.query(User).filter(func.lower(User.email) == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user (store email in lowercase for consistency)
    hashed_password = get_password_hash(user_data.password)
    new_user = User(email=user_data.email.lower(), hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    from models import User
    
    # Find user (case-insensitive email search)
    user = db.query(User).filter(func.lower(User.email) == user_data.email.lower()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/auth/debug")
async def debug_auth(request: Request):
    """Debug endpoint to check authentication headers and token format"""
    try:
        auth_header = request.headers.get("authorization")
        print(f"🔍 [DEBUG_AUTH] Authorization header: {auth_header}")
        
        return {"status": "ok", "auth_header": auth_header}
    except Exception as e:
        print(f"Debug error: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(email: str = Depends(verify_token), db: Session = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    from models import User
    
    # Find user (case-insensitive)
    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/api/user/info")
async def get_user_info(request: ProjectsRequest):
    """Get user information and check token scopes"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.freelancer.com/api/users/0.1/self/",
                headers={
                    "Authorization": f"Bearer {request.access_token}",
                    "freelancer-oauth-v1": request.access_token,
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "message": "Token is valid"
                }
            else:
                error_data = response.text
                # Check if it's a scope issue
                if "insufficient_scope" in error_data or response.status_code == 403:
                    return {
                        "success": False,
                        "error": "Token does not have required scopes for bidding",
                        "status_code": response.status_code,
                        "message": "You need to get a token with bid:write permissions. See the OAuth flow documentation."
                    }
                return {
                    "success": False,
                    "error": error_data,
                    "status_code": response.status_code
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/token/check-scopes")
async def check_token_scopes(request: ProjectsRequest):
    """Check if token has bidding permissions"""
    try:
        async with httpx.AsyncClient() as client:
            # Try to access a bid-related endpoint to check permissions
            response = await client.get(
                "https://www.freelancer.com/api/users/0.1/self/",
                headers={
                    "Authorization": f"Bearer {request.access_token}",
                    "freelancer-oauth-v1": request.access_token,
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Token is valid for basic operations",
                    "warning": "Cannot verify bid:write scope without attempting a bid. Token may still lack bidding permissions."
                }
            elif response.status_code == 403:
                return {
                    "success": False,
                    "error": "Token has insufficient scopes",
                    "message": "You need to obtain a token with bid:write, project:read, and user:read scopes"
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/user/info")
async def get_user_info_with_cookies(
    request_data: dict
):
    """Get user info using Freelancer cookies - for extension validation"""
    try:
        access_token = request_data.get("access_token")
        freelancer_cookies = request_data.get("freelancer_cookies")
        
        if not access_token and not freelancer_cookies:
            raise HTTPException(status_code=400, detail="access_token or freelancer_cookies required")
        
        # If we have an OAuth token, use it directly
        if access_token and access_token != "using_cookies":
            headers = {
                "Authorization": f"Bearer {access_token}",
                "freelancer-oauth-v1": access_token
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.freelancer.com/api/users/0.1/self?compact=true",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data}
        
        # If using cookies, we'd need to implement cookie-based requests
        # For now, return a mock response
        return {
            "success": False,
            "error": "Cookie-based authentication not implemented in backend"
        }
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return {"success": False, "error": str(e)}

