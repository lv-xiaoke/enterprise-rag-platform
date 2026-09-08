# Day 14：验证 Docker 和干净环境运行流程

今天将直接补齐“PostgreSQL 就绪 → 空库迁移 → API 启动 → 健康检查”的容器化闭环，使项目获得从公开配置复现运行环境的能力，并为面试中的 Docker、迁移顺序与配置安全问题提供可运行项目依据。

> 预计核心用时：约 60 分钟；首次构建镜像、安装依赖和下载 `BAAI/bge-small-zh-v1.5` 的外部耗时不计入核心学习时间  
> 今日唯一核心产物：一套从公开配置启动 PostgreSQL、迁移空数据库并运行 FastAPI 的可复现 Docker Compose 流程  
> 当前真实状态：已完成  
> 对应总体安排：Day 14

## 一、今天完成后的项目变化

### 升级前

```text
docker compose up
→ 只能启动 pgvector/pgvector:pg16 PostgreSQL

Dockerfile
→ 只复制 requirements.txt 和 app/
→ 镜像内没有 alembic.ini 与 migrations/
→ 无法在应用镜像内执行现有 Alembic 迁移

/health
→ 只说明 FastAPI 进程可响应以及 LLM 配置是否齐全
→ 不确认 PostgreSQL 是否可连接

新环境使用者
→ 仍需自行猜测何时迁移、怎样启动 API、容器内数据库主机名是什么
```

### 升级后

```text
公开的 .env.example
→ 复制成被 Git 忽略的本地环境文件
→ Docker Compose 校验三个必需的 PostgreSQL 变量

docker compose up --build
→ PostgreSQL 启动并通过 pg_isready
→ migrate 一次性服务执行 alembic upgrade head
→ migrate 成功退出后 API 才启动
→ API 加载 Embedding 模型并通过数据库感知的 /health

全新 Compose 项目名
→ 获得独立 postgres_data Volume
→ 从空数据库验证 vector 扩展、三张核心表和迁移 head
→ 不触碰 Day 13 已有数据库与数据
```

### 今天在完整项目中的位置

- 所属阶段：质量验收。
- 所属链路：支撑文档入库链路和数据库版 RAG 问答链路的可复现环境基础设施。
- 今天的输入：Day 1～Day 13 已存在的 PostgreSQL 配置、两条 Alembic 迁移、FastAPI API、固定依赖和持久化实现。
- 今天的输出：包含 `postgres`、`migrate`、`api` 三个服务的 Compose 启动顺序，以及公开配置、健康检查、空库迁移往返和最小 HTTP 验收命令。
- 下一天为什么需要它：Day 15 只有引用经过干净环境验证的启动步骤、端口、迁移 head 和限制，才能形成可信的求职版 README。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `Dockerfile` 使用 `python:3.11-slim`，安装 `requirements.txt`，以 Uvicorn 在容器的 `8000` 端口启动 `app.main:app`。
- `[当前事实]` `docker-compose.yml` 已有 `pgvector/pgvector:pg16`、`pg_isready` 健康检查、仅绑定回环地址的数据库端口和 `postgres_data` 命名 Volume。
- `[当前事实]` `.env.example` 已公开 PostgreSQL 示例值，并将三个 LLM 配置留空；真实 `.env` 存在，但已被 `.gitignore` 忽略，且本计划生成过程没有读取其内容。
- `[当前事实]` `.dockerignore` 已排除真实 `.env`、本地虚拟环境、Git 元数据、缓存、学习资料和本地数据。
- `[当前事实]` `requirements.txt` 固定了 FastAPI `0.141.1`、Pydantic `2.13.4`、Uvicorn `0.52.1`、SQLAlchemy `2.0.52`、Alembic `1.19.1`、pgvector `0.5.0`、psycopg `3.3.4` 和 sentence-transformers `5.7.0`。
- `[当前事实]` 项目虚拟环境是 Python `3.11.7`；Dockerfile 固定 Python `3.11` 系列，Compose 固定 PostgreSQL `16` 系列。
- `[当前事实]` Alembic 只有一个 head：`e780fe92751b`；它依赖 `751357b5d274`，迁移顺序为启用 `vector` 扩展后创建 `knowledge_bases`、`documents`、`chunks`。
- `[当前事实]` `/health` 已存在，当前返回 `status` 和 `llm_configured`；`app/db.py` 已提供不回显密码的 `check_database_connection()`。
- `[当前事实]` 2026-09-07 只读检查时 Docker Client/Server 均为 `29.7.2`，Docker Compose 为 `v5.4.0`，当前 Compose 语法校验通过。
- `[当前事实]` Day 13 已有用户完成标记和匹配提交 `0b15e88`；生成 Day 14 前 `git status --short` 为空。

### 仍然缺少

- `[当前事实]` Compose 只有 `postgres` 服务，没有负责执行迁移的单次服务，也没有 API 服务。
- `[当前事实]` Dockerfile 没有复制 `alembic.ini` 和 `migrations/`，所以当前应用镜像不能承载迁移命令。
- `[当前事实]` `/health` 没有查询数据库；仅有 HTTP 200 不能证明 PostgreSQL、连接池和迁移链路可用。
- `[当前事实]` `.gitignore` 只忽略精确文件名 `.env`，尚未保护 `.env.day14`、`.env.local` 等本地环境文件变体。
- `[当前事实]` `.env.example` 尚未区分容器对外端口与应用连接数据库所用的内部主机、端口。
- `[当前事实]` 尚未形成使用独立 Compose 项目名和独立 Volume 从空数据库到迁移 head 的公开步骤。

### 待实测

- `[待实测]` 修改后的镜像是否能安装全部固定依赖并导入 `app.main`。
- `[待实测]` 新的 `migrate` 服务是否在空数据库上升级到 `e780fe92751b` 并以退出码 `0` 结束。
- `[待实测]` `api` 是否只在 PostgreSQL healthy 且迁移成功后启动。
- `[待实测]` 首次启动下载 `BAAI/bge-small-zh-v1.5` 需要的时间与网络条件；模型缓存应写入独立命名 Volume。
- `[待实测]` `/health` 是否返回 `database_connected=true`，以及创建知识库后 PostgreSQL 是否出现对应记录。
- `[待实测]` 缺少 `POSTGRES_PASSWORD` 时，Compose 是否在创建任何容器前明确失败且只报告变量名。

### 需要保护的用户修改

- 当前工作区在生成前是干净的；执行时仍应先运行 `git status --short`，只按今天的明确文件清单操作。
- 不读取、不覆盖现有 `.env`；今天另建被忽略的 `.env.day14`，其中只放公开测试值。
- 不停止、不重建 Day 13 使用的现有 Compose 项目；今天使用带时间戳的新项目名和独立 Volume。
- 不删除任何数据库 Volume、目录或批量文件；迁移回滚只允许在今天新建的隔离数据库中执行。

