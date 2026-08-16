"""用户业务逻辑。"""
import hashlib
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole

USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fa5-]{3,32}$")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise ValueError("用户名需为 3-32 位字母、数字、下划线或中文")
    return username


def validate_password(password: str) -> None:
    if not password or len(password) < 6 or len(password) > 128:
        raise ValueError("密码长度需为 6-128 位")


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, password: str, role: str = UserRole.USER.value) -> User:
        username = validate_username(username)
        validate_password(password)
        if self.db.query(User).filter(User.username == username).first():
            raise ValueError("用户名已存在")
        user = User(username=username, password_hash=hash_password(password), role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.username == (username or "").strip()).first()
        if not user or user.password_hash != hash_password(password or ""):
            return None
        return user

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def list_users(self, query: str = "", page: int = 1, page_size: int = 20):
        from sqlalchemy import func
        from app.models.page import Page

        q = self.db.query(User)
        if query:
            q = q.filter(User.username.contains(query.strip()))
        total = q.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = max(1, min(page, total_pages))
        users = q.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size).all()

        # 每位用户的投稿数
        page_counts = dict(
            self.db.query(Page.uploader, func.count(Page.id))
            .filter(Page.uploader.isnot(None))
            .group_by(Page.uploader)
            .all()
        )
        return users, page_counts, total, page, page_size, total_pages

    def update_role(self, user_id: int, role: str) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        if role not in [r.value for r in UserRole]:
            raise ValueError("无效的角色，可选值：" + "、".join(r.value for r in UserRole))
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_status(self, user_id: int, is_active: bool) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        user.is_active = bool(is_active)
        self.db.commit()
        self.db.refresh(user)
        return user
