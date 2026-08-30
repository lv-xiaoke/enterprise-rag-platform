# Day 1：接通 PostgreSQL 并建立可回滚的 Alembic 基线

今天会在保留现有 SQLite 聊天链路的前提下，为企业 RAG 新增 PostgreSQL/SQLAlchemy 连接层和可回滚的 pgvector 基线迁移，解决应用尚未真正使用持久化向量数据库的问题，并让你能够在面试中解释数据库驱动、ORM 与迁移工具的职责边界。

> 预计用时：60 分钟  
> 今日唯一核心产物：可连接 PostgreSQL、可执行 `upgrade → downgrade → upgrade` 的数据库基础设施  
> 对应主计划：Day 1

## 一、开始前先明确边界

### 今天完成什么

- 将 SQLAlchemy、psycopg、pgvector Python 包和 Alembic 声明为项目直接依赖，并记录实际安装版本。
- 在 `app/config.py` 中读取 PostgreSQL 配置，新建 `app/db.py` 负责 SQLAlchemy Engine、Session 工厂和连接探针。
- 保留 `app/database.py` 的 SQLite 聊天历史职责，不迁移 `/chat` 和 `/history`。
- 初始化 `migrations/`，用第一条迁移启用 PostgreSQL 的 `vector` 扩展，并真实验证升级、回滚、再次升级。

### 今天不做什么

- 不创建 `knowledge_bases`、`documents`、`chunks` 三张业务表；这是 Day 2。
- 不实现知识库或文档 CRUD；这是 Day 3。
- 不写入 PDF Chunk 和向量；这是 Day 4。
- 不改 `/upload`、`/rag/chat` 或现有 FAISS 检索链路。
- 不删除现有 `alembic/__pycache__/`；缓存文件不是可用迁移源码，也不能作为完成证据。

### 当前真实起点

