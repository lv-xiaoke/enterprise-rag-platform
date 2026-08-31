# Day 2：建立企业 RAG 的三张核心数据表

今天会用 SQLAlchemy 定义知识库、文档和 Chunk 三个 ORM 模型并生成可回滚迁移，解决 PostgreSQL 目前只有 `vector` 扩展却没有业务结构的问题，并让你能够在面试中解释数据实体、外键约束、索引与向量字段的设计取舍。

> 预计用时：60 分钟  
> 今日唯一核心产物：`knowledge_bases`、`documents`、`chunks` 三张表的 ORM 模型和一条可验证、可回滚的 Alembic 迁移  
> 对应主计划：Day 2

## 一、开始前先明确边界

### 今天完成什么

- 新建 `app/db_models.py`，定义 `KnowledgeBase`、`Document`、`Chunk` 三个 SQLAlchemy ORM 模型。
- 为三张表加入主键、两个外键、文档状态约束、必要的数据合法性约束和查询索引。
- 将 `embedding` 定义为数据库端的 `vector(512)`，与当前 `BAAI/bge-small-zh-v1.5` 输出维度保持一致。
- 让 Alembic 能发现 ORM 元数据，生成并检查一条只负责三张业务表的迁移。
- 真实完成 `upgrade → 约束失败验证 → downgrade → upgrade`，并保留命令输出摘要。

### 今天不做什么

- 不实现创建或查询知识库的数据访问函数，属于 Day 3。
- 不解析 PDF、生成 Embedding 或写入真实 Chunk，属于 Day 4。
- 不实现 pgvector Top-K 查询，也不创建 HNSW/IVFFlat 向量索引，属于 Day 5 及后续基于数据规模的优化。
- 不新增知识库、上传或问答 API，分别属于 Day 6 和 Day 7。
- 不重命名现有 `app/models.py`；它当前负责 Pydantic 请求/响应结构，今天只新增独立的数据库模型模块。
- 不修改 Day 1 的 `vector` 扩展迁移，也不清理任何目录或缓存。

### 当前真实起点

- `[当前事实]` 仓库工作区在生成本计划时为干净状态，近期已有独立提交 `2f2afb3 Day1`。
- `[当前事实]` 使用仓库的 `.venv` 实测，数据库连接探针返回 `1`，PostgreSQL 容器为 `healthy`。
- `[当前事实]` Alembic 当前位于 `751357b5d274 (head)`，数据库端已能查询到 `vector` 扩展。
- `[当前事实]` PostgreSQL 的 `public` schema 目前只有 `alembic_version`，尚无 `knowledge_bases`、`documents`、`chunks`。
- `[当前事实]` `app/db.py` 已提供 `Base`、`engine` 和 `SessionLocal`，但目前没有任何 ORM 类注册到 `Base.metadata`。
- `[当前事实]` `app/models.py` 中的类都继承自 Pydantic `BaseModel`，用于 API 数据校验，不是数据库表。
- `[当前事实]` `migrations/env.py` 已把 `Base.metadata` 交给 Alembic，但如果它没有导入新 ORM 模块，自动生成迁移仍会看不到三张表。
- `[待实测]` 新迁移的自动生成内容、升级与回滚结果、数据库约束和索引都需要你亲自运行后记录，不能把下文预期结果写成已经通过。

## 二、核心知识铺垫

### 1. ORM 模型与 Pydantic 模型

- 通俗解释：ORM 模型描述“数据库怎样保存数据”，Pydantic 模型描述“接口允许接收或返回什么数据”。
- 在本项目中的职责：`app/db_models.py` 对应 PostgreSQL 三张表；现有 `app/models.py` 继续校验 `/chat`、`/upload`、`/rag/chat` 的 HTTP 数据。
- 与现有代码的关系：ORM 类继承 `app.db.Base`，它们的表结构会进入 `Base.metadata`；Pydantic 类继承 `BaseModel`，不会被 Alembic 当作表。
- 容易混淆的点：两类对象都可以叫“模型”，但 ORM 对象不能替代接口校验，Pydantic 对象也不会自动持久化到数据库。

### 2. 外键、约束与索引

