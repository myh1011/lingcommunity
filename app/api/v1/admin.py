from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Date, cast
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.db.database import get_db
from app.services.page_service import PageService
from app.services.user_service import UserService
from app.models.page import Page
from app.models.user import User
from app.models.tag import Tag
from app.models.page_tag import page_tags

router = APIRouter()

def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@router.get("/stats")
async def get_admin_stats(
    days: int = 30,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    db: Session = Depends(get_db)
):
    """获取管理员统计数据"""
    
    # 获取总角色数和总用户数
    total_pages = db.query(func.count(Page.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    
    # 获取今日新增角色
    today = datetime.now().date()
    today_pages = db.query(func.count(Page.id)).filter(
        func.date(Page.created_at) == today
    ).scalar() or 0
    
    # 获取每日统计
    daily_stats = []
    for i in range(days):
        date = today - timedelta(days=i)
        
        # 当日新增角色数
        page_count = db.query(func.count(Page.id)).filter(
            func.date(Page.created_at) == date
        ).scalar() or 0
        
        # 当日新增用户数
        user_count = db.query(func.count(User.id)).filter(
            func.date(User.created_at) == date  # 需要给User模型添加created_at字段
        ).scalar() or 0
        
        # 当日热门标签
        top_tags = db.query(
            Tag.name,
            func.count(page_tags.c.page_id).label('count')
        ).join(
            page_tags
        ).join(
            Page
        ).filter(
            func.date(Page.created_at) == date
        ).group_by(
            Tag.id
        ).order_by(
            func.count(page_tags.c.page_id).desc()
        ).limit(3).all()
        
        daily_stats.append({
            "date": date.strftime("%Y-%m-%d"),
            "count": page_count,
            "new_users": user_count,
            "top_tags": [tag[0] for tag in top_tags]
        })
    
    # 获取热门标签
    popular_tags = page_service.get_popular_tags(limit=5)
    top_tags = [tag[0].name for tag in popular_tags]
    
    return {
        "total_pages": total_pages,
        "total_users": total_users,
        "today_pages": today_pages,
        "daily_stats": list(reversed(daily_stats)),  # 从旧到新排序
        "top_tags": top_tags
    }

@router.get("/tags")
async def get_all_tags_with_count(db: Session = Depends(get_db)):
    """获取所有标签及其使用次数"""
    tags = db.query(
        Tag,
        func.count(page_tags.c.page_id).label('count')
    ).outerjoin(
        page_tags
    ).group_by(
        Tag.id
    ).order_by(
        Tag.name
    ).all()
    
    return [
        {
            "id": tag[0].id,
            "name": tag[0].name,
            "color": tag[0].color,
            "count": tag[1] or 0
        }
        for tag in tags
    ]

@router.post("/tags")
async def create_tag(
    name: str,
    color: str = "#3b82f6",
    db: Session = Depends(get_db)
):
    """创建新标签"""
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签已存在")
    
    tag = Tag(name=name, color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return {"id": tag.id, "name": tag.name, "color": tag.color}

@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """删除标签"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    db.delete(tag)
    db.commit()
    
    return {"detail": "标签已删除"}