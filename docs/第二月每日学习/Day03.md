# 第二月 Day 3：接入 ORM、数据库会话与 Alembic 基线迁移

> 来源计划：`docs/第二月每日实施参考.md` Day 3
> 预计用时：2～3 小时
> 今日状态：未开始
> 唯一产物：`alembic/versions/<revision>_postgresql_baseline.py`

Day 2 已经验证了 PostgreSQL 容器健康、`vector` 扩展和命名卷持久化；它现在是可重复使用的**数据层运行环境**。当前应用仍在 `app/database.py` 用 SQLite 保存聊天记录，并在 `app/main.py` 中把 FAISS 索引保存在内存。今天只建立 Python 应用通往 PostgreSQL 的标准通道：SQLAlchemy 2 引擎与会话、FastAPI 生命周期检查、Alembic 配置，以及一条可升级、可降级的基线迁移。今天不迁移 SQLite 聊天数据、不创建组织/用户/知识库等业务模型、不让接口读写 PostgreSQL，也不替换 FAISS；这些分别属于后续 Day。

## 先记住 5 件事

[[Day03-先记住 5 件事]]

- ORM（对象关系映射）让 Python 类和数据库表遵循同一份结构约定。今天先建立 SQLAlchemy 的 `Base`、引擎和会话工厂；Day 4 才设计真正的组织、文档和知识库模型。它改变的是数据访问基础设施，不改变现有 RAG 的检索结果。
- 数据库引擎（Engine）是应用管理连接池的入口；会话（Session）则是一段具体数据库操作的工作单元。以后每个 API 请求会得到自己的 Session，用完即关闭，不能把一个全局 Session 供所有请求共用。证明理解的方式：解释为什么 Engine 可复用、Session 不能长期全局共享。
- **Alembic 迁移**是可审查、可重复的数据库结构变更历史。今天的基线迁移有意不创建业务表，只验证“升级到一个版本、降回 base、再升级”的机制；Day 4 的模型设计会在此基础上新增下一条实际建表迁移。
- **应用生命周期**指 FastAPI 启动和退出时要做的事情。今天启动时主动执行一次 `SELECT 1`，因此 PostgreSQL 不可连接时应用会明确启动失败；退出时释放引擎连接池。它影响接口层与数据层的边界，但不取代 Day 25 的 liveness/readiness 健康检查设计。
- Day 2 已有的 PostgreSQL、`vector` 扩展和 `.env.example` 是今天的输入；今天的 Alembic 目录、数据库会话模块和基线迁移将成为 Day 4 设计数据模型的输入。最常见的错误是直接把 `app/database.py` 的 SQLite 函数改成 PostgreSQL：那会同时破坏当前聊天接口，并把“接通基础设施”和“迁移业务功能”混成一个难以排查的改动。

## 步骤 1：确认 PostgreSQL 已可用，并标出 SQLite 与 FAISS 的现状

先确认 Day 2 的运行证据仍然成立，再阅读现有入口。今天会新增 PostgreSQL 基础设施，但必须保留 `app/database.py`、`/chat`、`/history` 和内存 FAISS 的现状，避免把多个 Day 的改动混在一起。

### [你来完成] 只读检查

在项目根目录执行：

```powershell
git status --short
docker compose ps
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

python -m pip show SQLAlchemy
python -m pip show psycopg
python -m pip show alembic

Test-Path .\alembic
Test-Path .\alembic.ini
Get-Content .\app\database.py
Get-Content .\app\main.py
Get-Content .\app\config.py
Get-Content .\requirements.txt
```

目的与预期：

- `docker compose ps` 中的 `postgres` 应为 `healthy`，`vector` 查询应返回一行扩展和版本号；否则暂停 Day 3，先回到 Day 2 排查容器、端口或命名卷。
- 三个 `pip show` 在当前仓库可能显示“未安装”，`alembic/` 与 `alembic.ini` 也应尚不存在；这是今天要补齐的基础设施，不是故障。
- `app/database.py` 目前是 SQLite 聊天记录实现，`app/main.py` 在导入时调用 `init_database()`，并使用全局 `rag_service` 保存 FAISS 索引。只记录这些事实，不删除、重命名或替换它们。
- `git status --short` 中已有的 `Day02.md` 改动属于你的学习记录；保留它，今天只在新增文件和今天必须修改的公开配置中工作。