## 三、今天必须理解的核心知识

### 1. Dockerfile、Image 与 Container

- 一句话解释：Dockerfile 是构建规则，Image 是按规则生成的只读运行模板，Container 是 Image 的一次运行实例。
- 在当前项目中的职责：Dockerfile 把 Python 3.11、系统库、固定 Python 依赖、应用代码和 Alembic 文件装进同一个 API 镜像。
- 与其他组件的关系：`migrate` 与 `api` 复用同一镜像，但用不同命令和生命周期；前者执行一次迁移后退出，后者持续运行 Uvicorn。
- 容易混淆的点：修改 Dockerfile 不会自动改变已存在的容器，必须重新构建镜像并基于新镜像创建容器。
- 面试一句话：当前项目用一个可复用应用镜像承载迁移和 API，避免宿主机 Python 环境与容器运行环境不一致。

### 2. Compose Service、依赖条件与健康检查

- 一句话解释：Compose Service 描述一类容器怎样构建、配置、联网和运行，`depends_on` 的条件决定下游服务何时允许启动。
- 在当前项目中的职责：`postgres` 先通过 `pg_isready`，`migrate` 再执行 `alembic upgrade head`，只有迁移成功退出后 `api` 才启动。
- 与其他组件的关系：服务名 `postgres` 是 Compose 网络中的数据库主机名，容器内部固定连接 `postgres:5432`，宿主机才使用映射端口。
- 容易混淆的点：容器进程处于 running 不代表应用 ready；数据库端口打开也不代表业务表已迁移。
- 面试一句话：我把数据库健康与迁移成功设为 API 启动前置条件，消除了依赖人工等待的隐藏步骤。

### 3. Volume 与干净数据库

- 一句话解释：Volume 是独立于容器生命周期的持久化存储，容器重建并不等于数据被清空。
- 在当前项目中的职责：`postgres_data` 保存 PostgreSQL 数据目录，`huggingface_cache` 保存首次下载的 Embedding 模型缓存。
- 与其他组件的关系：Compose 项目名参与 Volume 实际名称；新的项目名会得到新的空数据库，同时不会触碰 Day 13 的 Volume。
- 容易混淆的点：`docker compose down` 默认不会删除命名 Volume；也绝不能通过删除 Volume 来证明持久化或制造空库。
- 面试一句话：Day 13 用同一个 Volume 验证跨重启持久化，Day 14 用新的 Compose 项目名获得隔离空库验证可复现性，两者验证目标不同。

### 4. `.env.example`、真实 `.env` 与容器环境变量

- 一句话解释：`.env.example` 只描述变量名和安全示例，真实凭据必须留在 Git 之外，再由 Compose 注入容器。
- 在当前项目中的职责：三个 PostgreSQL 变量是启动必需项；LLM 三项对健康检查和知识库 CRUD 是可选的，但对有可靠证据的生成式问答是必需的。
- 与其他组件的关系：宿主机运行 API 时使用 `127.0.0.1:5432`，Compose 中的 API 则由配置覆盖为 `postgres:5432`。
- 容易混淆的点：`docker compose config` 的完整输出会展开变量值，因此安全检查只使用静默校验和服务名输出，不打印完整配置。
- 面试一句话：仓库提交公开变量契约，不提交真实值；启动前先验证必需变量，错误只出现变量名而不出现密码。

### 5. Readiness 与业务最小请求

- 一句话解释：Readiness 用于证明依赖可用，最小业务请求用于证明 API、Session、事务和真实数据库表共同可用。
- 在当前项目中的职责：`/health` 执行 `SELECT 1` 并返回数据库连接状态，`POST /knowledge-bases` 再验证 ORM、Repository、提交和响应序列化。
- 与其他组件的关系：Compose 的 API 健康检查调用 `/health`；业务验收随后直接查询 PostgreSQL 交叉核对记录。
- 容易混淆的点：`llm_configured=false` 不应让基础设施健康检查失败，它明确表示生成式问答尚未注入可选秘密，而不是数据库或 API 不可用。
- 面试一句话：我的健康检查验证基础依赖，最小业务请求验证完整数据访问路径，二者不能互相替代。

## 四、升级涉及的文件

| 文件                      | 操作  | 作用                                                  |
| ----------------------- | --- | --------------------------------------------------- |
| `.gitignore`            | 修改  | 忽略本地环境文件变体，同时保留公开 `.env.example`                    |
| `.dockerignore`         | 修改  | 排除全部本地环境文件、测试缓存和非运行期资料，缩小并保护构建上下文                   |
| `.env.example`          | 修改  | 明确必需、可选、秘密、宿主机端口与容器内部连接边界                           |
| `Dockerfile`            | 修改  | 把 Alembic 配置与迁移脚本装入应用镜像，使迁移和 API 可复用同一镜像            |
| `docker-compose.yml`    | 修改  | 建立 `postgres → migrate → api` 启动顺序、健康检查和两个命名 Volume |
| `app/main.py`           | 修改  | 让 `/health` 检查数据库并在不可用时返回安全的 503                    |
| `docs/17天每日学习/Day14.md` | 新建  | 保存今天的实施、验证、排错和面试手册                                  |

### 今日不做

- 不重写求职版 README、架构图或评测报告；这属于 Day 15。
- 不修改 RAG 检索、拒答阈值、文档入库事务或 API 业务字段。
- 不新增 Kubernetes、云部署、生产监控、反向代理或多阶段镜像优化。
- 不创建新的业务表或新的 Alembic revision；今天只复用并验证现有迁移链。
- 不把 LLM 真实密钥写入计划、`.env.example`、Compose 或任何 Git 跟踪文件。
- 不删除现有容器数据、数据库 Volume、缓存目录或其他文件。

## 五、按顺序完成项目升级

### 步骤 1：收紧公开配置与忽略边界（建议 10 分钟）

**目标**

让使用者能从 `.env.example` 判断变量用途，并确保今天创建的 `.env.day14` 和以后常见的本地环境文件不会进入 Git 或 Docker 构建上下文。

**修改位置**

- 文件：`.gitignore`
- 定位：搜索 `# 环境变量和密钥`
- 操作：保留其他规则，使用下面的完整文件内容替换整份文件。

**复制下面的完整代码**

```gitignore
# Python 虚拟环境
.venv/

# 环境变量和密钥
.env
.env.*
!.env.example

# Python 缓存
__pycache__/
*.py[cod]

# 测试和工具缓存
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE 配置
.vscode/
.idea/

# 操作系统文件
.DS_Store
Thumbs.db

# Obsidian 本地配置
docs/.obsidian/

# SQLite 本地数据库
data/*.db
data/*.db-*

# 本地 PDF 文档
data/documents/
```

