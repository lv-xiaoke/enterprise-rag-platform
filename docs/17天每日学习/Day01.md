# Day 1：建立 PostgreSQL 连接与可回滚迁移基线

今天将直接补齐数据库配置校验和 Alembic 脱敏配置，并完成连接探针与 `upgrade → downgrade → upgrade` 验收，使项目获得安全、可回滚的 PostgreSQL + pgvector 基线，并为面试中的数据库连接、迁移和组件职责问题提供可运行证据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一套能够安全执行连接探针，并可将 vector 扩展升级、回滚、再次升级到 head 的 PostgreSQL/Alembic 基线  
> 当前真实状态：已完成 
> 对应总体安排：Day 1

## 一、今天完成后的项目变化

### 升级前

```text
.env / 环境变量
→ app.config 已能读取 PostgreSQL 配置
→ app.db 已有 URL、Engine、SessionLocal 和 SELECT 1 探针
→ 但 build_database_url() 尚未校验空配置
→ 数据库不可用时探针会直接暴露底层异常
→ migrations/env.py 的离线 URL 使用 hide_password=False
→ vector 迁移已有 upgrade/downgrade，但尚无迁移往返实测证据
```

### 升级后

```text
.env / 环境变量
→ build_database_url() 只按变量名报告缺失配置
→ 应用级 Engine 复用连接池
→ SessionLocal 为后续请求创建独立 Session
→ check_database_connection() 执行 SELECT 1，并把底层连接异常转换为无秘密的错误
→ Alembic 在线迁移复用真实 Engine，离线配置只使用隐藏密码的 URL
→ vector 扩展完成 upgrade → downgrade → upgrade，并留下真实数据库证据
```

### 今天在完整项目中的位置

- 所属阶段：数据基础。
- 所属链路：支撑“文档入库”和“用户问答”两条链路的数据库基础设施。
- 今天的输入：固定版本的 SQLAlchemy、psycopg、Alembic、pgvector 依赖，PostgreSQL Compose 服务，以及现有 vector 基线迁移。
- 今天的输出：安全的数据库入口、可主动执行的连接探针、可回滚的 vector 扩展迁移基线和真实验收记录。
- 下一天为什么需要它：Day 2 要复用 `Base`、Engine 和 Alembic 环境创建三张业务表；如果连接与迁移基线不可靠，后续模型和迁移都无法安全落地。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `requirements.txt` 已固定 `SQLAlchemy==2.0.52`、`alembic==1.19.1`、`pgvector==0.5.0` 和 `psycopg[binary]==3.3.4`。
- `[当前事实]` `docker-compose.yml` 使用 `pgvector/pgvector:pg16`，包含本地端口映射、命名 Volume 和 `pg_isready` 健康检查。
- `[当前事实]` `.env.example` 已列出 PostgreSQL 的公开示例变量，真实 `.env` 已被 `.gitignore` 和 `.dockerignore` 排除。
- `[当前事实]` `app/db.py` 已有应用级 Engine、`SessionLocal`、`Base`、3 秒连接超时和 `SELECT 1` 连接探针。
- `[当前事实]` `migrations/env.py` 已把 `Base.metadata` 注册为 Alembic 的 `target_metadata`，在线迁移会使用应用 Engine。
- `[当前事实]` `migrations/versions/751357b5d274_enable_vector_extension.py` 已定义 `CREATE EXTENSION IF NOT EXISTS vector` 和对应的 `DROP EXTENSION IF EXISTS vector`。

### 仍然缺少

- `[当前事实]` `app/db.py` 的必需配置校验仍是 `[你来完成]` 占位注释；空的数据库名、用户名或密码不会在创建 Engine 前得到清晰提示。
- `[当前事实]` 连接探针未将 SQLAlchemy/psycopg 底层异常转换为稳定、无秘密的应用错误。
- `[当前事实]` `migrations/env.py` 在离线模式中显式使用 `hide_password=False`，不符合“不输出数据库密码”的边界。
- `[当前事实]` 仓库没有连接探针、迁移往返和 vector 扩展查询的真实运行记录。

### 待实测

- `[待实测]` Docker Desktop、Compose 和当前 Python 虚拟环境在本机是否可用。
- `[待实测]` PostgreSQL 容器是否能通过健康检查，连接探针是否真实输出 `1`。
- `[待实测]` 当前学习数据库处于 Alembic 的哪个 revision。
- `[待实测]` vector 迁移能否成功升级、回滚并恢复到 `751357b5d274 (head)`。
- `[待实测]` 配置缺失和数据库停止时，错误输出是否只包含安全提示而不包含密码或完整连接串。

### 需要保护的用户修改