如果你的 PostgreSQL 用户名或数据库名并非示例值，请把后续命令中的 `rag_app`、`enterprise_rag` 替换为你自己的非敏感名称；不要在终端输出、学习记录或 Git 中写入数据库密码。

## 步骤 2：安装数据库基础依赖，并把连接配置限定在本机环境

现在让 Python 拥有连接 PostgreSQL 和执行迁移的工具，但不让密码进入仓库。连接 URL 只存在于本机 `.env`，公开的 `.env.example` 只保留可替换示例；不要把 `.env.example` 整体复制覆盖已有 `.env`，以免丢失 LLM 配置。

### [你来完成] 添加 SQLAlchemy、psycopg 与 Alembic

先在你实际使用的虚拟环境中安装兼容主版本，并记录安装后的真实版本：

```powershell
python -m pip install "SQLAlchemy>=2,<2.1" "psycopg[binary]>=3,<4" "alembic>=1.14,<2"
python -m pip show SQLAlchemy psycopg alembic
```

然后把三项依赖写入 `requirements.txt`。沿用当前文件的格式，写入本机实际安装的精确版本，例如：

```text
SQLAlchemy==[填写 pip show 得到的版本]
psycopg[binary]==[填写 pip show 得到的版本]
alembic==[填写 pip show 得到的版本]
```

`psycopg` 是 PostgreSQL 驱动，SQLAlchemy 会通过 URL 中的 `postgresql+psycopg://` 使用它；不要误装已废弃或不匹配的 `psycopg2` 后继续沿用同一 URL。若安装失败，先确认此处的 `python` 是否就是你运行 FastAPI 所用虚拟环境中的解释器。

### [你来完成] 只追加公开示例和本机连接 URL

在 `.env.example` 的 PostgreSQL 配置区追加一行公开示例：

```text
DATABASE_URL=postgresql+psycopg://rag_app:change-me-local-only@127.0.0.1:5432/enterprise_rag
```

在你本机 `.env` 的末尾追加相同键名、但使用你自己的本机用户名、密码、端口和数据库名。不要读取、展示、提交或复制 `.env` 内容。

如果密码含有 `@`、`:`、`/`、`?`、`#` 等 URL 保留字符，需要先做 URL 编码；学习阶段更简单的做法是为本机开发数据库使用一个不含这些字符的独立密码。不要因为方便而把密码硬编码进 Python、`alembic.ini` 或命令行。

### [你来完成] 新建独立的 PostgreSQL 会话模块

保留 `app/database.py` 作为旧 SQLite 聊天记录模块；新建 `app/postgres.py`，只负责今后 PostgreSQL 的 Engine、Session、`Base` 和连接检查。最小骨架如下，理解每个对象后再亲手写入：

```python
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def check_postgres_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def close_postgres_engine() -> None:
    engine.dispose()
```

同时在 `app/config.py` 中读取 `DATABASE_URL`。应当在缺少该变量时抛出一条不含密码的明确错误，例如“缺少 DATABASE_URL，无法连接 PostgreSQL”；不要把完整 URL 回显在异常或日志中。`pool_pre_ping=True` 的作用是使用连接前确认连接仍可用；它不是重试策略，也不替代 Day 25 的健康检查。

### [AI 辅助] 请求一次不涉及秘密的结构审查

完成草稿后可提问：

> 请只审查我贴出的 `app/postgres.py`、`app/config.py` 中与 `DATABASE_URL` 读取有关的非敏感代码，以及 `.env.example` 的单行示例。检查 SQLAlchemy 2 的 Engine/Session 生命周期、`get_db` 是否会关闭 Session、URL 驱动名是否正确、错误信息是否可能泄露密码。不要读取或索要 `.env`，不要替我安装依赖、运行迁移或修改文件；请按“会阻塞连接 / 可以改进”分类说明。

## 步骤 3：让 FastAPI 在启动和退出时管理 PostgreSQL 引擎

