"""用户相关 Schema。"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LoginOut(BaseModel):
    token: str
    user: UserOut


class UserAdminOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    page_count: int = 0

    model_config = {"from_attributes": True}
