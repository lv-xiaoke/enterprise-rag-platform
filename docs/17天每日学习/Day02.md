# Day 2：建立 KnowledgeBase、Document 和 Chunk 三张核心表

今天只完成一件事：使用 SQLAlchemy ORM 定义知识库、文档和文本块三层数据骨架，并生成一条可升级、可回滚的 Alembic 迁移，让 PostgreSQL 真实具备外键、状态约束、常用查询索引和 `vector(512)` 字段。验证命令保留供需要时执行，但不要求保存或填写实际验收结果。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：三张核心 ORM 表及其可回滚建表迁移  
> 当前真实状态：已完成
> 对应总体安排：Day 2

## 一、今天完成后的项目变化

### 升级前

```text
app/models.py
→ 只保存 FastAPI 使用的 Pydantic 请求/响应模型

app/database.py
→ SQLite 只保存旧的聊天历史

app/db.py
→ 已有 PostgreSQL Engine、SessionLocal 和 ORM Base

migrations/env.py
→ target_metadata 指向 Base.metadata
→ 但没有导入任何业务 ORM 模型

PostgreSQL
→ 已由 751357b5d274 启用 vector 扩展
→ 尚无 knowledge_bases、documents、chunks 三张业务表

现有 /upload
→ PDF → Chunk → 512 维 Embedding → 内存 FAISS
→ 服务重启后数据仍会丢失
```

### 升级后

```text
app/orm_models.py
├─ KnowledgeBase
│  └─ 1:N Document
├─ Document
│  ├─ N:1 KnowledgeBase
│  ├─ status 数据库级检查约束
│  └─ 1:N Chunk
└─ Chunk
   ├─ N:1 Document
   ├─ 页码与文档内顺序约束
   └─ embedding: vector(512)

migrations/env.py
→ 显式导入 app.orm_models
→ Base.metadata 能看见三张表

新 Alembic revision
→ down_revision = 751357b5d274
→ upgrade 创建三张表、外键、约束和索引
→ downgrade 按 chunks → documents → knowledge_bases 逆序删除
```

### 今天在完整项目中的位置

```text
Day 1 PostgreSQL + pgvector + Alembic 基线（已完成）
                         ↓
Day 2 三张核心表和可回滚迁移（今天）
                         ↓
Day 3 Repository 数据访问层
                         ↓
Day 4 PDF、Chunk 和向量持久化
                         ↓
Day 5 指定知识库内的 pgvector 检索
```

今天只固定“数据长什么样、关系如何约束”。不写 CRUD、不改上传接口，也不把 FAISS 替换成 pgvector 检索。

## 二、开始前的真实状态

### 已经具备

- Day 1 的核心代码已落地，并有对应提交 `ac14dd5`；因此不因缺少旧验收输出停留在 Day 1。
- `app/db.py` 已定义 `Base`、`engine` 和 `SessionLocal`，数据库 URL 使用 `postgresql+psycopg`。
- `migrations/env.py` 已把 `Base.metadata` 交给 Alembic，并开启 `compare_type=True`。
- `migrations/versions/751357b5d274_enable_vector_extension.py` 已提供 vector 扩展的升级和回滚基线。
- `requirements.txt` 已包含 SQLAlchemy、Alembic、pgvector 和 psycopg。
- `docker-compose.yml` 使用 `pgvector/pgvector:pg16`。
- 当前 Embedding 模型输出 512 维向量，和今天的 `Vector(512)` 设计一致。

### 仍然缺少

- 仓库中没有 `KnowledgeBase`、`Document`、`Chunk` 三个 SQLAlchemy ORM 业务模型。
- `Base.metadata` 中尚未注册任何业务表。
- 没有三张表对应的 Alembic revision。
- 数据库层尚未固定文档状态、父子关系、级联删除、页码、Chunk 顺序和向量维度。

### 待实测

