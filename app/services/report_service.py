"""举报业务逻辑。"""
from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus, REPORT_CATEGORIES
from app.models.page import Page, PageStatus


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, page_uid: str, reporter: str, category: str, reason: str) -> Report:
        page = self.db.query(Page).filter(Page.uid == page_uid).first()
        if not page:
            raise HTTPException(status_code=404, detail="角色不存在")
        if category not in REPORT_CATEGORIES:
            raise HTTPException(status_code=400, detail="举报类型无效")
        reason = (reason or "").strip()[:1000]
        if not reason:
            raise HTTPException(status_code=400, detail="请填写举报理由")

        # 同一用户对同一内容已有待处理举报时直接复用，保留首次举报内容
        existing = (
            self.db.query(Report)
            .filter(
                Report.page_uid == page_uid,
                Report.reporter == reporter,
                Report.status == ReportStatus.PENDING,
            )
            .first()
        )
        if existing:
            return existing

        report = Report(
            page_id=page.id,
            page_uid=page.uid,
            page_title=page.title,
            reporter=reporter,
            category=category,
            reason=reason,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def list_reports(self, status: Optional[str] = None, page: int = 1, page_size: int = 20):
        q = self.db.query(Report)
        if status:
            q = q.filter(Report.status == status)
        total = q.count()
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = max(1, min(page, total_pages))
        items = q.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total, page, page_size, total_pages

    def review(self, report_id: int, action: str, remove_page: bool, note: str, handler: str) -> Report:
        if action not in ("approve", "reject"):
            raise HTTPException(status_code=400, detail="无效的处理动作")
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="举报不存在")
        if report.status != ReportStatus.PENDING:
            raise HTTPException(status_code=400, detail="该举报已处理过")

        report.status = ReportStatus.APPROVED if action == "approve" else ReportStatus.REJECTED
        report.handled_by = handler
        report.handled_note = (note or "").strip()[:500]
        report.handled_at = datetime.now()

        # 通过举报且选择下架内容时，同步下架对应角色
        if action == "approve" and remove_page and report.page_uid:
            page = self.db.query(Page).filter(Page.uid == report.page_uid).first()
            if page:
                page.status = PageStatus.REMOVED

        self.db.commit()
        self.db.refresh(report)
        return report
