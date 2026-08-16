# LingChat Communitymods（角色分享社区）

一个用于创建、分享与发现 LingChat 角色的社区网站。用户可上传/创建角色（含头像、标签、下载直链），
浏览与搜索角色、查看下载榜、举报违规内容；管理员后台提供完整的数据图表、内容管理、举报审阅、
用户管理与标签管理。

## 功能

- 角色浏览：搜索、标签筛选、最新/下载量排序、分页、下载榜单
- 角色创建器（/make）：参照 LingChat 角色设置结构，分标签页配置
  - 基本信息：角色名/称号/用户称呼/显示标题/介绍
  - 系统提示词：system_prompt / 示例
  - 立绘设置：缩放/偏移/气泡位置/思考提示语/宠物参数
  - 服装列表：动态添加多个（名称 + 提示词）
  - 语音设置：语音引擎/语言 + 各引擎专属模型字段（按需显隐）
  - 发布：头像上传、标签、下载直链、介绍
- 快捷上传（/create）：仅填写名称/介绍/标签/链接即可发布
- 角色详情：Markdown 介绍、角色设定展示、下载计数、复制链接、举报、编辑/删除（所有者或管理员）
- 举报审阅：用户举报 → 管理员后台审阅（通过/驳回，可通过时一并下架内容）
- 管理员后台（/admin）：
  - 仪表盘：今日/本周/本月上架数、总角色/用户/下载、待审举报、已下架数
  - 上架趋势图（按日/周/月）、下载趋势图（按日/周/月）
  - 内容下载榜单（全部/今日/本周/本月，图表 + 表格）、标签分布饼图
  - 内容管理：搜索、上架/下架、删除
  - 举报审阅：按状态筛选、处理备注
  - 用户管理：角色分配（仅超级管理员）、封禁/解封
  - 标签管理：添加、改色、删除
- 认证：HMAC 签名令牌（7 天有效期）、角色权限（user / admin / super_admin）

## 项目结构

```
app
├── main.py              # FastAPI 入口、页面路由、全局异常处理
├── config.py            # 环境变量配置
├── core/security.py     # 令牌签发/校验、认证依赖
├── db
│   ├── database.py      # 引擎与会话
│   └── init_db.py       # 幂等建表/补列迁移、初始管理员
├── models               # SQLAlchemy 模型（User/Page/Tag/Report/DownloadLog）
├── schemas              # Pydantic 模型
├── services             # 业务逻辑（page/user/report/stats）
├── api/v1               # auth / pages / stats / admin 路由
├── templates            # Jinja2 页面
└── static               # styles.css / js/common.js / uploads
```

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 复制 `.env.example` 为 `.env` 并配置（本地调试可用 SQLite）
3. 启动：`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. 访问 http://localhost:8000

首次启动（用户表为空）会自动创建初始管理员（账号密码见 `.env` 的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`），
请上线前修改密码。

## API 摘要

- 认证：`POST /api/v1/auth/{register,login}`、`GET /api/v1/auth/me`
- 角色：`GET|POST /api/v1/pages`、`GET|PUT|DELETE /api/v1/pages/{uid}`
- 下载：`GET /api/v1/pages/{uid}/download`（计数后 302 跳转）
- 举报：`POST /api/v1/pages/{uid}/report`
- 公开统计：`GET /api/v1/stats/{summary,rankings}`
- 管理员：`/api/v1/admin/{stats/*, pages, reports, users, tags}`（需 Bearer 令牌 + 管理员角色）

## License

MIT
