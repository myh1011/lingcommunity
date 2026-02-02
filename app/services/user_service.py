from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, password: str) -> User:
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("username exists")
        u = User(username=username, password_hash=hash_password(password))
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