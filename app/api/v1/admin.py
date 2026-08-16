"""管理员接口：统计图表、内容管理、举报审阅、用户管理、标签管理。

除明确标注外，所有接口均需 admin/super_admin 权限（Bearer 令牌）。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import require_admin, require_super_admin
from app.db.database import get_db
from app.models.page_tag import page_tags
from app.models.report import Report
from app.models.tag import Tag
from app.models.user import User, UserRole
from app.schemas.report import ReportOut, ReportListResult, ReportReview
from app.services.page_service import PageService
from app.services.report_service import ReportService
from app.services.stats_service import StatsService
from app.services.user_service import UserService

router = APIRouter(dependencies=[Depends(require_admin)])


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


class StatusUpdate(BaseModel):
    status: str


class RoleUpdate(BaseModel):
    role: str


class BanUpdate(BaseModel):
    is_active: bool


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#3b82f6", max_length=20)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20)


# ================= 统计与图表 =================

@router.get("/stats/summary")
async def stats_summary(db: Session = Depends(get_db_session)):
    return StatsService(db).admin_summary()


@router.get("/stats/uploads")
async def stats_uploads(
    period: str = Query("week", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db_session),
):
    """内容上架趋势（天/周/月）。"""
    return StatsService(db).upload_series(period)


@router.get("/stats/downloads")
async def stats_downloads(
    period: str = Query("week", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db_session),
):
    """下载趋势（天/周/月）。"""
    return StatsService(db).download_series(period)


@router.get("/stats/rankings")
async def stats_rankings(
    limit: int = Query(10, ge=1, le=50),
    period: str = Query("all", pattern="^(all|day|week|month)$"),
    db: Session = Depends(get_db_session),
):
    """内容下载榜单。"""
    return StatsService(db).download_rankings(limit=limit, period=period)


@router.get("/stats/tags")
async def stats_tags(db: Session = Depends(get_db_session)):
    """标签分布（用于饼图）。"""
    return StatsService(db).tag_distribution()


# ================= 内容管理 =================

@router.get("/pages")
async def admin_pages(
    query: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, pattern="^(published|removed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
):
    items, total, page, page_size, total_pages = PageService(db).list_pages(
        query=query, sort="latest", page=page, page_size=page_size, status=status
    )
    return {
        "items": [
            {
                "id": p.id,
                "uid": p.uid,
                "title": p.title,
                "url": p.url,
                "uploader": p.uploader,
                "avatar_url": p.avatar_url,
                "created_at": p.created_at,
                "download_count": p.download_count or 0,
                "status": p.status,
                "tags": [t.name for t in p.tags] if p.tags else [],
            }
            for p in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.put("/pages/{uid}/status")
async def admin_set_page_status(uid: str, payload: StatusUpdate, db: Session = Depends(get_db_session)):
    """上架/下架内容。"""
    page = PageService(db).set_status(uid, payload.status)
    return {"detail": "ok", "status": page.status}


@router.delete("/pages/{uid}")
async def admin_delete_page(uid: str, db: Session = Depends(get_db_session)):
    PageService(db).delete(uid)
    return {"detail": "deleted"}


# ================= 举报审阅 =================

@router.get("/reports", response_model=ReportListResult)
async def admin_reports(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
):
    items, total, page, page_size, total_pages = ReportService(db).list_reports(
        status=status, page=page, page_size=page_size
    )
    return ReportListResult(
        items=[ReportOut.model_validate(r).model_dump(mode="json") for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/reports/counts")
async def admin_report_counts(db: Session = Depends(get_db_session)):
    """各状态举报数量（用于审阅页选项卡角标）。"""
    rows = db.query(Report.status, func.count(Report.id)).group_by(Report.status).all()
    counts = {"pending": 0, "approved": 0, "rejected": 0}
    for status, cnt in rows:
        counts[status] = cnt
    return counts


@router.post("/reports/{report_id}/review")
async def admin_review_report(
    report_id: int,
    payload: ReportReview,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db_session),
):
    """审阅举报：通过（可选同时下架内容）/ 驳回。"""
    report = ReportService(db).review(
        report_id, payload.action, payload.remove_page, payload.note, admin.username
    )
    return ReportOut.model_validate(report)


# ================= 用户管理 =================

@router.get("/users")
async def admin_users(
    query: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    users, page_counts, total, page, page_size, total_pages = UserService(db).list_users(
        query=query, page=page, page_size=page_size
    )
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "page_count": page_counts.get(u.username, 0),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.put("/users/{user_id}/role")
async def admin_update_role(
    user_id: int,
    payload: RoleUpdate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db_session),
):
    """修改用户角色（仅超级管理员）。"""
    if payload.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="无效的角色")
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    try:
        user = UserService(db).update_role(user_id, payload.role)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"detail": "ok", "username": user.username, "role": user.role}


@router.put("/users/{user_id}/status")
async def admin_update_status(
    user_id: int,
    payload: BanUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db_session),
):
    """封禁/解封用户。"""
    target = UserService(db).get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能封禁自己")
    if target.is_super_admin() and not admin.is_super_admin():
        raise HTTPException(status_code=403, detail="只有超级管理员可以封禁超级管理员")
    user = UserService(db).update_status(user_id, payload.is_active)
    return {"detail": "ok", "username": user.username, "is_active": user.is_active}


# ================= 标签管理 =================

@router.get("/tags")
async def admin_tags(db: Session = Depends(get_db_session)):
    tags = (
        db.query(Tag, func.count(page_tags.c.page_id).label("count"))
        .outerjoin(page_tags)
        .group_by(Tag.id)
        .order_by(Tag.name)
        .all()
    )
    return [{"id": t.id, "name": t.name, "color": t.color, "count": c or 0} for t, c in tags]


@router.post("/tags")
async def admin_create_tag(payload: TagCreate, db: Session = Depends(get_db_session)):
    name = payload.name.strip()
    if db.query(Tag).filter(Tag.name == name).first():
        raise HTTPException(status_code=400, detail="标签已存在")
    tag = Tag(name=name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name, "color": tag.color}


@router.put("/tags/{tag_id}")
async def admin_update_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db_session)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    if payload.name is not None:
        name = payload.name.strip()
        exists = db.query(Tag).filter(Tag.name == name, Tag.id != tag_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="标签已存在")
        tag.name = name
    if payload.color is not None:
        tag.color = payload.color
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name, "color": tag.color}


@router.delete("/tags/{tag_id}")
async def admin_delete_tag(tag_id: int, db: Session = Depends(get_db_session)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(tag)
    db.commit()
    return {"detail": "标签已删除"}
