
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.db.database import get_db
from app.services.page_service import PageService
from app.schemas.page import Pagecreate, PageOut, PageListOut

router = APIRouter()

def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)

# 列表路由
@router.get("", response_model=List[PageListOut])
@router.get("/", response_model=List[PageListOut])
async def list_pages(page_service: PageService = Depends(get_page_service)):
    try:
        return page_service.list_all()
    except AttributeError:
        return []

# 创建角色路由 - 支持文件上传
@router.post("", response_model=PageOut)
@router.post("/", response_model=PageOut)
async def create_page(
    title: str = Form(...),
    body: str = Form(...),
    url: str = Form(...),
    uploader: str = Form(None),
    avatar: UploadFile = File(None),
    page_service: PageService = Depends(get_page_service)
):
    try:
        return page_service.create_with_avatar(title, body, url, uploader, avatar)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail="创建角色失败")

# 读取角色
@router.get("/{uid}", response_model=PageOut)
async def read_page(uid: str, page_service: PageService = Depends(get_page_service)):
    page = page_service.get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page

# 删除角色 - 只有上传者可以删除
@router.delete("/{uid}")
async def delete_page(
    uid: str, 
    page_service: PageService = Depends(get_page_service),
    x_user: Optional[str] = Header(None, alias="X-User")  # 从请求头获取用户名
):
    # 获取要删除的角色
    page = page_service.get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # 验证权限：只有上传者可以删除
    if not page.uploader:
        raise HTTPException(status_code=403, detail="此角色没有上传者信息，无法删除")
    
    if not x_user or x_user != page.uploader:
        raise HTTPException(status_code=403, detail="只有上传者可以删除此角色")
    
    # 删除关联的头像文件（如果有）
    if page.avatar_url and page.avatar_url.startswith("/static/uploads/avatars/"):
        try:
            avatar_path = f"app{page.avatar_url}"
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        except Exception as e:
            print(f"删除头像文件失败: {e}")
            # 继续删除数据库记录
    
    page_service.delete_by_uid(uid)
    return {"detail": "deleted"}