这一步把“Python 能导入 SQLAlchemy”变成“应用确实会连接 PostgreSQL”。使用 FastAPI 的 `lifespan`，在启动阶段执行连接检查、退出阶段释放 Engine；现有 SQLite 初始化和 RAG 服务暂时保留，目的是让旧功能不在今天被重构。

### [你来完成] 为应用增加最小生命周期边界

在 `app/main.py` 中引入 `asynccontextmanager` 以及 `check_postgres_connection`、`close_postgres_engine`，并在创建 `FastAPI` 时传入 `lifespan`。核心结构应类似：

```python
from contextlib import asynccontextmanager

from app.postgres import check_postgres_connection, close_postgres_engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    check_postgres_connection()
    try:
        yield
    finally:
        close_postgres_engine()


app = FastAPI(
    title="Mini RAG Backend",
    description="一个用于学习 RAG 和 AI 应用开发的后端项目",
    version="0.1.0",
    lifespan=lifespan,
)
```

这里的 `application` 即使暂时未使用也保留，表示 FastAPI 把应用生命周期交给这个上下文管理器。不要在模块导入阶段直接执行数据库查询，也不要创建全局 `Session`；连接检查应发生在应用启动阶段，而单次数据库操作以后会通过 `get_db()` 获得独立 Session。

先进行不连接数据库的语法检查：

```powershell
python -m compileall app
```

预期没有 Python 语法错误。若出现循环导入，先检查 `app/postgres.py` 只依赖 `app.config`，而业务模型尚未反向导入 `app.main`。

## 步骤 4：初始化 Alembic，并创建可升级、可回滚的基线迁移

今天的唯一核心产物是基线迁移文件。它记录“本项目从没有 Alembic 历史，到拥有一个已知迁移起点”的事实；因为 Day 4 才设计业务模型，基线迁移的 `upgrade()` 和 `downgrade()` 可以为空，但必须真的被 Alembic 执行和回滚，不能只创建文件不运行。

### [你来完成] 建立不含秘密的 Alembic 配置

在项目根目录执行一次：

```powershell
alembic init alembic
```

这会创建 `alembic/` 与 `alembic.ini`。随后做两处关键调整：

1. `alembic.ini` 不写真实连接 URL，保留占位值即可。
2. 在 `alembic/env.py` 中导入 `DATABASE_URL` 与 `Base`，以 `config.set_main_option("sqlalchemy.url", DATABASE_URL)` 把本机环境变量注入 Alembic，并设置 `target_metadata = Base.metadata`。

不要在 `alembic.ini` 复制 `.env` 中的连接 URL，也不要把密码写进迁移脚本。`target_metadata` 今天还没有业务表是正常的；Day 4 的模型类继承 `Base` 后，后续迁移才能有统一的元数据来源。

创建基线 revision：

```powershell
alembic revision -m "postgresql baseline"
```

在生成的 `alembic/versions/<revision>_postgresql_baseline.py` 中确认：

- `revision`、`down_revision`、`upgrade()` 与 `downgrade()` 均存在；首条迁移的 `down_revision` 应为 `None`。
- 今天不创建组织、用户、知识库、文档、Chunk 或向量表；`upgrade()` 与 `downgrade()` 可以只保留 `pass`。
- 不在这条迁移中重复创建或删除 Day 2 已启用的 `vector` 扩展。业务表和扩展的长期迁移策略将在模型开始出现后再统一设计。

### [你来完成] 实际证明升级、回滚和恢复

终端 A 运行迁移；终端 B 只检查数据库状态：

```powershell
# 终端 A
alembic upgrade head
alembic current
alembic downgrade base
alembic current
alembic upgrade head
alembic current
```

```powershell
# 终端 B：在最后一次 upgrade 后执行
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT version_num FROM alembic_version;"
```

预期：第一次与最后一次 `alembic current` 都指向这条基线 revision；`downgrade base` 后当前 revision 不再指向它；最后一次升级后 `alembic_version` 中重新出现该 revision。不要把 `alembic_version` 的确切修订号手写进计划或提交说明，记录实际输出即可。

