"""认证与授权：HMAC 签名的登录令牌 + FastAPI 依赖。

令牌格式：base64url(payload).hexdigest(hmac_sha256(payload, SECRET_KEY))
payload: {"sub": username, "role": role, "exp": 过期时间戳}
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models.user import User, UserRole


def _sign(payload_b64: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_token(username: str, role: str) -> str:
    """签发登录令牌。"""
    payload = {"sub": username, "role": role, "exp": int(time.time()) + settings.TOKEN_TTL}
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify_token(token: str) -> Optional[dict]:
    """校验令牌，返回 payload；无效或过期返回 None。"""
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(payload_b64)):
        return None
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode("utf-8")
        )
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or int(payload.get("exp", 0)) < time.time():
        return None
    return payload


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    # 兼容旧的前端 X-User 传用户名的方式已废弃；这里仅接受签名令牌
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """必须登录：解析 Bearer 令牌并返回数据库中的用户。"""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被封禁")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """必须是管理员（admin / super_admin）。"""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """必须是超级管理员。"""
    if not current_user.is_super_admin():
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


def admin_or_owner(current_user: User, owner_username: Optional[str]) -> bool:
    """管理员或内容所有者。"""
    return current_user.is_admin() or (
        owner_username is not None and current_user.username == owner_username
    )
