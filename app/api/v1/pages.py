"""角色（内容）接口：列表/创建/详情/更新/删除/下载/举报/标签。"""
from typing import Optional, List
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.page import Page
from app.models.user import User
from app.schemas.page import (
    PageListOut,
    PageListResult,
    PageOut,
    PageReportCreate,
    RankingItem,
    TagBase,
)
from app.schemas.report import ReportOut
from app.services.page_service import PageService
from app.services.report_service import ReportService

router = APIRouter()


def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


def _to_list_out(page: Page) -> PageListOut:
    return PageListOut(
        id=page.id,
        uid=page.uid,
        title=page.title,
        url=page.url,
        uploader=page.uploader,
        avatar_url=page.avatar_url,
        created_at=page.created_at,
        download_count=page.download_count or 0,
        status=page.status,
        tags=[tag.name for tag in page.tags] if page.tags else [],
    )


def _to_out(page: Page) -> PageOut:
    return PageOut(
        id=page.id,
        uid=page.uid,
        title=page.title,
        body=page.body,
        url=page.url,
        uploader=page.uploader,
        avatar_url=page.avatar_url,
        created_at=page.created_at,
        download_count=page.download_count or 0,
        status=page.status,
        settings=page.settings or {},
        tags=[tag.name for tag in page.tags] if page.tags else [],
        tag_objects=[TagBase(id=tag.id, name=tag.name, color=tag.color) for tag in page.tags]
        if page.tags
        else [],
    )


# ---------- 标签 ----------

@router.get("/tags", response_model=List[TagBase])
async def get_all_tags(page_service: PageService = Depends(get_page_service)):
    return page_service.get_all_tags()


# ---------- 下载榜单（需在 /{uid} 之前注册） ----------

@router.get("/rankings", response_model=List[RankingItem])
async def rankings(
    limit: int = Query(10, ge=1, le=50),
    page_service: PageService = Depends(get_page_service),
):
    return [
        RankingItem(
            uid=p.uid,
            title=p.title,
            uploader=p.uploader,
            avatar_url=p.avatar_url,
            download_count=p.download_count or 0,
            created_at=p.created_at,
        )
        for p in page_service.get_rankings(limit)
    ]


# ---------- 列表 ----------

@router.get("", response_model=PageListResult)
@router.get("/", response_model=PageListResult)
async def list_pages(
    query: Optional[str] = Query(None, max_length=100),
    tag: Optional[str] = Query(None, max_length=50),
    sort: str = Query("latest", pattern="^(latest|downloads)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    page_service: PageService = Depends(get_page_service),
):
    items, total, page, page_size, total_pages = page_service.list_pages(
        query=query, tag=tag, sort=sort, page=page, page_size=page_size
    )
    return PageListResult(
        items=[_to_list_out(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------- 创建 ----------

@router.post("", response_model=PageOut)
@router.post("/", response_model=PageOut)
async def create_page(
    title: str = Form(..., max_length=255),
    body: str = Form(""),
    url: str = Form(...),
    tags: str = Form(""),
    settings: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    page_service: PageService = Depends(get_page_service),
):
    """创建角色（需登录）。settings 为 JSON 字符串，包含角色创建器的结构化设定。"""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    settings_dict = None
    if settings:
        try:
            settings_dict = json.loads(settings)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="settings 不是合法的 JSON")
        if not isinstance(settings_dict, dict):
            raise HTTPException(status_code=400, detail="settings 必须是 JSON 对象")

    page = page_service.create(
        title=title,
        body=body,
        url=url,
        uploader=current_user.username,
        avatar_file=avatar,
        tags=tag_list,
        settings=settings_dict,
    )
    return _to_out(page)


# ---------- 详情 / 更新 / 删除 ----------

@router.get("/{uid}", response_model=PageOut)
async def read_page(uid: str, page_service: PageService = Depends(get_page_service)):
    page = page_service.get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="角色不存在或已下架")
    return _to_out(page)


@router.put("/{uid}", response_model=PageOut)
async def update_page(
    uid: str,
    title: Optional[str] = Form(None, max_length=255),
    body: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    clear_avatar: bool = Form(False),
    current_user: User = Depends(get_current_user),
    page_service: PageService = Depends(get_page_service),
):
    """更新角色（所有者或管理员）。"""
    existing = page_service.get_by_uid(uid, include_removed=True)
    if not existing:
        raise HTTPException(status_code=404, detail="角色不存在")
    if existing.uploader != current_user.username and not current_user.is_admin():
        raise HTTPException(status_code=403, detail="只有上传者或管理员可以修改此角色")

    settings_dict = None
    if settings is not None:
        try:
            settings_dict = json.loads(settings)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="settings 不是合法的 JSON")
        if not isinstance(settings_dict, dict):
            raise HTTPException(status_code=400, detail="settings 必须是 JSON 对象")

    tag_list = None
    if tags is not None:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if clear_avatar:
        from app.services.page_service import remove_avatar_file
        remove_avatar_file(existing.avatar_url)
        existing.avatar_url = None

    page = page_service.update(
        uid=uid,
        title=title,
        body=body,
        url=url,
        avatar_file=avatar,
        tags=tag_list,
        settings=settings_dict,
    )
    return _to_out(page)


@router.delete("/{uid}")
async def delete_page(
    uid: str,
    current_user: User = Depends(get_current_user),
    page_service: PageService = Depends(get_page_service),
):
    """删除角色（所有者或管理员）。"""
    page = page_service.get_by_uid(uid, include_removed=True)
    if not page:
        raise HTTPException(status_code=404, detail="角色不存在")
    if page.uploader != current_user.username and not current_user.is_admin():
        raise HTTPException(status_code=403, detail="只有上传者或管理员可以删除此角色")
    page_service.delete(uid)
    return {"detail": "deleted"}


# ---------- 下载 ----------

@router.get("/{uid}/download")
async def download_page(
    uid: str,
    request: Request,
    page_service: PageService = Depends(get_page_service),
):
    """记录一次下载并 302 跳转到外部下载链接。"""
    page = page_service.get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="角色不存在或已下架")
    client_ip = request.client.host if request.client else None
    page_service.record_download(page, client_ip)
    return RedirectResponse(url=page.url, status_code=302)


# ---------- 举报 ----------

@router.post("/{uid}/report", response_model=ReportOut)
async def report_page(
    uid: str,
    payload: PageReportCreate,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """举报角色（需登录）。"""
    report = report_service.create(uid, current_user.username, payload.category, payload.reason)
    return ReportOut.model_validate(report)