- 文件：`.dockerignore`
- 定位：搜索 `# 密钥和本地配置`
- 操作：使用下面的完整文件内容替换整份文件。

```dockerignore
# 本地 Python 环境和缓存
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/

# 密钥和本地配置
.env
.env.*

# Git、编辑器和系统文件
.git/
.gitignore
.vscode/
.idea/
.DS_Store
Thumbs.db

# 运行镜像不需要的测试、学习资料和本地数据
tests/
docs/
scripts/
data/
README.md
requirements-test.txt
requirements-demo.txt
```

- 文件：`.env.example`
- 定位：当前文件全部内容。
- 操作：使用下面的完整文件内容替换整份文件。

```dotenv
# PostgreSQL：启动 Compose 的必需公开示例值
POSTGRES_DB=enterprise_rag
POSTGRES_USER=rag_app
POSTGRES_PASSWORD=change-me-local-only

# 宿主机直接运行 Python 时使用；Compose 内的 API 会覆盖为 postgres:5432
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# 容器映射到宿主机的端口；端口冲突时只修改本地环境文件
POSTGRES_HOST_PORT=5432
API_HOST_PORT=8000

# LLM：健康检查和知识库 CRUD 可留空；执行生成式问答时必须在本地填写
# LLM_API_KEY 是秘密，绝不能提交真实值
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

**这段配置怎样工作**

| 变量                   | 作用                         | 例子                       |
| -------------------- | -------------------------- | ------------------------ |
| `POSTGRES_DB`        | 数据库名称                      | `enterprise_rag`         |
| `POSTGRES_USER`      | PostgreSQL 用户名             | `rag_app`                |
| `POSTGRES_PASSWORD`  | PostgreSQL 密码              | 本地真实密码                   |
| `POSTGRES_HOST`      | Python 去哪里找数据库             | `127.0.0.1` / `postgres` |
| `POSTGRES_PORT`      | Python 连接数据库时使用的端口         | `5432`                   |
| `POSTGRES_HOST_PORT` | Docker PostgreSQL 映射到电脑的端口 | `5432`                   |
| `API_HOST_PORT`      | FastAPI 映射到电脑的端口           | `8000`                   |
| `LLM_API_KEY`        | 模型 API 密钥                  | 保密                       |
| `LLM_BASE_URL`       | 模型 API 地址                  | 某个模型服务地址                 |
| `LLM_MODEL`          | 调用的模型名称                    | 对应模型名称                   |

- 输入：公开变量名、安全示例值以及本地生成的 `.env.day14`。
- 输出：Git 只跟踪 `.env.example`；Docker 构建上下文不包含任何 `.env` 变体。
- 调用谁：Compose 用这些变量完成插值，再将数据库与 LLM 配置注入容器。
- 被谁调用：`docker-compose.yml`、`app/config.py` 和执行计划中的 PowerShell 命令。
- 正常路径：`.env.day14` 被 `.gitignore` 命中，Compose 能读取安全测试值。
- 失败路径：三个必需 PostgreSQL 变量缺失或为空时，Compose 在创建容器前终止。

**完成本步骤后的预期状态**

- `git check-ignore -v .env.day14` 指向 `.gitignore` 中的 `.env.*`。
- `git ls-files -- .env .env.day14` 没有输出。
- `git ls-files -- .env.example` 只输出 `.env.example`。
- 公开文件没有真实 API Key、数据库密码或访问令牌。

### 步骤 2：让应用镜像同时支持迁移与 API（建议 8 分钟）

**目标**

在不引入第二套 Python 环境的前提下，让同一个镜像既能执行 `alembic upgrade head`，又能运行 Uvicorn。

**修改位置**

- 文件：`Dockerfile`
- 定位：搜索 `FROM python:3.11-slim`
- 操作：使用下面的完整内容替换整份文件；原系统依赖安装块也一并替换，不保留其中的批量删除命令。

**复制下面的完整代码**

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1

COPY requirements.txt ./
RUN python -m pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**这段代码怎样工作**

- 输入：Python 3.11 基础镜像、`requirements.txt`、`alembic.ini`、`migrations/` 和 `app/`。
- 输出：工作目录为 `/app`、同时包含 Alembic CLI 所需文件与 FastAPI 代码的应用镜像。
- 调用谁：构建阶段调用 pip 安装固定依赖；默认命令调用 Uvicorn。
- 被谁调用：Compose 的 `migrate` 服务覆盖默认命令执行 Alembic，`api` 服务保留默认命令运行 Uvicorn。
- 正常路径：镜像内执行 `alembic heads` 返回 `e780fe92751b (head)`，执行 Uvicorn 能导入 `app.main`。
- 失败路径：依赖下载、基础镜像获取或模型下载失败时构建/启动非零退出，不能把失败容器当成 ready。

**完成本步骤后的预期状态**

- 镜像构建上下文只包含运行与迁移需要的文件。
- `migrate` 和 `api` 不再依赖宿主机 `.venv`。
- 镜像默认仍以非 reload 模式启动 API，适合可重复验收。

### 步骤 3：建立 `postgres → migrate → api` Compose 闭环（建议 15 分钟）

**目标**

把数据库就绪、迁移完成和 API 可用变成机器可检查的顺序，不再依赖使用者手工等待。

**修改位置**

- 文件：`docker-compose.yml`
- 定位：当前文件全部内容。
- 操作：使用下面的完整内容替换整份文件。

**复制下面的完整代码**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB:?POSTGRES_DB is required}
      POSTGRES_USER: ${POSTGRES_USER:?POSTGRES_USER is required}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    ports:
      - "127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 20

  migrate:
    build:
      context: .
    image: enterprise-rag-api:local
    command: ["alembic", "upgrade", "head"]
    environment: &app_environment
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_DB: ${POSTGRES_DB:?POSTGRES_DB is required}
      POSTGRES_USER: ${POSTGRES_USER:?POSTGRES_USER is required}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      LLM_API_KEY: ${LLM_API_KEY:-}
      LLM_BASE_URL: ${LLM_BASE_URL:-}
      LLM_MODEL: ${LLM_MODEL:-}
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  api:
    build:
      context: .
    image: enterprise-rag-api:local
    environment: *app_environment
    ports:
      - "127.0.0.1:${API_HOST_PORT:-8000}:8000"
    volumes:
      - huggingface_cache:/root/.cache/huggingface
    depends_on:
      migrate:
        condition: service_completed_successfully
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"
      interval: 10s
      timeout: 10s
      retries: 30
      start_period: 10m

volumes:
  postgres_data:
  huggingface_cache:
```

