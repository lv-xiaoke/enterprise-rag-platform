# Day 3：建立知识库、文档和 Chunk 的 Repository 层

今天将直接建立 KnowledgeBase、Document 和 Chunk 的最小数据访问层，使项目获得可复用、事务边界清晰的 PostgreSQL ORM 操作能力，并为面试中的 Repository/Service 分层、Session 生命周期和事务问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：覆盖知识库创建与查询、文档创建与状态更新、Chunk 批量保存与查询的最小 Repository 接口  
> 当前真实状态：已完成
> 对应总体安排：Day 3

## 一、今天完成后的项目变化

### 升级前

```text
app/db.py
→ 已有应用级 Engine、SessionLocal 和 Base

app/orm_models.py
→ 已有 KnowledgeBase、Document、Chunk ORM 模型

PostgreSQL
→ 已有三张业务表及其外键、约束、索引和 vector(512)

业务代码
→ 尚无统一的数据访问入口
→ 后续 Service 若直接操作 Session/ORM，查询和写入会散落各处
```

### 升级后

```text
Service / 后续业务编排
→ 创建并持有一次业务操作的 Session
→ KnowledgeBaseRepository：create / get / list_all
→ DocumentRepository：create / get / list_by_knowledge_base / update_status
→ ChunkRepository：bulk_create / list_by_document
→ Repository 使用同一个 Session 执行 add / select / flush / refresh
→ Service 成功时 commit，失败时 rollback，最后 close
→ SQLAlchemy
→ PostgreSQL + pgvector
```

### 今天在完整项目中的位置

- 所属阶段：数据基础。
- 所属链路：API/Service 与 PostgreSQL 之间的数据访问边界，同时服务于文档入库和用户问答两条链路。
- 今天的输入：Day 1 的 `SessionLocal`，以及 Day 2 的三个 ORM 模型和 `e780fe92751b` 建表迁移。
- 今天的输出：三个同步 Repository、一个 Chunk 写入数据对象，以及统一导出入口。
- 下一天为什么需要它：Day 4 要在同一事务中创建 Document、批量保存带页码和 512 维向量的 Chunk，并更新文档状态；这些稳定的数据访问动作必须先存在。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1 有匹配提交 `ac14dd5`，`app/db.py` 已定义同步 `engine`、`SessionLocal` 和 `Base`，固定依赖为 SQLAlchemy `2.0.52` 与 psycopg `3.3.4`。
- `[当前事实]` Day 2 有匹配提交 `e156828`，`app/orm_models.py` 已定义 `KnowledgeBase`、`Document`、`Chunk` 及双向 relationship。
- `[当前事实]` `migrations/versions/e780fe92751b_create_core_rag_tables.py` 接在 `751357b5d274` 后，静态定义了三张表、两个外键、状态/数值/唯一约束、联合索引和 `Vector(512)`。
- `[当前事实]` `Document.status` 当前允许 `pending`、`processing`、`ready`、`failed`，`Chunk` 使用 `page_number`、`chunk_index`、`content`、`embedding` 字段。
- `[当前事实]` `EmbeddingService.embed_documents()` 返回 `list[list[float]]`，可直接成为后续 `ChunkCreate.embedding` 的输入。
- `[当前事实]` 当前应用和数据库入口都是同步 SQLAlchemy；今天不引入异步 Engine 或 AsyncSession。

### 仍然缺少

- `[当前事实]` 仓库中不存在 `app/repositories/`，也没有任何 `KnowledgeBaseRepository`、`DocumentRepository` 或 `ChunkRepository`。
- `[当前事实]` 尚无统一的知识库 create/get/list、文档 create/get/list/update、Chunk 批量写入/查询方法。
- `[当前事实]` 尚未形成“Repository 不提交事务，调用方决定 commit/rollback/close”的代码边界。
- `[当前事实]` 没有针对 Repository 正常路径、未找到结果和数据库约束异常的自动测试；正式 pytest 测试集属于 Day 12。

### 待实测

- `[待实测]` 本机 PostgreSQL 容器当前是否健康，数据库 revision 是否已到 `e780fe92751b (head)`。
- `[待实测]` 新 Repository 模块能否在当前 Python 环境成功导入。
- `[待实测]` 一次 Session 中能否创建并查询 KnowledgeBase、创建并更新 Document、批量保存并顺序查询 Chunk。
- `[待实测]` 调用方 rollback 后，Repository 已 flush 的临时数据是否全部消失。
- `[待实测]` 不存在资源是否返回 `None`，无效外键是否继续作为 `IntegrityError` 向调用方暴露并可安全回滚。

### 需要保护的用户修改

- `docs/17天每日学习/Day02.md` 当前有未提交修改：用户已把“当前真实状态”改为“已完成”。必须保留，不覆盖、不还原，也不放入 Day 3 的 `git add`。
- 今天只新建 `app/repositories/` 下四个文件和本计划 `docs/17天每日学习/Day03.md`；不处理其他修改。
- 不读取或打印真实 `.env`、数据库密码、LLM Key；只允许读取公开变量名或从运行中的 Compose 容器取得非秘密的数据库用户名、数据库名。

## 三、今天必须理解的核心知识

### 1. Repository 与 Service 的职责边界