- 当前工作区正在重构 17 天文档，存在已删除的旧版 Day 文件以及未提交的新总安排、生成器和 `docs/README.md`；不要恢复旧文件，不要把这些无关改动混入 Day 1 的暂存范围。
- `app/db.py`、`migrations/env.py`、现有 vector 迁移和依赖文件当前未显示用户未提交修改；执行前仍要再次运行 `git status --short`。
- 只按本日明确文件清单操作，不使用 `git add .`，不读取或打印真实 `.env` 内容。

## 三、今天必须理解的核心知识

### 1. SQLAlchemy 与 psycopg 的职责边界

- 一句话解释：SQLAlchemy 提供 Engine、连接池、Session 和 ORM 等高层数据库接口，psycopg 是真正与 PostgreSQL 进行网络通信的驱动。
- 在当前项目中的职责：`create_engine()` 根据 `postgresql+psycopg` URL 选择 psycopg；SQLAlchemy 组织连接和 SQL，psycopg 把请求发送给 PostgreSQL。
- 与其他组件的关系：应用代码调用 SQLAlchemy，SQLAlchemy 调用 psycopg，psycopg 连接 PostgreSQL；Alembic 又通过 SQLAlchemy Engine 执行迁移 SQL。
- 容易混淆的点：安装 SQLAlchemy 不等于已经安装 PostgreSQL 驱动；psycopg 也不是数据库服务器。
- 面试一句话：当前项目用 SQLAlchemy 管理连接池和 ORM 边界，用 psycopg 作为 PostgreSQL 3.x 驱动，二者分别解决抽象层和通信层问题。

### 2. Engine、Connection 与 Session 的生命周期

- 一句话解释：Engine 是应用级数据库入口，Connection 是从连接池借出的一条连接，Session 是一次业务工作单元的 ORM 操作上下文。
- 在当前项目中的职责：`engine` 在模块加载时创建一次；探针用 `engine.connect()` 临时借出连接；后续 API/Service 会用 `SessionLocal()` 为每个业务操作创建独立 Session。
- 与其他组件的关系：Session 绑定 Engine，Engine 管理连接池，真实网络连接由 psycopg 建立。
- 容易混淆的点：创建 Engine 通常是惰性的，不会立即连接数据库；多个请求也不能共享一个长期 Session。
- 面试一句话：我让 Engine 随应用复用，让 Session 随请求或业务工作单元创建和关闭，并用主动 `SELECT 1` 区分“Engine 已构造”和“数据库真实可用”。

### 3. Alembic migration 与 `Base.metadata.create_all()`

- 一句话解释：`create_all()` 只能按当前 metadata 补建缺失表，Alembic migration 则保存有顺序、可审查、可回滚的结构变更历史。
- 在当前项目中的职责：Day 1 的首个 revision 管理 PostgreSQL `vector` 扩展，Day 2 以后所有表和字段变化都要沿 revision 链演进。
- 与其他组件的关系：Alembic 读取 `Base.metadata` 支持后续自动比较，但 Day 1 的扩展属于显式 SQL 迁移。
- 容易混淆的点：生成 revision 不等于执行 upgrade；执行 upgrade 成功也不代表 downgrade 一定安全。
- 面试一句话：企业项目需要可审查的数据库版本历史，所以我用 Alembic 管理 upgrade/downgrade，而不是在应用启动时依赖 `create_all()` 静默改结构。

### 4. PostgreSQL vector 扩展与 Python pgvector 包

- 一句话解释：数据库里的 `vector` 扩展让 PostgreSQL 理解向量类型和距离运算，Python 的 `pgvector` 包负责把 Python/SQLAlchemy 值映射为数据库 vector 类型。
- 在当前项目中的职责：Day 1 只启用数据库扩展；真正的 `vector(512)` ORM 字段属于 Day 2。
- 与其他组件的关系：PostgreSQL 扩展提供存储和计算能力，pgvector Python 包与 SQLAlchemy 对接，Embedding 服务在后续提供 512 维数据。
- 容易混淆的点：只安装 `pgvector==0.5.0` 不会自动在数据库中执行 `CREATE EXTENSION vector`。
- 面试一句话：我把数据库扩展启用放进 Alembic 基线，确保环境可复现；Python 包只负责类型适配，不能代替数据库扩展。

## 四、升级涉及的文件

| 文件                      | 操作     | 作用                                       |
| ----------------------- | ------ | ---------------------------------------- |
| `app/db.py`             | 修改     | 补齐必需配置校验、稳定的 Engine/Session 工厂和无秘密连接探针错误 |
| `migrations/env.py`     | 修改     | 在线迁移复用真实 Engine，离线迁移只使用隐藏密码的 URL         |
| `docs/17天每日学习/Day01.md` | 更新执行记录 | 保存实际命令、正常/失败结果和最终 commit，不记录真实秘密         |

以下文件只复核、不修改，因此不进入最后的 `git add`：

