from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class TagBase(BaseModel):
    id: Optional[int] = None
    name: str
    color: Optional[str] = None

    model_config = {"from_attributes": True}

class Pagecreate(BaseModel):
    title: str
    body: str
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None  # 新增：标签名称列表

    model_config = {"from_attributes": True}

class PageUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = {"from_attributes": True}

class PageOut(Pagecreate):
    id: Optional[int] = None
    uid: Optional[str] = None
    created_at: Optional[datetime] = None
    tag_objects: Optional[List[TagBase]] = None  # 新增：包含完整的标签对象

    model_config = {"from_attributes": True}

class PageListOut(BaseModel):
    id: Optional[int] = None
    uid: Optional[str] = None
    title: str
    url: str
    uploader: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    tags: Optional[List[str]] = None  # 新增：标签名称列表

    model_config = {"from_attributes": True}