[[Repository 与 Service 的职责边界]]

- 一句话解释：Repository 封装“数据怎样存取”，Service 编排“业务按什么顺序执行”。
- 在当前项目中的职责：三个 Repository 只接收参数、操作 ORM、执行查询或 `flush`；Day 4 的文档入库 Service 才负责 PDF 解析、Chunk 切分、Embedding、状态流转和事务结果。
- 与其他组件的关系：`API → Service → Repository → SQLAlchemy → PostgreSQL`；Embedding、PDF 和 LLM 服务不会被塞进 Repository。
- 容易混淆的点：Repository 不是“所有数据库相关逻辑的垃圾桶”，也不应该知道 HTTP 状态码或上传文件对象。
- 面试一句话：我把稳定的数据访问动作集中到 Repository，把跨组件流程留给 Service，从而让 API 不直接依赖 SQLAlchemy 细节。

### 2. Session 与事务所有权

[[Session 与事务所有权]]

- 一句话解释：Session 是一次业务工作单元，谁编排多个 Repository，谁就应该拥有 commit、rollback 和 close 的决定权。
- 在当前项目中的职责：调用方创建一个 `SessionLocal()`，把同一个 Session 传给三个 Repository；Repository 不创建第二个 Session，也不自行提交。
- 与其他组件的关系：应用长期复用 Engine；一次 Service 调用使用一次 Session；多个 Repository 操作共享同一个数据库事务。
- 容易混淆的点：如果 `DocumentRepository.create()` 自己 commit，后面的 Chunk 写入失败时就无法把已提交的 Document 一起回滚。
- 面试一句话：Repository 只 `flush` 让 SQL 到达数据库并获得主键，最终 commit/rollback 由业务工作单元统一控制，保证跨 Repository 原子性。

### 3. `flush`、`commit`、`refresh` 和 `rollback`

[[`flush`、`commit`、`refresh` 和 `rollback`]]

- 一句话解释：`flush` 把当前变更发送到数据库但不结束事务，`commit` 最终持久化，`refresh` 从数据库重读对象，`rollback` 撤销当前未提交事务。
- 在当前项目中的职责：create/update 方法在返回前 `flush`，单对象再 `refresh` 以取得主键、时间戳和数据库更新后的值；批量 Chunk 只 flush，避免逐条 refresh 的额外查询。
- 与其他组件的关系：数据库约束通常在 flush 时触发；调用方捕获 `IntegrityError` 后必须 rollback，Session 才能继续安全使用或关闭。
- 容易混淆的点：flush 成功不等于数据已经永久保存；另一个 Session 通常看不到未提交数据。
- 面试一句话：我用 flush 提前发现外键和唯一约束错误并获得 ID，但保持事务开放，只有完整业务链路成功后才 commit。

### 4. “未找到”与“数据库异常”不是同一种结果

- 一句话解释：合法查询没有匹配记录应返回 `None` 或空列表，连接失败、约束失败等数据库异常则应继续抛出。
- 在当前项目中的职责：`get()` 和 `update_status()` 对不存在 ID 返回 `None`；无效外键、重复名称、连接失败等 `SQLAlchemyError` 不被 Repository 伪装成“没找到”。
- 与其他组件的关系：未来 Service 根据 `None` 形成业务未找到，Day 6 的 API 再映射为 404；系统异常则进入统一错误处理，而不是误报 404。
- 容易混淆的点：捕获所有异常后返回 `None` 会掩盖数据库宕机、SQL 错误和约束失败。
- 面试一句话：空结果是正常查询语义，数据库异常是系统或一致性问题，我让两者沿不同路径返回。

## 四、升级涉及的文件

| 文件 | 操作 | 作用 |
| --- | --- | --- |
| `app/repositories/__init__.py` | 新建 | 统一导出三个 Repository、`DocumentStatus` 和 `ChunkCreate` |
| `app/repositories/knowledge_base_repository.py` | 新建 | 提供知识库 create/get/list_all 数据访问方法 |
| `app/repositories/document_repository.py` | 新建 | 提供文档 create/get/list/update_status 数据访问方法 |
| `app/repositories/chunk_repository.py` | 新建 | 定义 Chunk 写入数据对象并提供批量保存、按文档查询方法 |
| `docs/17天每日学习/Day03.md` | 新建 | 保存今天的可执行升级手册；实际验证记录可选 |

### 今日不做

- 不解析 PDF、不切分文本、不调用 Embedding、不把 `/upload` 改成数据库入库；这些属于 Day 4。
- 不实现 pgvector 相似度查询、知识库/ready 状态过滤或 Top-K；这些属于 Day 5。
- 不增加 FastAPI 路由、依赖注入或 Pydantic API schema；这些属于 Day 6。
- 不提前实现完整异常映射和上传失败状态策略；Day 8 会系统加固。
- 不新建 pytest 测试目录或追求完整自动测试；Day 12 再建立正式回归测试集。
- 不修改 ORM 模型和数据库结构，因此今天不生成新的 Alembic revision。

## 五、按顺序完成项目升级

### 步骤 1：创建 Repository 包（建议 5 分钟）

**目标**

建立与现有 `app/services/` 平级的数据访问包，并提供稳定的公开导入路径。

**修改位置**

