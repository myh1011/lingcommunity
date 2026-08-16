"""统计业务逻辑：上架趋势、下载趋势、榜单、标签分布。

为保证跨数据库（MySQL/SQLite）一致，时间序列统一先按天聚合再在 Python 中按周/月汇总。
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.page import Page, PageStatus
from app.models.user import User
from app.models.tag import Tag
from app.models.page_tag import page_tags
from app.models.report import Report, ReportStatus
from app.models.download_log import DownloadLog


def _bucketize(daily: Dict[date, int], period: str, end: date) -> List[Dict[str, Any]]:
    """将按天聚合的 {date: count} 汇总为 天/周/月 桶。"""
    buckets: List[Dict[str, Any]] = []
    if period == "day":
        # 天视图直接按日期输出（最近 30 天）
        for i in range(29, -1, -1):
            d = end - timedelta(days=i)
            buckets.append({"label": f"{d:%m-%d}", "count": daily.get(d, 0)})
        return buckets
    if period == "week":
        # 最近 12 周
        for i in range(11, -1, -1):
            monday = end - timedelta(days=end.weekday()) - timedelta(weeks=i)
            sunday = monday + timedelta(days=6)
            count = sum(c for d, c in daily.items() if monday <= d <= sunday)
            buckets.append({"label": f"{monday:%m-%d}~{sunday:%m-%d}", "count": count})
        return buckets
    # month：最近 12 个月
    for i in range(11, -1, -1):
        year, month = end.year, end.month - i
        while month <= 0:
            month += 12
            year -= 1
        first = date(year, month, 1)
        if month == 12:
            last = date(year, month, 31)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        count = sum(c for d, c in daily.items() if first <= d <= last)
        buckets.append({"label": f"{year}-{month:02d}", "count": count})
    return buckets


def _daily_counts(db: Session, model, dt_column, start: date) -> Dict[date, int]:
    """按天聚合某张表在 start 之后的记录数。"""
    rows = (
        db.query(func.date(dt_column).label("d"), func.count())
        .filter(dt_column >= datetime.combine(start, datetime.min.time()))
        .group_by("d")
        .all()
    )
    return {datetime.fromisoformat(str(d)).date(): c for d, c in rows}


class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def public_summary(self) -> Dict[str, Any]:
        """首页公开概览。"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        def count_pages(since: Optional[date] = None):
            q = self.db.query(func.count(Page.id)).filter(Page.status == PageStatus.PUBLISHED)
            if since:
                q = q.filter(Page.created_at >= datetime.combine(since, datetime.min.time()))
            return q.scalar() or 0

        return {
            "total_pages": count_pages(),
            "total_users": self.db.query(func.count(User.id)).scalar() or 0,
            "total_downloads": self.db.query(func.coalesce(func.sum(Page.download_count), 0)).scalar() or 0,
            "today_pages": count_pages(today),
            "week_pages": count_pages(week_start),
            "month_pages": count_pages(month_start),
            "top_tags": [tag.name for tag, _ in self.top_tags(8)],
        }

    def admin_summary(self) -> Dict[str, Any]:
        summary = self.public_summary()
        summary["pending_reports"] = (
            self.db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING).scalar() or 0
        )
        summary["removed_pages"] = (
            self.db.query(func.count(Page.id)).filter(Page.status == PageStatus.REMOVED).scalar() or 0
        )
        return summary

    def upload_series(self, period: str = "month") -> Dict[str, Any]:
        end = datetime.now().date()
        start = end - timedelta(days=365)
        daily = _daily_counts(self.db, Page, Page.created_at, start)
        buckets = _bucketize(daily, period, end)
        return {"buckets": buckets, "total": sum(b["count"] for b in buckets)}

    def download_series(self, period: str = "month") -> Dict[str, Any]:
        end = datetime.now().date()
        start = end - timedelta(days=365)
        try:
            daily = _daily_counts(self.db, DownloadLog, DownloadLog.downloaded_at, start)
        except Exception as e:
            # 下载日志表不可用（未迁移）时回退为 0
            print(f"[stats] 下载日志查询失败，回退为空: {e}")
            daily = {}
        buckets = _bucketize(daily, period, end)
        return {"buckets": buckets, "total": sum(b["count"] for b in buckets)}

    def download_rankings(self, limit: int = 10, period: Optional[str] = None) -> List[Dict[str, Any]]:
        """内容下载榜单；period 为 today/week/month 时基于日志统计，否则用累计计数。"""
        if period in ("day", "week", "month"):
            end = datetime.now().date()
            if period == "day":
                start = end
            elif period == "week":
                start = end - timedelta(days=end.weekday())
            else:
                start = end.replace(day=1)
            since = datetime.combine(start, datetime.min.time())
            rows = (
                self.db.query(
                    DownloadLog.page_uid,
                    func.count(DownloadLog.id).label("cnt"),
                )
                .filter(DownloadLog.downloaded_at >= since)
                .group_by(DownloadLog.page_uid)
                .order_by(func.count(DownloadLog.id).desc())
                .limit(limit)
                .all()
            )
            result = []
            for uid, cnt in rows:
                page = self.db.query(Page).filter(Page.uid == uid).first()
                if not page:
                    continue
                result.append(
                    {
                        "uid": page.uid,
                        "title": page.title,
                        "uploader": page.uploader,
                        "avatar_url": page.avatar_url,
                        "download_count": cnt,
                        "created_at": page.created_at,
                    }
                )
            return result

        pages = (
            self.db.query(Page)
            .filter(Page.status == PageStatus.PUBLISHED)
            .order_by(Page.download_count.desc(), Page.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "uid": p.uid,
                "title": p.title,
                "uploader": p.uploader,
                "avatar_url": p.avatar_url,
                "download_count": p.download_count or 0,
                "created_at": p.created_at,
            }
            for p in pages
        ]

    def top_tags(self, limit: int = 10):
        return (
            self.db.query(Tag, func.count(page_tags.c.page_id).label("count"))
            .join(page_tags)
            .group_by(Tag.id)
            .order_by(func.count(page_tags.c.page_id).desc())
            .limit(limit)
            .all()
        )

    def tag_distribution(self) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(Tag, func.count(page_tags.c.page_id).label("count"))
            .outerjoin(page_tags)
            .group_by(Tag.id)
            .order_by(func.count(page_tags.c.page_id).desc())
            .all()
        )
        return [{"name": t.name, "color": t.color, "count": c or 0} for t, c in rows]
