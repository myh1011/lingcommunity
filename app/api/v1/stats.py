"""公开统计接口（首页概览 + 下载榜单）。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.stats_service import StatsService

router = APIRouter()


def get_stats_service(db: Session = Depends(get_db)) -> StatsService:
    return StatsService(db)


@router.get("/summary")
async def public_summary(stats: StatsService = Depends(get_stats_service)):
    return stats.public_summary()


@router.get("/rankings")
async def public_rankings(
    limit: int = Query(10, ge=1, le=50),
    period: str = Query("all", pattern="^(all|day|week|month)$"),
    stats: StatsService = Depends(get_stats_service),
):
    """公开的内容下载榜单。"""
    return stats.download_rankings(limit=limit, period=period)