如果 `alembic` 找不到，使用同一解释器调用 `python -m alembic`；如果迁移提示无法连接，先确认 `postgres` 仍为 `healthy`、`DATABASE_URL` 使用 `postgresql+psycopg`、并且端口与 Day 2 的本机配置一致。不要为绕过错误而改回 SQLite URL。

## 步骤 5：验证应用连接与一个安全失败路径，并记录 Day 4 边界

迁移命令成功只能说明 Alembic 可连接；还要证明 FastAPI 启动时实际使用同一连接配置。随后用一次只影响当前 PowerShell 进程的错误 URL 验证失败会显式暴露，而不会让应用悄悄回退到 SQLite。

### [你来完成] 运行正常路径

终端 A 启动应用：

```powershell
uvicorn app.main:app --reload
```

预期启动日志中没有 PostgreSQL 连接异常。终端 B 再执行：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

预期 `/health` 仍返回现有服务状态；更关键的证据是终端 A 已通过启动阶段的 `SELECT 1`，而不是把“HTTP 返回 200”误当成数据库已经连通。停止终端 A 时应正常触发生命周期退出并释放 Engine。

### [你来完成] 观察安全失败路径

不要修改 `.env`、Compose 或数据库。仅在一个新 PowerShell 窗口设置无效的进程级 URL，再运行连接检查：

```powershell
$env:DATABASE_URL = "postgresql+psycopg://invalid:invalid@127.0.0.1:1/invalid"
python -c "from app.postgres import check_postgres_connection; check_postgres_connection()"
Remove-Item Env:DATABASE_URL
```

预期命令非零退出，并清晰提示连接被拒绝或无法连接；错误中不应打印真实 `.env` 密码。`Remove-Item Env:DATABASE_URL` 只清除当前终端临时变量，不会改动 `.env`。随后在正常配置的终端再次运行 `docker compose ps`，预期 `postgres` 仍为 `healthy`。

最后检查本日公开改动：

```powershell
git diff -- requirements.txt .env.example app/config.py app/postgres.py app/main.py alembic.ini alembic
git status --short
```

应看到依赖、公开示例、PostgreSQL 会话与 Alembic 文件；不应看到 `.env`、真实密码或被删除的 `app/database.py`。今天结束时明确写下：SQLite 聊天记录、FAISS、业务模型和业务接口仍未迁移，Day 4 才开始设计第一批业务实体和下一条建表迁移。

## 常见问题

- `ModuleNotFoundError: sqlalchemy` 或 `alembic` 找不到：先比较 `python -m pip show` 与 `python --version`，确认安装和运行使用同一个虚拟环境；再用 `python -m alembic` 重试。
- Alembic 或 FastAPI 连不上 PostgreSQL：先看 `docker compose ps` 是否为 `healthy`，再检查 `.env` 中 `DATABASE_URL` 的驱动名、端口、数据库名和 URL 特殊字符编码；不要展示密码。
- `psycopg` 驱动报错：先确认 URL 以 `postgresql+psycopg://` 开头，且安装的是 `psycopg[binary]`，不要混用 `psycopg2` 的驱动名。
- `alembic revision` 生成的 `down_revision` 不为 `None`：先运行 `alembic heads` 检查是否已有未记录的 revision；不要删除已有迁移，记录冲突后再决定最小处理方式。
- Uvicorn 启动后 `/health` 可访问但没有验证 PostgreSQL：先确认 `lifespan` 已传给 `FastAPI`，并在启动阶段调用了 `check_postgres_connection()`；HTTP 200 本身不是数据库证明。
- 回滚后不知道数据库状态：用 `alembic current` 与 `SELECT version_num FROM alembic_version;` 观察实际 revision，再执行 `alembic upgrade head` 恢复到 Day 3 完成状态。

## 验收清单

