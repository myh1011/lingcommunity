from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from uuid import uuid4
import os
import shutil

from app.schemas.page import Pagecreate
from app.models.page import Page as PageModel
from app.models.tag import Tag
from app.models.page_tag import page_tags

class PageService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: Pagecreate) -> PageModel:
        # 检查 url 唯一性
        existing = self.db.query(PageModel).filter(PageModel.url == payload.url).first()
        if existing:
            raise HTTPException(status_code=400, detail="URL already exists")

        # 生成唯一 uid
        uid = str(uuid4())
        while self.db.query(PageModel).filter(PageModel.uid == uid).first():
            uid = str(uuid4())

        # 创建角色对象
        page = PageModel(
            title=payload.title, 
            body=payload.body, 
            url=payload.url, 
            uid=uid, 
            uploader=payload.uploader,
            avatar_url=payload.avatar_url
        )
        
        # 处理标签
        if payload.tags:
            self._attach_tags(page, payload.tags)
        
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        return page

    def create_with_avatar(self, title: str, body: str, url: str, 
                         uploader: Optional[str], avatar_file: Optional[UploadFile],
                         tags: Optional[List[str]] = None) -> PageModel:
        avatar_url = None
        
        # 处理头像上传
        if avatar_file:
            # 验证文件类型
            if not avatar_file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="只能上传图片文件")
            
            # 生成唯一文件名
            import uuid
            file_ext = os.path.splitext(avatar_file.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # 保存文件
            upload_dir = "app/static/uploads/avatars"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, unique_filename)
            
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(avatar_file.file, buffer)
                avatar_url = f"/static/uploads/avatars/{unique_filename}"
            except Exception as e:
                print(f"保存头像文件失败: {e}")
                # 不因为头像保存失败而阻止创建角色
        
        # 创建角色数据对象
        page_create = Pagecreate(
            title=title,
            body=body,
            url=url,
            uploader=uploader,
            avatar_url=avatar_url,
            tags=tags or []
        )
        
        return self.create(page_create)

    def _attach_tags(self, page: PageModel, tag_names: List[str]):
        """为页面附加标签"""
        for tag_name in tag_names:
            # 查找或创建标签
            tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self.db.add(tag)
                self.db.flush()  # 获取标签ID但不提交事务
            page.tags.append(tag)

    def get_by_url(self, url: str) -> Optional[PageModel]:
        return self.db.query(PageModel).filter(PageModel.url == url).first()

    def get_by_uid(self, uid: str) -> Optional[PageModel]:
        return self.db.query(PageModel).filter(PageModel.uid == uid).first()

    def delete_by_url(self, url: str) -> None:
        obj = self.db.query(PageModel).filter(PageModel.url == url).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Page not found")
        self.db.delete(obj)
        self.db.commit()

    def delete_by_uid(self, uid: str) -> None:
        obj = self.db.query(PageModel).filter(PageModel.uid == uid).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Page not found")
        self.db.delete(obj)
        self.db.commit()

    def list_all(self) -> List[PageModel]:
        return self.db.query(PageModel).order_by(PageModel.created_at.desc() if hasattr(PageModel, 'created_at') else PageModel.id.desc()).all()

    def search(self, query: Optional[str] = None, tag: Optional[str] = None) -> List[PageModel]:
        """搜索页面，支持标题搜索和标签筛选"""
        q = self.db.query(PageModel)
        
        if query:
            q = q.filter(PageModel.title.contains(query))
        
        if tag:
            q = q.join(PageModel.tags).filter(Tag.name == tag)
        
        return q.order_by(PageModel.created_at.desc()).all()

    def get_all_tags(self) -> List[Tag]:
        """获取所有标签"""
        return self.db.query(Tag).order_by(Tag.name).all()

    def get_popular_tags(self, limit: int = 10) -> List[Tag]:
        """获取热门标签"""
        # 使用原生SQL查询标签使用频率
        from sqlalchemy import func
        return self.db.query(
            Tag, 
            func.count(page_tags.c.page_id).label('count')
        ).join(
            page_tags
        ).group_by(
            Tag.id
        ).order_by(
            func.count(page_tags.c.page_id).desc()
        ).limit(limit).all()