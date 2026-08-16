"""认证接口：注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import create_token, get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut, LoginOut
from app.services.user_service import UserService

router = APIRouter()


def _get_user_service(db=Depends(get_db)) -> UserService:
    return UserService(db)


@router.post("/register", response_model=LoginOut)
async def register(payload: UserCreate, user_service: UserService = Depends(_get_user_service)):
    try:
        user = user_service.create_user(payload.username, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return LoginOut(token=create_token(user.username, user.role), user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginOut)
async def login(payload: UserLogin, user_service: UserService = Depends(_get_user_service)):
    user = user_service.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被封禁，请联系管理员")
    return LoginOut(token=create_token(user.username, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """返回当前登录用户信息（用于前端校验令牌有效性）。"""
    return UserOut.model_validate(current_user)
