"""举报相关 Schema。"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ReportOut(BaseModel):
    id: int
    page_id: Optional[int] = None
    page_uid: Optional[str] = None
    page_title: Optional[str] = None
    reporter: str
    category: str
    reason: str = ""
    status: str
    handled_by: Optional[str] = None
    handled_note: Optional[str] = None
    created_at: Optional[datetime] = None
    handled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportListResult(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportReview(BaseModel):
    action: str  # approve / reject
    remove_page: bool = False
    note: str = ""
