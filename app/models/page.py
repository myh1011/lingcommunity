"""角色（内容）模型。

title/body/url 等字段保留向后兼容；
settings 存放参照 LingChat 角色创建器的结构化设定（JSON）。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

from app.models.page_tag import page_tags


class PageStatus:
    PUBLISHED = "published"
    REMOVED = "removed"


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False, default="")
    url = Column(String(500), nullable=False)
    uploader = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    # 时间统一由应用侧生成（本地时间），避免数据库 CURRENT_TIMESTAMP 时区不一致
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    # 下载次数（每次通过 /download 跳转时 +1）
    download_count = Column(Integer, default=0, nullable=False)
    # 内容状态：published 正常 / removed 已下架（管理员处理举报）
    status = Column(String(20), default=PageStatus.PUBLISHED, nullable=False)
    # 角色结构化设定（参照 LingChat SettingsCharacterInfo 的字段）
    settings = Column(JSON, default=dict, nullable=True)

    tags = relationship("Tag", secondary=page_tags, backref="pages")