- 通俗解释：外键保证“子记录指向的父记录真实存在”；约束阻止非法状态或负数进入数据库；索引像目录，帮助数据库更快定位候选行。
- 在本项目中的职责：`documents.knowledge_base_id` 把文档归属到知识库，`chunks.document_id` 把片段归属到文档；`documents.status` 只能是 `processing`、`ready`、`failed`。
- 与后续检索的关系：Day 5 会先按知识库和 `ready` 状态过滤文档，所以 `documents(knowledge_base_id, status)` 需要联合索引；`chunks(document_id, chunk_index)` 的唯一约束既避免同一文档出现重复序号，也能支持按 `document_id` 查 Chunk。
- 容易混淆的点：外键不会自动在 PostgreSQL 的引用列上创建索引；主键和唯一约束会创建索引，但普通外键本身不会。

### 3. `vector(512)` 与向量索引

- 通俗解释：`vector(512)` 是“只允许恰好 512 个数”的数据库列类型；向量索引则是加速近似相似度搜索的额外结构。
- 在本项目中的职责：`chunks.embedding` 保存每个文本 Chunk 的 BGE 向量，维度错误时应由数据库拒绝。
- 与现有代码的关系：`app/services/embedding_service.py` 当前把模型输出转成 Python 列表；Day 4 才会把该列表写入今天创建的列。
- 容易混淆的点：创建 `vector(512)` 列不等于已经创建 HNSW/IVFFlat 索引。当前数据量很小，先保证结构和过滤正确，再用真实评测决定是否需要近似索引。

### 4. `Base.metadata` 与 Alembic 自动生成

- 通俗解释：`Base.metadata` 是 SQLAlchemy 已知表结构的清单；Alembic 自动生成会比较“这份清单”和“当前数据库”之间的差异。
- 在本项目中的职责：新 ORM 类必须被 Python 导入，三张表才会登记进 `Base.metadata`，随后 `revision --autogenerate` 才能生成建表语句。
- 与现有代码的关系：`migrations/env.py` 已设置 `target_metadata = Base.metadata`，今天只需在读取该对象前导入 `app.db_models`。
- 容易混淆的点：Python 文件存在并不代表其中的类已执行注册；如果生成了一条空迁移，首先检查导入链，而不是手写一份看似正确的迁移掩盖问题。

## 三、逐步完成今天的升级

### 步骤 1：固定表结构并编写 ORM 模型（建议 18 分钟）

**为什么先做这一步**

迁移应当来源于明确的 ORM 结构；先把字段、约束和索引的职责确定下来，后面才能判断 Alembic 自动生成是否准确。

**[你来完成]**

1. 在项目根目录确认起点，并继续使用仓库自己的 `.venv`，不要误用系统或 Anaconda 的 `python`：

```powershell
git status --short
.\.venv\Scripts\python.exe -c "from app.db import check_database_connection; print(check_database_connection())"
.\.venv\Scripts\alembic.exe current
```

2. 检查现有职责后，新建 `app/db_models.py`：

```powershell
Get-Content -LiteralPath app\db.py
Get-Content -LiteralPath app\models.py
```

3. 使用下面的最小结构。字段必须覆盖主计划，不添加用户、权限、文件存储地址等未来字段：

```python
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "page_count >= 0 AND chunk_count >= 0",
            name="ck_documents_counts_nonnegative",
        ),
        Index("ix_documents_knowledge_base_status", "knowledge_base_id", "status"),
    )

    # [你来完成] id、knowledge_base_id、filename、status、
    # page_count、chunk_count、created_at。
    # knowledge_base_id 使用 ForeignKey("knowledge_bases.id")；
    # status 默认 processing，两个计数默认 0。


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunks_document_chunk_index"
        ),
        CheckConstraint("page > 0", name="ck_chunks_page_positive"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_index_nonnegative"),
    )

    # [你来完成] id、document_id、page、chunk_index、text、embedding。
    # document_id 使用 ForeignKey("documents.id")；
    # text 使用 Text；embedding 使用 Vector(512)；所有字段均不可为空。
```

4. 暂不设置 `ondelete="CASCADE"`。当前主计划没有删除 API，先让 PostgreSQL 默认阻止仍有子记录时删除父记录，等删除语义明确后再决定级联策略。

