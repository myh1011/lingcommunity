from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

# 导入 page_tags 表
from app.models.page_tag import page_tags

class Page(Base):
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    uploader = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 添加标签关系 - 注意：使用 Tag 类，通过 page_tags 关联表
    tags = relationship("Tag", secondary=page_tags, backref="pages")