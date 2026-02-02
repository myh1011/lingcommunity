
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime

from app.db.database import Base, engine, get_db
from app.services.page_service import PageService
from app.api.v1.pages import router as pages_router
from app.api.v1.auth import router as auth_router
from app.models.page import Page
from app.db.database import SessionLocal
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError
from uuid import uuid4

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages_router, prefix="/api/v1/pages", tags=["pages"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

# 创建静态文件目录
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/static/uploads", exist_ok=True)
os.makedirs("app/static/uploads/avatars", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_start(request: Request):
    return templates.TemplateResponse("start.html", {"request": request})

@app.get("/create")
async def create_page_view(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.get("/login")
async def login_view(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_view(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/pages")
async def list_page_view(request: Request):
    return templates.TemplateResponse("list.html", {"request": request})

@app.get("/page/{uid}")
async def render_page(request: Request, uid: str, db: Session = Depends(get_db)):
    page = PageService(db).get_by_uid(uid)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    # 返回页面模板并传入模板所需的字段，避免返回 None 导致前端显示 null
    return templates.TemplateResponse("page.html", {
        "request": request,
        "title": page.title,
        "body": page.body,
        "uid": page.uid,
        "url": page.url,
        "uploader": page.uploader,
        "avatar_url": page.avatar_url,
        "created_at": page.created_at,
        # current_user 由前端 localStorage 管理，后端先传 None
        "current_user": None,
    })
    
@app.get("/download_url")
async def download_url_view(request: Request):
    return templates.TemplateResponse("download_url.html", {"request": request})
    
@app.post("/api/v1/upload/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    # 验证文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    
    # 生成唯一文件名
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4().hex}{file_ext}"
    
    # 保存文件
    file_path = f"app/static/uploads/avatars/{unique_filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="文件保存失败")
    
    # 返回访问URL
    return {"url": f"/static/uploads/avatars/{unique_filename}"}

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'pages' in tables:
            cols = [c['name'] for c in inspector.get_columns('pages')]
            
            # 检查并添加 uid 列
            if 'uid' not in cols:
                print("初始化：pages.uid 列不存在，开始添加并填充 uid ...")
                try:
                    with engine.begin() as conn:
                        conn.execute(text('ALTER TABLE pages ADD COLUMN uid VARCHAR(36) DEFAULT NULL;'))
                    print("已添加列 uid")
                except ProgrammingError as e:
                    print("添加 uid 列时发生错误（可能已存在），继续：", e)

                db = SessionLocal()
                try:
                    rows = db.query(Page).filter(Page.uid == None).all()
                    for r in rows:
                        r.uid = str(uuid4())
                    db.commit()
                    print(f'为 {len(rows)} 行填充 uid')
                finally:
                    db.close()

                try:
                    with engine.begin() as conn:
                        conn.execute(text('ALTER TABLE pages MODIFY uid VARCHAR(36) NOT NULL;'))
                        try:
                            conn.execute(text('create UNIQUE INDEX idx_pages_uid ON pages(uid);'))
                        except ProgrammingError:
                            pass
                    print("uid 已设为 NOT NULL 并确保唯一索引")
                except ProgrammingError as e:
                    print("修改 uid 属性或创建索引时发生错误：", e)

            # 检查并添加 uploader 列
            if 'uploader' not in cols:
                print("初始化：pages.uploader 列不存在，开始添加 uploader 列 ...")
                try:
                    with engine.begin() as conn:
                        conn.execute(text("ALTER TABLE pages ADD COLUMN uploader VARCHAR(100) DEFAULT NULL;"))
                    print("已添加列 uploader")
                except ProgrammingError as e:
                    print("添加 uploader 列时发生错误（可能已存在），继续：", e)
            
            # 检查并添加 avatar_url 列
            if 'avatar_url' not in cols:
                print("初始化：pages.avatar_url 列不存在，开始添加 avatar_url 列 ...")
                try:
                    with engine.begin() as conn:
                        conn.execute(text("ALTER TABLE pages ADD COLUMN avatar_url VARCHAR(255) DEFAULT NULL;"))
                    print("已添加列 avatar_url")
                except ProgrammingError as e:
                    print("添加 avatar_url 列时发生错误（可能已存在），继续：", e)
            
            # 检查并添加 created_at 列
            if 'created_at' not in cols:
                print("初始化：pages.created_at 列不存在，开始添加 created_at 列 ...")
                try:
                    with engine.begin() as conn:
                        conn.execute(text("ALTER TABLE pages ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
                    print("已添加列 created_at")
                except ProgrammingError as e:
                    print("添加 created_at 列时发生错误（可能已存在），继续：", e)
                    
    except Exception as e:
        print("启动时初始化检查失败：", e)