**这段配置怎样工作**

- 输入：`.env.day14` 中的 PostgreSQL 必需值、宿主机映射端口和可选 LLM 配置。
- 输出：一个有独立网络、独立数据库 Volume 和独立模型缓存 Volume 的三服务环境。
- 调用谁：`postgres` 调用 `pg_isready`；`migrate` 调用现有 Alembic head；`api` 调用 Dockerfile 默认 Uvicorn 命令和 `/health`。
- 被谁调用：Docker Compose CLI 与 Day 15 将整理的公开运行文档。
- 正常路径：PostgreSQL healthy 后迁移成功，API 首次下载/加载 BGE 模型，随后健康检查转为 healthy。
- 失败路径：数据库变量缺失会在配置阶段失败；PostgreSQL 不健康会阻止迁移；迁移非零退出会阻止 API 启动；数据库连接异常会让 API 健康检查失败。

**完成本步骤后的预期状态**

- `docker compose config --services` 按定义列出 `postgres`、`migrate`、`api`。
- Compose 网络内 API 使用 `postgres:5432`，不会错误连接自身容器的 `127.0.0.1`。
- LLM 配置留空时 API 仍能健康启动并执行知识库 CRUD，`/health` 明确返回 `llm_configured=false`。
- 首次模型下载可能明显超过 60 分钟时间盒中的代码修改部分，因此健康检查提供 10 分钟启动宽限，并在命令层再提供 20 分钟等待上限。

### 步骤 4：让 `/health` 验证数据库可连接（建议 7 分钟）

**目标**

让 API 健康状态覆盖 FastAPI 进程和 PostgreSQL 连接，同时保持错误信息不泄露连接串或密码。

**修改位置一**

- 文件：`app/main.py`
- 定位：搜索 `from app.db import get_db_session`
- 操作：将这一行完整替换为下面的 import。

**复制下面的完整代码**

```python
from app.db import check_database_connection, get_db_session
```

**修改位置二**

- 文件：`app/main.py`
- 定位：搜索 `@app.get("/health")`
- 操作：从该装饰器开始，完整替换到原 `health()` 函数返回字典结束；不要改动后面的 `/chat` 路由。

**复制下面的完整代码**

```python
@app.get("/health")
async def health(response: Response) -> dict[str, str | bool]:
    try:
        database_connected = check_database_connection() == 1
    except RuntimeError:
        response.status_code = 503
        return {
            "status": "error",
            "database_connected": False,
            "llm_configured": llm_service.is_configured(),
        }

    return {
        "status": "ok",
        "database_connected": database_connected,
        "llm_configured": llm_service.is_configured(),
    }
```

**这段代码怎样工作**

- 输入：一次 `GET /health` 请求，以及 `app/db.py` 中已创建的 Engine。
- 输出：成功时 HTTP `200` 和三个稳定字段；数据库不可连接时 HTTP `503` 和不含内部信息的稳定结构。
- 调用谁：调用 `check_database_connection()`，由 SQLAlchemy 执行 `SELECT 1`。
- 被谁调用：Compose 的 API 健康检查、人工 PowerShell 验收和后续公开 README。
- 正常路径：数据库返回整数 `1`，响应包含 `status=ok`、`database_connected=true`。
- 失败路径：`check_database_connection()` 把底层 SQLAlchemy 异常转换为不含连接串的 `RuntimeError`；路由只返回泛化状态，不回显异常文本。

**完成本步骤后的预期状态**

- PostgreSQL 可用时 `/health` 返回 HTTP `200`。
- PostgreSQL 不可用时 `/health` 返回 HTTP `503`，响应中没有数据库 URL、用户名、密码、主机堆栈或驱动细节。
- LLM 未配置只通过布尔字段表达，不影响数据库/API readiness。

## 六、运行数据库迁移或环境命令

> 今天不新增数据库结构，也不生成新 migration；但必须在全新的隔离数据库上执行现有迁移的 `upgrade → downgrade base → upgrade head` 往返。`downgrade base` 会删除今天隔离库中的三张表和 `vector` 扩展，只能在下面新建的 Day 14 Compose 项目中运行，绝不能对 Day 13 或其他含业务数据的数据库执行。

### 1. 检查当前状态

执行目录：项目根目录。  
执行目的：确认工作区、工具版本、迁移 head 和秘密忽略边界。  
执行顺序：先运行这一组，再修改文件；修改完成后重新运行 `git status --short`。  
预期结果：Docker 与 Compose 可用，项目虚拟环境为 Python 3.11，Alembic head 为 `e780fe92751b`，真实 `.env` 被忽略。

```powershell
git status --short
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}'
docker compose version
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\alembic.exe --version
.\.venv\Scripts\alembic.exe heads
git check-ignore -v .env
git ls-files -- .env .env.example Dockerfile docker-compose.yml
```

如果失败：

- `docker version` 无法返回 Server 版本：启动 Docker Desktop，等待 Engine ready 后重试。
- `.venv` 命令不存在：不在今天安装宿主机依赖；继续使用 Docker 路径，但记录宿主机虚拟环境缺失。
- `alembic heads` 不是唯一的 `e780fe92751b (head)`：停止，不启动 Day 14 环境，先检查 `migrations/versions/` 是否有未预期的分支。
- `git ls-files -- .env` 输出 `.env`：停止，不提交任何内容，先确认它是否误被跟踪；不要打印文件内容。

完成步骤 1～4 的文件修改后，在同一个 PowerShell 窗口创建一个只含公开测试值的本地环境文件。这里使用 `55432` 和 `58000`，避免与常见的现有 `5432`、`8000` 服务冲突；不要改动现有 `.env`。

```powershell
$day14Project = "enterprise-rag-day14-$(Get-Date -Format 'yyyyMMddHHmmss')"
$day14EnvPath = Join-Path (Get-Location) ".env.day14"
$day14EnvLines = @(
    "POSTGRES_DB=enterprise_rag_day14"
    "POSTGRES_USER=rag_app"
    "POSTGRES_PASSWORD=day14-local-only"
    "POSTGRES_HOST=127.0.0.1"
    "POSTGRES_PORT=55432"
    "POSTGRES_HOST_PORT=55432"
    "API_HOST_PORT=58000"
    "LLM_API_KEY="
    "LLM_BASE_URL="
    "LLM_MODEL="
)
[System.IO.File]::WriteAllLines(
    $day14EnvPath,
    $day14EnvLines,
    [System.Text.UTF8Encoding]::new($false)
)
git check-ignore -v .env.day14
docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    config --quiet
docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    config --services
```

预期结果：

