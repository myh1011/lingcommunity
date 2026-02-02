from sqlalchemy import Column, Integer, String
from app.db.database import Base

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(20), default="#3b82f6")  # 标签颜色
    
    def __repr__(self):
        return f"<Tag(name={self.name})>"