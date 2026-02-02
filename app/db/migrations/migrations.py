
"""
数据库迁移脚本
运行此脚本以添加标签相关表
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine, Base
from app.models.page import Page
from app.models.tag import Tag
from app.models.page_tag import page_tags

def migrate():
    print("开始数据库迁移...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 所有表已创建")
    
    # 检查并添加 User 表的 created_at 字段（用于统计）
    try:
        with engine.begin() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'created_at'"))
            if not result.fetchone():
                conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("✅ 已为 users 表添加 created_at 字段")
            else:
                print("ℹ️  users 表已存在 created_at 字段")
    except Exception as e:
        print(f"⚠️  检查 users 表时出错: {e}")
    
    print("数据库迁移完成！")

if __name__ == "__main__":
    migrate()