- `.env.day14` 被 `.gitignore` 的 `.env.*` 命中。
- `config --quiet` 退出码为 `0`，且不会打印已展开的完整环境配置。
- `config --services` 输出 `postgres`、`migrate`、`api`。
- `$day14Project` 含当前时间戳；后续所有 Compose 命令必须继续使用同一个 PowerShell 窗口中的这两个变量。

如果 `55432` 或 `58000` 已被占用，使用下面的只读命令确认占用者，然后只修改 `.env.day14` 中对应的宿主机端口；容器内部的 PostgreSQL 端口仍是 `5432`，API 端口仍是 `8000`。

```powershell
Get-NetTCPConnection `
    -State Listen `
    -LocalPort 55432,58000 `
    -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

### 2. 执行升级

执行目录：项目根目录，沿用上一节同一个 PowerShell 窗口。  
执行目的：构建应用镜像，在新项目名下创建空数据库，自动升级到 head，并等 API 健康。  
执行顺序：先 `up`，成功后检查服务、镜像内版本、迁移版本和真实表结构。  
预期结果：`postgres` healthy，`migrate` 退出码 `0`，`api` healthy；首次模型下载可能延长等待时间。

```powershell
docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    up --detach --build --wait --wait-timeout 1200

if ($LASTEXITCODE -ne 0) {
    docker compose `
        --project-name $day14Project `
        --env-file $day14EnvPath `
        ps --all
    docker compose `
        --project-name $day14Project `
        --env-file $day14EnvPath `
        logs --tail 100 postgres migrate api
    throw "Day 14 Compose 环境未在等待时间内就绪"
}

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    ps --all

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api python --version

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic heads

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic current

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT version_num FROM alembic_version;"

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT to_regclass('public.knowledge_bases') AS knowledge_bases, to_regclass('public.documents') AS documents, to_regclass('public.chunks') AS chunks;"
```

预期结果：

- 应用容器显示 Python `3.11.x`。
- `alembic heads` 显示 `e780fe92751b (head)`，`alembic current` 显示 `e780fe92751b`。
- `alembic_version.version_num` 是 `e780fe92751b`。
- `pg_extension` 查询返回一行 `vector`。
- `to_regclass` 的三个结果分别是 `knowledge_bases`、`documents`、`chunks`。
- `migrate` 是一次性服务，成功后的 `Exited (0)` 是正确状态，不应把它误判为崩溃。

### 3. 回滚并恢复

执行目录：项目根目录，继续沿用同一 PowerShell 窗口。  
执行目的：只在今天新建且尚无业务数据的隔离数据库中验证现有迁移可以完整回滚和恢复。  
执行顺序：确认项目名 → `downgrade base` → 查询表与扩展已回滚 → `upgrade head` → 再次确认结构。  
预期结果：回滚后业务表和 `vector` 扩展不存在；恢复后重新出现，head 回到 `e780fe92751b`。

```powershell
$day14Project
$day14EnvPath

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic downgrade base

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT to_regclass('public.knowledge_bases') AS knowledge_bases, to_regclass('public.documents') AS documents, to_regclass('public.chunks') AS chunks;"

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic upgrade head

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic current

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT version_num FROM alembic_version; SELECT extname FROM pg_extension WHERE extname = 'vector'; SELECT to_regclass('public.knowledge_bases'), to_regclass('public.documents'), to_regclass('public.chunks');"
```

### 预期结果

- `downgrade base` 依次删除 `chunks`、`documents`、`knowledge_bases`，再删除 `vector` 扩展；三个 `to_regclass` 值应为空，扩展查询应为零行。
- `upgrade head` 先恢复 `vector` 扩展，再恢复三张表、外键、检查约束、索引和 `vector(512)` 字段。
- 最终 `alembic current` 与数据库 `alembic_version` 均回到 `e780fe92751b`。
- `revision --autogenerate` 今天不应执行；它不是数据库升级命令，也没有新增 ORM 结构需要生成。
- 如果任何一步失败，不继续 HTTP 验收；先查看 `migrate`/`api` 日志和当前 revision，但不要输出完整 Compose 配置或真实秘密。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录，沿用第六节中的 `$day14Project` 与 `$day14EnvPath`。  
执行目的：确认迁移恢复到 head，服务健康，并获得公开 API 地址。  
执行顺序：先检查迁移与服务，再请求健康接口。  
预期结果：API 地址为 `http://127.0.0.1:58000`，Swagger 为 `http://127.0.0.1:58000/docs`。

```powershell
docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T api alembic current

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    ps --all

$day14Health = Invoke-WebRequest `
    -Uri "http://127.0.0.1:58000/health" `
    -Method Get

$day14Health.StatusCode
$day14Health.Content |
    ConvertFrom-Json |
    ConvertTo-Json -Depth 5
```

### 执行正常请求或测试

先创建一个最小知识库，再通过列表 API 和数据库 SQL 交叉核对。这个请求不需要 LLM Key，能够验证 API、Pydantic、Repository、Session、事务提交和 PostgreSQL 表。

```powershell
$day14KnowledgeBaseJson = @{
    name = "Day14 干净环境知识库"
    description = "用于验证公开 Compose 流程"
} | ConvertTo-Json

$day14KnowledgeBaseBytes = [System.Text.Encoding]::UTF8.GetBytes(
    $day14KnowledgeBaseJson
)

$day14Create = Invoke-WebRequest `
    -Uri "http://127.0.0.1:58000/knowledge-bases" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body $day14KnowledgeBaseBytes

$day14Create.StatusCode
$day14CreatedKnowledgeBase = $day14Create.Content | ConvertFrom-Json
$day14CreatedKnowledgeBase | ConvertTo-Json -Depth 5

$day14List = Invoke-RestMethod `
    -Uri "http://127.0.0.1:58000/knowledge-bases" `
    -Method Get

$day14List | ConvertTo-Json -Depth 5

docker compose `
    --project-name $day14Project `
    --env-file $day14EnvPath `
    exec -T postgres `
    psql -U rag_app -d enterprise_rag_day14 `
    -c "SELECT id, name, description FROM knowledge_bases ORDER BY id;"
```

### 预期状态码或输出结构

健康接口预期 HTTP `200`：

```json
{
  "status": "ok",
  "database_connected": true,
  "llm_configured": false
}
```

如果只在本地环境中填入了完整的三项 LLM 配置，`llm_configured` 可以是 `true`；这不是今天基础设施验收的必需条件。

创建知识库预期 HTTP `201`：

```json
{
  "id": "数据库生成的正整数",
  "name": "Day14 干净环境知识库",
  "description": "用于验证公开 Compose 流程",
  "created_at": "数据库生成的时间戳"
}
```

列表接口应包含同一个 `id`、`name` 和 `description`；SQL 查询也应出现同一行。ID 与时间戳是动态值，不预先写死。