- `requirements.txt`：固定版本已经满足 Day 1。
- `docker-compose.yml`：PostgreSQL、Volume 和健康检查已经存在。
- `.env.example`：公开示例变量已经齐全；真实 `.env` 只在本地使用且禁止提交。
- `migrations/versions/751357b5d274_enable_vector_extension.py`：upgrade/downgrade 已成对定义，今天只做真实往返验证。

### 今日不做

- 不创建 `KnowledgeBase`、`Document`、`Chunk` ORM 模型或业务表；这属于 Day 2。
- 不编写 Repository；这属于 Day 3。
- 不修改 PDF 入库、FAISS 检索或 RAG API。
- 不创建 `vector(512)` 字段，不提前建立 HNSW/IVFFlat 索引。
- 不删除数据库 Volume，不在包含业务数据的数据库上验证 downgrade。

## 五、按顺序完成项目升级

### 步骤 1：确认本地配置入口，不输出秘密（建议 5 分钟）

**目标**

确认 `.env` 只作为本地配置存在；如果它尚不存在，仅从公开示例复制一次，绝不覆盖现有 `.env`。

**修改位置**

- 文件：`.env`（本地文件、已被 Git 忽略）
- 定位：项目根目录
- 操作：仅在不存在时从 `.env.example` 创建，然后由你填写自己的本地学习数据库密码；不要把真实值粘贴到本计划或终端输出中。

**在项目根目录执行**

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "已从公开示例创建 .env；请填写你自己的本地配置。"
} else {
    Write-Host ".env 已存在，本步骤不会覆盖。"
}

git check-ignore .env
```

预期 `git check-ignore .env` 输出 `.env`。打开 `.env` 时只在本机确认以下变量都有值，不要使用会把整份文件打印到终端的命令：

```env
POSTGRES_DB=enterprise_rag
POSTGRES_USER=rag_app
POSTGRES_PASSWORD=填写你自己的本地学习数据库密码
POSTGRES_PORT=5432
POSTGRES_HOST=127.0.0.1
```

**这一步怎样工作**

- 输入：公开的 `.env.example` 和你自己的本地配置。
- 输出：只存在于本机、不会被 Git 暂存的 `.env`。
- 调用谁：`app/config.py` 的 `load_dotenv()` 和 Docker Compose 都会从项目根目录读取这些变量。
- 被谁调用：`app/db.py` 构造 URL，`docker-compose.yml` 初始化 PostgreSQL。
- 正常路径：变量齐全，Python 和 Compose 使用一致的数据库名、用户、密码、主机和端口。
- 失败路径：变量缺失时，下一步新增的校验只报告变量名，不回显值。

**完成本步骤后的预期状态**

`.env` 存在且仍被 Git 忽略，真实密码没有出现在命令历史、学习文档或 Git diff 中。

### 步骤 2：补齐安全数据库入口（建议 15 分钟）

**目标**

保留已有 Engine、Base、SessionLocal 和探针，补齐必需配置校验，并将底层连接异常转换为不含 DSN 和密码的稳定错误。

**修改位置**

- 文件：`app/db.py`
- 定位：整份文件较短，搜索 `def build_database_url() -> URL:`
- 操作：先核对没有自己额外加入的内容，再用下面代码替换整份文件。

**复制下面的完整代码**

```python
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def build_database_url() -> URL:
    required_settings = {
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    }
    missing_settings = [
        name
        for name, value in required_settings.items()
        if not value.strip()
    ]
    if missing_settings:
        raise RuntimeError(
            "缺少必需的数据库配置: " + ", ".join(missing_settings)
        )

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
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise RuntimeError(
            "数据库连接失败，请检查 PostgreSQL 服务状态和 POSTGRES_* 配置。"
        ) from None
```

**这段代码怎样工作**

- 输入：`app.config` 中的五项 PostgreSQL 配置。
- 输出：一个 `postgresql+psycopg` URL、应用级 Engine、Session 工厂，以及返回整数的连接探针。
- 调用谁：Engine 通过 SQLAlchemy 调用 psycopg；探针向 PostgreSQL 执行 `SELECT 1`。
- 被谁调用：Alembic 复用 `Base` 和 `engine`；Day 2 模型会继承 `Base`；后续 Repository 会通过 `SessionLocal()` 创建 Session。
- 正常路径：Engine 惰性创建，调用探针时借出 Connection，执行查询得到 `1`，退出 `with` 后归还连接。
- 失败路径：缺少必需变量时，在构造 Engine 前只列出缺失变量名；连接失败时抑制底层异常链，只返回固定安全信息。
- 事务边界：本日探针只有只读查询，不创建 Session、不需要 commit/rollback；后续业务事务不能交给这个探针管理。

**完成本步骤后的预期状态**

`app.db` 可以在配置齐全时导入，配置缺失和数据库不可用时均快速、安全地失败，且没有创建全局长期 Session。

### 步骤 3：让 Alembic 离线配置隐藏密码（建议 10 分钟）

**目标**

继续让在线迁移使用真实应用 Engine，但离线迁移只把隐藏密码后的 URL 交给 Alembic。

**修改位置**

- 文件：`migrations/env.py`
- 定位：搜索 `def run_migrations_offline() -> None:`
- 操作：先核对没有自己额外加入的模型 import，再用下面代码替换整份文件。

**复制下面的完整代码**

```python
from logging.config import fileConfig

