"""用户模型。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    # 封禁状态：is_active=False 时禁止登录
    is_active = Column(Boolean, default=True, nullable=False)

    def is_admin(self) -> bool:
        return self.role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN.value

    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"
