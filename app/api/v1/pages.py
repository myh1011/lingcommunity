from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.db.database import get_db
from app.services.page_service import PageService
from app.schemas.page import Pagecreate, PageOut, PageListOut, TagBase

router = APIRouter()

def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)

# 获取所有标签
@router.get("/tags", response_model=List[TagBase])
async def get_all_tags(page_service: PageService = Depends(get_page_service)):
    tags = page_service.get_all_tags()
    return tags

# 列表路由 - 支持搜索和筛选
@router.get("", response_model=List[PageListOut])
@router.get("/", response_model=List[PageListOut])
async def list_pages(
    query: Optional[str] = Query(None, description="搜索标题"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    page_service: PageService = Depends(get_page_service)
):
    try:
        pages = page_service.search(query, tag)
        # 转换为响应模型
        result = []
        for page in pages:
            page_dict = {
                "id": page.id,
                "uid": page.uid,
                "title": page.title,
                "url": page.url,
                "uploader": page.uploader,
                "avatar_url": page.avatar_url,
                "created_at": page.created_at,
                "tags": [tag.name for tag in page.tags] if page.tags else []
            }
            result.append(PageListOut(**page_dict))
        return result
    except Exception as e:
        print(f"获取页面列表失败: {e}")
        return []

# 创建角色路由 - 支持文件上传和标签
@router.post("", response_model=PageOut)
@router.post("/", response_model=PageOut)
async def create_page(
    title: str = Form(...),
    body: str = Form(...),
    url: str = Form(...),
    uploader: str = Form(None),
    tags: str = Form(""),  # 以逗号分隔的标签字符串
    avatar: UploadFile = File(None),
    page_service: PageService = Depends(get_page_service)
):
    try:
        # 解析标签字符串
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        return page_service.create_with_avatar(
            title=title,
            body=body,
            url=url,
            uploader=uploader,
            avatar_file=avatar,
            tags=tag_list
        )
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
    
    # 转换为响应模型，包含标签对象
    page_dict = {
        "id": page.id,
        "uid": page.uid,
        "title": page.title,
        "body": page.body,
        "url": page.url,
        "uploader": page.uploader,
        "avatar_url": page.avatar_url,
        "created_at": page.created_at,
        "tags": [tag.name for tag in page.tags] if page.tags else [],
        "tag_objects": [
            {"id": tag.id, "name": tag.name, "color": tag.color}
            for tag in page.tags
        ] if page.tags else []
    }
    
    return PageOut(**page_dict)

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