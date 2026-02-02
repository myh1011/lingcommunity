from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from uuid import uuid4
import os
import shutil

from app.schemas.page import Pagecreate
from app.models.page import Page as PageModel

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
        
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        return page

    def create_with_avatar(self, title: str, body: str, url: str, uploader: Optional[str], avatar_file: Optional[UploadFile]) -> PageModel:
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
            avatar_url=avatar_url
        )
        
        return self.create(page_create)

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
