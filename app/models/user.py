
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

# 定义角色枚举
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 新增角色字段
    role = Column(String(20), default=UserRole.USER.value, nullable=False)

    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"
    
    # 添加方法检查权限
    def is_admin(self):
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN.value
