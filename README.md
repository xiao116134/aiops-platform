# AiOps（前后端分离）

运维平台基础项目，当前已完成：
- 前端：`React + Vite` 登录页（玻璃风 + 机房背景）
- 后端：`FastAPI` 独立服务
- 鉴权：`JWT Access Token + Refresh Token（前端 401 自动刷新并重试）`
- 数据存储：`PostgreSQL`（容器默认，用户、密码、头像）

## 项目结构

```text
AiOps/
├─ src/                  # 前端代码
├─ public/               # 前端静态资源
├─ backend/              # Python 后端（独立服务）
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ schemas.py
│  │  └─ security.py
│  ├─ requirements.txt
│  └─ .env.example
└─ .env.example          # 前端环境变量
```

## 前端启动

```bash
cd <AIOPS_PROJECT_ROOT>
npm install
cp .env.example .env
npm run dev
```

前端默认地址：`http://localhost:5173`

## Docker Compose 部署（推荐）

1) 准备环境变量（生产建议）

```bash
cd <AIOPS_PROJECT_ROOT>
cp .env.compose.example .env.compose
```

编辑 `.env.compose`，至少修改：
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`

2) 启动服务

```bash
docker compose --env-file .env.compose up -d --build
```

仅启动数据库依赖（用于本地直启后端联调）：

```bash
docker compose --env-file .env.compose up -d postgres redis
```

访问地址：`http://localhost:5174`

常用命令：

```bash
# 查看状态
docker compose --env-file .env.compose ps

# 查看日志
docker compose --env-file .env.compose logs -f frontend
docker compose --env-file .env.compose logs -f backend

# 健康检查脚本
sh docker/healthcheck.sh http://localhost:5174 http://localhost:8000

# 停止并保留数据卷
docker compose --env-file .env.compose down

# 停止并删除数据卷（会清空数据库/缓存）
docker compose --env-file .env.compose down -v
```

说明：
- `frontend`：Nginx 托管前端静态文件，开启 gzip 与静态资源缓存，反向代理 `/api`、`/uploads` 到后端。
- `backend`：FastAPI（当前默认连接 `postgres` 容器，`DATABASE_URL` 由 Compose 注入）。
- `postgres`：主数据库容器（通过 volume 持久化）。
- `redis`：缓存/队列预留容器。
- 所有服务已配置日志轮转（`json-file` + `max-size/max-file`）。

## 后端启动

```bash
cd <AIOPS_PROJECT_ROOT>/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端默认地址：`http://localhost:8000`

## 环境变量

### 前端（`<AIOPS_PROJECT_ROOT>/.env`）

- `VITE_API_BASE_URL`：后端 API 地址（默认 `http://localhost:8000`）

### 后端（`<AIOPS_PROJECT_ROOT>/backend/.env`）

- `APP_NAME`：服务名
- `APP_HOST`：监听地址
- `APP_PORT`：监听端口
- `CORS_ORIGINS`：允许跨域来源，英文逗号分隔
- `JWT_SECRET_KEY`：JWT 密钥（生产环境务必修改）
- `JWT_EXPIRE_MINUTES`：Access Token 过期分钟数
- `DATABASE_URL`：PostgreSQL 连接串（Compose 模式自动注入；本地直连需手动配置）

本地开发（非 Compose）建议：

```env
DATABASE_URL=postgresql://aiops:aiops_change_me@localhost:5432/aiops
```

生产 CORS 白名单示例（按你的域名替换）：

```env
CORS_ORIGINS=https://aiops.example.com,https://ops.example.com,http://192.168.0.200:5174
```

## API 说明

### 健康检查

- `GET /health`

### 登录

- `POST /api/login`

请求：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

成功响应：

```json
{
  "token": "<access-token>",
  "refresh_token": "<refresh-token>",
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### 刷新 Access Token

- `POST /api/refresh-token`

请求：

```json
{
  "refresh_token": "<refresh-token>"
}
```

成功响应：

```json
{
  "token": "<new-access-token>"
}
```

### 获取当前用户

- `GET /api/me`
- Header: `Authorization: Bearer <access-token>`
- 前端会在 `401` 时自动调用 `/api/refresh-token` 获取新 access token 并重试当前请求

### 上传头像

- `POST /api/upload-avatar`
- Header: `Authorization: Bearer <access-token>`
- Body: `multipart/form-data`，字段名 `file`
- 支持：`png/jpg/webp`，大小不超过 `2MB`

成功响应：

```json
{
  "message": "头像上传成功",
  "avatar_url": "http://localhost:8000/uploads/avatars/xxx.png"
}
```

### 修改密码

- `POST /api/change-password`
- Header: `Authorization: Bearer <access-token>`

请求：

```json
{
  "old_password": "admin123",
  "new_password": "newpass123"
}
```

成功响应：

```json
{
  "message": "密码修改成功"
}
```

## 后端测试（一键）

```bash
cd <AIOPS_PROJECT_ROOT>
./scripts/test_backend.sh
```

说明：
- 会先确保 `postgres`、`backend` 容器启动
- 然后执行 `backend/tests/test_*.py`（当前包含 `/api/profile` 核心回归）

## PostgreSQL 验证（Compose）

```bash
cd <AIOPS_PROJECT_ROOT>
docker compose --env-file .env.compose exec -T postgres \
  psql -U ${POSTGRES_USER:-aiops} -d ${POSTGRES_DB:-aiops} \
  -c "select username, role from users order by username;"
```

## 测试账号（当前后端内置）

- `admin / admin123`（role: admin）
- `ops / ops123456`（role: ops）