- 本机 PostgreSQL 容器当前是否健康。
- 本机数据库当前 revision 是否确实为 `751357b5d274 (head)`。
- vector 扩展是否已在当前学习数据库中启用。
- 新迁移应用后，三张表、约束、索引和 `vector(512)` 是否与模型一致。

这些项目可以使用第六至第八节的命令验证，但实际输出不要求保存到文档中。

### 需要保护的用户修改

- `docs/17天-当日项目升级计划生成器.md` 当前已有未提交修改，这是用户正在调整的提示词。
- 今天不能覆盖、还原或顺带暂存该文件。
- 后续只使用明确路径执行 `git add`，不要使用 `git add .`。
- 保留现有 `app/models.py`、`app/database.py` 和 FAISS 代码；它们的替换不属于 Day 2。

## 三、今天必须理解的核心知识

### 1. SQLAlchemy ORM 模型和 Pydantic 模型解决的问题不同

Pydantic 模型描述进入或离开 HTTP 接口的数据形状，例如当前 `ChatRequest` 和 `RAGChatResponse`；SQLAlchemy ORM 模型描述数据库表、列、外键、索引和对象关系。两者都叫“模型”，但生命周期不同。

因此今天新建 `app/orm_models.py`，不把数据库实体塞进现有 `app/models.py`。Day 3 的 Repository 依赖 ORM 实体，FastAPI 仍依赖 Pydantic schema。

### 2. 外键保证关系存在，索引保证常用关系查询不会退化

`documents.knowledge_base_id` 保证文档属于真实知识库；`chunks.document_id` 保证 Chunk 属于真实文档。外键主要解决完整性，并不会自动建立所有查询所需索引。

后续最常见的是“按知识库和状态找文档”以及“按文档和页码找 Chunk”，所以今天建立：

- `ix_documents_knowledge_base_id_status (knowledge_base_id, status)`
- `ix_chunks_document_id_page_number (document_id, page_number)`

### 3. 数据库约束是最后一道一致性边界

Python 校验只能覆盖当前应用入口，数据库约束还能覆盖脚本、后台任务和未来服务。今天由 PostgreSQL 保证：

- 状态只能是 `pending`、`processing`、`ready`、`failed`。
- 页码从 `1` 开始，`chunk_index` 从 `0` 开始。
- 同一文档内的 `chunk_index` 不重复。
- 父知识库或父文档不存在时，子记录不能写入。

### 4. `vector(512)` 把模型输出维度固化为数据库契约

当前 Embedding 模型输出 512 维向量。`Vector(512)` 会让数据库拒绝维度不一致的数据，避免到检索阶段才发现错误。

今天不建立 HNSW 或 IVFFlat。索引策略要结合距离函数、数据量和查询方式，提前创建超出 Day 2 范围。

### 5. Alembic 只有导入模型后才能自动发现表

`target_metadata = Base.metadata` 不会自动搜索 Python 文件。必须先导入定义 ORM 类的模块，类声明才会把表注册到 metadata。

所以 `migrations/env.py` 必须显式 `from app import orm_models`。新 revision 要接在 `751357b5d274` 后，因为数据库先要有 vector 类型，才能创建向量列。

## 四、升级涉及的文件

| 文件                                                            | 操作    | 作用                        |
| ------------------------------------------------------------- | ----- | ------------------------- |
| `app/orm_models.py`                                           | 新建    | 定义三张 ORM 表、关系、约束和索引       |
| `migrations/env.py`                                           | 修改    | 导入 ORM 模块，使 Alembic 发现三张表 |
| `migrations/versions/<动态 revision>_create_core_rag_tables.py` | 生成并检查 | 创建和回滚三张业务表                |
| `docs/17天每日学习/Day02.md`                                       | 新建    | 保存今天的实施计划；执行记录可选          |

### 今日不做

- 不实现 Repository/CRUD；这是 Day 3。
- 不修改 `/upload`、`/rag/chat` 或现有 Pydantic schema。
- 不迁移 SQLite 聊天历史，不切换现有 FAISS 链路。
- 不创建 HNSW、IVFFlat 等向量索引。
- 不删除容器、Volume、数据库目录或已有迁移。
- 不执行 `Base.metadata.create_all()` 绕过 Alembic。

