"""举报模型：用户举报内容，管理员审阅。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.database import Base


class ReportStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


REPORT_CATEGORIES = ("色情内容", "违法内容", "侵权内容", "垃圾广告", "辱骂攻击", "其他")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="SET NULL"), nullable=True, index=True)
    page_uid = Column(String(36), nullable=True, index=True)  # 页面被删除后仍可追溯
    page_title = Column(String(255), nullable=True)
    reporter = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False, default="")
    status = Column(String(20), default=ReportStatus.PENDING, nullable=False, index=True)
    handled_by = Column(String(100), nullable=True)
    handled_note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    handled_at = Column(DateTime(timezone=True), nullable=True)