**[AI 辅助]**

完成后可以让 AI 只检查字段是否与主计划逐项对应、联合索引列顺序是否支持 Day 5 的过滤，不要让 AI 扩展业务字段或提前实现关系加载和 CRUD。

**预期结果**

- `app/db_models.py` 中只有三个 ORM 类，字段分别为主计划规定的 3、7、6 项。
- `Document` 的状态和计数、`Chunk` 的页码和序号均有数据库级约束。
- `embedding` 明确是 `Vector(512)`，而不是普通 JSON、数组或没有维度的 `Vector()`。

**理解检查**

> 请用自己的话解释：为什么现有 `app/models.py` 不能直接当作三张数据库表？

### 步骤 2：注册元数据并生成迁移（建议 12 分钟）

**为什么现在做这一步**

Alembic 只能比较已经加载进 `Base.metadata` 的表；先验证元数据，再自动生成，能及时发现“空迁移”问题。

**[你来完成]**

1. 在 `migrations/env.py` 的 `target_metadata = Base.metadata` 之前导入新模块：

```python
import app.db_models  # 导入会让三个 ORM 类注册到 Base.metadata
from app.db import Base, engine
```

2. 先验证元数据，不连接数据库也应看到三张表：

```powershell
.\.venv\Scripts\python.exe -c "import app.db_models; from app.db import Base; print(sorted(Base.metadata.tables))"
```

预期输出包含：

```text
['chunks', 'documents', 'knowledge_bases']
```

3. 自动生成一条迁移并打开最新文件检查：

```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "create rag core tables"
$migration = Get-ChildItem -LiteralPath migrations\versions -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
Get-Content -LiteralPath $migration.FullName
git diff -- app\db_models.py migrations\env.py migrations\versions
```

4. 逐项确认迁移：`down_revision` 指向 `751357b5d274`；升级按知识库、文档、Chunk 的顺序建表；存在两个外键、`vector(512)`、命名约束和联合索引；降级按相反顺序删除；没有修改 `vector` 扩展或无关表。

**预期结果**

- 只新增一条非空迁移，内容与 ORM 模型一致。
- 如果迁移为空，停止并修正 `migrations/env.py` 的导入，不要手工补一份脱离 ORM 的建表迁移。

**理解检查**

> 为什么 `target_metadata = Base.metadata` 已经存在，仍然必须导入 `app.db_models`？

### 步骤 3：验证正常升级和真实数据库结构（建议 10 分钟）

**为什么这样验证**

ORM 和迁移文件只是设计；只有迁移真实执行，并从 PostgreSQL 反查表、外键、索引和列类型，才能证明核心产物存在。

**[你来完成]**

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current

@'
from sqlalchemy import inspect
from app.db import engine

inspector = inspect(engine)
tables = set(inspector.get_table_names())
expected = {"knowledge_bases", "documents", "chunks"}
assert expected <= tables, tables

document_targets = {
    item["referred_table"] for item in inspector.get_foreign_keys("documents")
}
chunk_targets = {
    item["referred_table"] for item in inspector.get_foreign_keys("chunks")
}
assert document_targets == {"knowledge_bases"}, document_targets
assert chunk_targets == {"documents"}, chunk_targets

with engine.connect() as connection:
    vector_type = connection.exec_driver_sql("""
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        WHERE c.relname = 'chunks'
          AND a.attname = 'embedding'
          AND a.attnum > 0
    """).scalar_one()

assert vector_type == "vector(512)", vector_type
print("tables:", sorted(expected))
print("foreign keys: documents -> knowledge_bases, chunks -> documents")
print("embedding:", vector_type)
'@ | .\.venv\Scripts\python.exe -
```

**预期结果**

- `current` 显示新迁移为 `head`。
- 脚本打印三张表、两条正确的父子关系以及 `embedding: vector(512)`。
- 这是“预期结果”；只有你实际看到输出后，才能把它记录为已通过。

**理解检查**

> 请从 `KnowledgeBase` 开始，说明一条 Chunk 如何通过两个外键找到所属知识库，以及 Day 5 为什么要先过滤文档状态。

### 步骤 4：验证非法状态和迁移回滚边界（建议 15 分钟）

**为什么必须验证失败路径**

数据库模型的价值不只是能建表，还要在应用代码漏检时拒绝非法数据；迁移也必须能回到 Day 1 基线，再恢复到最新结构。

**[你来完成]**

1. 尝试在同一事务中写入一个知识库和非法状态文档。预期第二条 SQL 被 `ck_documents_status` 拒绝，整笔事务回滚，不留下第一条记录：

```powershell
@'
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db import engine

