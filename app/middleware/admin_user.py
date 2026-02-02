
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.services.user_service import UserService
from app.models.user import UserRole
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@router.get("/users", response_model=List[UserOut])
async def list_all_users(
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)  # 需要身份验证中间件
):
    """获取所有用户列表（仅管理员可用）"""
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    users = user_service.list_users()
    return users

@router.put("/users/{username}/role")
async def update_user_role(
    username: str,
    role: str,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    """更新用户角色（仅管理员可用）"""
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    if role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail=f"无效的角色。必须是以下之一: {[r.value for r in UserRole]}")
    
    try:
        updated_user = user_service.update_user_role(username, role)
        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {"detail": "角色更新成功", "user": updated_user.username, "role": updated_user.role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="更新角色失败")

@router.get("/users/admins")
async def get_admin_users(
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    """获取所有管理员用户"""
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    admins = user_service.get_admins()
    return admins
