"""下载日志：用于下载趋势统计（按天/周/月）。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base


class DownloadLog(Base):
    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=True, index=True)
    page_uid = Column(String(36), nullable=True, index=True)
    ip = Column(String(64), nullable=True)
    downloaded_at = Column(DateTime(timezone=True), default=datetime.now, index=True)