marker = "__day2_invalid_status_check__"

try:
    with engine.begin() as connection:
        kb_id = connection.execute(
            text("INSERT INTO knowledge_bases (name) VALUES (:name) RETURNING id"),
            {"name": marker},
        ).scalar_one()
        connection.execute(
            text("""
                INSERT INTO documents
                    (knowledge_base_id, filename, status, page_count, chunk_count)
                VALUES (:kb_id, 'invalid.pdf', 'unknown', 0, 0)
            """),
            {"kb_id": kb_id},
        )
except IntegrityError as exc:
    constraint = getattr(exc.orig.diag, "constraint_name", None)
    assert constraint == "ck_documents_status", constraint
    print("invalid status rejected by:", constraint)
else:
    raise SystemExit("expected ck_documents_status to reject the row")

with engine.connect() as connection:
    remaining = connection.execute(
        text("SELECT count(*) FROM knowledge_bases WHERE name = :name"),
        {"name": marker},
    ).scalar_one()
assert remaining == 0, remaining
print("failed transaction rolled back; marker rows:", remaining)
'@ | .\.venv\Scripts\python.exe -
```

2. 在回滚迁移前确认三张新表没有业务数据。若任一计数不为 `0`，立即停止，不要执行 `downgrade`：

```powershell
@'
from app.db import engine
with engine.connect() as connection:
    for table in ("knowledge_bases", "documents", "chunks"):
        count = connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one()
        print(table, count)
'@ | .\.venv\Scripts\python.exe -
```

3. 计数全为 `0` 后，回到 Day 1 迁移；确认三张表消失但 `vector` 扩展仍存在，然后恢复到 `head`：

```powershell
.\.venv\Scripts\alembic.exe downgrade -1
.\.venv\Scripts\alembic.exe current

@'
from sqlalchemy import inspect
from app.db import engine

with engine.connect() as connection:
    tables = set(inspect(connection).get_table_names())
    vector_extension = connection.exec_driver_sql(
        "SELECT extname FROM pg_extension WHERE extname = 'vector'"
    ).scalar_one_or_none()

assert not {"knowledge_bases", "documents", "chunks"} & tables, tables
assert vector_extension == "vector", vector_extension
print("Day 2 tables removed; Day 1 vector extension kept")
'@ | .\.venv\Scripts\python.exe -

