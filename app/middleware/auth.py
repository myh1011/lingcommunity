
"""
认证中间件
"""
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.services.user_service import UserService

async def get_current_user_simple(request: Request):
    """
    简化版认证：直接从请求参数或localStorage获取用户名
    用于/admin页面的模板渲染
    """
    # 从查询参数获取用户名（前端可以传递?user=xxx）
    username = request.query_params.get("user")
    
    # 如果没有从查询参数获取到，尝试从cookie或header获取
    if not username:
        username = request.cookies.get("user")
    
    return {"username": username or "guest"}

async def require_admin_api(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    API路由的管理员权限检查
    从请求头X-User获取用户名
    """
    username = request.headers.get("X-User")
    
    if not username:
        raise HTTPException(status_code=401, detail="未提供用户信息")
    
    user_service = UserService(db)
    user = user_service.get_by_username(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 检查是否为管理员
    if not hasattr(user, 'role') or user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return user

async def require_admin_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    页面路由的管理员权限检查
    用于/admin页面
    """
    # 从查询参数获取用户名（前端JavaScript设置）
    username = request.query_params.get("user")
    
    # 如果没有，尝试从cookie获取
    if not username:
        username = request.cookies.get("user")
    
    if not username:
        # 返回未授权，但让前端处理重定向
        raise HTTPException(status_code=401, detail="请先登录")
    
    user_service = UserService(db)
    user = user_service.get_by_username(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 检查是否为管理员
    if not hasattr(user, 'role') or user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
