from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__)

# package init for API v1
from .pages import router as pages_router
from .auth import router as auth_router