"""数据库初始化：创建缺失的表/列 + 种子管理员。

对已有数据库做幂等的轻量迁移（create_all 不会为旧表补列）。
"""
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

from app.config import settings
from app.db.database import Base, engine, SessionLocal
from app.models import User, UserRole
from app.services.user_service import hash_password

# 需要补的列：(表名, 列名, MySQL DDL, SQLite/其他 DDL)
COLUMN_MIGRATIONS = [
    ("pages", "uid", "ALTER TABLE pages ADD COLUMN uid VARCHAR(36) DEFAULT NULL", "ALTER TABLE pages ADD COLUMN uid VARCHAR(36)"),
    ("pages", "uploader", "ALTER TABLE pages ADD COLUMN uploader VARCHAR(100) DEFAULT NULL", "ALTER TABLE pages ADD COLUMN uploader VARCHAR(100)"),
    ("pages", "avatar_url", "ALTER TABLE pages ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL", "ALTER TABLE pages ADD COLUMN avatar_url VARCHAR(500)"),
    ("pages", "created_at", "ALTER TABLE pages ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "ALTER TABLE pages ADD COLUMN created_at DATETIME"),
    ("pages", "download_count", "ALTER TABLE pages ADD COLUMN download_count INT DEFAULT 0", "ALTER TABLE pages ADD COLUMN download_count INTEGER DEFAULT 0"),
    ("pages", "status", "ALTER TABLE pages ADD COLUMN status VARCHAR(20) DEFAULT 'published'", "ALTER TABLE pages ADD COLUMN status VARCHAR(20) DEFAULT 'published'"),
    ("pages", "settings", "ALTER TABLE pages ADD COLUMN settings JSON DEFAULT NULL", "ALTER TABLE pages ADD COLUMN settings TEXT DEFAULT NULL"),
    ("pages", "emotions", "ALTER TABLE pages ADD COLUMN emotions JSON DEFAULT NULL", "ALTER TABLE pages ADD COLUMN emotions TEXT DEFAULT NULL"),
    ("users", "role", "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'", "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"),
    ("users", "is_active", "ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1", "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"),
    ("users", "created_at", "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "ALTER TABLE users ADD COLUMN created_at DATETIME"),
]


def _ensure_columns(conn) -> None:
    inspector = inspect(conn)
    dialect = conn.dialect.name
    existing_tables = set(inspector.get_table_names())
    for table, column, mysql_ddl, other_ddl in COLUMN_MIGRATIONS:
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if column in cols:
            continue
        ddl = mysql_ddl if dialect == "mysql" else other_ddl
        try:
            conn.execute(text(ddl))
            print(f"[init_db] 已为 {table} 添加列 {column}")
        except ProgrammingError as e:
            print(f"[init_db] 添加列 {table}.{column} 失败（可能已存在）：{e}")


def _ensure_unique_indexes(conn) -> None:
    """为旧表补 uid 唯一索引（仅 MySQL 需要显式处理）。"""
    if conn.dialect.name != "mysql":
        return
    inspector = inspect(conn)
    if "pages" not in inspector.get_table_names():
        return
    indexes = {ix["name"] for ix in inspector.get_indexes("pages")}
    if "idx_pages_uid" not in indexes:
        try:
            conn.execute(text("CREATE UNIQUE INDEX idx_pages_uid ON pages(uid)"))
            print("[init_db] 已创建 pages.uid 唯一索引")
        except ProgrammingError as e:
            print(f"[init_db] 创建 pages.uid 索引失败：{e}")


def _backfill(conn) -> None:
    """为旧数据补齐 uid。"""
    inspector = inspect(conn)
    if "pages" not in inspector.get_table_names():
        return
    if "uid" not in {c["name"] for c in inspector.get_columns("pages")}:
        return
    rows = conn.execute(text("SELECT id, uid FROM pages WHERE uid IS NULL OR uid = ''")).fetchall()
    for row in rows:
        conn.execute(
            text("UPDATE pages SET uid = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": row[0]},
        )
    if rows:
        print(f"[init_db] 为 {len(rows)} 条旧数据补齐 uid")


def _seed_admin() -> None:
    """用户表为空时创建初始管理员（账号密码来自环境变量）。"""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN.value,
        )
        db.add(admin)
        db.commit()
        print(
            f"[init_db] 已创建初始管理员：{settings.ADMIN_USERNAME} "
            f"（请在 .env 修改 ADMIN_PASSWORD 后重新部署）"
        )
    finally:
        db.close()


def init_db() -> None:
    """幂等的数据库初始化入口。"""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _ensure_columns(conn)
        _backfill(conn)
        _ensure_unique_indexes(conn)
    _seed_admin()
