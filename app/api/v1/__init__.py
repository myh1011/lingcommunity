from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__)

# package init for API v1
from .pages import router as pages_router
from .auth import router as auth_router
from .admin import router as admin_router  # 新增管理员路由