- 文件：`app/repositories/__init__.py`
- 定位：`app/repositories/` 当前不存在；先在编辑器中新建目录和文件，或在项目根目录执行目录创建命令。
- 操作：新建完整文件；不要改动 `app/services/`。

```powershell
New-Item -ItemType Directory -Force -Path "app/repositories" | Out-Null
```

**复制下面的完整代码**

```python
from app.repositories.chunk_repository import ChunkCreate, ChunkRepository
from app.repositories.document_repository import (
    DocumentRepository,
    DocumentStatus,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)


__all__ = [
    "ChunkCreate",
    "ChunkRepository",
    "DocumentRepository",
    "DocumentStatus",
    "KnowledgeBaseRepository",
]
```

**这段代码怎样工作**

- 输入：三个具体 Repository 模块中定义的公开类型。
- 输出：后续 Service 可以统一从 `app.repositories` 导入所需对象。
- 调用谁：只做 Python 模块导出，不访问数据库。
- 被谁调用：今天的验证脚本，以及 Day 4 的文档入库 Service。
- 正常路径：`from app.repositories import DocumentRepository` 成功。
- 失败路径：任一具体模块缺失或 import 名称不一致时，导入立即失败，便于在运行数据库操作前定位。

**完成本步骤后的预期状态**

`app/repositories` 成为 Python 包，公开名称集中在 `__all__`，没有创建第二套 Engine、Base 或 Session 工厂。

### 步骤 2：实现 KnowledgeBaseRepository（建议 10 分钟）

**目标**

提供创建、按主键查询和稳定排序列出知识库的最小接口。

**修改位置**

- 文件：`app/repositories/knowledge_base_repository.py`
- 定位：新文件。
- 操作：复制完整内容。

**复制下面的完整代码**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
        description: str | None = None,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            name=name,
            description=description,
        )
        self._session.add(knowledge_base)
        self._session.flush()
        self._session.refresh(knowledge_base)
        return knowledge_base

    def get(self, knowledge_base_id: int) -> KnowledgeBase | None:
        return self._session.get(KnowledgeBase, knowledge_base_id)

    def list_all(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).order_by(KnowledgeBase.id)
        return list(self._session.scalars(statement))
```

**这段代码怎样工作**

- 输入：调用方传入的同步 `Session`、知识库名称和可选描述。
- 输出：已获得数据库主键/时间戳的 `KnowledgeBase`，单个对象或按 ID 排序的列表。
- 调用谁：SQLAlchemy `Session.add()`、`flush()`、`refresh()`、`get()` 和 `scalars()`。
- 被谁调用：后续知识库 Service、Day 4 文档入库前置检查和 Day 6 API。
- 正常路径：create 在当前事务中插入记录，flush 取得 ID，get/list 可在同一 Session 中读到它。
- 失败路径：主键不存在时 get 返回 `None`；重复名称等约束错误在 flush 时抛出 `IntegrityError`，由调用方 rollback。

**完成本步骤后的预期状态**

知识库访问逻辑不再需要散落的 `select(KnowledgeBase)`；方法自身不 commit、rollback 或 close Session。

### 步骤 3：实现 DocumentRepository（建议 10 分钟）

**目标**

提供文档记录创建、查询、按知识库列出和状态更新，并保持数据库四状态契约。

**修改位置**

- 文件：`app/repositories/document_repository.py`
- 定位：新文件。
- 操作：复制完整内容。

**复制下面的完整代码**

```python
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Document


DocumentStatus = Literal[
    "pending",
    "processing",
    "ready",
    "failed",
]


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        knowledge_base_id: int,
        filename: str,
        status: DocumentStatus = "pending",
    ) -> Document:
        document = Document(
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            status=status,
        )
        self._session.add(document)
        self._session.flush()
        self._session.refresh(document)
        return document

    def get(self, document_id: int) -> Document | None:
        return self._session.get(Document, document_id)

    def list_by_knowledge_base(
        self,
        knowledge_base_id: int,
    ) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(Document.id)
        )
        return list(self._session.scalars(statement))

    def update_status(
        self,
        document_id: int,
        status: DocumentStatus,
        failure_reason: str | None = None,
    ) -> Document | None:
        document = self.get(document_id)
        if document is None:
            return None

        document.status = status
        document.failure_reason = failure_reason
        self._session.flush()
        self._session.refresh(document)
        return document
```

**这段代码怎样工作**

- 输入：Session、真实知识库 ID、文件名，以及 ORM/数据库已经约定的四种状态之一。
- 输出：Document 对象、按知识库和 ID 排序的文档列表，或对不存在 ID 返回 `None`。
- 调用谁：`app.orm_models.Document` 和同步 SQLAlchemy Session。
- 被谁调用：Day 4 的入库 Service 会创建 processing 文档、保存 Chunk 后更新为 ready；失败状态的系统化处理属于 Day 8。
- 正常路径：外键有效时创建文档；状态更新触发 UPDATE，refresh 后返回数据库中的最新状态和 `updated_at`。
- 失败路径：不存在文档的 update 返回 `None`；不存在知识库、非法状态等数据库约束错误从 flush 向上抛出。

**完成本步骤后的预期状态**

Document 的最小状态写入和父级范围查询集中到一个类中；没有 HTTP 404、PDF 或 Embedding 逻辑。

### 步骤 4：实现 ChunkRepository（建议 15 分钟）

**目标**

用明确的数据对象接收 Day 4 的切块结果，一次性把同一文档的多个 Chunk 加入当前事务，并按 `chunk_index` 查询。

**修改位置**

- 文件：`app/repositories/chunk_repository.py`
- 定位：新文件。
- 操作：复制完整内容。

**复制下面的完整代码**

```python
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Chunk


