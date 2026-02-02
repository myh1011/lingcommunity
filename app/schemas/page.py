from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class Pagecreate(BaseModel):
    title: str
    body: str
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}

class PageUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}

class PageOut(Pagecreate):
    id: Optional[int] = None
    uid: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class PageListOut(BaseModel):
    id: Optional[int] = None
    uid: Optional[str] = None
    title: str
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
