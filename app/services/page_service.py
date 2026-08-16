"""角色（内容）业务逻辑。"""
import os
import re
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

# 情绪立绘槽位（与 LingChat 0.4.1 的 REQUIRED_EMOTION_SLOTS 一致，共 20 个）
EMOTION_SLOTS = [
    "兴奋", "厌恶", "哭泣", "害怕", "害羞", "平静", "心动", "惊讶", "慌张",
    "担心", "无奈", "生气", "疑惑", "紧张", "自信", "认真", "调皮", "难为情",
    "高兴", "正常",
]
# 目录名非法字符（与 LingChat 的校验一致）
INVALID_FOLDER_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_resource_folder(folder: Optional[str]) -> Optional[str]:
    """校验角色目录名（可空；不合法时抛 400）。"""
    folder = (folder or "").strip()
    if not folder:
        return None
    if len(folder) > 64:
        raise HTTPException(status_code=400, detail="目录名过长（最多 64 字符）")
    if INVALID_FOLDER_CHARS_RE.search(folder):
        raise HTTPException(status_code=400, detail="目录名包含非法字符（不允许 \\ / : * ? \" < > |）")
    return folder

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



EMOTION_UPLOAD_DIR = "app/static/uploads/emotions"


def save_emotion_files(
    emotion_names: Optional[List[str]],
    emotion_files: Optional[List[UploadFile]],
) -> Dict[str, str]:
    """校验并保存情绪立绘，返回 {情绪名: 访问URL}。"""
    names = list(emotion_names or [])
    files = list(emotion_files or [])
    if not names and not files:
        return {}
    if len(names) != len(files):
        raise HTTPException(status_code=400, detail="情绪立绘名称与文件数量不匹配")
    if len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="情绪立绘名称存在重复")

    saved: Dict[str, str] = {}
    os.makedirs(EMOTION_UPLOAD_DIR, exist_ok=True)
    for name, upload in zip(names, files):
        name = str(name).strip()
        if name not in EMOTION_SLOTS:
            raise HTTPException(status_code=400, detail=f"未知的情绪立绘：{name}")
        if name in saved:
            continue
        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext not in ALLOWED_AVATAR_EXT:
            raise HTTPException(status_code=400, detail=f"立绘「{name}」仅支持 png/jpg/jpeg/gif/webp 格式")
        if upload.content_type and not upload.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"立绘「{name}」必须是图片文件")
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(EMOTION_UPLOAD_DIR, filename)
        size = 0
        try:
            with open(file_path, "wb") as buffer:
                while chunk := upload.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.MAX_AVATAR_SIZE:
                        raise HTTPException(status_code=400, detail=f"立绘「{name}」文件过大（最大 5MB）")
                    buffer.write(chunk)
        except HTTPException:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"[page_service] 保存情绪立绘失败: {e}")
            continue
        saved[name] = f"/static/uploads/emotions/{filename}"
    return saved


def remove_emotion_files(emotions: Optional[dict], names: Optional[List[str]] = None) -> None:
    """删除情绪立绘文件；names 为 None 时删除全部。"""
    if not emotions:
        return
    target = list(names) if names else list(emotions.keys())
    for name in target:
        url = emotions.get(name)
        if not url or not str(url).startswith("/static/uploads/emotions/"):
            continue
        try:
            path = os.path.join("app", str(url).lstrip("/"))
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print(f"[page_service] 删除情绪立绘失败: {e}")


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
        emotion_names: Optional[List[str]] = None,
        emotion_files: Optional[List[UploadFile]] = None,
    ) -> PageModel:
        title = title.strip()
        if not title or len(title) > 255:
            raise HTTPException(status_code=400, detail="标题不能为空且不超过 255 字")
        body = body or ""
        clean_url = validate_url(url)
        if self.db.query(PageModel).filter(PageModel.url == clean_url).first():
            raise HTTPException(status_code=400, detail="该下载链接已被其他角色使用")

        settings_dict = settings if isinstance(settings, dict) else {}
        # 目录名校验（参照 LingChat resource_folder 规则）
        if settings_dict.get("resource_folder"):
            validate_resource_folder(settings_dict.get("resource_folder"))

        avatar_url = save_avatar(avatar_file)
        emotions = save_emotion_files(emotion_names, emotion_files)

        page = PageModel(
            uid=str(uuid.uuid4()),
            title=title,
            body=body,
            url=clean_url,
            uploader=uploader,
            avatar_url=avatar_url,
            settings=settings_dict,
            emotions=emotions,
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
        emotion_names: Optional[List[str]] = None,
        emotion_files: Optional[List[UploadFile]] = None,
        clear_emotions: bool = False,
        remove_emotion_names: Optional[List[str]] = None,
    ) -> PageModel:
        page = self.get_by_uid(uid, include_removed=True)
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")

        if clear_emotions:
            remove_emotion_files(page.emotions or {})
            page.emotions = {}

        # 按名称移除单个情绪立绘
        remove_names = [str(n).strip() for n in (remove_emotion_names or []) if str(n).strip()]
        if remove_names:
            remove_emotion_files(page.emotions or {}, remove_names)
            page.emotions = {
                k: v for k, v in (page.emotions or {}).items() if k not in remove_names
            }

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
        if page.settings.get("resource_folder"):
            validate_resource_folder(page.settings.get("resource_folder"))

        if avatar_file is not None:
            remove_avatar_file(page.avatar_url)
            page.avatar_url = save_avatar(avatar_file)

        if tags is not None:
            page.tags = []
            self._attach_tags(page, tags)

        # 新上传的情绪立绘按名称覆盖旧文件
        new_emotions = save_emotion_files(emotion_names, emotion_files)
        if new_emotions:
            old = page.emotions or {}
            for name, url in new_emotions.items():
                if old.get(name):
                    remove_emotion_files(old, [name])
            merged = dict(old)
            merged.update(new_emotions)
            page.emotions = merged

        self.db.commit()
        self.db.refresh(page)
        return page

    def delete(self, uid: str) -> None:
        page = self.get_by_uid(uid, include_removed=True)
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")
        remove_avatar_file(page.avatar_url)
        remove_emotion_files(page.emotions or {})
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