.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
```

**预期结果**

- 非法状态被命名约束拒绝，并且失败事务没有留下知识库记录。
- `downgrade -1` 只撤销 Day 2 的三张表，不撤销 Day 1 的 `vector` 扩展。
- 再次 `upgrade head` 后三张表恢复，Alembic 回到新迁移 `head`。

**理解检查**

> 为什么非法文档插入失败后，前面已经执行的知识库插入也不应该保留？这与 Day 8 的“上传失败不留下半成品 Chunk”有什么联系？

### 步骤 5：记录结果并准备提交（建议 5 分钟）

- 在本文件的底部只记录你真实执行的命令与结果摘要；未运行的项目继续保持 `[ ]`。
- 执行以下检查，确认没有 `.env`、缓存、数据库文件或无关修改：

```powershell
git status --short
git diff --check
git diff -- app\db_models.py migrations\env.py migrations\versions docs\17天每日学习\Day02.md
```

- 只暂存 Day 2 相关文件；生成计划时工作区是干净的，但提交前仍需重新检查。
- 建议 commit message：`feat: add core RAG database models`
- 验收全部通过后再由你执行 Git commit，本计划不会替你提交。

## 四、面试高频问题

### 问题 1：Pydantic 模型和 SQLAlchemy ORM 模型有什么区别？

- 考察点：API 边界与持久化边界是否分清。
- 回答要点：Pydantic 负责输入输出校验和序列化；ORM 负责表、列、关系以及数据库读写映射；二者可能字段相似，但生命周期和职责不同。
- 结合本项目：说明为什么保留 `app/models.py`，并把三张数据库表放进 `app/db_models.py`。

### 问题 2：为什么 Alembic 自动生成迁移前必须导入 ORM 模型？

- 考察点：是否理解自动迁移的工作原理，而不只是会背命令。
- 回答要点：Alembic 比较的是 `target_metadata` 与数据库；类定义只有被导入并执行后才注册到 `Base.metadata`；未导入通常得到空迁移。
- 结合本项目：指出 `migrations/env.py` 中导入 `app.db_models` 与 `target_metadata = Base.metadata` 的配合关系。

### 问题 3：有外键以后为什么还要考虑索引？

- 考察点：数据完整性与查询性能的区别。
- 回答要点：外键保证引用存在，不等于为引用列自动创建索引；索引服务于过滤、连接和排序；索引越多也会增加写入和维护成本。
- 结合本项目：`documents(knowledge_base_id, status)` 支持知识库和状态联合过滤，`chunks(document_id, chunk_index)` 唯一约束同时避免重复序号。

### 问题 4：为什么用字符串加 CHECK 约束表示文档状态，而不是只靠 Python 枚举？

- 考察点：应用校验与数据库最终防线。
- 回答要点：应用枚举改善代码表达，但其他脚本或并发路径仍可能绕过应用；数据库 CHECK 能守住所有写入入口；原生 PostgreSQL ENUM 更严格，但修改枚举值的迁移成本更高。
- 结合本项目：三个固定状态通过 `ck_documents_status` 验证，非法 `unknown` 状态应触发失败并回滚整笔事务。

### 问题 5：为什么今天创建 `vector(512)`，却不立即创建 HNSW 或 IVFFlat？

- 考察点：正确性、规模和性能优化的先后顺序。
- 回答要点：定长向量列先保证维度正确；近似索引是性能结构，会引入构建成本、参数和召回率取舍；小数据量可以先精确扫描，再用真实延迟和召回实验决定。
- 结合本项目：Day 2 只建立正确持久化结构，Day 5 完成带知识库和状态过滤的检索，后续再根据评测决定索引。

## 五、今天结束后应当留下的证据

- 代码或配置：`app/db_models.py`、更新后的 `migrations/env.py`、一条只创建三张核心表的迁移文件。
- 运行证据：元数据表名、Alembic 新 `head`、数据库反查到的两条外键和 `vector(512)`。
- 失败证据：`ck_documents_status` 拒绝非法状态，事务回滚后标记知识库数量为 `0`。
- 回滚证据：`downgrade -1` 后三张表消失但 `vector` 扩展仍存在，再次 `upgrade head` 后恢复。
- 学习记录：能画出 `knowledge_bases → documents → chunks` 数据关系，并解释每个约束和索引服务的风险或查询。
- Git：验收通过后只提交 Day 2 相关文件，记录真实 commit hash 或提交说明。

# Day 2 完成标准

```text
[ ] 能解释 Pydantic 模型与 SQLAlchemy ORM 模型的职责区别，以及为什么本项目分文件保存
[ ] 能解释 ORM 模块必须先导入，三张表才会进入 Base.metadata 并被 Alembic 发现
[ ] app/db_models.py 已定义 KnowledgeBase、Document、Chunk，字段与 17 天主计划逐项一致
[ ] 新迁移包含两条外键、vector(512)、文档状态/计数约束、Chunk 页码/序号约束和必要索引
[ ] upgrade head 后从 PostgreSQL 真实反查到三张表、正确外键关系和 vector(512)
[ ] 非法文档状态被 ck_documents_status 拒绝，失败事务没有留下知识库记录
[ ] 能从知识库、文档讲到 Chunk 和向量，并说明 Day 5 检索如何限制知识库与 ready 状态
[ ] downgrade -1 后仅撤销 Day 2 三张表且保留 vector 扩展，再次 upgrade head 后恢复
[ ] 已记录真实命令和结果，没有把预期输出写成已通过
[ ] git diff 中没有秘密、缓存或无关修改，验收后完成边界清晰的 Git commit
```

实际完成：未完成

遇到的卡点：暂无

Git commit：未提交
