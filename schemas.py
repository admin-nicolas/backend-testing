from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List

class UserSignup(BaseModel):
    email: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

class UserLogin(BaseModel):
    email: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    
    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    upwork_job_categories: Optional[List[str]] = None
    upwork_max_jobs: Optional[int] = None
    upwork_payment_verified: Optional[bool] = None
    freelancer_job_category: Optional[str] = None
    freelancer_max_jobs: Optional[int] = None

class SettingsResponse(BaseModel):
    id: int
    upwork_job_categories: List[str]
    upwork_max_jobs: int
    upwork_payment_verified: bool
    freelancer_job_category: str
    freelancer_max_jobs: int
    
    class Config:
        from_attributes = True