- [ ] 我能用自己的话解释 Engine、Session、ORM、Alembic 和 FastAPI 生命周期的职责边界。
- [ ] 已在 `requirements.txt` 记录实际安装的 SQLAlchemy 2、psycopg 和 Alembic 版本，且未提交 `.env` 或真实密码。
- [ ] 已新增独立的 PostgreSQL 会话模块，包含 `Base`、Engine、`SessionLocal`、`get_db()` 与连接检查；旧 `app/database.py` 的 SQLite 聊天逻辑仍保留。
- [ ] FastAPI 启动时会检查 PostgreSQL，关闭时会释放 Engine，且应用可在正常数据库配置下启动。
- [ ] 已创建并实际执行唯一核心产物 `alembic/versions/<revision>_postgresql_baseline.py`。
- [ ] 已运行 `alembic upgrade head → downgrade base → upgrade head`，并记录最终 `alembic current` 与 `alembic_version` 的真实输出。
- [ ] 已运行临时无效 URL 的失败路径，确认连接失败明确暴露、未泄露真实密码，且 PostgreSQL 容器仍为 `healthy`。
- [ ] 我明确记录了今天尚未迁移 SQLite 聊天、FAISS、业务模型和业务接口；它们将从 Day 4 开始逐步处理。

## 今日学习记录

```text
实际完成：
- [ ] 已完成唯一产物：`alembic/versions/[填写真实 revision]_postgresql_baseline.py`。
- [ ] 已安装并在 `requirements.txt` 记录 SQLAlchemy、psycopg、Alembic 的实际版本。
- [ ] 已新增 `app/postgres.py`，并让 FastAPI 生命周期检查 PostgreSQL、关闭时释放 Engine。
- [ ] 已完成迁移链路：upgrade head → downgrade base → upgrade head。
- 未完成或需要补充说明：[无则写“无”；否则填写原因与下一步]。

我今天真正理解了：
- Engine 管理可复用连接池；Session 是单次数据库操作的工作单元，不能做成一个全局共享对象。
- Alembic 记录可重复的结构变更历史；Day 3 的基线迁移验证迁移机制，Day 4 才会把业务模型变成建表迁移。
- 今天改变的是应用与 PostgreSQL 的数据访问基础设施，尚未改变 SQLite 聊天记录、FAISS 检索或 RAG 接口行为。
- 我自己的表述或需要修正处：[填写]。

仍然不理解：
- `Base.metadata`、`target_metadata` 与后续自动生成迁移的关系：[已理解 / 填写具体问题]。

遇到的报错：
- 依赖安装、Alembic、Uvicorn 或连接检查：[填写脱敏后的真实错误摘要；无则写“无阻塞报错”]。
- 处理方式与结果：[填写；无则写“不适用”]。

测试/验证结果：
- `docker compose ps` 与 `vector` 查询：证明 Day 2 PostgreSQL 环境仍可用；真实结果：[填写 healthy 状态与扩展版本摘要]。
- `alembic upgrade head → downgrade base → upgrade head`：证明迁移可升级、可回滚且最终恢复；真实结果：[填写三个 `alembic current` 的摘要]。
- `SELECT version_num FROM alembic_version;`：证明最终数据库位于 Day 3 基线 revision；真实结果：[填写 revision 摘要]。
- `uvicorn app.main:app --reload`：证明应用启动生命周期实际连通 PostgreSQL；真实结果：[填写启动与 `/health` 摘要]。
- 临时错误 `DATABASE_URL` 连接检查：预期明确连接失败且不泄露密码；真实结果：[填写脱敏错误摘要，并确认容器仍 healthy]。

AI 代办内容及我的复核结果：
- AI 仅辅助审查不含秘密的 Engine/Session、生命周期和 Alembic 配置；我自行运行依赖安装、迁移、应用启动与失败路径。
- 我复核的文件、输出或结论：[填写；若未使用 AI 辅助则写“本日未使用 AI 辅助”]。

与原计划的偏差：
- 无；如有则填写：[实际差异、原因、采取的最小处理方式，以及对 Day 4 的影响]。

明天开始前要解决：
- 无；或填写仍会阻塞 Day 4 设计组织、部门、用户、知识库、文档和版本模型的具体事项。

Git commits：
- [填写提交哈希与说明；未提交则写“未提交”]。
```

Day 4 会读取今天的 `app/postgres.py`、FastAPI 生命周期边界、Alembic 配置和已位于 head 的基线迁移，开始设计组织、部门、用户、知识库、文档和文档版本之间的关系，并创建下一条实际建表迁移。如果今天的应用连接、升级/回滚或失败路径未通过，Day 4 不应开始建模；应先修复数据库连接和迁移基础设施。