from alembic import context

from app.db import Base, engine


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    safe_url = engine.url.render_as_string(hide_password=True)

    context.configure(
        url=safe_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**这段代码怎样工作**

- 输入：`app.db` 中的应用 Engine 和 `Base.metadata`。
- 输出：在线、离线两种 Alembic 执行上下文。
- 调用谁：在线模式从 Engine 获取真实 Connection；离线模式只根据脱敏 URL 方言生成 SQL。
- 被谁调用：`python -m alembic upgrade`、`downgrade` 和带 `--sql` 的离线命令。
- 正常路径：在线迁移连接真实数据库并在事务上下文中运行 revision。
- 失败路径：必需配置缺失时由 `build_database_url()` 安全失败；离线 URL 中密码固定显示为 `***`。
- 事务边界：Alembic 的 `context.begin_transaction()` 管理迁移事务；应用 Session 不参与迁移。

**完成本步骤后的预期状态**

代码中不再出现 `hide_password=False`，Alembic 在线连接仍使用真实 Engine，离线模式不会把真实密码拼进 URL 输出。

### 步骤 4：复核现有 vector 基线迁移（建议 5 分钟）

**目标**

确认当前只有一个基线 revision，upgrade 与 downgrade 成对存在；今天不生成新 revision。

**在项目根目录执行**

```powershell
rg -n "revision|down_revision|CREATE EXTENSION|DROP EXTENSION" migrations/versions/751357b5d274_enable_vector_extension.py
python -m alembic history
```

**预期结果**

- revision 是 `751357b5d274`，`down_revision` 是 `None`。
- upgrade 包含 `CREATE EXTENSION IF NOT EXISTS vector`。
- downgrade 包含 `DROP EXTENSION IF EXISTS vector`。
- `alembic history` 显示该 revision 为当前链路的 `<base> -> 751357b5d274 (head)`。

**这一步怎样工作**

- 输入：已有迁移脚本和 Alembic revision 目录。
- 输出：对迁移链和双向操作的静态核对结果。
- 正常路径：只有一个 head，升级和回滚方向清楚。
- 失败路径：如果出现多个 head 或 revision 文件缺失，先按第九节排错，不执行 downgrade。

**完成本步骤后的预期状态**

确认今天不需要生成第二个迁移，后续只对现有基线做真实往返验收。

## 六、运行数据库迁移或环境命令

> 今天涉及数据库结构变更：vector 扩展会在专用学习数据库中被创建、删除并恢复。downgrade 会改变数据库能力，只能对确认没有业务数据和 vector 业务列的 Day 1 学习数据库执行；不要删除 Volume，也不要在共享、生产或已有业务数据的数据库执行。

### 1. 检查当前状态

执行目录：项目根目录。目的：确认工具版本、用户修改边界和 Compose 服务定义。按顺序执行；这里只读取状态，不启动服务。

```powershell
git status --short
python --version
python -m pip show SQLAlchemy alembic pgvector psycopg
docker --version
docker compose version
docker compose config --services
```

预期结果：依赖版本与 `requirements.txt` 一致，Compose 服务列表包含 `postgres`。如果 `pip show` 缺包，先激活本项目虚拟环境；只有确实未安装时才执行：

```powershell
python -m pip install -r requirements.txt
```

安装依赖属于用户实际执行阶段；本计划生成时没有执行该命令。

### 2. 启动数据库并验证配置脱敏

执行目录：项目根目录。目的：启动 PostgreSQL 并等待健康检查，然后确认 URL 的显示形式隐藏密码。

```powershell
docker compose up -d --wait postgres
docker compose ps postgres
python -c "from app.db import engine; print(engine.url.render_as_string(hide_password=True))"
```

预期结果：`postgres` 为 `running`/`healthy`；URL 结构类似下面内容，密码位置必须是 `***`，主机、端口、数据库名是动态配置值：

```text
postgresql+psycopg://rag_app:***@127.0.0.1:5432/enterprise_rag
```

### 3. 检查初始 revision 并升级到 head

执行目录：项目根目录。目的：先记录数据库当前版本，再应用 vector 基线迁移并查询真实数据库。

```powershell
python -m alembic current
python -m alembic upgrade head
python -m alembic current

$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT version_num FROM alembic_version;"
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS vector_enabled;"
```

预期结果：

- `alembic upgrade head` 退出码为 `0`。
- `alembic current` 显示 `751357b5d274 (head)`。
- `alembic_version.version_num` 是 `751357b5d274`。
- `vector_enabled` 是 `t`。

`revision` 文件存在或 `revision --autogenerate` 成功都不等于数据库已升级；上面的版本表和扩展查询才是数据库证据。

### 4. 回滚到 base

执行目录：项目根目录。目的：先确认数据库没有任何 vector 业务列，再回滚唯一基线 revision。只在 Day 1 专用学习数据库执行。

```powershell
$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
$vectorColumnCount = (docker compose exec -T postgres psql -U $dbUser -d $dbName -tAc "SELECT COUNT(*) FROM information_schema.columns WHERE udt_name = 'vector';").Trim()

if ($vectorColumnCount -ne "0") {
    throw "检测到 vector 业务列；停止 Day 1 downgrade，请改用没有业务数据的专用学习数据库。"
}

python -m alembic downgrade base
if ($LASTEXITCODE -ne 0) {
    throw "Alembic downgrade 失败，先排错，不要继续执行恢复命令。"
}

python -m alembic current
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS vector_enabled;"
```

预期结果：downgrade 退出码为 `0`；当前 revision 回到 base（`alembic current` 不再显示 head）；`vector_enabled` 是 `f`。

### 5. 再次升级并恢复最终状态

执行目录：项目根目录。目的：证明迁移可重复应用，并把数据库恢复到后续 Day 所需的 head。

```powershell
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "恢复到 head 失败，Day 1 尚未完成。"
}

python -m alembic current

$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT version_num FROM alembic_version;"
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

### 预期结果

- 最终 revision 是 `751357b5d274 (head)`。
- `alembic_version` 中保存 `751357b5d274`。
- `pg_extension` 中有且只有名为 `vector` 的目标记录；实际 `extversion` 由镜像内扩展版本决定，是动态值。
- 全程没有删除容器、Volume 或数据库数据目录。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。目的：确保数据库健康且迁移最终处于 head。

```powershell
docker compose up -d --wait postgres
python -m alembic current
```

### 执行正常请求或测试

今天没有新增 HTTP API；正常路径通过应用连接探针和数据库真实查询验证。

```powershell
python -c "from app.db import check_database_connection; print(check_database_connection())"

$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT current_database() AS database_name, current_user AS database_user;"
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT version_num FROM alembic_version;"
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

### 预期状态码或输出结构

```text
连接探针进程退出码：0
连接探针标准输出：1
Alembic revision：751357b5d274
vector 扩展：存在
数据库名、用户、vector 版本：按本机配置动态生成，但不得包含密码
```

### 为什么它能证明今天已经完成

- `SELECT 1` 证明 Engine 不只是成功构造，而是 SQLAlchemy 已通过 psycopg 与 PostgreSQL 完成真实往返。
- `alembic_version` 证明迁移已经应用到数据库，而不是只存在于代码目录。
- `pg_extension` 证明 PostgreSQL 服务器真实启用了 vector 扩展。
- 第六节已经验证 downgrade 后扩展消失、再次 upgrade 后恢复，因此迁移基线具备双向性。

执行后把真实摘要填写到第十五节，不要提前写成“已通过”。

## 八、验证失败和边界路径

### 场景 1：必需配置为空时只报告变量名

下面命令只在当前 PowerShell 进程中临时把密码设为空白字符串，子进程结束后会恢复原来的进程变量；不会修改 `.env`，也不会打印原密码。

```powershell
$previousPassword = [Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "Process")

try {
    [Environment]::SetEnvironmentVariable("POSTGRES_PASSWORD", "   ", "Process")
    python -c "from app.db import build_database_url; build_database_url()"
    $missingConfigExitCode = $LASTEXITCODE
} finally {
    [Environment]::SetEnvironmentVariable("POSTGRES_PASSWORD", $previousPassword, "Process")
}

if ($missingConfigExitCode -eq 0) {
    throw "失败路径未触发：空白 POSTGRES_PASSWORD 不应通过校验。"
}

Write-Host "缺配置失败路径已触发，进程退出码：$missingConfigExitCode"
```

### 预期结果

- 进程退出码：非 `0`。
- 异常类型：`RuntimeError`。
- 稳定信息：`缺少必需的数据库配置: POSTGRES_PASSWORD`。
- 数据库应该保留：原有 revision、扩展和数据完全不变，因为失败发生在 Engine 创建前。
- 数据库不应该存在：本测试不应新增任何表、扩展或记录。
- 输出不能泄露：原密码、完整数据库 URL、LLM Key 或其他 `.env` 值。

### 场景 2：数据库停止时探针快速、安全失败并恢复服务

执行目录：项目根目录。目的：验证 3 秒连接超时和固定安全错误。`finally` 会重新启动数据库；不要关闭当前 PowerShell 窗口，直到恢复命令执行完成。

```powershell
docker compose stop postgres

try {
    $probeOutput = & python -c "from app.db import check_database_connection; check_database_connection()" 2>&1
    $probeExitCode = $LASTEXITCODE
    $probeOutput

    if ($probeExitCode -eq 0) {
        throw "失败路径未触发：数据库停止后探针不应成功。"
    }

    if (($probeOutput | Out-String) -notmatch "数据库连接失败") {
        throw "失败信息不符合约定，请检查 app/db.py。"
    }
} finally {
    docker compose up -d --wait postgres
}

python -c "from app.db import check_database_connection; print(check_database_connection())"
```

### 预期结果

- 停库后的探针退出码：非 `0`，通常在约 3 秒内失败。
- 异常类型：`RuntimeError`，稳定信息只说明数据库连接失败和应检查的配置类别。
- 恢复服务后的探针退出码：`0`，输出 `1`。
- 数据库应该保留：`alembic_version=751357b5d274` 和 vector 扩展；`docker compose stop/start` 不删除 Volume。
- 数据库不应该存在：不应产生额外 revision、表或测试数据。
- 输出不能泄露：真实密码、完整 DSN、LLM Key；如果输出出现这些内容，Day 1 不得验收或提交。

## 九、常见错误与解决办法

| 错误现象                                                            | 最可能原因                                          | 检查命令或位置                                                                    | 解决方法                                                                           |
| --------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `ModuleNotFoundError: No module named 'sqlalchemy'` 或 `alembic` | 未激活项目虚拟环境或依赖未安装                                | `python -m pip show SQLAlchemy alembic psycopg pgvector`                   | 激活正确虚拟环境；缺包时在项目根目录执行 `python -m pip install -r requirements.txt`               |
| `缺少必需的数据库配置: ...`                                               | `.env` 不存在、变量为空，或命令不在项目根目录执行                   | 检查 `app/config.py` 的 `BASE_DIR` 和 `.env.example` 变量名；不要打印真实 `.env`         | 在项目根目录创建/补齐本地 `.env`，保持 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 有非空值 |
| `invalid literal for int()` 指向 `POSTGRES_PORT`                  | 端口不是整数                                         | `.env` 的 `POSTGRES_PORT`                                                   | 改为未被占用的整数端口，例如 `5432`；不要添加引号或其他字符                                              |
| `docker compose up` 报端口已占用                                      | 本机已有 PostgreSQL 或其他进程占用端口                      | `Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue`       | 把本地 `.env` 的 `POSTGRES_PORT` 改为一个未占用端口，例如 `5433`，然后重新执行 Compose 和探针            |
| `postgres` 长时间 `unhealthy`                                      | 初始化配置不一致、Docker Desktop 未就绪或数据库启动失败            | `docker compose ps postgres`；`docker compose logs --tail 50 postgres`      | 先确认 Docker Desktop 正常，再核对 Compose 变量名；不要删除 Volume，保留日志并针对首个错误处理                |
| 探针输出 `数据库连接失败`                                                  | 服务未启动、主机/端口错误，或现有 Volume 的初始化用户与当前 `.env` 不一致  | `docker compose ps postgres`；核对 `.env.example` 的变量名和本机配置                   | 先让容器健康；如 Volume 已由另一套账号初始化，不要删除它，改用匹配的本地配置或新建明确命名的专用学习数据库环境                    |
| `permission denied to create extension vector`                  | 当前数据库用户没有创建扩展权限                                | `docker compose exec -T postgres ... psql` 的当前用户查询；迁移日志                    | 本地 Compose 应使用初始化时的 `POSTGRES_USER` 超级用户执行 Day 1 基线；共享数据库请让管理员预装扩展，不要自行提权      |
| `alembic current` 出现多个 head 或 revision 找不到                      | revision 链冲突、文件缺失或工作区切换不完整                     | `python -m alembic heads`；`python -m alembic history`；`git status --short` | 停止迁移，先确认唯一 head 和文件来源；不要用破坏性 Git 命令覆盖用户改动                                      |
| downgrade 报 vector 被其他对象依赖                                      | 数据库已有 vector 列、索引或其他依赖，不适合做 Day 1 往返           | 执行第六节的 `information_schema.columns` 计数；查看 Alembic 首个错误                     | 不使用 `CASCADE`，不删除对象或 Volume；改用没有业务数据的专用学习数据库完成往返验证                             |
| 离线模式或日志中出现未脱敏 URL                                               | `migrations/env.py` 仍在使用 `hide_password=False` | `rg -n "hide_password" migrations/env.py`                                  | 按步骤 3 完整替换，确保唯一调用为 `hide_password=True`，泄密输出不得保存或提交                            |

## 十、检查最终代码差异

```powershell
git status --short
git diff -- app/db.py migrations/env.py docs/17天每日学习/Day01.md
git diff --check
```

重点检查：

- `app/db.py` 只增加 Day 1 所需的配置校验和安全探针，没有业务模型、Repository 或 API 代码。
- `migrations/env.py` 不再出现 `hide_password=False`，在线迁移仍复用应用 Engine。
- 没有改动现有 vector revision 的 ID、`down_revision` 或 SQL。
- diff 中没有 `.env`、密码、API Key、数据库数据文件、缓存或无关旧文档。
- `git status --short` 中原有的文档重构仍保持原状，后续 `git add` 不应把它们意外暂存。
- 第十五节只记录结果摘要，不粘贴包含秘密的完整错误日志。

## 十一、Git 提交

只有连接探针、迁移往返、缺配置失败路径和停库失败路径全部验收通过，并已填写第十五节后才执行：

```powershell
git add app/db.py migrations/env.py docs/17天每日学习/Day01.md
git diff --cached -- app/db.py migrations/env.py docs/17天每日学习/Day01.md
git commit -m "build: establish PostgreSQL migration baseline"
```

如果 `git diff --cached` 出现上述三个路径以外的内容，先停止提交并逐个核对暂存边界；不要使用 `git add .`，测试未通过时不要提交。

## 十二、面试高频问题与参考答案

### 问题 1：项目已经用了 SQLAlchemy，为什么还需要 psycopg？

#### 30 秒参考答案

SQLAlchemy 不是 PostgreSQL 网络驱动。当前项目由 SQLAlchemy 提供 URL、Engine、连接池、Connection、Session 和后续 ORM 能力，但 `postgresql+psycopg` 中的 psycopg 才负责遵循 PostgreSQL 协议建立真实连接并发送 SQL。把两者分开后，业务代码依赖稳定的 SQLAlchemy 抽象，同时仍需要一个与 PostgreSQL 通信的具体驱动。

#### 继续追问：如果只安装 psycopg，不用 SQLAlchemy 可以吗？

可以直接使用 psycopg 手写 SQL 和事务，但当前项目后续要建立三张 ORM 表、Repository、请求级 Session 和 Alembic metadata，SQLAlchemy 能统一这些边界并减少分散的连接与映射代码。对非常小的脚本只用 psycopg也合理，但不适合本项目后续的分层和迁移目标。

#### 回答时要引用的项目证据

- `requirements.txt` 中固定的 `SQLAlchemy==2.0.52` 与 `psycopg[binary]==3.3.4`。
- `app/db.py` 的 `postgresql+psycopg` URL、Engine 和 `SELECT 1` 探针。
- 实际连接探针输出 `1`。

### 问题 2：Engine、Connection 和 Session 有什么区别？

#### 30 秒参考答案

Engine 是应用级数据库入口和连接池管理者，一般在进程内创建一次；Connection 是从 Engine 的连接池临时借出的一条连接；Session 是一次请求或业务工作单元中的 ORM 上下文，它跟踪对象并承担 flush、commit、rollback 等职责。当前 Day 1 探针只借出 Connection 执行只读 `SELECT 1`，后续 Repository 才会使用 `SessionLocal()` 创建独立 Session。

#### 继续追问：为什么不能所有请求共享一个全局 Session？

Session 持有事务和对象状态，共享会让不同请求互相污染事务、并发状态和异常回滚。当前项目只全局复用线程安全的 Engine/Session 工厂，具体 Session 应由一次请求或业务工作单元创建、提交或回滚并最终关闭。

#### 回答时要引用的项目证据

- `app/db.py` 中模块级 `engine` 和 `SessionLocal` 工厂。
- `check_database_connection()` 中 `with engine.connect()` 的借出/归还边界。
- Day 1 没有创建全局 Session，也没有对只读探针执行 commit。

### 问题 3：为什么创建 Engine 成功，不代表数据库已经可连接？

#### 30 秒参考答案

SQLAlchemy 的 `create_engine()` 默认是惰性的，主要完成配置和连接池对象构造，通常到第一次 `connect()` 或执行 SQL 时才真正让 psycopg 连接 PostgreSQL。因此我单独提供 `check_database_connection()`，用 3 秒连接超时执行 `SELECT 1`；只有返回 `1` 才能证明应用、驱动、网络、认证和数据库都真实打通。

#### 继续追问：`pool_pre_ping=True` 能代替启动探针吗？

不能完全代替。`pool_pre_ping` 是每次从池中取出旧连接时先检查连接是否仍有效，解决陈旧连接问题；主动探针则在部署、排错或验收时给出明确的即时可用性证据。两者目标互补。

#### 回答时要引用的项目证据

- `app/db.py` 的 `pool_pre_ping=True`、`connect_timeout=3` 和 `SELECT 1`。
- 正常路径的实际输出 `1`。
- 停止 PostgreSQL 后探针非零退出、恢复后重新输出 `1` 的记录。

### 问题 4：为什么用 Alembic，而不是直接调用 `Base.metadata.create_all()`？

#### 30 秒参考答案

`create_all()` 适合快速创建当前 metadata 中缺失的表，但不会形成可审查的结构演进历史，也不能可靠表达扩展启用、字段变化和回滚步骤。当前项目把 vector 扩展作为 Alembic 基线 revision，真实验证 upgrade、downgrade 和再次 upgrade；Day 2 的业务表会继续接在同一 revision 链上。

#### 继续追问：`alembic revision --autogenerate` 成功是否说明迁移完成？

不说明。它只生成候选脚本，仍需人工检查 revision 链、字段、约束、索引和向量维度，再执行 `upgrade` 并查询真实数据库。本日用 `alembic_version` 和 `pg_extension` 作为迁移已经落库的证据。

#### 回答时要引用的项目证据

- `migrations/env.py` 的 `target_metadata` 和在线/离线模式。
- `migrations/versions/751357b5d274_enable_vector_extension.py` 的双向 SQL。
- 实际 `upgrade → downgrade → upgrade` 与 `alembic_version` 查询结果。

### 问题 5：Python 的 pgvector 包和 PostgreSQL vector 扩展有什么区别？

#### 30 秒参考答案

PostgreSQL vector 扩展运行在数据库端，提供 vector 数据类型、距离运算和后续向量索引能力；Python `pgvector` 包运行在应用端，负责与 SQLAlchemy/psycopg 做类型映射。当前 Day 1 的迁移只保证数据库扩展可复现启用，Day 2 才会用 Python 类型声明 `vector(512)` 字段。

#### 继续追问：为什么不手工进入数据库执行一次 `CREATE EXTENSION`？

手工执行无法保证其他环境重复得到相同状态，也没有回滚和版本证据。把扩展放进首个 Alembic revision 后，新环境可以按 revision 链建立相同基线，并能明确知道它何时被启用。

#### 回答时要引用的项目证据

- `requirements.txt` 的 `pgvector==0.5.0`。
- Compose 使用的 `pgvector/pgvector:pg16` 镜像。
- vector 基线迁移和 `pg_extension` 的实际查询结果。

## 十三、今天的完整数据流

### 正常路径

```text
本地 .env（不提交）
→ app.config 加载 PostgreSQL 配置
→ build_database_url() 校验必需项并构造 URL 对象
→ create_engine() 创建应用级 Engine 和连接池
→ Alembic 通过 Engine 获取 Connection
→ upgrade 执行 CREATE EXTENSION vector
→ PostgreSQL 写入 alembic_version 并启用 vector
→ downgrade 执行 DROP EXTENSION vector
→ 再次 upgrade 恢复 head
→ check_database_connection() 借出 Connection
→ psycopg 连接 PostgreSQL 并执行 SELECT 1
→ 返回 1，Connection 归还连接池
```

### 失败路径

```text
配置为空
→ build_database_url() 在 Engine 创建前识别缺失项
→ 只返回缺失变量名
→ 不连接数据库、不修改 revision

数据库停止
→ check_database_connection() 尝试连接
→ connect_timeout 在约 3 秒内结束等待
→ SQLAlchemyError 被转换为固定 RuntimeError，底层异常链被抑制
→ 不泄露密码、不修改数据库
→ Compose 恢复 PostgreSQL
→ 探针再次返回 1
```

## 十四、完成标准

```text
[ ] 能结合本项目解释 SQLAlchemy 为什么仍然需要 psycopg，以及 Engine 与 Session 的生命周期差异
[ ] 能解释 Alembic migration 为什么不能被 create_all() 或“生成了 revision 文件”替代
[ ] app/db.py 已完成空配置校验，错误只列出缺失变量名
[ ] app/db.py 的连接探针真实返回 1，且数据库停止时在约 3 秒内安全失败
[ ] migrations/env.py 的离线 URL 使用 hide_password=True，输出中没有真实密码或完整未脱敏 DSN
[ ] vector 基线已在专用学习数据库完成 upgrade → downgrade → upgrade，最终恢复到 751357b5d274 (head)
[ ] 已保存 alembic_version、pg_extension 和 SELECT 1 的真实结果摘要
[ ] 配置缺失与停库两个失败路径均未修改数据库，停库测试后服务和探针已恢复正常
[ ] 能不看代码复述“配置 → Engine → psycopg → PostgreSQL → Alembic/vector”和失败路径
[ ] git diff 只包含 app/db.py、migrations/env.py 和本 Day 1 记录，不包含秘密或其他文档重构；验收后完成边界清晰的 commit
```

## 十五、实际执行记录

- 实际完成：已完成
- 正常路径结果：已通过
- 失败路径结果：已完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
