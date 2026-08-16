"""角色（内容）相关 Schema。"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class TagBase(BaseModel):
    id: Optional[int] = None
    name: str
    color: Optional[str] = None

    model_config = {"from_attributes": True}


class PageCreate(BaseModel):
    title: str
    body: str = ""
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PageOut(PageCreate):
    id: Optional[int] = None
    uid: Optional[str] = None
    created_at: Optional[datetime] = None
    download_count: int = 0
    status: str = "published"
    tag_objects: Optional[List[TagBase]] = None

    model_config = {"from_attributes": True}


class PageListOut(BaseModel):
    id: Optional[int] = None
    uid: Optional[str] = None
    title: str
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    download_count: int = 0
    status: str = "published"
    tags: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class PageListResult(BaseModel):
    items: List[PageListOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class RankingItem(BaseModel):
    uid: str
    title: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    download_count: int
    created_at: Optional[datetime] = None


class PageReportCreate(BaseModel):
    category: str
    reason: str = ""