### 为什么它能证明今天已经完成

- `/health` 的 HTTP 200 证明 Uvicorn、FastAPI 和 SQLAlchemy `SELECT 1` 同时成功。
- `POST /knowledge-bases` 的 HTTP 201 证明空库迁移后的业务表真实可用，且请求经过 Pydantic、Repository、Session 和 commit。
- 列表 API 与 PostgreSQL SQL 结果一致，证明响应不是内存伪造或旧 SQLite 数据。
- 整套命令使用新的 Compose 项目名、公开测试配置和独立 Volume，不依赖现有 `.env` 或 Day 13 数据。
- 实际执行、保存和回填输出是可选项；缺少记录不改变核心实现是否已经形成。

## 八、验证失败和边界路径

### 场景：缺少必需的 `POSTGRES_PASSWORD`

执行目录：项目根目录。  
执行目的：验证公开配置缺少必需项时，在任何容器和数据库写入发生前快速失败，并且错误只指出变量名。  
执行顺序：新建一个同样被忽略的安全失败配置 → 静默校验 Compose → 检查不存在失败项目容器。  
注意：该文件故意使用空密码，只用于 `config --quiet`，不要用它启动服务。

```powershell
$day14MissingEnvPath = Join-Path (Get-Location) ".env.day14-missing"
$day14MissingEnvLines = @(
    "POSTGRES_DB=enterprise_rag_day14_missing"
    "POSTGRES_USER=rag_app"
    "POSTGRES_PASSWORD="
    "POSTGRES_HOST_PORT=55433"
    "API_HOST_PORT=58001"
    "LLM_API_KEY="
    "LLM_BASE_URL="
    "LLM_MODEL="
)
[System.IO.File]::WriteAllLines(
    $day14MissingEnvPath,
    $day14MissingEnvLines,
    [System.Text.UTF8Encoding]::new($false)
)

git check-ignore -v .env.day14-missing

docker compose `
    --project-name "${day14Project}-missing" `
    --env-file $day14MissingEnvPath `
    config --quiet

$day14MissingExitCode = $LASTEXITCODE
$day14MissingExitCode

docker ps `
    --filter "label=com.docker.compose.project=${day14Project}-missing" `
    --format "{{.Names}}"
```

### 预期结果

- HTTP 状态码或异常：不会发出 HTTP 请求；Compose 配置阶段以非零退出码失败，并报告 `POSTGRES_PASSWORD is required` 或等价的缺失变量错误。
- 数据库应该保留：正常 Day 14 项目中的 `enterprise_rag_day14` 数据库及刚创建的知识库记录保持不变。
- 数据库不应该存在：失败项目不应创建 PostgreSQL 容器、Volume、数据库或任何业务行；最后一条 `docker ps` 应无输出。
- 响应不能泄露：不能出现真实 `.env` 内容、数据库连接 URL、密码值、LLM API Key、Authorization Header 或 Python 堆栈。
- 不要为了这个测试修改或清空现有 `.env`；失败文件本身没有秘密且已被 Git 忽略。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `docker version` 只有 Client，没有 Server | Docker Desktop Engine 尚未启动 | `docker version` | 启动 Docker Desktop，等待 Engine ready，再从环境检查开始重试 |
| `config --quiet` 报必需变量缺失 | `--env-file` 路径错误，或 PostgreSQL 三个必需值为空 | 输出 `$day14EnvPath`；检查 `.env.day14` 的变量名，不打印真实环境文件 | 重新按计划创建只含公开测试值的 `.env.day14`，确认命令沿用同一 PowerShell 窗口 |
| 宿主机端口绑定失败 | `55432` 或 `58000` 已被其他进程监听 | `Get-NetTCPConnection -State Listen -LocalPort 55432,58000 -ErrorAction SilentlyContinue` | 只修改 `.env.day14` 的 `POSTGRES_HOST_PORT` 或 `API_HOST_PORT`，不要改容器内部 `5432`/`8000` |
| `migrate` 报找不到 `alembic.ini` 或 migrations | Dockerfile 没有复制迁移文件，或构建仍使用旧缓存镜像 | `docker compose --project-name $day14Project --env-file $day14EnvPath logs --tail 100 migrate`；核对 Dockerfile 的三个 `COPY` | 保存 Dockerfile 后重新执行带 `--build` 的 `up`；不要在宿主机手工迁移来掩盖镜像缺失 |
| `migrate` 连接 `127.0.0.1:5432` 失败 | Compose 没有把应用容器的主机覆盖为服务名 `postgres` | `docker-compose.yml` 的 `&app_environment` | 保持 `POSTGRES_HOST: postgres` 和 `POSTGRES_PORT: "5432"`，宿主机映射端口只用于宿主机访问 |
| `migrate` 已 `Exited (0)`，但被误认为服务崩溃 | 一次性迁移服务完成后本来就应退出 | `docker compose --project-name $day14Project --env-file $day14EnvPath ps --all` | 确认退出码为 `0` 且 API 已启动；非零退出才查看迁移日志 |
| API 长时间处于 starting | 首次下载或加载 BGE 模型，网络较慢，或模型源不可达 | `docker compose --project-name $day14Project --env-file $day14EnvPath logs --tail 100 api`；查看 `huggingface_cache` Volume 是否挂载 | 等待首次下载完成；若明确是网络错误，修复网络后重新启动同一项目以复用缓存，不删除 Volume |
| `/health` 返回 503 | PostgreSQL 尚未 ready、连接参数错误或数据库已停止 | `docker compose --project-name $day14Project --env-file $day14EnvPath ps --all`；`docker compose --project-name $day14Project --env-file $day14EnvPath logs --tail 100 postgres api` | 先恢复 PostgreSQL healthy，核对容器内使用 `postgres:5432`，再重试健康请求 |
| `/health` 是 200 但没有 `database_connected` | `app/main.py` 仍是旧 health 实现，或镜像未重建 | 搜索 `check_database_connection`；检查 API 镜像创建时间 | 按步骤 4 替换两个位置，然后带 `--build` 重新创建 Day 14 API 容器 |
| `alembic current` 为空 | 空库还没有升级，或迁移服务失败 | `docker compose --project-name $day14Project --env-file $day14EnvPath logs --tail 100 migrate`；`docker compose --project-name $day14Project --env-file $day14EnvPath exec -T api alembic heads` | 修复连接/迁移错误后执行 `docker compose --project-name $day14Project --env-file $day14EnvPath exec -T api alembic upgrade head`，确认 `e780fe92751b` 后再进行 HTTP 验收 |
| `downgrade base` 提示对象依赖或数据风险 | 命令指向了非隔离数据库，或库中已有不属于今天的数据 | 先输出 `$day14Project`、`$day14EnvPath`，查询 `knowledge_bases` 行数 | 立即停止回滚；只在本计划新建、尚未写入业务数据的独立 Day 14 数据库执行迁移往返 |
| Git 状态出现 `.env.day14` 或 `.env.day14-missing` | `.gitignore` 没有按步骤 1 更新，或文件名不符合规则 | `git check-ignore -v .env.day14 .env.day14-missing` | 修正 `.gitignore` 的 `.env.*` 与 `!.env.example`；不要暂存本地环境文件 |
| LLM 问答返回 503 `大模型服务未配置` | 今天的安全示例刻意留空三个 LLM 变量 | `GET /health` 查看 `llm_configured`，不要打印密钥 | 基础设施验收继续使用健康和知识库 CRUD；需要真实问答时只在本地未跟踪环境文件中填写完整三项 |

## 十、检查最终代码差异

执行目录：项目根目录。下面只检查今天的明确文件，不展开或读取本地环境文件。

```powershell
git status --short
git diff --check
git diff -- `
    .gitignore `
    .dockerignore `
    .env.example `
    Dockerfile `
    docker-compose.yml `
    app/main.py `
    docs/17天每日学习/Day14.md
git check-ignore -v .env .env.day14 .env.day14-missing
git ls-files -- .env .env.day14 .env.day14-missing .env.example
```

