"""角色（内容）业务逻辑。"""
import os
import shutil
import uuid
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.page import Page as PageModel, PageStatus
from app.models.tag import Tag
from app.models.page_tag import page_tags

ALLOWED_AVATAR_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def validate_url(url: str) -> str:
    """校验下载链接：仅允许 http/https，且必须是合法 URL。"""
    url = (url or "").strip()
    try:
        parsed = urlparse(url)
    except ValueError:
        raise HTTPException(status_code=400, detail="下载链接格式不正确")
    if parsed.scheme not in settings.ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise HTTPException(status_code=400, detail="下载链接必须是合法的 http/https 地址")
    if len(url) > 500:
        raise HTTPException(status_code=400, detail="下载链接过长")
    return url


def save_avatar(avatar_file: Optional[UploadFile]) -> Optional[str]:
    """保存头像文件，返回可访问的相对 URL；失败时返回 None 并记录。"""
    if not avatar_file:
        return None
    ext = os.path.splitext(avatar_file.filename or "")[1].lower()
    if ext not in ALLOWED_AVATAR_EXT:
        raise HTTPException(status_code=400, detail="头像仅支持 png/jpg/jpeg/gif/webp 格式")
    if avatar_file.content_type and not avatar_file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="头像必须是图片文件")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    size = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := avatar_file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_AVATAR_SIZE:
                    raise HTTPException(status_code=400, detail="头像文件过大（最大 5MB）")
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"[page_service] 保存头像失败: {e}")
        return None
    return f"/static/uploads/avatars/{filename}"


def remove_avatar_file(avatar_url: Optional[str]) -> None:
    """删除本地上传的头像文件（仅限本服务上传的路径）。"""
    if not avatar_url or not avatar_url.startswith("/static/uploads/avatars/"):
        return
    try:
        path = os.path.join("app", avatar_url.lstrip("/"))
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        print(f"[page_service] 删除头像文件失败: {e}")


class PageService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- 基础查询 ----------

    def get_by_uid(self, uid: str, include_removed: bool = False) -> Optional[PageModel]:
        q = self.db.query(PageModel).filter(PageModel.uid == uid)
        if not include_removed:
            q = q.filter(PageModel.status == PageStatus.PUBLISHED)
        return q.first()

    def get_by_id(self, page_id: int) -> Optional[PageModel]:
        return self.db.query(PageModel).filter(PageModel.id == page_id).first()

    def _attach_tags(self, page: PageModel, tag_names: List[str]) -> None:
        """附加标签（不存在则创建），并清理非法标签。"""
        if not tag_names:
            return
        normalized: List[str] = []
        for raw in tag_names[:10]:  # 最多 10 个标签
            name = str(raw).strip()[:50]
            if name and name not in normalized:
                normalized.append(name)
        for name in normalized:
            tag = self.db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name)
                self.db.add(tag)
                self.db.flush()
            if tag not in page.tags:
                page.tags.append(tag)

    # ---------- 创建 / 更新 ----------

    def create(
        self,
        title: str,
        body: str,
        url: str,
        uploader: Optional[str],
        avatar_file: Optional[UploadFile] = None,
        tags: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> PageModel:
        title = title.strip()
        if not title or len(title) > 255:
            raise HTTPException(status_code=400, detail="标题不能为空且不超过 255 字")
        body = body or ""
        clean_url = validate_url(url)
        if self.db.query(PageModel).filter(PageModel.url == clean_url).first():
            raise HTTPException(status_code=400, detail="该下载链接已被其他角色使用")

        avatar_url = save_avatar(avatar_file)

        page = PageModel(
            uid=str(uuid.uuid4()),
            title=title,
            body=body,
            url=clean_url,
            uploader=uploader,
            avatar_url=avatar_url,
            settings=settings if isinstance(settings, dict) else {},
        )
        self.db.add(page)
        self._attach_tags(page, tags or [])
        self.db.commit()
        self.db.refresh(page)
        return page

    def update(
        self,
        uid: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        url: Optional[str] = None,
        avatar_file: Optional[UploadFile] = None,
        tags: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> PageModel:
        page = self.get_by_uid(uid, include_removed=True)
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")

        if title is not None:
            title = title.strip()
            if not title or len(title) > 255:
                raise HTTPException(status_code=400, detail="标题不能为空且不超过 255 字")
            page.title = title
        if body is not None:
            page.body = body or ""
        if url is not None:
            clean_url = validate_url(url)
            exists = (
                self.db.query(PageModel)
                .filter(PageModel.url == clean_url, PageModel.id != page.id)
                .first()
            )
            if exists:
                raise HTTPException(status_code=400, detail="该下载链接已被其他角色使用")
            page.url = clean_url

        if settings is not None:
            page.settings = settings if isinstance(settings, dict) else {}

        if avatar_file is not None:
            remove_avatar_file(page.avatar_url)
            page.avatar_url = save_avatar(avatar_file)

        if tags is not None:
            page.tags = []
            self._attach_tags(page, tags)

        self.db.commit()
        self.db.refresh(page)
        return page

    def delete(self, uid: str) -> None:
        page = self.get_by_uid(uid, include_removed=True)
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")
        remove_avatar_file(page.avatar_url)
        self.db.delete(page)
        self.db.commit()

    def set_status(self, uid: str, status: str) -> PageModel:
        if status not in (PageStatus.PUBLISHED, PageStatus.REMOVED):
            raise HTTPException(status_code=400, detail="无效的状态")
        page = self.get_by_uid(uid, include_removed=True)
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")
        page.status = status
        self.db.commit()
        self.db.refresh(page)
        return page

    # ---------- 下载计数 ----------

    def record_download(self, page: PageModel, ip: Optional[str]) -> None:
        page.download_count = (page.download_count or 0) + 1
        from app.models.download_log import DownloadLog
        try:
            self.db.add(DownloadLog(page_id=page.id, page_uid=page.uid, ip=ip))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"[page_service] 记录下载日志失败: {e}")

    # ---------- 列表 / 搜索 ----------

    def list_pages(
        self,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "latest",
        page: int = 1,
        page_size: int = 12,
        status: Optional[str] = None,
    ):
        q = self.db.query(PageModel).options(joinedload(PageModel.tags))
        if status:
            q = q.filter(PageModel.status == status)
        else:
            q = q.filter(PageModel.status == PageStatus.PUBLISHED)
        if query:
            q = q.filter(PageModel.title.contains(query.strip()))
        if tag:
            q = q.join(PageModel.tags).filter(Tag.name == tag)

        total = q.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = max(1, min(page, total_pages))

        if sort == "downloads":
            q = q.order_by(PageModel.download_count.desc(), PageModel.created_at.desc())
        else:
            q = q.order_by(PageModel.created_at.desc(), PageModel.id.desc())

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total, page, page_size, total_pages

    def get_rankings(self, limit: int = 10) -> List[PageModel]:
        return (
            self.db.query(PageModel)
            .filter(PageModel.status == PageStatus.PUBLISHED)
            .order_by(PageModel.download_count.desc(), PageModel.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_all_tags(self) -> List[Tag]:
        return self.db.query(Tag).order_by(Tag.name).all()

    def get_popular_tags(self, limit: int = 10):
        return (
            self.db.query(Tag, func.count(page_tags.c.page_id).label("count"))
            .join(page_tags)
            .group_by(Tag.id)
            .order_by(func.count(page_tags.c.page_id).desc())
            .limit(limit)
            .all()
        )