@dataclass(frozen=True)
class ChunkCreate:
    page_number: int
    chunk_index: int
    content: str
    embedding: list[float]


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_create(
        self,
        document_id: int,
        chunks: Sequence[ChunkCreate],
    ) -> list[Chunk]:
        chunk_models = [
            Chunk(
                document_id=document_id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
            )
            for chunk in chunks
        ]

        if not chunk_models:
            return []

        self._session.add_all(chunk_models)
        self._session.flush()
        return chunk_models

    def list_by_document(self, document_id: int) -> list[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return list(self._session.scalars(statement))
```

**这段代码怎样工作**

- 输入：真实 Document ID，以及包含页码、文档内顺序、原文和 512 维向量的 `ChunkCreate` 序列。
- 输出：当前事务中的 Chunk ORM 列表，或空输入对应的空列表；查询结果按 `chunk_index` 稳定排序。
- 调用谁：SQLAlchemy `add_all()`、`flush()` 和 `select()`，以及 Day 2 的 `Chunk` ORM 映射。
- 被谁调用：Day 4 文档入库 Service；Day 5 会扩展数据访问层实现向量 Top-K，但今天不做相似度查询。
- 正常路径：全部 Chunk 在同一次 flush 中写入，主键可供调用方读取，最终是否持久化仍由调用方 commit 决定。
- 失败路径：任一页码、顺序、外键或向量维度违反数据库契约，flush 抛出异常，调用方 rollback 后整批未提交数据都不会保留。

**完成本步骤后的预期状态**

Day 4 可以把 `EmbeddingService` 的 `list[list[float]]` 与页码/顺序/文本组合为 `ChunkCreate`，无需直接构造或查询 ORM。

### 步骤 5：静态复核公开接口与事务边界（建议 5 分钟）

**目标**

在连接数据库前确认包能导入、方法名齐全，并且 Repository 内没有偷偷提交、回滚或关闭 Session。

执行目录：项目根目录。

```powershell
python -c "from app.repositories import ChunkCreate, ChunkRepository, DocumentRepository, DocumentStatus, KnowledgeBaseRepository; print('repository imports ok')"

rg -n "class .*Repository|def create|def get|def list_all|def list_by_knowledge_base|def update_status|def bulk_create|def list_by_document" app/repositories

$forbiddenCalls = rg -n "\.commit\(|\.rollback\(|\.close\(|SessionLocal\(" app/repositories
if ($LASTEXITCODE -eq 0) {
    $forbiddenCalls
    throw "Repository 中出现事务所有权或 Session 创建逻辑，请按本日边界移除。"
}
if ($LASTEXITCODE -ne 1) {
    throw "rg 检查执行失败。"
}

Write-Host "Repository 事务边界静态检查通过。"
```

预期：导入命令退出码为 `0` 并输出 `repository imports ok`；方法清单齐全；最后输出事务边界检查通过。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不新建 Alembic revision，也不执行 downgrade。只确认 Day 2 head、数据库连通性和 Repository 导入；`python -m alembic upgrade head` 是把本机学习数据库补到已有 head 的幂等准备命令，不是生成新迁移。

### 1. 检查当前状态

执行目录：项目根目录。目的：确认工作区边界、固定依赖、Compose 服务和已有迁移链；按顺序执行。

```powershell
git status --short
python --version
python -m pip show SQLAlchemy psycopg pgvector alembic
docker compose config --services
python -m alembic heads
```

预期结果：`git status --short` 仍显示用户自己的 `Day02.md` 修改，并显示今天新建的文件；依赖版本与 `requirements.txt` 一致；Compose 包含 `postgres`；唯一 Alembic head 是 `e780fe92751b`。

如果 `pip show` 提示缺包，先确认当前是否使用项目虚拟环境；只有确实缺失时才执行：

```powershell
python -m pip install -r requirements.txt
```

### 2. 准备已有数据库基线

执行目录：项目根目录。目的：启动 PostgreSQL、把数据库升级到已有 head，并确认应用连接；不会改模型或生成 revision。

```powershell
docker compose up -d --wait postgres
python -m alembic upgrade head
python -m alembic current
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

预期结果：postgres 服务为 healthy；current 显示 `e780fe92751b (head)`；连接探针输出 `1`。

### 3. 确认 Repository 没有引入 schema 差异

```powershell
python -m alembic check
```

预期结果：退出码为 `0`，提示没有新的升级操作。若出现候选 schema 变化，先核对是否意外修改了 `app/orm_models.py`；Day 3 不应通过新迁移解决它。

### 4. 回滚与恢复

今天没有数据库结构变更，因此不执行 `alembic downgrade`。第七、八节的验证数据都在显式事务中 rollback，或在异常后由调用方 rollback；不需要删除表、容器或 Volume。

### 预期结果

- 数据库最终仍位于 `e780fe92751b (head)`。
- `knowledge_bases`、`documents`、`chunks` 结构保持 Day 2 状态。
- Repository 模块成功导入，不会仅因导入而创建 Session、执行查询或提交数据。
- 今天不新增迁移文件、不修改 `alembic_version` 的目标 revision。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。今天没有新增 HTTP API，不启动 FastAPI；只需要 PostgreSQL 健康且数据库位于已有 head。

```powershell
docker compose up -d --wait postgres
python -m alembic upgrade head
```

### 执行正常请求或测试

下面脚本创建三个 Repository，并让它们共享一个 Session。它会创建临时知识库、文档和两个 512 维 Chunk，查询并更新状态，然后由调用方 rollback；脚本最后使用新 Session 确认没有测试数据残留。

```powershell
@'
import json

from sqlalchemy import func, select

from app.db import SessionLocal
from app.orm_models import KnowledgeBase
from app.repositories import (
    ChunkCreate,
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)


validation_name = "day03-repository-check"

with SessionLocal() as session:
    knowledge_bases = KnowledgeBaseRepository(session)
    documents = DocumentRepository(session)
    chunks = ChunkRepository(session)

    try:
        knowledge_base = knowledge_bases.create(
            name=validation_name,
            description="temporary Day 3 validation row",
        )
        assert knowledge_base.id is not None
        assert knowledge_bases.get(knowledge_base.id) is knowledge_base
        assert knowledge_base in knowledge_bases.list_all()

        document = documents.create(
            knowledge_base_id=knowledge_base.id,
            filename="day03-check.pdf",
            status="processing",
        )
        assert document.id is not None
        assert documents.get(document.id) is document
        assert documents.list_by_knowledge_base(
            knowledge_base.id
        ) == [document]

        updated_document = documents.update_status(
            document_id=document.id,
            status="ready",
        )
        assert updated_document is not None
        assert updated_document.status == "ready"
        assert updated_document.failure_reason is None

        created_chunks = chunks.bulk_create(
            document_id=document.id,
            chunks=[
                ChunkCreate(
                    page_number=1,
                    chunk_index=0,
                    content="Day 3 first validation chunk",
                    embedding=[0.0] * 512,
                ),
                ChunkCreate(
                    page_number=2,
                    chunk_index=1,
                    content="Day 3 second validation chunk",
                    embedding=[0.0] * 512,
                ),
            ],
        )
        loaded_chunks = chunks.list_by_document(document.id)

        assert len(created_chunks) == 2
        assert [chunk.chunk_index for chunk in loaded_chunks] == [0, 1]
        assert all(chunk.id is not None for chunk in created_chunks)

        print(
            json.dumps(
                {
                    "knowledge_base_id": knowledge_base.id,
                    "document_id": document.id,
                    "document_status": updated_document.status,
                    "chunk_ids": [chunk.id for chunk in loaded_chunks],
                    "chunk_count": len(loaded_chunks),
                },
                ensure_ascii=False,
            )
        )
    finally:
        session.rollback()

with SessionLocal() as verification_session:
    remaining_rows = verification_session.scalar(
        select(func.count())
        .select_from(KnowledgeBase)
        .where(KnowledgeBase.name == validation_name)
    )
    assert remaining_rows == 0
    print(json.dumps({"remaining_rows": remaining_rows}))
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Repository 正常路径验证失败。"
}
```

再从数据库侧确认没有残留测试知识库：

```powershell
$dbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$dbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()

docker compose exec -T postgres psql -U $dbUser -d $dbName -c "SELECT count(*) AS remaining_rows FROM knowledge_bases WHERE name = 'day03-repository-check';"
```

### 预期状态码或输出结构

```json
{
  "knowledge_base_id": "动态正整数",
  "document_id": "动态正整数",
  "document_status": "ready",
  "chunk_ids": ["动态正整数", "动态正整数"],
  "chunk_count": 2
}
```

随后脚本和 psql 都应显示：

```json
{
  "remaining_rows": 0
}
```

Python 和 psql 进程退出码均应为 `0`。实际 ID 由数据库动态生成，不要求固定或记录。

### 为什么它能证明今天已经完成

- 同一个 Session 驱动三个 Repository，证明它们能组成一个业务工作单元。
- create/get/list/update/bulk_create/list_by_document 全部走过真实 PostgreSQL，而不是只验证 import。
- 两个 Chunk 按 `chunk_index` 返回，并成功写入 512 维向量字段。
- Repository 内部 flush 后调用方 rollback，最终两个查询都为 `0`，证明 Repository 没有擅自 commit，也没有污染学习数据库。

## 八、验证失败和边界路径

### 场景：未找到返回 `None`，无效外键抛出数据库异常并由调用方回滚

下面脚本先验证不存在的 KnowledgeBase/Document 不会被伪造成空对象，然后尝试给不存在的 Document 写 Chunk，确认外键异常不会被误报为“未找到”，且 rollback 后无测试数据残留。

```powershell
@'
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.orm_models import Chunk
from app.repositories import (
    ChunkCreate,
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)


missing_id = 2147483647

with SessionLocal() as session:
    knowledge_bases = KnowledgeBaseRepository(session)
    documents = DocumentRepository(session)
    chunks = ChunkRepository(session)

    assert knowledge_bases.get(missing_id) is None
    assert documents.get(missing_id) is None
    assert documents.update_status(missing_id, "failed") is None

    try:
        chunks.bulk_create(
            document_id=missing_id,
            chunks=[
                ChunkCreate(
                    page_number=1,
                    chunk_index=0,
                    content="must not be persisted",
                    embedding=[0.0] * 512,
                )
            ],
        )
    except IntegrityError:
        session.rollback()
        print(
            json.dumps(
                {
                    "missing_resources": "returned_none",
                    "database_error": "IntegrityError",
                    "rolled_back": True,
                }
            )
        )
    else:
        session.rollback()
        raise AssertionError(
            "不存在的 document_id 不应允许写入 Chunk"
        )

with SessionLocal() as verification_session:
    leaked_chunks = verification_session.scalar(
        select(func.count())
        .select_from(Chunk)
        .where(Chunk.document_id == missing_id)
    )
    assert leaked_chunks == 0
    print(json.dumps({"leaked_chunks": leaked_chunks}))
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Repository 失败路径验证失败。"
}
```

### 预期结果

- 进程退出码：`0`，因为脚本明确捕获预期的 `IntegrityError` 并完成断言。
- 未找到结果：KnowledgeBase/Document 的 get 和不存在文档的 update 都返回 `None`。
- 数据库异常：无效 Document 外键在 flush 时触发 `IntegrityError`，而不是返回 `None`。
- 数据库应该保留：Day 2 三张表、现有业务数据和 `e780fe92751b` revision 均不改变。
- 数据库不应该存在：`document_id=2147483647` 的 Chunk，`leaked_chunks` 必须为 `0`。
- 响应不能泄露：真实密码、完整数据库 URL、SQL 参数、异常堆栈或 `.env` 内容；脚本只打印稳定的异常类型摘要。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `ModuleNotFoundError: app.repositories` | 目录或 `__init__.py` 未创建，或命令不在项目根目录运行 | `Get-ChildItem -Path app/repositories -Force` | 按第五节创建四个明确文件，并从项目根目录运行 Python |
| `ImportError: cannot import name ...` | `__init__.py` 导出名称与具体模块不一致 | `Get-Content -Path app/repositories/__init__.py` | 对照第五节统一类名和 import 路径，不改成通配导入 |
| `缺少必需的数据库配置` | 本地 `.env` 不存在或 PostgreSQL 必需变量为空 | `app/config.py`、`.env.example`；不要打印真实 `.env` | 在本机补齐配置后重开 Python 进程，不把真实值写入文档或 Git |
| `OperationalError` / `数据库连接失败` | PostgreSQL 未启动、端口或账号配置不一致 | `docker compose ps postgres`；`python -c "from app.db import check_database_connection; print(check_database_connection())"` | 先让 `postgres` 健康，再核对本地配置；不要删除 Volume |
| `relation "knowledge_bases" does not exist` | 本机数据库没有升级到 Day 2 head | `python -m alembic current`、`python -m alembic heads` | 执行 `python -m alembic upgrade head`，预期到 `e780fe92751b`；不要用 `create_all()` |
| `PendingRollbackError` | flush 触发异常后继续复用 Session，没有先 rollback | 查找调用脚本或未来 Service 的 `except` 分支 | 在捕获数据库异常后由 Session 所有者执行 `session.rollback()`，再结束或继续工作单元 |
| 重复知识库名称触发 `IntegrityError` | 命中 `uq_knowledge_bases_name`，Repository 正常向上抛出 | 数据库约束名和 `KnowledgeBaseRepository.create()` | 调用方 rollback；Day 6 再把重复资源映射成合适 HTTP 错误，不要吞异常返回 `None` |
| 无效状态、页码或 Chunk 顺序在 flush 时报错 | 命中 Day 2 Check/UniqueConstraint | `app/orm_models.py` 与异常中的约束名 | 修正调用数据并 rollback；不要绕过数据库约束 |
| `expected 512 dimensions, not N` | 传入向量长度与 `Vector(512)` 不一致 | `ChunkCreate.embedding` 的构造位置；`app/services/embedding_service.py` | 确认使用当前 512 维模型输出，不在 Repository 中截断或补零真实向量 |
| 正常脚本结束后仍有测试数据 | Repository 内误加 commit，或调用方没有执行 finally rollback | `rg -n "\.commit\(" app/repositories` 和正常路径脚本 | Repository 只 flush；由调用方统一 rollback/commit，并用 psql 再查 `remaining_rows=0` |
| `Day02.md` 被加入暂存区 | 使用了过宽的 add 命令 | `git diff --cached --name-only` | 只执行第十一节的明确路径 `git add -- ...`；停止提交并人工核对暂存边界 |

## 十、检查最终代码差异

执行目录：项目根目录。新文件在暂存前不会完整显示在普通 `git diff` 中，因此同时使用 `git status` 和 `Get-Content` 复核完整内容。

```powershell
git status --short
git diff -- app/repositories/__init__.py app/repositories/knowledge_base_repository.py app/repositories/document_repository.py app/repositories/chunk_repository.py docs/17天每日学习/Day03.md

Get-Content -Path app/repositories/__init__.py
Get-Content -Path app/repositories/knowledge_base_repository.py
Get-Content -Path app/repositories/document_repository.py
Get-Content -Path app/repositories/chunk_repository.py
Get-Content -Path docs/17天每日学习/Day03.md

git diff --check
```

重点检查：

- 三个 Repository 都接收调用方 Session，没有 import 或调用 `SessionLocal`。
- `app/repositories/` 中不存在 `commit()`、`rollback()`、`close()`，事务所有权留给 Service/调用脚本。
- get/update 的未找到路径返回 `None`，数据库异常没有被宽泛 `except Exception` 吞掉。
- `DocumentStatus` 与数据库的四个状态一致，`ChunkCreate` 字段与 ORM 的页码、顺序、原文、Embedding 一致。
- 查询分别按 KnowledgeBase ID、Document ID、`chunk_index` 使用已知访问方式，没有提前加入 Top-K 或向量距离表达式。
- 没有修改 `app/db.py`、`app/orm_models.py`、`app/main.py`、迁移文件、FAISS 或 SQLite 基线。
- `docs/17天每日学习/Day02.md` 的用户修改仍在工作区，但不属于今天的暂存范围。
- diff 中没有 `.env`、密码、API Key、数据库文件、运行缓存或无关文档。

## 十一、Git 提交

核心 Repository 实现完成并检查 Git diff 边界后即可执行；正常与失败路径实际执行、保存或回填结果均为可选。如果选择执行并发现已知失败，应先修复再提交。

```powershell
git add -- app/repositories/__init__.py app/repositories/knowledge_base_repository.py app/repositories/document_repository.py app/repositories/chunk_repository.py docs/17天每日学习/Day03.md

git diff --cached --name-only
git diff --cached -- app/repositories/__init__.py app/repositories/knowledge_base_repository.py app/repositories/document_repository.py app/repositories/chunk_repository.py docs/17天每日学习/Day03.md

git commit -m "feat: add core RAG repositories"
```

预期暂存区只包含上面五个明确文件。`docs/17天每日学习/Day02.md`、`.env`、迁移文件、数据库文件和其他用户修改都不应出现；不要使用 `git add .`。

## 十二、面试高频问题与参考答案

### 问题 1：为什么要引入 Repository，不能让 FastAPI 或 Service 直接操作 SQLAlchemy 吗？

#### 30 秒参考答案

小型 Demo 可以直接查询 ORM，但企业 RAG 后续会反复创建知识库、文档、Chunk，更新状态并按父级查询。如果这些 `select/add/flush` 散落在 API 和 Service，HTTP、业务编排和数据库细节会耦合。当前项目把稳定的数据访问动作放进三个 Repository，Service 只组合业务步骤，API 以后只负责请求校验和错误映射。

#### 继续追问：Repository 是否应该包含 PDF 解析或 Embedding？

不应该。PDF 解析和 Embedding 是业务/外部能力，Repository 只知道 ORM 和 Session。Day 4 的 Service 会先调用 PDF、Chunk、Embedding 服务，再把结构化结果交给 DocumentRepository 和 ChunkRepository 保存。

#### 回答时要引用的项目依据

- `app/repositories/knowledge_base_repository.py` 的 create/get/list_all。
- `app/repositories/document_repository.py` 的 create/update_status。
- `app/repositories/chunk_repository.py` 只接收 `ChunkCreate`，不 import PDF 或 Embedding Service。

### 问题 2：为什么 Repository 只 flush，不自己 commit？

#### 30 秒参考答案

一次文档入库会跨多个 Repository：先创建 Document，再批量保存 Chunk，最后更新 ready。如果 create 自己 commit，后面的 Chunk 失败时已提交的半成品无法和本次事务一起回滚。因此当前 Repository 只 flush，让数据库执行 SQL、分配主键并提前检查约束，最终 commit/rollback 由持有同一 Session 的 Service 决定。

#### 继续追问：flush 后别的请求能看到数据吗？

通常不能。flush 仍处于当前事务，其他 Session 在常见隔离级别下看不到未提交变更；只有 commit 后才成为持久化结果。rollback 会撤销本事务中已经 flush 但尚未提交的写入。

#### 回答时要引用的项目依据

- 三个 Repository 中的 `self._session.flush()`。
- Repository 中没有 commit/rollback/close。
- 第七节在 flush/查询后由调用方 rollback，并验证 `remaining_rows=0`。

### 问题 3：`flush`、`refresh`、`commit` 和 `rollback` 分别做什么？

#### 30 秒参考答案

flush 把 Session 当前变更发给 PostgreSQL，但事务仍开放；refresh 重新读取一条对象，拿到数据库生成的 ID、时间戳或更新值；commit 结束事务并持久化；rollback 撤销未提交事务。当前单对象 create/update 会 flush+refresh，批量 Chunk 只 flush 减少逐条查询，最终提交权留给调用方。

#### 继续追问：为什么批量 Chunk 不逐条 refresh？

Day 4 主要需要确认整批写入和取得 ORM 主键，flush 已足够；对每个 Chunk refresh 会额外产生大量 SELECT。需要数据库生成字段时可以针对实际使用点补充查询，但不应默认制造 N 次往返。

#### 回答时要引用的项目依据

- KnowledgeBase/Document create 的 flush+refresh。
- ChunkRepository.bulk_create 的 add_all+flush。
- `SessionLocal(expire_on_commit=False)` 位于 `app/db.py`。

### 问题 4：为什么查询不到返回 `None`，数据库异常却不统一返回 `None`？

#### 30 秒参考答案

查询一个不存在的主键是正常业务结果，可以由 Service 转成“资源不存在”，API 再映射为 404；数据库断连、外键/唯一约束失败或 SQL 错误则说明系统或数据一致性有问题。如果都返回 None，数据库宕机会被误报成资源不存在。当前 get/update 明确返回可空类型，而 SQLAlchemy 异常继续向上抛出。

#### 继续追问：Repository 是否应该直接抛 HTTPException？

不应该。Repository 不依赖 HTTP，未来也可能被脚本、后台任务或测试调用。业务层可定义领域错误，API 层再把它映射为 HTTP 状态码，这样数据访问层保持可复用。

#### 回答时要引用的项目依据

- `get(...) -> ... | None` 和 `update_status(...) -> Document | None`。
- 第八节无效 ID 返回 None、无效外键触发 IntegrityError 的两条路径。
- Repository 文件没有 FastAPI import。

### 问题 5：一个 Session 为什么要传给多个 Repository？

#### 30 秒参考答案

Session 代表一次工作单元。Day 4 的 Document 创建、Chunk 批量写入和状态更新必须共享同一事务，任何一步失败都能整体 rollback。如果每个 Repository 自己创建 Session，它们会处于不同事务，难以保证原子性，也更容易泄漏连接。

#### 继续追问：Session 能否作为全局单例复用？

不能。Session 保存事务和 ORM 对象状态，不适合跨请求共享。项目全局复用 Engine 和 SessionLocal 工厂，每次请求或业务工作单元创建独立 Session，结束时 commit/rollback 并 close，把连接归还连接池。

#### 回答时要引用的项目依据

- `app/db.py` 的模块级 Engine 和 `SessionLocal` 工厂。
- 三个 Repository 的构造函数都接收同一个 `Session`。
- 第七节一个 `with SessionLocal()` 同时构造三个 Repository。

## 十三、今天的完整数据流

### 正常路径

```text
调用方 / 未来 Service
→ SessionLocal() 创建本次工作单元 Session
→ KnowledgeBaseRepository.create()
→ Session.add + flush + refresh，得到 knowledge_base_id
→ DocumentRepository.create()
→ 外键指向真实知识库，flush + refresh 得到 document_id
→ ChunkRepository.bulk_create()
→ 同一 document_id 下 add_all + flush 多个 Chunk/vector(512)
→ DocumentRepository.update_status(..., "ready")
→ 调用方确认完整链路成功
→ 调用方 commit
→ 最后 close Session，连接归还 Engine 连接池
```

今天的验证脚本为了不污染数据库，把倒数第二步替换为调用方 rollback；Day 4 的真实 Service 才会在完整入库成功后 commit。

### 失败路径

```text
按不存在 ID 查询
→ Repository 执行合法 SELECT/get
→ 没有匹配行
→ 返回 None
→ 未来 Service 转成业务“未找到”

无效外键 / 重复名称 / 非法状态 / 数据库异常
→ Repository 在 flush 或查询时收到 SQLAlchemy 异常
→ 不捕获为 None，不自行 commit
→ 异常交给 Session 所有者
→ 调用方 rollback
→ 当前事务中的 Document/Chunk 等未提交变更全部撤销
→ 最后 close Session
```

## 十四、完成标准

```text
[ ] 能解释 Repository 与 Service 的职责边界，并指出 PDF/Embedding 为什么不进入 Repository
[ ] 能解释 Session 为什么由业务工作单元持有，以及多个 Repository 为什么共享同一个 Session
[ ] 能准确区分 flush、refresh、commit、rollback 的作用
[ ] app/repositories/__init__.py 已统一导出三个 Repository、DocumentStatus 和 ChunkCreate
[ ] KnowledgeBaseRepository 已提供 create、get、list_all，未找到返回 None
[ ] DocumentRepository 已提供 create、get、list_by_knowledge_base、update_status，四状态与 ORM 约束一致
[ ] ChunkRepository 已提供 bulk_create 和按 chunk_index 排序的 list_by_document，并接收 512 维向量数据
[ ] 所有 Repository 都不创建 Session，也不执行 commit、rollback、close 或 HTTP 错误映射
[ ] 已提供真实 PostgreSQL 正常路径验证命令，预期可完成创建/查询/更新/批量写入并由调用方 rollback；实际执行与记录可选
[ ] 已提供未找到与无效外键失败路径命令，预期分别得到 None 与 IntegrityError，且不留下 Chunk；实际执行与记录可选
[ ] 能不看代码复述“调用方 Session → 三个 Repository → SQLAlchemy → PostgreSQL → commit/rollback”的完整数据流
[ ] git diff 和暂存区只包含四个 Repository 文件与 Day03.md，不含 Day02.md 用户修改、秘密、迁移或无关文件
[ ] 核心实现完成并检查差异后，可以执行边界清晰的 Git commit；不要求提交验证输出
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