## 五、按顺序完成项目升级

### 步骤 1：确认依赖和迁移基线（建议 5 分钟）

执行目录：项目根目录。

```powershell
python -m pip show SQLAlchemy alembic pgvector psycopg
python -m alembic heads
git status --short
```

预期：四个依赖都能找到；唯一 head 是 `751357b5d274`；提示词文件保持未暂存。依赖缺失时再运行 `python -m pip install -r requirements.txt`。

实际结果：751357b5d274 (head)

### 步骤 2：新建 ORM 模型（建议 25 分钟）

新建 `app/orm_models.py`，完整内容如下：

```python
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint("name", name="uq_knowledge_bases_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        Index(
            "ix_documents_knowledge_base_id_status",
            "knowledge_base_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey(
            "knowledge_bases.id",
            name="fk_documents_knowledge_base_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="pending",
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(
        back_populates="documents",
    )
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint(
            "page_number >= 1",
            name="ck_chunks_page_number_positive",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_chunks_chunk_index_nonnegative",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_chunks_document_id_chunk_index",
        ),
        Index(
            "ix_chunks_document_id_page_number",
            "document_id",
            "page_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "documents.id",
            name="fk_chunks_document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(512),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
```

验证模块导入和 metadata；该命令只构造 Engine，不连接数据库：

```powershell
python -c "from app.db import Base; import app.orm_models; print(sorted(Base.metadata.tables.keys()))"
```

预期输出：`['chunks', 'documents', 'knowledge_bases']`。

实际输出：['chunks', 'documents', 'knowledge_bases']

### 步骤 3：让 Alembic 导入 ORM 模型（建议 10 分钟）

用下面完整内容替换 `migrations/env.py`。相对于当前文件，职责变化只有导入 ORM 模块；不要改动现有安全 URL 和 Engine 逻辑。

```python
from logging.config import fileConfig

from alembic import context

from app import orm_models
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

这里导入模块只为触发 ORM 类注册，业务代码不需要通过 `migrations.env` 使用这些类。

### 步骤 4：生成并人工核对建表迁移（建议 20 分钟）

先让 PostgreSQL 健康并确认 Day 1 基线，再生成 revision：

```powershell
docker compose up -d --wait postgres
python -m alembic current
python -m alembic heads
python -m alembic revision --autogenerate -m "create core rag tables"

$migration = Get-ChildItem -Path "migrations/versions" -Filter "*_create_core_rag_tables.py" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $migration) {
    throw "没有找到刚生成的 create_core_rag_tables 迁移。"
}