重点检查：

- Compose 只有一个数据库入口，应用容器使用 `postgres:5432`，宿主机端口只负责映射。
- `migrate` 必须依赖 `postgres: service_healthy`，`api` 必须依赖 `migrate: service_completed_successfully`。
- Dockerfile 确实复制 `alembic.ini`、`migrations/` 和 `app/`，且没有复制真实 `.env`、测试数据或学习资料。
- `/health` 的数据库异常响应是固定 503 结构，不拼接异常文本、连接 URL 或密码。
- `.env.example` 只有安全示例和空 LLM 值；`.env`、`.env.day14`、`.env.day14-missing` 均未被 Git 跟踪。
- diff 不包含 Day 15 的 README 改写、业务功能、真实运行日志、模型缓存、数据库文件或无关修改。
- 所有未实际运行的容器、迁移和 HTTP 结论仍写为“预期结果”。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。先再次确认状态，再按今天的明确清单暂存：

```powershell
git status --short
git diff -- `
    .gitignore `
    .dockerignore `
    .env.example `
    Dockerfile `
    docker-compose.yml `
    app/main.py `
    docs/17天每日学习/Day14.md

git add `
    .gitignore `
    .dockerignore `
    .env.example `
    Dockerfile `
    docker-compose.yml `
    app/main.py `
    docs/17天每日学习/Day14.md

git commit -m "complete reproducible Docker startup flow"
```

提交前要求：

- `git status --short` 不得出现被暂存的 `.env` 变体、模型缓存、数据库文件、日志或无关文档。
- 如果实际执行发现已知失败，先修复对应实现再提交；不要求把实际输出提交到仓库。
- 不使用范围不明的批量暂存命令。

## 十二、面试高频问题与参考答案

### 问题 1：Dockerfile、Docker Compose 和 Volume 在当前项目中分别解决什么问题？

#### 30 秒参考答案

Dockerfile 定义应用镜像，固定 Python 3.11 运行环境、系统库、Python 依赖、应用代码和 Alembic 文件；Compose 编排 PostgreSQL、一次性迁移服务和持续运行的 API，并注入环境变量、端口和启动条件；Volume 独立保存 PostgreSQL 数据目录与 Hugging Face 模型缓存。三者分别解决“应用怎样打包”“多个服务怎样协作”和“容器变化后哪些数据仍保留”。

#### 继续追问：为什么 `migrate` 和 `api` 要复用同一个镜像？

如果宿主机执行迁移、容器运行 API，两边的 Python、SQLAlchemy、Alembic、pgvector 包和代码版本可能不一致。复用同一镜像可以保证迁移使用的 ORM 元数据、迁移脚本与实际 API 代码来自同一构建产物；两个服务只改变命令和生命周期，不复制第二套依赖。

#### 回答时要引用的项目依据

- `Dockerfile` 的固定基础镜像、依赖安装与三个 `COPY`。
- `docker-compose.yml` 的 `migrate`/`api` 共用 `enterprise-rag-api:local`。
- `postgres_data` 与 `huggingface_cache` 两个命名 Volume。

### 问题 2：怎样保证 API 不会在数据库尚未迁移时开始接收请求？

#### 30 秒参考答案

当前 Compose 把启动条件分成两级：PostgreSQL 先用 `pg_isready` 变成 healthy，`migrate` 才能执行 `alembic upgrade head`；只有迁移容器以退出码 0 完成后，API 才启动。API 启动后还通过数据库感知的 `/health` 做 readiness，只有 `SELECT 1` 成功才会变成 healthy。因此 running、数据库 ready、schema ready 和 API ready 是四个明确状态。

#### 继续追问：为什么不能只在 API 启动命令前拼接一次迁移？

把迁移和长期 API 放在一个命令里会混合生命周期，失败日志和重试语义不清，也可能在多个 API 副本同时启动时并发迁移。当前学习项目虽然只有一个 API，仍用一次性服务显式表达顺序；未来扩展副本时也更容易把迁移保持为单独部署步骤。

#### 回答时要引用的项目依据

- `docker-compose.yml` 的 `service_healthy` 与 `service_completed_successfully`。
- `migrate` 的 `command: ["alembic", "upgrade", "head"]` 和 `restart: "no"`。
- `migrations/versions/751357b5d274_enable_vector_extension.py` 到 `e780fe92751b_create_core_rag_tables.py` 的 revision 链。

### 问题 3：为什么 Compose 内的数据库地址是 `postgres:5432`，宿主机却是 `127.0.0.1:55432`？

#### 30 秒参考答案

Compose 会为项目创建内部网络，服务名 `postgres` 能被同一网络的容器解析；PostgreSQL 在容器内始终监听 5432。`55432` 只是把宿主机回环地址映射到容器 5432，供宿主机 psql 或本地 Python 使用。API 容器里的 `127.0.0.1` 指向 API 容器自身，因此必须用 `postgres:5432`，不能使用宿主机连接地址。

#### 继续追问：为什么数据库端口只绑定 `127.0.0.1`？

Day 14 是本机可复现环境，没有远程访问需求。绑定回环地址可以减少数据库暴露面；容器间通信走内部 Compose 网络，不依赖宿主机端口。生产环境仍需要独立的网络、密钥和访问控制设计，今天不把本地 Compose 误当生产部署方案。

#### 回答时要引用的项目依据

