from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.user_service import UserService
from app.schemas.user import Usercreate, UserLogin, UserOut

router = APIRouter()

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@router.post("/register", response_model=UserOut)
async def register(payload: Usercreate, user_service: UserService = Depends(get_user_service)):
    try:
        u = user_service.create_user(payload.username, payload.password)
        return u
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=UserOut)
async def login(payload: UserLogin, user_service: UserService = Depends(get_user_service)):
    u = user_service.authenticate(payload.username, payload.password)
    if not u:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # 简化：返回用户信息；真正项目可返回 JWT/Session
    return u