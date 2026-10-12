# 企业知识库 AI 全栈应用

面向企业制度与 SOP 的知识助手：React + TypeScript 前端、FastAPI 后端、PostgreSQL + pgvector，支持用户登录、私有知识库、多 PDF 入库、持久化会话、真实流式回答、原文来源核对和无证据拒答。

本项目用于求职作品展示与小规模试用。旧 RAG 基线保留在 Service、评测与历史文档中；主应用统一使用带权限的 `/api`，旧 `/chat`、`/history`、`/upload`、`/rag/chat` 和无前缀知识库接口不再开放。

## 第一轮升级资料

- [升级计划、接口契约与验收记录](docs/AI全栈第一轮升级计划.md)
- [运行与面试指南](docs/AI全栈第一轮-运行与面试指南.md)
- [真实模型验收记录](docs/真实模型验收记录.md)（真实 BGE + DeepSeek，回答与来源核对）
- [原 RAG 检索评测报告](docs/evaluation-report.md)
- [原后端架构说明](docs/architecture.md)（历史基线，用户/会话部分见第一轮指南）

## 产品流程

注册/登录 → 创建知识库 → 上传文本型 PDF → 查看文档状态 → 新建会话 → 提问/追问 → 流式阅读 → 展开来源 → 刷新恢复历史。

- 用户只能访问自己的知识库、文档、会话及消息；资源不存在或越权返回 404。
- 密码使用 PBKDF2 哈希；随机登录令牌放在 HttpOnly cookie，数据库只保存摘要；退出登录会撤销会话。
- 文档处理成功才进入 ready 状态；失败回滚 Chunk 并保留安全的 failed 状态。
- 回答保存生成状态、文本与来源，支持停止生成、失败提示和刷新后核对。
- 参考来源包括文档名、页码、Chunk 原文和分数；来源分数不是答案正确概率。

## 技术与数据

```text
浏览器 React/TypeScript
  → 同源 /api（开发 Vite 代理；Compose Nginx 代理）
  → FastAPI：认证 → 资源授权 → 文档/会话/RAG 编排
  → PostgreSQL：用户、登录会话、知识库、文档、Chunk、会话、消息
  → BGE 中文 Embedding + pgvector 检索 → LLM 流 → SSE → 浏览器
```

使用既有 `BAAI/bge-small-zh-v1.5` 512 维向量与 Top-3 检索。默认阈值仍为 0.55，通过 `RAG_MIN_RELEVANCE_SCORE` 配置；旧小样本实验推荐的 0.65 尚不代表普适最优值。

## Docker Compose 运行

准备 Docker Desktop（Linux 引擎）及本地配置：

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

修改 `.env` 的数据库密码。生成式回答还需要配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`；凭据仅放后端环境，禁止写进前端或提交到 Git。浏览器地址与 `APP_ORIGIN` 保持一致。

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps --all
```

- Web：`http://localhost:8080`，首次访问自行注册，没有硬编码演示密码。
- API 文档：`http://127.0.0.1:8000/docs`。
- 健康检查：`http://127.0.0.1:8000/health`。
- 顺序：数据库 healthy → Alembic 迁移成功 → API healthy → Web。
- Embedding 首次使用时加载/下载，模型缓存由命名 Volume 保留；首次上传可能较慢。
- PostgreSQL 数据由命名 Volume 保存；停止服务使用 `docker compose stop`，保留数据。
- 本轮 API 采用单 worker；启动时将遗留 generating 消息标为 interrupted。多 worker 的恢复租约属于后续升级。

本地 HTTP 使用 `AUTH_COOKIE_SECURE=false`。正式 HTTPS 部署设置为 true，并配置实际 `APP_ORIGIN` 与可信代理；这里提供部署文件，不会自动公开发布应用。

### Windows 下镜像认证连接超时

本机已验证：直接访问 `auth.docker.io` 超时，使用正在运行的本地 HTTP 代理 `127.0.0.1:7877` 可以访问认证服务。还出现过 `docker pull` 成功而 Compose/BuildKit 认证超时的差异；在执行构建的同一个 PowerShell 中设置客户端代理后，三个基础镜像认证和拉取均通过。

```powershell
# 端口必须与自己的 HTTP/Mixed 代理一致；7877 是本机已验证的端口
$env:HTTP_PROXY='http://127.0.0.1:7877'
$env:HTTPS_PROXY='http://127.0.0.1:7877'
$env:NO_PROXY='localhost,127.0.0.1,::1'
docker buildx imagetools inspect node:22-alpine
docker compose build --build-arg HTTP_PROXY=http://host.docker.internal:7877 --build-arg HTTPS_PROXY=http://host.docker.internal:7877 --build-arg NO_PROXY=localhost,127.0.0.1,::1 api web
docker compose up -d
docker compose ps --all
```

这些变量仅在当前终端及其子进程生效；新开终端需重新设置，并保持代理程序运行。HTTPS_PROXY 的值仍可使用 `http://`，因为这里指 HTTP 代理地址。客户端运行在 Windows，使用 `127.0.0.1`；构建容器中的 `127.0.0.1` 是容器自己，因此 RUN 阶段用 `host.docker.internal` 访问宿主机代理。本机已实际验证该地址可访问 PyPI，避免后端依赖直连下载缓慢。Docker CLI 的代理环境变量、Docker Desktop 的代理设置和 Dockerfile RUN 阶段的代理是不同作用范围；详情见 [Docker CLI 官方说明](https://docs.docker.com/reference/cli/docker/#environment-variables)、[构建代理参数](https://docs.docker.com/build/building/variables/#proxy-arguments) 和 [Desktop 代理设置](https://docs.docker.com/desktop/settings-and-maintenance/settings/#proxies)。镜像认证超时恢复不等于依赖安装或整个部署已完成，最终状态见验收记录。

## 本地前后端开发

后端环境延用已有 `.venv`。数据库启动且配置完成后：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端，Node.js 22.12 或更新版本：

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

浏览器打开 `http://localhost:5173`。Vite 代理 `/api` 到后端；不要直接让前端跨域调用 API。若 `.env` 中有 `APP_ORIGIN`，开发时改为浏览器实际地址。

## 旧知识库数据

升级迁移保留旧知识库、文档和 Chunk。历史知识库的 owner_id 为 NULL，不会自动展示给任意注册用户。先注册，再对每个明确的知识库 ID 执行一次归属分配：

```powershell
docker compose exec api python -m scripts.assign_legacy_knowledge_bases --username alice --knowledge-base-id 1
```

命令仅允许分配一个未归属的知识库，拒绝覆盖已有 owner。请替换真实用户名与 ID；不要将示例 1 当成固定值。

## 自动检查

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

CI 在干净 pgvector 数据库中执行迁移、pytest、前端测试/构建和 Playwright；首次推送后需查看真实 Actions 结果，本地存在工作流文件不等于云端 CI 已运行。

## 已知边界

- 只支持带文字层的 PDF；暂不支持 OCR、扫描件和复杂表格。
- 上传仍同步完成解析与 Embedding，本轮没有后台任务队列或真实百分比进度。
- 来源展示提取的原文，不提供原始 PDF 页面预览。
- 有限历史用于追问上下文，不代表无限记忆。
- 未实现账号找回、企业 SSO、复杂角色/共享权限、计费和生产级滥用防护。
- 既有评测只有 4 份虚构 PDF、18 道题，评测检索与拒答；Recall@3 不能当作最终回答准确率，检索延迟不能当作端到端 SLA。
- 自动化中的模型替身验证交互与工程链路；真实模型效果仍须使用本地 LLM 配置单独核验。