- `docker-compose.yml` 的 `127.0.0.1:${POSTGRES_HOST_PORT}:5432`。
- `&app_environment` 中的 `POSTGRES_HOST: postgres`、`POSTGRES_PORT: "5432"`。
- `.env.example` 对宿主机变量和映射端口的注释。

### 问题 4：怎样避免把秘密放进镜像、Git 或诊断输出？

#### 30 秒参考答案

仓库只跟踪 `.env.example`，真实 `.env` 和 `.env.*` 由 `.gitignore` 排除；`.dockerignore` 同时排除所有本地环境文件，所以它们不会进入构建上下文。Compose 通过运行时环境注入变量，三个 PostgreSQL 必需项使用只报告变量名的校验语法。诊断时使用 `config --quiet`、`git check-ignore` 和文件名级检查，不打印完整 Compose 展开结果或真实环境文件。

#### 继续追问：`.env.example` 中为什么可以有数据库示例密码？

因为它明确是仅本地隔离环境使用的公开测试值，不承担生产保密性；它的作用是让流程可复制。真正的秘密仍必须由使用者在未跟踪的本地文件或外部秘密系统中提供。公开示例密码不能复用于共享、测试外网或生产数据库。

#### 回答时要引用的项目依据

- `.gitignore` 的 `.env.*` 与 `!.env.example`。
- `.dockerignore` 的 `.env` 和 `.env.*`。
- `.env.example` 中空的 `LLM_API_KEY` 与 `change-me-local-only` 注释边界。
- `app/db.py` 的 URL 对象构造和泛化连接错误。

### 问题 5：什么证据能证明“在我的电脑能跑”已经升级为“可以复现”？

#### 30 秒参考答案

我不用原有数据库和真实 `.env`，而是用带时间戳的新 Compose 项目名、公开测试配置和新的命名 Volume。从空库自动执行两条迁移，再检查 revision、vector 扩展和三张表；随后 `/health` 真实查询数据库，创建知识库并用 API 列表和 SQL 交叉核对。失败路径还证明缺少必需变量时不会创建容器或泄密。这样证据覆盖配置、构建、启动顺序、schema 和最小业务流，而不只是看到一个进程 running。

#### 继续追问：当前复现能力还有什么限制？

基础镜像目前固定到 Python 3.11 系列和 PostgreSQL 16 系列，但没有固定 Docker image digest；BGE 模型名也没有固定 Hugging Face revision，首次启动依赖外部网络；LLM 服务本身是外部依赖，真实问答需要用户本地凭据。Day 14 能证明本地干净环境流程，但不能宣称它已经具备生产级供应链锁定、离线部署或云平台高可用能力。

#### 回答时要引用的项目依据

- `$day14Project` 的时间戳项目名与独立 `postgres_data`。
- `alembic current`、`pg_extension`、`to_regclass` 的预期证据。
- `/health`、`POST /knowledge-bases` 和数据库 SQL 的交叉核对。
- `Dockerfile` 的 `python:3.11-slim`、Compose 的 `pgvector/pgvector:pg16`、`EmbeddingService.MODEL_NAME`。

## 十三、今天的完整数据流

### 正常路径

```text
.env.example 的公开契约
→ 新建且被 Git 忽略的 .env.day14
→ 唯一时间戳 Compose 项目名
→ docker compose config --quiet 校验必需变量与 YAML
→ 构建 enterprise-rag-api:local
→ 新建独立 postgres_data 与 huggingface_cache
→ postgres 容器启动
→ pg_isready 返回成功
→ migrate 容器连接 postgres:5432
→ Alembic 执行 751357b5d274：启用 vector 扩展
→ Alembic 执行 e780fe92751b：创建三张核心表、约束、索引和 vector(512)
→ migrate 以退出码 0 结束
→ api 容器启动 Uvicorn
→ EmbeddingService 首次下载或从 Volume 加载 BGE 模型
→ Compose 调用 GET /health
→ check_database_connection 执行 SELECT 1
→ HTTP 200 + database_connected=true
→ POST /knowledge-bases
→ Pydantic 校验
→ KnowledgeBaseRepository.create
→ SQLAlchemy Session commit
→ PostgreSQL 写入 knowledge_bases
→ HTTP 201
→ GET 列表与 psql 查询返回同一记录
→ 形成公开配置到最小业务请求的复现闭环
```

### 失败路径

```text
.env.day14-missing 中 POSTGRES_PASSWORD 为空
→ Compose 解析 ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
→ config --quiet 非零退出
→ 不构建、不创建容器、不创建 Volume、不写数据库
→ 错误只说明缺少 POSTGRES_PASSWORD
→ 不读取或回显现有 .env

PostgreSQL 启动后不可连接
→ /health 调用 check_database_connection
→ SQLAlchemy 连接异常被转换为泛化 RuntimeError
→ /health 返回 HTTP 503
→ status=error + database_connected=false
→ 不返回连接 URL、密码、驱动异常或堆栈
→ Compose 不把 API 标记为 healthy
```

## 十四、完成标准

```text
[ ] 能解释 Dockerfile、Image、Container、Compose Service 和 Volume 的职责差异
[ ] 能说明为什么容器内使用 postgres:5432，而宿主机使用回环地址与映射端口
[ ] 已按清单完成 .gitignore、.dockerignore、.env.example、Dockerfile、docker-compose.yml 和 app/main.py 的修改
[ ] 应用镜像同时包含 app/、alembic.ini 与 migrations/，migrate 和 api 复用同一固定依赖环境
[ ] Compose 明确实现 postgres healthy → migrate 成功 → api 启动，并为 PostgreSQL 与模型缓存使用命名 Volume
[ ] 已提供独立项目名、公开测试配置和空数据库 upgrade → downgrade base → upgrade head 的完整命令与预期结果，实际执行和记录可选
[ ] 已提供 /health、创建知识库、列表 API 与 PostgreSQL 查询的正常路径命令和稳定预期结构，实际执行和记录可选
[ ] 已提供缺少 POSTGRES_PASSWORD 的失败路径，预期在创建容器前非零退出且不泄露任何秘密
[ ] 能不看代码复述“公开配置 → 空库 → 迁移 → API readiness → 最小业务写入”的完整数据流
[ ] git diff 只包含今天七个明确文件，不包含 .env 变体、模型缓存、数据库文件、日志、秘密或 Day 15 内容
[ ] 核心实现完成并检查 diff 边界后，可使用明确文件列表执行 Git commit，不以回填验收输出为前提
```

## 十五、可选执行记录

- 实际完成：已完成
- Compose 项目名：可选，不要求填写
- Docker / Compose / Python 版本：可选，不要求填写
- 空库迁移 head 与往返结果：可选，不要求填写
- `/health` 与最小知识库请求结果：可选，不要求填写
- 缺失配置失败结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
