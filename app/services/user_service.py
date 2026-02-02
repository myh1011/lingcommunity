
from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User, UserRole
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, password: str, role: str = UserRole.USER.value) -> User:
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("username exists")
        u = User(
            username=username, 
            password_hash=hash_password(password),
            role=role
        )
        self.db.add(u)
        self.db.commit()
        self.db.refresh(u)
        return u

    def authenticate(self, username: str, password: str) -> Optional[User]:
        u = self.db.query(User).filter(User.username == username).first()
        if not u:
            return None
        if u.password_hash != hash_password(password):
            return None
        return u

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def list_users(self):
        return self.db.query(User).order_by(User.id.desc()).all()
    
    def update_user_role(self, username: str, role: str) -> Optional[User]:
        """更新用户角色"""
        user = self.get_by_username(username)
        if not user:
            return None
        
        if role not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role. Must be one of: {[r.value for r in UserRole]}")
        
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_admins(self):
        """获取所有管理员"""
        return self.db.query(User).filter(
            User.role.in_([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])
        ).all()
