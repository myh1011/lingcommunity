
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.services.user_service import UserService

security = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """获取当前登录用户信息"""
    # 如果使用JWT，这里应该解析token
    # 这里简化处理，从localStorage中获取用户名
    
    # 从请求头中获取用户名（简单方式）
    username = request.headers.get('X-User')
    if not username:
        # 尝试从查询参数获取
        username = request.query_params.get('user')
    
    if not username:
        raise HTTPException(status_code=401, detail="未提供用户信息")
    
    user_service = UserService(db)
    user = user_service.get_by_username(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return {
        "username": user.username,
        "role": user.role,
        "is_admin": user.is_admin(),
        "is_super_admin": user.is_super_admin()
    }
