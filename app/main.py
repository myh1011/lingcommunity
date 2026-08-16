"""FastAPI 应用入口。"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import router as auth_router
from app.api.v1.pages import router as pages_router
from app.api.v1.admin import router as admin_router
from app.api.v1.stats import router as stats_router
from app.config import settings
from app.db.database import get_db
from app.db.init_db import init_db
from app.services.page_service import PageService

# 静态目录（头像上传）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("app/static", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LingChat Communitymods", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(pages_router, prefix="/api/v1/pages", tags=["pages"])
app.include_router(stats_router, prefix="/api/v1/stats", tags=["stats"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ================= 全局异常处理 =================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "请求参数不合法", "errors": exc.errors()})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "数据库操作失败，请稍后重试"})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# ================= 页面路由 =================

@app.get("/")
async def read_start(request: Request):
    return templates.TemplateResponse("start.html", {"request": request})


@app.get("/create")
async def create_page_view(request: Request):
    """上传已有角色（快捷表单）。"""
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/make")
async def make_page_view(request: Request):
    """角色创建器（参照 LingChat 的字段结构）。"""
    return templates.TemplateResponse("make.html", {"request": request})


@app.get("/login")
async def login_view(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
async def register_view(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/pages")
async def list_page_view(request: Request):
    return templates.TemplateResponse("list.html", {"request": request})


@app.get("/download_url")
async def download_url_view(request: Request):
    return templates.TemplateResponse("download_url.html", {"request": request})


@app.get("/admin")
async def admin_view(request: Request):
    """管理员后台（权限由前端 /api/v1/auth/me + 后台接口双重校验）。"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/page/{uid}")
async def render_page(request: Request, uid: str, db: Session = Depends(get_db)):
    page = PageService(db).get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return templates.TemplateResponse(
        "page.html",
        {
            "request": request,
            "page": page,
            "tags": [{"name": t.name, "color": t.color} for t in page.tags],
        },
    )
