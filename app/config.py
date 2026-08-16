"""应用配置：统一从环境变量读取。"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 登录令牌有效期（秒），默认 7 天
    TOKEN_TTL: int = int(os.getenv("TOKEN_TTL", str(7 * 24 * 3600)))

    # 初始管理员账号（首次启动时若用户表为空则自动创建）
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "app/static/uploads/avatars")
    MAX_AVATAR_SIZE: int = int(os.getenv("MAX_AVATAR_SIZE", str(5 * 1024 * 1024)))  # 5MB

    # 允许的下载链接协议（安全校验）
    ALLOWED_URL_SCHEMES = ("http", "https")


settings = Settings()