$migration.FullName
Get-Content -Path $migration.FullName
```

启动 PostgreSQL → 确认 Alembic 当前迁移状态 → 自动根据 SQLAlchemy 模型生成一份新迁移文件 → 找到这个刚生成的迁移文件 → 打印出来让你人工检查。

revision ID、文件名前缀和创建时间由 Alembic 动态生成。确认 `down_revision` 是 `751357b5d274`，且生成文件没有删除旧表或旧扩展。

如果生成文件没有正确导入 pgvector 类型，添加：

```python
from pgvector.sqlalchemy import Vector
```

把生成文件中的 `upgrade()` 和 `downgrade()` 完整替换为下面内容；保留 Alembic 自动生成的文档头、`revision`、`down_revision`、`branch_labels` 和 `depends_on`：

```python
def upgrade() -> None:
    """Create the core RAG tables."""
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_knowledge_bases_name"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="fk_documents_knowledge_base_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_knowledge_base_id_status",
        "documents",
        ["knowledge_base_id", "status"],
        unique=False,
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_chunks_chunk_index_nonnegative",
        ),
        sa.CheckConstraint(
            "page_number >= 1",
            name="ck_chunks_page_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_chunks_document_id_chunk_index",
        ),
    )
    op.create_index(
        "ix_chunks_document_id_page_number",
        "chunks",
        ["document_id", "page_number"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the core RAG tables in dependency order."""
    op.drop_index(
        "ix_chunks_document_id_page_number",
        table_name="chunks",
    )
    op.drop_table("chunks")
    op.drop_index(
        "ix_documents_knowledge_base_id_status",
        table_name="documents",
    )
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
```

最后静态核对：

```powershell
if ((Get-Content -Path $migration.FullName -Raw) -notmatch "down_revision.*751357b5d274") {
    throw "新迁移没有接在 Day 1 revision 后面。"
}

rg -n "knowledge_bases|documents|chunks|Vector\(512\)|ck_documents_status|ondelete|create_index|drop_table" $migration.FullName
```

## 六、运行数据库迁移或环境命令

以下命令用于需要时验证迁移。它们不是填写今日计划的前置条件，也不要求把输出复制到第十五节。

### 1. 检查当前状态

```powershell
docker compose up -d --wait postgres
python -m alembic current
python -m alembic heads

$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()

docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

预期：升级前 current 和 heads 都是 `751357b5d274`，查询返回 `vector`。

### 2. 执行升级

```powershell
python -m alembic upgrade head
python -m alembic current

$schemaSql = @'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('knowledge_bases', 'documents', 'chunks')
ORDER BY table_name;

SELECT
    c.relname AS table_name,
    a.attname AS column_name,
    format_type(a.atttypid, a.atttypmod) AS data_type
FROM pg_attribute AS a
JOIN pg_class AS c ON c.oid = a.attrelid
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = 'chunks'
  AND a.attname = 'embedding'
  AND a.attnum > 0
  AND NOT a.attisdropped;

SELECT
    conrelid::regclass AS table_name,
    conname,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN (
    'knowledge_bases'::regclass,
    'documents'::regclass,
    'chunks'::regclass
)
ORDER BY table_name, conname;

SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('knowledge_bases', 'documents', 'chunks')
ORDER BY tablename, indexname;
'@

docker compose exec -T postgres psql -U $dbUser -d $dbName -c $schemaSql
```

### 3. 回滚并恢复

回滚会删除今天新建的三张表。只允许在专用学习数据库且三张表都为空时执行。保护查询发现数据时会中止，不得改成 `CASCADE`。

```powershell
$emptyCheckSql = @'
DO $$
BEGIN
    IF (SELECT count(*) FROM knowledge_bases) > 0
       OR (SELECT count(*) FROM documents) > 0
       OR (SELECT count(*) FROM chunks) > 0 THEN
        RAISE EXCEPTION 'Day 2 tables contain data; downgrade cancelled';
    END IF;
END $$;
'@

docker compose exec -T postgres psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $emptyCheckSql
if ($LASTEXITCODE -ne 0) {
    throw "三张表不是空表，停止回滚并保留数据。"
}

python -m alembic downgrade 751357b5d274

docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT count(*) AS remaining_core_tables FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('knowledge_bases', 'documents', 'chunks');"

python -m alembic upgrade head
python -m alembic current
```

### 预期结果

- 升级后 current 是动态生成的新 revision，并标记 `(head)`。
- public schema 存在三张目标表，`chunks.embedding` 显示为 `vector(512)`。
- 能查到两个外键、状态检查、两个数值检查、两个唯一约束和两个显式联合索引。
- 回滚到 `751357b5d274` 后三张表数量为 `0`，vector 扩展仍存在。
- 再次升级后恢复三张表，最终 current 回到新 head。

## 七、验证正常路径

### 启动或准备服务

```powershell
docker compose up -d --wait postgres
python -m alembic upgrade head

$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
```

### 执行正常请求或测试

今天没有新增 HTTP API。用一个事务写入“知识库 → 文档 → Chunk”，查询 ID 和向量维度后回滚，证明正常链路且不留下测试数据。

```powershell
$normalPathSql = @'
BEGIN;

WITH new_kb AS (
    INSERT INTO knowledge_bases (name, description)
    VALUES ('day02-schema-check', 'temporary Day 2 validation row')
    RETURNING id
),
new_document AS (
    INSERT INTO documents (
        knowledge_base_id,
        filename,
        status
    )
    SELECT id, 'day02-check.pdf', 'processing'
    FROM new_kb
    RETURNING id
),
new_chunk AS (
    INSERT INTO chunks (
        document_id,
        page_number,
        chunk_index,
        content,
        embedding
    )
    SELECT
        id,
        1,
        0,
        'Day 2 schema validation chunk',
        array_fill(0.0::real, ARRAY[512])::vector
    FROM new_document
    RETURNING id, embedding
)
SELECT
    (SELECT id FROM new_kb) AS knowledge_base_id,
    (SELECT id FROM new_document) AS document_id,
    (SELECT id FROM new_chunk) AS chunk_id,
    (SELECT vector_dims(embedding) FROM new_chunk) AS embedding_dimensions;

ROLLBACK;
'@

docker compose exec -T postgres psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $normalPathSql
docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT count(*) AS remaining_test_rows FROM knowledge_bases WHERE name = 'day02-schema-check';"
```

### 预期状态码或输出结构

```text
psql 退出码：0
knowledge_base_id：正整数
document_id：正整数
chunk_id：正整数
embedding_dimensions：512
ROLLBACK：成功
remaining_test_rows：0
```

### 为什么它能证明今天已经完成

- 三层 CTE 成功写入，证明表、主键和两级外键协同工作。
- 合法的 `processing` 状态能通过数据库约束。
- 512 个元素能写入，且 `vector_dims()` 返回 `512`。
- 最后查询为 `0`，证明验证事务没有污染学习数据库。
- 今日目标是数据结构，直接验证数据库比临时增加 API 更贴近完成标准。

## 八、验证失败和边界路径

### 场景 1：非法文档状态被数据库拒绝

单条数据修改 CTE 具有原子性：即使知识库子句先执行，只要文档状态非法，整条语句都会回滚。

```powershell
$invalidStatusSql = @'
WITH new_kb AS (
    INSERT INTO knowledge_bases (name)
    VALUES ('day02-invalid-status')
    RETURNING id
)
INSERT INTO documents (knowledge_base_id, filename, status)
SELECT id, 'invalid-status.pdf', 'corrupted'
FROM new_kb;
'@

$invalidStatusOutput = & docker compose exec -T postgres psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $invalidStatusSql 2>&1
$invalidStatusExitCode = $LASTEXITCODE
$invalidStatusOutput

if ($invalidStatusExitCode -eq 0) {
    throw "失败路径未触发：非法 status 不应写入数据库。"
}

if (($invalidStatusOutput | Out-String) -notmatch "ck_documents_status") {
    throw "数据库拒绝了写入，但没有命中预期的状态约束。"
}

docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT count(*) AS leaked_rows FROM knowledge_bases WHERE name = 'day02-invalid-status';"
```

### 预期结果

- psql 退出码非 `0`，错误包含 `ck_documents_status`。
- `leaked_rows` 为 `0`，没有非法文档或临时父记录。
- 既有 schema、revision 和业务数据保持不变。

### 场景 2：不存在的知识库外键被拒绝

```powershell
$invalidForeignKeySql = @'
INSERT INTO documents (knowledge_base_id, filename, status)
VALUES (2147483647, 'orphan.pdf', 'pending');
'@

$invalidForeignKeyOutput = & docker compose exec -T postgres psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $invalidForeignKeySql 2>&1
$invalidForeignKeyExitCode = $LASTEXITCODE
$invalidForeignKeyOutput

if ($invalidForeignKeyExitCode -eq 0) {
    throw "失败路径未触发：不存在的 knowledge_base_id 不应写入。"
}

if (($invalidForeignKeyOutput | Out-String) -notmatch "fk_documents_knowledge_base_id") {
    throw "数据库拒绝了写入，但没有命中预期的知识库外键。"
}
```

### 预期结果

- psql 退出码非 `0`，错误包含 `fk_documents_knowledge_base_id`。
- 数据库中不产生 `orphan.pdf` 文档。
- 不删除或修改任何已有知识库来制造失败场景。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `Base.metadata.tables` 为空 | 没有导入 `app.orm_models` | `migrations/env.py` 顶部 | 添加模块导入，不要用 `create_all()` |
| autogenerate 生成空迁移 | 模型未注册或继承了另一个 Base | metadata 检查命令 | 三个类必须继承 `app.db.Base`，再单独处理这个未应用的空 revision |
| `Target database is not up to date` | 数据库没先到 Day 1 head | `alembic current/heads` | 先升级到 `751357b5d274`，不要手改 `alembic_version` |
| `type "vector" does not exist` | vector 基线未应用或 revision 链错误 | 查询 `pg_extension` | 确认新迁移接在 `751357b5d274` 后 |
| `NameError: Vector` | 迁移使用 `Vector(512)` 却没导入 | 新迁移 imports | 添加 `from pgvector.sqlalchemy import Vector` |
| 迁移使用未定义的 `pgvector.sqlalchemy.vector.VECTOR` | Alembic 自定义类型渲染不完整 | embedding 列 | 按第五节统一成 `Vector(512)` |
| `relation ... already exists` | 有人手工创建同名表 | schema 与 `alembic_version` | 停止升级，先确认来源；不要直接 drop/stamp |
| downgrade 保护脚本中止 | 三张表已有数据 | 三张表 count | 保留数据并停止回滚，不使用 `CASCADE` |
| Git 暂存提示词文件 | 使用了 `git add .` | `git diff --cached --name-only` | 只 add 第十一节明确路径 |

## 十、检查最终代码差异

```powershell
$migration = Get-ChildItem -Path "migrations/versions" -Filter "*_create_core_rag_tables.py" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $migration) {
    throw "缺少 Day 2 迁移文件。"
}

git status --short
git diff -- migrations/env.py
Get-Content -Path app/orm_models.py
Get-Content -Path $migration.FullName
Get-Content -Path docs/17天每日学习/Day02.md
git diff --check
```

重点检查：

- 三个 ORM 类都继承 `app.db.Base`，没有新建第二套 Engine、Session 或 Base。
- `app/models.py` 的 Pydantic schema 和 `app/database.py` 的 SQLite 历史没有被修改。
- 新 revision 的 `down_revision` 是 `751357b5d274`，升级顺序是知识库 → 文档 → Chunk，回滚相反。
- 模型与迁移的字段、nullable、默认值、命名约束、外键级联、索引和 `Vector(512)` 一致。
- 没有生成向量近似索引、Repository、API 或数据库写入 Service。
- diff 中没有 `.env`、密码、API Key、数据库文件、缓存或无关文档。
- `docs/17天-当日项目升级计划生成器.md` 仍是用户自己的未暂存修改。

## 十一、Git 提交

核心模型、metadata 注册和迁移文件实现完整，并完成静态差异检查后即可提交。第六至第八节验证和第十五节结果填写是可选项，不是提交前置条件。

```powershell
$migration = Get-ChildItem -Path "migrations/versions" -Filter "*_create_core_rag_tables.py" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $migration) {
    throw "缺少 Day 2 迁移文件，停止提交。"
}

git add -- app/orm_models.py migrations/env.py $migration.FullName docs/17天每日学习/Day02.md
git diff --cached --name-only
git diff --cached -- app/orm_models.py migrations/env.py $migration.FullName docs/17天每日学习/Day02.md
git commit -m "feat: add core RAG data model"
```

预期暂存区只包含：

```text
app/orm_models.py
migrations/env.py
migrations/versions/<动态 revision>_create_core_rag_tables.py
docs/17天每日学习/Day02.md
```

如果暂存区出现提示词文件、`.env` 或其他路径，停止提交并逐项取消误暂存；不要使用会覆盖工作区的破坏性 Git 命令。

## 十二、面试高频问题与参考答案

### 问题 1：ORM 模型和 Pydantic 模型有什么区别，为什么项目要分文件？

#### 30 秒参考答案

Pydantic 定义 API 输入输出的数据契约，负责解析和校验 JSON；SQLAlchemy ORM 定义数据库结构和持久化映射，负责表、列、外键、约束和关系。当前项目把接口 schema 留在 `app/models.py`，三张业务表放在 `app/orm_models.py`，避免接口和数据库演进互相污染。

#### 继续追问：能否让一个类同时承担两种职责？

技术上可以封装转换，但直接混用容易把数据库内部字段暴露到 API，也让 relationship、延迟加载和序列化纠缠。当前分层目标下，明确分开更易维护。

#### 回答时要引用的项目证据

- `app/models.py` 中的 `ChatRequest`、`RAGChatResponse`。
- `app/orm_models.py` 中的三个业务实体。
- `migrations/env.py` 只导入 ORM 模块来注册 metadata。

### 问题 2：有外键后为什么还要建立索引？

#### 30 秒参考答案

外键保证子记录引用的父记录存在，解决完整性；索引服务于查询和连接性能。PostgreSQL 不会因外键自动建立所有查询所需索引。本项目按知识库和状态筛文档、按文档和页码取 Chunk，所以建立两个以外键为最左列的联合索引。

#### 继续追问：为什么不为每一列都建索引？

索引占空间并增加写入成本。Day 2 只根据已知访问模式建两个联合索引；向量索引等检索方式和数据量明确后再选。

#### 回答时要引用的项目证据

- `ix_documents_knowledge_base_id_status`。
	知识库
	 ↓
	找该知识库中特定状态的 documents
- `ix_chunks_document_id_page_number`。
	文档
	 ↓
	查该文档某一页的 chunks
- Day 3 父级查询和 Day 5 知识库内检索链路。

### 问题 3：为什么文档状态还要做数据库 CheckConstraint？

#### 30 秒参考答案

应用校验只覆盖当前 Python 入口，数据库约束还能覆盖脚本、后台任务和未来服务。`ck_documents_status` 把状态限制为 pending、processing、ready、failed，使 Repository 和 Service 能依赖稳定状态机。

#### 继续追问：为什么这里不用 PostgreSQL ENUM？

ENUM 约束更强，但增删值需要类型迁移。当前状态仍可能演进，`String + CheckConstraint` 已提供数据库级保证，迁移也更直接。

我没有只依赖 Python 层的状态校验，因为未来写数据库的不一定只有当前 API，还可能有 Worker、脚本或者其他服务。所以我在 `documents.status` 上增加了 `ck_documents_status`，把状态限制为 `pending / processing / ready / failed`，这样数据库本身也能保证状态合法。这里没有直接使用 PostgreSQL ENUM，是因为状态集合后续可能变化，`String + CheckConstraint` 已经能提供数据库级完整性，同时迁移和扩展更灵活。

#### 回答时要引用的项目证据

- `documents.status` 默认值 `pending`。
- `ck_documents_status` 的四个允许值。
- 第八节非法状态失败路径。

### 问题 4：ORM cascade 和数据库 `ON DELETE CASCADE` 有什么区别？

#### 30 秒参考答案

ORM cascade 控制通过 Session 操作对象图时父子对象如何一起保存或删除；数据库 `ON DELETE CASCADE` 保证任何 SQL 入口删除父记录时都能清理子记录。当前同时配置 `cascade="all, delete-orphan"`、`passive_deletes=True` 和外键级联，让两层规则一致。

#### 继续追问：为什么 downgrade 仍按子表到父表删除？

级联删除主要针对数据，不代表迁移可以忽略表依赖。按 chunks、documents、knowledge_bases 逆序 drop 更明确，也更容易审查。

#### 回答时要引用的项目证据

- 两个 relationship 的 cascade 和 `passive_deletes=True`。
- 两个命名外键的 `ON DELETE CASCADE`。
- migration 的 downgrade 顺序。

### 问题 5：为什么向量维度必须固定为 512？

#### 30 秒参考答案

同一列中的数据必须与查询向量维度一致，距离计算才有意义。当前 Embedding 模型输出 512 维，`Vector(512)` 把模型假设变成数据库契约，错误维度会在写入时尽早失败。

#### 继续追问：以后换成 768 维模型怎么办？

不能只改 Python 常量。要新增列或表、重算历史 Embedding、切换查询后再处理旧列；旧向量与新模型的语义空间也不兼容。

#### 回答时要引用的项目证据

- 当前 Embedding 模型的 512 维输出。
- `Chunk.embedding` 的 `Vector(512)`。
- `format_type(...) = vector(512)` 和 `vector_dims(...) = 512`。

## 十三、今天的完整数据流

### 正常路径

```text
Python 导入 app.orm_models
→ 三个类注册到 Base.metadata
→ Alembic env 读取同一个 metadata
→ autogenerate 比较 metadata 与当前 PostgreSQL schema
→ 新 revision 接在 vector 扩展 revision 后
→ upgrade 依次建立 knowledge_bases、documents、chunks
→ 外键、状态/数值/唯一约束、联合索引和 vector(512) 落库
→ 合法的知识库、文档和 Chunk 可以按父子顺序写入
→ Day 3 Repository 可以依赖稳定 ORM 实体
```

### 失败路径

```text
非法 status
→ 命中 ck_documents_status
→ 整条语句失败并回滚
→ 不留下非法文档或临时父记录

不存在的 knowledge_base_id
→ 命中 fk_documents_knowledge_base_id
→ 子记录拒绝写入
→ 不产生孤儿文档

回滚迁移
→ 先确认三张表为空
→ 按 chunks → documents → knowledge_bases 删除
→ Day 1 vector 扩展和 revision 基线保留
→ 再次 upgrade 恢复新 head
```

## 十四、完成标准

```text
[ ] 能解释 Pydantic schema 与 SQLAlchemy ORM 的职责差异
[ ] app/orm_models.py 完整定义 KnowledgeBase、Document、Chunk
[ ] 三个类共同继承 app.db.Base，metadata 中能看到三张表
[ ] KnowledgeBase.name 有命名唯一约束
[ ] Document 有知识库外键、四状态约束、失败原因和时间字段
[ ] Chunk 有文档外键、页码、顺序、原文和 Vector(512)
[ ] 页码、Chunk 顺序和同文档顺序唯一性由数据库约束保护
[ ] 两级外键使用 ON DELETE CASCADE，ORM 生命周期配置匹配
[ ] 两个联合索引符合后续查询，未提前建立向量近似索引
[ ] migrations/env.py 导入 app.orm_models，保留 Day 1 安全配置
[ ] 新 revision 的 down_revision 是 751357b5d274，升级/回滚顺序正确
[ ] 没有实现 Repository、入库 Service 或修改 API/FAISS/SQLite
[ ] 暂存区只包含 Day 2 目标文件，不含提示词修改、秘密或无关改动
[ ] 核心实现已用边界清晰的提交保存；验证和结果记录均为可选
```

## 十五、可选执行记录

本节只在你希望保留运行证据时填写；不执行验证、不保存输出或不填写本节，都不会把已实现并提交的 Day 2 降级为“待验收”。

- 实际完成：已完成
- 正常路径结果：可选，尚未执行
- 失败路径结果：可选，尚未执行
- 迁移往返结果：可选，尚未执行
- 遇到的错误：暂无
- 最终解决方式：暂无
- 用户完成标记：完成
- Git commit：已提交