- `[当前事实]` `app/database.py` 只使用标准库 `sqlite3`，为普通 `/chat` 和 `/history` 保存消息。
- `[当前事实]` `app/config.py` 当前只读取 LLM 配置，尚未提供 PostgreSQL 应用配置。
- `[当前事实]` `requirements.txt` 没有声明 SQLAlchemy、psycopg、pgvector 和 Alembic；当前 Python 3.11.7 环境中可导入 SQLAlchemy 2.0.25，但另外三个包未安装，环境里“碰巧已安装”不能替代项目依赖声明。
- `[当前事实]` `docker-compose.yml` 已使用 `pgvector/pgvector:pg16`，生成本计划时 PostgreSQL 容器状态为 `healthy`，端口映射为 `127.0.0.1:5432`。
- `[当前事实]` `.env.example` 已声明 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_PORT`；本次只确认了本地 `.env` 存在，没有读取或展示其中的值。
- `[当前事实]` 仓库没有 `alembic.ini` 和可读的 Alembic 源码，只有被忽略的 `.pyc` 缓存，因此 Day 1 尚未完成。
- `[当前事实]` 工作区已有多项与今天无关的文档删除、修改和未跟踪文件；必须保留，提交时只暂存今天的文件。
- `[待实测]` 新增依赖的实际安装版本、数据库连接、迁移升级/回滚结果都要由你运行后记录，不能根据当前容器健康状态提前判定通过。

## 二、核心知识铺垫

### 1. SQLAlchemy、psycopg 与 PostgreSQL

- 通俗解释：PostgreSQL 是数据库服务；psycopg 是 Python 与 PostgreSQL 对话的底层驱动；SQLAlchemy 在驱动之上统一管理连接、事务和对象映射。
- 在本项目中的职责：SQLAlchemy 创建 Engine 和 Session，psycopg 真正发送 PostgreSQL 协议请求，PostgreSQL 最终保存后续的知识库、文档、Chunk 和向量。
- 与现有代码的关系：`app/database.py` 继续服务 SQLite 聊天历史；新的 `app/db.py` 只服务企业 RAG 的 PostgreSQL 链路，避免今天顺手破坏旧接口。
- 容易混淆的点：安装 SQLAlchemy 不等于已经具备 PostgreSQL 驱动；连接串使用 `postgresql+psycopg` 才明确选择 psycopg 3。

### 2. Engine、Session 与连接探针

- 通俗解释：Engine 是应用的数据库连接入口和连接池管理者；Session 是一次业务操作中组织查询、写入和事务的工作单元；连接探针只是执行 `SELECT 1`，证明链路可达。
- 在本项目中的职责：Day 1 只建立 Engine、Session 工厂和探针；Day 3 的数据访问层再按请求创建和关闭 Session。
- 与现有代码的关系：FastAPI 目前不会在启动时强制连接 PostgreSQL，所以今天先用独立命令验证，避免让旧 `/chat` 因新数据库配置暂时不完整而无法启动。
- 容易混淆的点：创建 Engine 通常是惰性的，`create_engine(...)` 成功不代表数据库可用；必须真正 `connect()` 并执行 SQL 才算连接成功。

### 3. Alembic 迁移与 pgvector 扩展

- 通俗解释：Alembic 把数据库结构变化保存成有顺序、可升级和可回滚的版本脚本；pgvector 扩展让 PostgreSQL 认识 `vector` 类型和向量距离运算。
- 在本项目中的职责：第一条迁移只启用 `vector` 扩展，为 Day 2 的 `vector(512)` 字段准备数据库能力。
- 与现有代码的关系：Alembic 的 `migrations/env.py` 复用 `app/db.py` 的 Engine 和 Base，确保应用与迁移读取同一套连接配置。
- 容易混淆的点：`pgvector` Python 包负责 SQLAlchemy 类型适配，数据库中的 `CREATE EXTENSION vector` 负责服务器能力；两者都需要，但不是同一个东西。

## 三、逐步完成今天的升级

### 步骤 1：安装并声明四个直接依赖（建议 8 分钟）

**为什么先做这一步**

后面的连接代码和迁移命令都依赖这些包；先固定实际版本，才能区分“代码错误”和“依赖根本不存在”。

**[你来完成]**

1. 在项目根目录确认当前解释器和已有声明：

```powershell
python --version
python -c "import sys; print(sys.executable)"
Get-Content -LiteralPath requirements.txt
```

2. 在你为本项目使用的 Python 环境中安装直接依赖：

```powershell
python -m pip install SQLAlchemy alembic pgvector "psycopg[binary]"
python -m pip show SQLAlchemy alembic pgvector psycopg psycopg-binary
python -c "import sqlalchemy, alembic, psycopg; from pgvector.sqlalchemy import Vector; print('database imports ok')"
```

3. 根据 `pip show` 的真实结果，在 `requirements.txt` 中只新增四条直接依赖并使用精确版本；不要用 `pip freeze > requirements.txt` 覆盖整份文件：

```text
SQLAlchemy==<实际版本>
alembic==<实际版本>
pgvector==<实际版本>
psycopg[binary]==<psycopg 的实际版本>
```

**[AI 辅助]**

如果 `psycopg` 与 `psycopg-binary` 的显示方式让你不确定，把 `pip show` 输出贴给 AI，让 AI 只判断应该如何声明直接依赖，不要让 AI 重写整个 `requirements.txt`。

**预期结果**

- 四类 import 均成功，并输出 `database imports ok`。
- `requirements.txt` 新增精确版本，但原有依赖没有被批量升级或重排。

**理解检查**

> 请用自己的话解释：为什么项目同时需要 SQLAlchemy 和 psycopg，而不是二选一？

### 步骤 2：建立独立的 PostgreSQL 连接层（建议 15 分钟）

**为什么现在做这一步**

先形成唯一、可复用的数据库入口，后续模型、迁移和数据访问层才能共享连接配置；同时隔离已有 SQLite 逻辑，控制今天的改动边界。

**[你来完成]**

1. 打开并对照：`app/config.py`、`app/database.py`、`.env.example`。不要执行 `Get-Content .env`，也不要把真实密码粘贴到终端输出或聊天中。
2. 在 `.env.example` 增加非秘密的主机示例，并在你本地 `.env` 中私下补同名变量：

```dotenv
POSTGRES_HOST=127.0.0.1
```

3. 在 `app/config.py` 中增加 PostgreSQL 配置读取，保持现有 LLM 配置不变：

```python
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
```

4. 新建 `app/db.py`，按下面的职责组织最小结构；使用 `URL.create(...)`，不要手工拼接带密码的 URL，也不要打印 Engine URL：

```python
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def build_database_url() -> URL:
    # [你来完成] 检查 DB、USER、PASSWORD 是否为空；缺失时只报告变量名。
    return URL.create(
        drivername="postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )


class Base(DeclarativeBase):
    pass


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def check_database_connection() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()
```

5. 不要修改 `app/main.py` 的启动流程，也不要删除或改名 `app/database.py`。

**预期结果**

- `app/db.py` 成为 PostgreSQL 的唯一基础设施入口。
- 模块不记录、不打印真实密码；错误只说明缺失的变量名。
- SQLite 与 PostgreSQL 的职责在文件层面清楚分开。

**理解检查**

> 请画出并口述：`.env → app/config.py → URL.create → SQLAlchemy Engine → psycopg → PostgreSQL`，其中每一段负责什么？

### 步骤 3：初始化 Alembic 并创建 pgvector 基线迁移（建议 17 分钟）

**为什么现在做这一步**

连接层可复用以后，迁移工具才能与应用使用同一数据库；第一条迁移只管理扩展，不提前侵入 Day 2 的表模型。

**[你来完成]**

1. 从项目根目录初始化新的 `migrations/` 目录；不要尝试复用只有缓存文件的 `alembic/`，也不要批量删除它：

```powershell
python -m alembic init migrations
```

2. 编辑 `migrations/env.py`：导入 `Base` 和 `engine`，把 `target_metadata` 指向 `Base.metadata`，在线迁移直接复用 Engine。关键形状如下：

```python
from app.db import Base, engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
```

3. 离线迁移分支也应从 `engine.url.render_as_string(hide_password=False)` 取得 URL，但不要 `print`；`alembic.ini` 中不要写真实账号和密码。
4. 创建第一条迁移：

```powershell
python -m alembic revision -m "enable vector extension"
```

5. 打开新生成的 `migrations/versions/<revision>_enable_vector_extension.py`，只实现这一项结构变化：

```python
from alembic import op


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
```

**预期结果**

- 根目录出现 `alembic.ini`，并生成可读的 `migrations/env.py` 和一条版本脚本。
- 迁移脚本不包含业务表、不包含密码，`upgrade` 与 `downgrade` 一一对应。

**理解检查**

> 为什么今天只迁移 `vector` 扩展，而不顺便创建三张业务表？

### 步骤 4：验证正常连接与升级路径（建议 8 分钟）

**为什么要真实运行**

容器 `healthy` 只说明 PostgreSQL 自检成功，不能证明 Python 驱动、应用配置和 Alembic 链路都正确。

**[你来完成]**

```powershell
docker compose ps
python -c "from app.db import check_database_connection; print(check_database_connection())"
python -m alembic upgrade head
python -m alembic current
docker compose exec -T postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx vector"'
```

**预期结果**

- `docker compose ps` 显示 PostgreSQL 为 `healthy`。
- 连接探针输出 `1`。
- `alembic current` 显示刚创建的 revision，并带有 `(head)`。
- `\dx vector` 能看到 `vector` 扩展；以上都属于预期，必须用你的真实输出确认后再记为通过。

**理解检查**

> 如果 Engine 创建成功但 `SELECT 1` 失败，能够排除什么，又还不能排除什么？

### 步骤 5：验证回滚和数据库不可用路径（建议 8 分钟）

**为什么不能只测成功路径**

Day 1 的核心承诺包括“可回滚”，同时应用面对错误端口时应明确失败而不是假装连接成功或泄露密码。

**[你来完成]**

1. 先回滚到基线之前，检查扩展消失，再恢复到 head：

```powershell
python -m alembic downgrade base
python -m alembic current
docker compose exec -T postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx vector"'
python -m alembic upgrade head
python -m alembic current
docker compose exec -T postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx vector"'
```

2. 在一个独立 Python 进程里覆盖为错误端口，不修改 `.env`，确认探针失败：

```powershell
python -c "import os; os.environ['POSTGRES_PORT']='1'; from app.db import check_database_connection; check_database_connection()"
```

3. 最后再次运行正常探针，证明失败实验没有污染配置：

```powershell
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

**预期结果**

- `downgrade base` 后 `vector` 不再列出；再次 `upgrade head` 后恢复。
- 错误端口命令在约 3 秒内以连接异常失败，不出现真实密码，也不能被吞掉后输出成功。
- 最后的正常探针重新输出 `1`。
- 如果 Day 2 以后已有依赖 `vector` 的列，不要再执行这条 `downgrade base`，更不要用 `CASCADE` 绕过依赖。

**理解检查**

> 正常探针、迁移 current、扩展查询三项证据分别证明了什么，为什么缺一项都不完整？

### 步骤 6：记录结果并准备提交（建议 4 分钟）

- 在本文件“实际完成”上方补充你真实执行的命令与结果摘要；失败就记录失败，不把“预期结果”写成“已经通过”。
- 检查今天的差异和全局状态：

```powershell
git diff -- requirements.txt .env.example app/config.py app/db.py alembic.ini migrations docs/17天每日学习/Day01.md
git status --short
```

- 确认 `.env`、密码、缓存文件和既有文档改动没有进入差异。
- 验收全部通过后，只暂存今天的文件：

```powershell
git add requirements.txt .env.example app/config.py app/db.py alembic.ini migrations docs/17天每日学习/Day01.md
git diff --cached
```

- 建议 commit message：`feat(db): bootstrap PostgreSQL migrations`
- 本计划不替你执行 `git commit`；请在检查暂存差异后自行提交。

## 四、常见卡点与排查顺序

### 卡点 1：`ModuleNotFoundError` 或 Alembic 找不到 `app`

1. 先用 `python -c "import sys; print(sys.executable)"` 确认安装包和运行命令使用同一解释器。
2. 再确认当前目录是仓库根目录，而不是 `app/` 或 `migrations/`。
3. 用 `python -m alembic ...`，不要依赖可能来自另一 Python 环境的全局 `alembic` 命令。

### 卡点 2：容器 healthy，但 Python 连接被拒绝或认证失败

1. 先运行 `docker compose ps`，确认端口仍为 `127.0.0.1:5432`。
2. 再核对 `.env` 中 PostgreSQL 变量名是否与 `.env.example` 一致；只在本机查看，不粘贴真实值。
3. 确认 `POSTGRES_HOST=127.0.0.1`，因为今天 Python 在宿主机运行；容器内应用以后才会使用服务名 `postgres`。
4. 不要把密码直接写进 `alembic.ini`，也不要通过打印完整 URL 排错。

### 卡点 3：`alembic init migrations` 提示目录已存在

1. 先用 `Get-ChildItem -LiteralPath migrations -Force` 查看里面是否已有本次生成的源码。
2. 如果是刚才部分生成，逐个核对 `env.py`、`script.py.mako` 和 `versions/`，不要再次初始化覆盖。
3. 不要使用递归删除命令；无法判断文件归属时停止并请求人工确认。

### 卡点 4：回滚 `vector` 扩展失败

1. 先确认现在确实仍是 Day 1，数据库还没有依赖 `vector` 的业务列。
2. 查看错误是否提示 dependent objects；若已有 Day 2 数据，停止回滚并保留现场。
3. 不要添加 `CASCADE`，它可能连带删除向量列或数据。

## 五、面试高频问题

### 问题 1：为什么选择 SQLAlchemy + psycopg，而不是直接写 psycopg SQL？

- 考察点：抽象层职责、事务管理和工程可维护性。
- 回答要点：psycopg 是 PostgreSQL 驱动；SQLAlchemy 提供 Engine、连接池、Session、类型映射及与 Alembic 的元数据协作；复杂向量查询仍可在 SQLAlchemy 中使用明确 SQL 表达式，而不是完全放弃数据库能力。
- 结合本项目：指出 `app/db.py` 统一连接基础设施，Day 3 的数据访问层会使用 Session，Day 5 再表达 pgvector Top-K 查询。

### 问题 2：为什么创建 Engine 不能证明数据库已经连接？

- 考察点：惰性连接和连接池行为。
- 回答要点：`create_engine` 主要建立配置对象，通常到第一次 `connect()` 或执行 SQL 时才向数据库发起真实连接；因此需要 `SELECT 1` 探针。
- 结合本项目：说明今天的 `check_database_connection()` 如何从 Engine 经 psycopg 到 PostgreSQL，并返回标量 `1`。

### 问题 3：pgvector Python 包和 PostgreSQL 的 vector 扩展有什么区别？

- 考察点：客户端类型适配与服务器端能力的边界。
- 回答要点：Python 包让 SQLAlchemy 理解向量类型和操作；数据库扩展提供 `vector` 列类型、距离运算符和相关索引能力；只安装任一侧都不能形成完整链路。
- 结合本项目：今天安装 Python 包并通过 Alembic 启用扩展，Day 2 才真正建立 `vector(512)` 列。

### 问题 4：为什么数据库结构要使用 Alembic，而不是应用启动时执行 `CREATE TABLE IF NOT EXISTS`？

- 考察点：结构版本、可审计变更和回滚能力。
- 回答要点：启动时建表难以记录变更顺序、评审差异和可靠回滚；Alembic 为每次结构变化提供 revision、依赖关系以及 upgrade/downgrade。
- 结合本项目：第一条 revision 只管理 `vector` 扩展，并用 `upgrade → downgrade → upgrade` 留下真实证据。

## 六、今天结束后应当留下的证据

- 代码或配置：`requirements.txt`、`.env.example`、`app/config.py`、`app/db.py`、`alembic.ini`、`migrations/env.py`、`migrations/versions/<revision>_enable_vector_extension.py`。
- 运行证据：依赖版本、连接探针输出 `1`、Alembic 当前 revision、回滚前后 `\dx vector` 的差异、错误端口连接失败摘要。
- 学习记录：能口述 SQLite 与 PostgreSQL 两条链路，以及 `.env` 到数据库的完整连接数据流。
- Git：只包含 Day 1 产物的暂存差异；不包含 `.env`、缓存或原有无关文档改动。

# Day 1 完成标准

```text
[ ] 能解释 SQLAlchemy、psycopg、PostgreSQL 三者为什么缺一不可
[ ] 能解释 pgvector Python 包与数据库 vector 扩展的职责区别
[ ] requirements.txt 已按实际安装结果声明四个直接依赖的精确版本
[ ] app/db.py 已提供不泄露密码的 URL 构造、Engine、SessionLocal、Base 和连接探针
[ ] 能从 .env、配置模块、Engine、驱动讲到 PostgreSQL 的完整连接数据流
[ ] 正常连接探针真实输出 1，upgrade head 后能查询到 vector 扩展
[ ] downgrade base 后扩展消失，再次 upgrade head 后恢复且 current 位于 head
[ ] 错误端口验证在限定时间内明确失败，错误信息未泄露真实密码，随后正常连接恢复
[ ] git diff 中没有 .env、秘密、缓存或既有无关修改，验收后完成边界清晰的 Git commit
```

实际完成：未完成

遇到的卡点：暂无

Git commit：未提交
