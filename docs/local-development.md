# 本地开发、测试与旧数据迁移

项目介绍和 Docker Compose 快速启动见 [README](../README.md)，环境故障见 [排障与请求追踪](troubleshooting.md)。以下命令使用 Windows PowerShell；宿主机开发建议 Python 3.11、Node.js 22.12 或更新版本。

## 开发环境准备

在项目根目录执行：

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

已有 `.venv` 时复用即可。配置 `.env` 中的 `POSTGRES_*` 与实际数据库一致，`APP_ORIGIN` 改为 `http://localhost:5173`，本地 HTTP 保持 `AUTH_COOKIE_SECURE=false`。使用非默认宿主机数据库端口时，同时检查 Compose 的 `POSTGRES_HOST_PORT` 和宿主机 Python 使用的 `POSTGRES_PORT`。

完成配置后再启动数据库：

```powershell
docker compose up -d postgres
```

生成式问答需配置后端 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`；模型调用会发送检索原文和有限历史，应使用允许发送的数据。首次 Embedding 推理会加载或下载 BGE 模型。

## 启动前后端

数据库启动并配置完成后，在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端，在项目根目录执行：

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

浏览器打开 `http://localhost:5173`。Vite 将同源 `/api` 代理到 `http://127.0.0.1:8000`，后端校验的 `APP_ORIGIN` 应与浏览器实际地址一致。

## 自动检查

先在单独终端将 `POSTGRES_*` 指向独立 PostgreSQL/pgvector 测试库，并用同一组配置执行 `alembic upgrade head`。下面的 pytest 从这组环境变量读取数据库配置；只设置 `E2E_DATABASE_URL` 不会改变 pytest 的目标数据库。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd test
npm.cmd run build
```

后端完整测试需要已迁移的 PostgreSQL + pgvector；事务夹具在测试后回滚。为避免影响已有数据，建议使用独立测试数据库。

浏览器集成测试启动真实 API 与 Vite，替换外部 Embedding/LLM 推理，验证真实路由、权限、PDF 解析、数据库与 SSE。测试模型文本明确标注“测试模型”，不会进入生产应用。

```powershell
# 在 frontend 目录执行；沿用正确的 POSTGRES_*，使用独立测试库
$env:E2E_DATABASE_URL='postgresql+psycopg://测试用户:测试密码@127.0.0.1:55432/测试数据库'
npx.cmd playwright install chromium
npx.cmd playwright test
```

测试服务仅在 `RAG_E2E_TESTING=1` 时允许启动；Playwright 配置自动设置。未设置 E2E_DATABASE_URL 时会创建一次性 SQLite 测试文件，并使用测试专用余弦 SQL 函数；这不能代替 pgvector 验收。已有 Edge 可通过 `E2E_BROWSER_CHANNEL=msedge` 使用，避免重复下载浏览器。

仓库的 [GitHub Actions 工作流](../.github/workflows/ci.yml) 配置了干净 pgvector 数据库中的迁移、pytest、前端测试/构建和 Playwright。实际执行状态应查看对应提交的 Actions 结果。

## 旧知识库归属分配

升级迁移保留旧知识库、文档和 Chunk。历史知识库的 owner_id 为 NULL，不会自动展示给任意注册用户。先注册，再对每个明确的知识库 ID 执行一次归属分配：

```powershell
docker compose exec api python -m scripts.assign_legacy_knowledge_bases --username alice --knowledge-base-id 1
```

命令仅允许分配一个未归属的知识库，拒绝覆盖已有 owner。请替换真实用户名与 ID；不要将示例 1 当成固定值。

## 历史接口兼容性

主应用统一使用带认证和资源授权的 `/api`。旧 `/chat`、`/history`、`/upload`、`/rag/chat` 和无前缀知识库业务接口已停用；历史 Service 与评测资料保留，用于理解演进和复现实验。
