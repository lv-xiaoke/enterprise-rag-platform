# Day 4：将 PDF 处理结果持久化到 PostgreSQL + pgvector

今天将直接完成最小数据库版文档入库 Service，使 PDF 的文档元数据、分页 Chunk 与 512 维向量能够持久化到 PostgreSQL + pgvector，并为面试中的 Service 编排、状态流转和批量入库问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：输入知识库 ID、PDF 文件名和字节，输出可查询 Document 与 Chunk 记录的 `DocumentIngestionService`  
> 当前真实状态：已完成
> 对应总体安排：Day 4

## 一、今天完成后的项目变化

### 升级前

```text
POST /upload
→ PDFService 按页提取文本
→ split_text 切分 Chunk
→ EmbeddingService 生成向量
→ FAISSVectorStore 写入进程内存
→ 全局 rag_service 只保留最近一次上传
→ PostgreSQL 中虽已有 KnowledgeBase / Document / Chunk 表与 Repository，但没有入库业务编排
```

### 升级后

```text
调用方提供 knowledge_base_id + filename + pdf_bytes
→ DocumentIngestionService 检查知识库
→ 创建并提交 processing Document
→ PDFService 按页提取文本
→ split_text 保留页码并生成文档内连续 chunk_index
→ EmbeddingService 一次批量生成向量
→ 校验向量数量和每个向量的 512 维契约
→ ChunkRepository 在同一事务中批量写入 Chunk
→ DocumentRepository 更新为 ready
→ commit 后 Document / Chunk / 页码 / 文本 / Vector 持久化到 PostgreSQL

任一步骤失败
→ rollback 当前 Chunk/ready 事务
→ 把已存在的 processing Document 更新为 failed
→ 不产生 ready 半成品
```

现有 `/upload` 在今天仍保持 FAISS 行为；把新 Service 接入知识库/文档 HTTP API 属于 Day 6，不能在 Day 4 提前修改 `app/main.py`。

### 今天在完整项目中的位置

- 所属阶段：核心 MVP。
- 所属链路：文档入库链路。
- 今天的输入：已存在的 KnowledgeBase、PDF 文件名与 PDF 字节、Day 3 Repository、当前 PDF/Chunk/Embedding 服务。
- 今天的输出：状态为 `ready` 或 `failed` 的 Document，以及成功时持久化的分页 Chunk 和 512 维向量。
- 下一天为什么需要它：Day 5 必须先有真实 pgvector Chunk 数据，才能实现按知识库和文档状态过滤的 Top-K 检索。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1、Day 2、Day 3 分别有匹配提交 `ac14dd5`、`e156828`、`9cc6d60`，对应计划也有用户完成标记。
- `[当前事实]` `app/db.py` 提供一个应用级 Engine、`SessionLocal` 和连接探针；Repository 不创建或关闭 Session。
- `[当前事实]` `app/orm_models.py` 已定义 `KnowledgeBase 1:N Document 1:N Chunk`，Document 支持 `pending/processing/ready/failed`，Chunk 使用 `Vector(512)`。
- `[当前事实]` `app/repositories/` 已提供知识库查询、文档创建与状态更新、Chunk 批量写入和按文档查询，并且只 `flush`、不 `commit`。
- `[当前事实]` `PDFService.extract_pages_from_bytes()` 能拒绝空字节、损坏 PDF 和无文本 PDF；`split_text()` 能按字符切块；`EmbeddingService.embed_documents()` 返回批量向量。
- `[当前事实]` Docker 使用 Python 3.11，固定依赖包括 SQLAlchemy 2.0.52、psycopg 3.3.4、pgvector 0.5.0、pypdf 6.15.0 和 sentence-transformers 5.7.0。
- `[当前事实]` 当前 Alembic head 为业务表迁移 `e780fe92751b`；Day 4 不需要改变数据库结构。

### 仍然缺少

- `[当前事实]` 仓库中没有 `DocumentIngestionService` 或 `ingest_pdf()`，现有 Service 尚未组合三个 Repository。
- `[当前事实]` 没有代码把 PDF 页码、Chunk 顺序、原文和 Embedding 组装为 `ChunkCreate` 并提交到 PostgreSQL。
- `[当前事实]` 现有 `/upload` 仍把权威向量数据写进全局 FAISS 对象，重启后丢失；今天只建立新数据库入库入口，不改 HTTP 路由。
- `[当前事实]` 没有无文本 PDF 对新数据库状态流转的验证；新架构 pytest 测试集属于 Day 12。

### 待实测

- `[待实测]` 当前模型首次下载完成后，真实输出是否全部为 512 维。
- `[待实测]` 一份文本型 PDF 是否能产生多个按页可追溯、`chunk_index` 连续的数据库 Chunk。
- `[待实测]` 无文本 PDF 是否留下一个 `failed` Document 且 Chunk 数为 0。
- `[待实测]` 本机 PostgreSQL 是否位于 `e780fe92751b (head)` 并能接受 pgvector 数据。

### 需要保护的用户修改

- 生成本计划时 `git status --short` 为空；执行时仍只按今日文件清单操作，不处理、恢复或暂存后来出现的其他修改。
- 不修改 `app/main.py`、现有 FAISS Service、ORM、Repository、迁移、旧 Day 文件或任何真实 `.env`。

## 三、今天必须理解的核心知识

### 1. Service 是业务编排者，Repository 是数据访问者

- 一句话解释：Service 决定“先检查什么、再处理什么、何时提交或回滚”，Repository 只封装稳定的 ORM 读写动作。
- 在当前项目中的职责：`DocumentIngestionService` 组合 PDF 解析、切块、Embedding 和三个 Repository；Repository 不接触 PDF、模型或 HTTP。
- 与其他组件的关系：调用方管理 Session 生命周期，Service 控制本次业务事务，Repository 使用同一个 Session 执行 `get/add/flush/refresh`。
- 容易混淆的点：Repository 的 `flush()` 会把 SQL 发给数据库，但不等于持久化完成；最终仍由 Service `commit()`。
- 面试一句话：当前入库 Service 把跨多个 Repository 的业务步骤组成一个工作单元，Repository 保持无事务所有权，因此 Chunk 写入失败时可以由 Service 统一回滚。

### 2. `processing → ready/failed` 是可观察的处理状态

- 一句话解释：Document 状态告诉调用方文档还在处理、已经可检索，还是处理失败。
- 在当前项目中的职责：先提交 `processing`，成功时把 Chunk 与 `ready` 一起提交；失败时回滚未完成 Chunk，再提交安全的 `failed` 原因。
- 与其他组件的关系：Day 5 检索必须只选择 `ready` 文档；`processing` 与 `failed` 永远不能被当作可用知识。
- 容易混淆的点：今天实现的是最小可用状态流；数据库断连、失败状态二次写入失败、所有非法输入和 API 错误映射将在 Day 8 统一加固。
- 面试一句话：`ready` 是检索资格而不是普通展示字段，只有 Chunk 和向量完整提交后才能设置。

### 3. 页码与 `chunk_index` 分别解决来源追溯和稳定顺序

- 一句话解释：页码回答“来自原 PDF 哪一页”，`chunk_index` 回答“这是整份文档中的第几个 Chunk”。
- 在当前项目中的职责：每页分别切块，页码从 1 开始；`chunk_index` 跨页连续从 0 开始。
- 与其他组件的关系：Day 5 检索返回 Chunk，Day 7 需要把文档名、页码、原文和分数映射成来源。
- 容易混淆的点：页码可能重复，因为同一页可产生多个 Chunk；`chunk_index` 在同一 Document 下必须唯一。
- 面试一句话：入库时保存来源元数据，才能让后续检索结果可解释、可核对，而不是只返回一段脱离文档位置的文本。

### 4. 批量 Embedding 与批量持久化必须先验证数量和维度

- 一句话解释：第 N 段文本必须严格对应第 N 个向量，且每个向量都必须满足数据库的 512 维契约。
- 在当前项目中的职责：先构造有稳定顺序的 `_PreparedChunk` 列表，再一次调用 `embed_documents()`，校验后才构造 `ChunkCreate`。
- 与其他组件的关系：`EmbeddingService` 负责生成向量，Service 负责检查跨组件契约，`ChunkRepository.bulk_create()` 负责一次 flush 整批 ORM 对象。
- 容易混淆的点：`zip()` 会静默截断较长一侧，因此不能只 zip 而不先检查数量；数据库报维度错误时也不能截断或补零伪造向量。
- 面试一句话：批量处理减少模型调用和数据库往返，但必须在写库前验证文本、向量数量和固定维度，防止错位来源进入知识库。

## 四、升级涉及的文件

| 文件 | 操作 | 作用 |
| --- | --- | --- |
| `app/services/document_ingestion_service.py` | 新建 | 编排知识库检查、processing 状态、PDF 解析、分页切块、批量 Embedding、Chunk 批量写入及 ready/failed 状态。 |
| `docs/17天每日学习/Day04.md` | 新建 | 保存今天可直接执行的升级、验证、排错和面试手册。 |

现有 `app/services/__init__.py` 保持为空：今天直接从具体模块导入 Service，不为了形式增加额外改动。

### 今日不做

- 不实现 pgvector 相似度检索、Top-K、知识库范围过滤或 ready 状态过滤；这些属于 Day 5。
- 不新增知识库/文档 HTTP API，也不替换当前 `/upload`；这些属于 Day 6。
- 不修改数据库表或生成 Alembic revision；Day 2 的字段已经满足今天需要。
- 不覆盖非 PDF、空文件、数据库中途断连、错误响应映射等全部组合；Day 8 负责完整事务与错误治理。
- 不删除 FAISS 代码，不修改数据库 Volume，不启动 LLM 问答。

## 五、按顺序完成项目升级

### 步骤 1：确认前置接口没有漂移（建议 5 分钟）

**目标**

在复制 Service 前确认当前模型、Repository 和处理函数仍与本计划一致，防止把代码接到已经改名的接口上。

**修改位置**

- 本步骤不修改文件。
- 在项目根目录执行只读定位命令。

```powershell
rg -n "class KnowledgeBase|class Document|class Chunk|Vector\(512\)" app/orm_models.py
rg -n "class .*Repository|def create|def get|def update_status|def bulk_create|def list_by_document" app/repositories
rg -n "def extract_pages_from_bytes|def split_text|def embed_documents" app/services
rg -n "\.commit\(|\.rollback\(|\.close\(" app/repositories
```

预期：前三组能定位到当前接口；最后一条没有输出，证明 Repository 没有取得事务所有权。如果最后一条出现内容，先保留用户修改并核对事务边界，不要直接覆盖。

### 步骤 2：新建数据库版文档入库 Service（建议 30 分钟）

**目标**

建立今天唯一核心产物：使用同一 Session 编排文档状态、PDF 处理、向量生成和 PostgreSQL 写入，并给 Day 5 留下真实 Chunk 向量。

**修改位置**

- 文件：`app/services/document_ingestion_service.py`
- 操作：新建文件。
- 调用边界：今天由验证脚本直接调用；Day 6 再由 HTTP API 调用。

**复制下面的完整代码**

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories import (
    ChunkCreate,
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService


DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 40
EMBEDDING_DIMENSION = 512


@dataclass(frozen=True)
class DocumentIngestionResult:
    document_id: int
    knowledge_base_id: int
    filename: str
    page_count: int
    chunk_count: int
    status: str


@dataclass(frozen=True)
class _PreparedChunk:
    page_number: int
    chunk_index: int
    content: str


class DocumentIngestionService:
    """把 PDF 处理结果持久化为 Document 和 Chunk 记录。"""

    def __init__(
        self,
        session: Session,
        pdf_service: PDFService,
        embedding_service: EmbeddingService,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

        self._session = session
        self._pdf_service = pdf_service
        self._embedding_service = embedding_service
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._knowledge_bases = KnowledgeBaseRepository(session)
        self._documents = DocumentRepository(session)
        self._chunks = ChunkRepository(session)

    def ingest_pdf(
        self,
        knowledge_base_id: int,
        filename: str,
        pdf_bytes: bytes,
    ) -> DocumentIngestionResult:
        cleaned_filename = filename.strip()
        if not cleaned_filename:
            raise ValueError("filename 不能为空")

        knowledge_base = self._knowledge_bases.get(knowledge_base_id)
        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        document = self._documents.create(
            knowledge_base_id=knowledge_base.id,
            filename=cleaned_filename,
            status="processing",
        )
        self._session.commit()
        document_id = document.id

        try:
            pages = self._pdf_service.extract_pages_from_bytes(
                pdf_bytes
            )
            prepared_chunks = self._prepare_chunks(pages)

            if not prepared_chunks:
                raise ValueError("PDF 没有生成任何 Chunk")

            embeddings = self._embedding_service.embed_documents(
                [chunk.content for chunk in prepared_chunks]
            )
            self._validate_embeddings(
                embeddings=embeddings,
                expected_count=len(prepared_chunks),
            )

            chunk_inputs = [
                ChunkCreate(
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=embedding,
                )
                for chunk, embedding in zip(
                    prepared_chunks,
                    embeddings,
                )
            ]
            stored_chunks = self._chunks.bulk_create(
                document_id=document_id,
                chunks=chunk_inputs,
            )

            ready_document = self._documents.update_status(
                document_id=document_id,
                status="ready",
            )
            if ready_document is None:
                raise RuntimeError("Document 状态更新失败")

            self._session.commit()

            return DocumentIngestionResult(
                document_id=document_id,
                knowledge_base_id=knowledge_base.id,
                filename=cleaned_filename,
                page_count=len(pages),
                chunk_count=len(stored_chunks),
                status="ready",
            )
        except Exception as exc:
            self._session.rollback()
            try:
                self._mark_document_failed(
                    document_id=document_id,
                    error=exc,
                )
            except Exception as status_error:
                self._session.rollback()
                raise RuntimeError(
                    "文档处理失败，且无法保存 failed 状态"
                ) from status_error
            raise

    def _prepare_chunks(
        self,
        pages: list[str],
    ) -> list[_PreparedChunk]:
        prepared_chunks: list[_PreparedChunk] = []

        for page_number, page_text in enumerate(pages, start=1):
            page_chunks = split_text(
                page_text,
                chunk_size=self._chunk_size,
                overlap=self._chunk_overlap,
            )
            for content in page_chunks:
                prepared_chunks.append(
                    _PreparedChunk(
                        page_number=page_number,
                        chunk_index=len(prepared_chunks),
                        content=content,
                    )
                )

        return prepared_chunks

    @staticmethod
    def _validate_embeddings(
        embeddings: list[list[float]],
        expected_count: int,
    ) -> None:
        if len(embeddings) != expected_count:
            raise RuntimeError(
                "Chunk 与 Embedding 数量不一致: "
                f"chunks={expected_count}, embeddings={len(embeddings)}"
            )

        for index, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSION:
                raise RuntimeError(
                    f"第 {index} 个 Embedding 维度应为 "
                    f"{EMBEDDING_DIMENSION}，实际为 {len(embedding)}"
                )

    def _mark_document_failed(
        self,
        document_id: int,
        error: Exception,
    ) -> None:
        failed_document = self._documents.update_status(
            document_id=document_id,
            status="failed",
            failure_reason=self._safe_failure_reason(error),
        )
        if failed_document is None:
            raise RuntimeError("找不到需要标记失败的 Document")
        self._session.commit()

    @staticmethod
    def _safe_failure_reason(error: Exception) -> str:
        if isinstance(error, ValueError):
            message = str(error).strip()
            if message:
                return message[:500]
        return "文档处理失败"
```

**这段代码怎样工作**

| 函数                        | 核心作用                                    |
| ------------------------- | --------------------------------------- |
| `__init__()`              | 准备 Session、PDF、Embedding、Repository 等依赖 |
| `ingest_pdf()`            | **总流程：PDF → Chunk → Embedding → 数据库**   |
| `_prepare_chunks()`       | 把每一页文本切成带页码和编号的 Chunk                   |
| `_validate_embeddings()`  | 检查 Embedding 数量和 512 维是否正确              |
| `_mark_document_failed()` | 处理失败时把 Document 改成 `failed`             |
| `_safe_failure_reason()`  | 生成安全、简短的失败原因                            |
| `DocumentIngestionResult` | 表示最终成功的入库结果                             |

- 输入：已存在的 `knowledge_base_id`、非空 `filename` 和上传得到的 `pdf_bytes`。
- 输出：成功时返回只包含稳定摘要字段的 `DocumentIngestionResult`；真实数据以 PostgreSQL 中的 ORM 记录为准。
- 调用谁：`KnowledgeBaseRepository`、`DocumentRepository`、`ChunkRepository`、`PDFService`、`split_text()` 和 `EmbeddingService`。
- 被谁调用：今天的 Service 级验证脚本；Day 6 的文档上传 API。
- 正常路径：先让 `processing` 可观察，再把整批 Chunk 与 `ready` 放在同一事务中提交。
- 失败路径：PDF、切块、Embedding、向量契约或 Chunk flush 任一步骤失败时，先 rollback 未完成事务，再把 Document 标记为 `failed`；只有 `ValueError` 的安全业务消息会入库，未知异常不保存 SQL、连接串或堆栈。
- Session 边界：Service 对本次业务执行 `commit/rollback`，但不 `close` 注入的 Session；调用方通过 `with SessionLocal()` 或未来 FastAPI 依赖关闭它。

**完成本步骤后的预期状态**

- 新模块可以导入，且没有导入 FastAPI、FAISS 或 LLM。
- Service 复用现有 Repository，不直接 `session.add()` 或编写 SQL。
- 成功时 Chunk 和 `ready` 一起提交；无文本 PDF 不会成为 `ready`。
- 不新增迁移，不修改当前 `/upload`。

### 步骤 3：静态检查范围和跨层契约（建议 5 分钟）

**目标**

在启动数据库或下载模型前，先发现导入、常量、越界实现和事务位置错误。

**修改位置**

- 不再修改其他代码；检查刚新建的 Service。

```powershell
python -m compileall app/services/document_ingestion_service.py
python -c "from app.services.document_ingestion_service import DocumentIngestionResult, DocumentIngestionService; print('document ingestion imports ok')"
rg -n "DEFAULT_CHUNK_SIZE|DEFAULT_CHUNK_OVERLAP|EMBEDDING_DIMENSION|processing|ready|failed|commit\(|rollback\(" app/services/document_ingestion_service.py
rg -n "FastAPI|HTTPException|FAISS|LLMService|distance|cosine_distance|l2_distance" app/services/document_ingestion_service.py
```

预期：编译和导入退出码为 `0`；第三条能定位 `200/40/512` 和状态/事务；最后一条没有输出，证明没有提前接 API、FAISS、LLM 或 Day 5 检索。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成新 Alembic revision，也不执行 downgrade；只把学习数据库准备到 Day 2 已有 head，并确认新 Service 没有产生 schema 差异。

### 1. 检查当前状态

执行目录：项目根目录。目的：保护工作区、确认 Python 3.11 环境、固定依赖、Compose 服务和迁移 head；按顺序执行。

```powershell
git status --short
python --version
python -m pip show SQLAlchemy psycopg pgvector alembic pypdf sentence-transformers
docker compose config --services
python -m alembic heads
```

预期：Python 与 Dockerfile 的 3.11 基线一致；依赖版本与 `requirements.txt` 一致；Compose 只有当前 `postgres` 服务；唯一 head 是 `e780fe92751b`。如果依赖缺失，先确认已激活项目虚拟环境；只有确实缺失时才执行：

```powershell
python -m pip install -r requirements.txt
```

首次下载 `BAAI/bge-small-zh-v1.5` 的外部耗时不计入 60 分钟核心时间。

### 2. 执行升级

执行目录：项目根目录。目的：启动已有 pgvector PostgreSQL、幂等升级到当前 head、确认连接和 metadata 没有漂移。

```powershell
docker compose up -d --wait postgres
python -m alembic upgrade head
python -m alembic current
python -c "from app.db import check_database_connection; print(check_database_connection())"
python -m alembic check
```

预期：postgres 为 healthy；current 显示 `e780fe92751b (head)`；连接探针输出 `1`；`alembic check` 退出码为 `0` 并提示没有新的升级操作。

### 3. 回滚并恢复

今天没有 schema 变化，因此不执行 Alembic downgrade。Service 自身的失败路径会 rollback 未完成的 Chunk/ready 事务，再单独提交 `failed` 状态；第八节会验证这一行为，不需要删除表、容器或 Volume。

### 预期结果

- 数据库最终仍位于 `e780fe92751b (head)`。
- `knowledge_bases`、`documents`、`chunks` 的表结构和约束保持 Day 2 状态。
- 新 Service 导入时不会建立 Session、下载模型、访问数据库或改变 schema。
- 只有实际构造 `EmbeddingService` 并执行入库验证时才可能首次下载模型。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。今天没有新增 HTTP API，不启动 FastAPI 或 LLM；只准备 PostgreSQL 和已有迁移。

```powershell
docker compose up -d --wait postgres
python -m alembic upgrade head
```

### 执行正常请求或测试

下面命令在内存中生成一页可提取英文文本的最小 PDF，不写临时文件；随后创建唯一命名的知识库，调用真实 BGE 模型入库，并通过 Repository 重新查询 PostgreSQL。数据库 ID、Chunk 数量和模型加载耗时都是动态值。

```powershell
@'
import json
from uuid import uuid4

from app.db import SessionLocal
from app.repositories import (
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.services.document_ingestion_service import (
    DocumentIngestionService,
)
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService


def build_text_pdf() -> bytes:
    text = (
        "Enterprise leave policy requires manager approval and records "
        "the request date duration reason and handover plan. "
    ) * 12
    content = (
        f"BT /F1 12 Tf 72 720 Td ({text.strip()}) Tj ET"
    ).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"
        ),
        (
            b"<< /Length "
            + str(len(content)).encode("ascii")
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


with SessionLocal() as session:
    knowledge_base = KnowledgeBaseRepository(session).create(
        name=f"day04_normal_{uuid4().hex[:12]}",
        description="Day 4 normal ingestion verification",
    )
    session.commit()

    service = DocumentIngestionService(
        session=session,
        pdf_service=PDFService(),
        embedding_service=EmbeddingService(),
    )
    result = service.ingest_pdf(
        knowledge_base_id=knowledge_base.id,
        filename="day04-smoke.pdf",
        pdf_bytes=build_text_pdf(),
    )

    stored_document = DocumentRepository(session).get(
        result.document_id
    )
    stored_chunks = ChunkRepository(session).list_by_document(
        result.document_id
    )

    assert stored_document is not None
    assert stored_document.status == "ready"
    assert stored_document.failure_reason is None
    assert len(stored_chunks) == result.chunk_count
    assert len(stored_chunks) > 1
    assert [chunk.chunk_index for chunk in stored_chunks] == list(
        range(len(stored_chunks))
    )
    assert {chunk.page_number for chunk in stored_chunks} == {1}
    assert all(len(chunk.embedding) == 512 for chunk in stored_chunks)

    print(
        json.dumps(
            {
                "knowledge_base_id": result.knowledge_base_id,
                "document_id": result.document_id,
                "filename": result.filename,
                "status": stored_document.status,
                "page_count": result.page_count,
                "chunk_count": len(stored_chunks),
                "page_numbers": sorted(
                    {chunk.page_number for chunk in stored_chunks}
                ),
                "embedding_dimensions": sorted(
                    {len(chunk.embedding) for chunk in stored_chunks}
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 4 正常路径验证失败。"
}
```

### 预期状态码或输出结构

今天是 Service/数据库验证，没有 HTTP 状态码；Python 进程预期退出码为 `0`，并输出下列稳定结构：

```json
{
  "knowledge_base_id": "数据库动态整数",
  "document_id": "数据库动态整数",
  "filename": "day04-smoke.pdf",
  "status": "ready",
  "page_count": 1,
  "chunk_count": "大于 1 的动态整数",
  "page_numbers": [1],
  "embedding_dimensions": [512]
}
```

### 为什么它能证明今天已经完成

- 脚本不是检查 Python 内存对象，而是 Service `commit()` 后通过 Repository 再次查询 PostgreSQL。
- `ready` 证明状态流完成；多个连续 `chunk_index` 证明按文档切块顺序被保留。
- `page_numbers=[1]` 证明来源页码进入数据库；`embedding_dimensions=[512]` 证明 pgvector 字段收到真实模型向量。
- 测试数据有唯一知识库名称并保留在学习数据库中，便于 Day 5 直接获得真实向量；实际 ID 和数量不需要手工写回本计划。

## 八、验证失败和边界路径

### 场景：无文本 PDF 不能成为 ready 文档

执行目录：项目根目录。下面脚本在内存中生成一页空白 PDF，创建独立知识库并调用同一 Service；它要求 PDF 解析抛出明确错误，随后查询数据库确认 Document 为 `failed` 且没有 Chunk。

```powershell
@'
import json
from io import BytesIO
from uuid import uuid4

from pypdf import PdfWriter

from app.db import SessionLocal
from app.repositories import (
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.services.document_ingestion_service import (
    DocumentIngestionService,
)
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService


def build_blank_pdf() -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    return buffer.getvalue()


with SessionLocal() as session:
    knowledge_base = KnowledgeBaseRepository(session).create(
        name=f"day04_blank_{uuid4().hex[:12]}",
        description="Day 4 blank PDF boundary verification",
    )
    session.commit()

    service = DocumentIngestionService(
        session=session,
        pdf_service=PDFService(),
        embedding_service=EmbeddingService(),
    )

    try:
        service.ingest_pdf(
            knowledge_base_id=knowledge_base.id,
            filename="day04-blank.pdf",
            pdf_bytes=build_blank_pdf(),
        )
    except ValueError as exc:
        assert "没有提取到文本" in str(exc)
        error_message = str(exc)
    else:
        raise AssertionError("空白 PDF 不应入库成功")

    documents = DocumentRepository(
        session
    ).list_by_knowledge_base(knowledge_base.id)
    assert len(documents) == 1

    failed_document = documents[0]
    stored_chunks = ChunkRepository(session).list_by_document(
        failed_document.id
    )

    assert failed_document.status == "failed"
    assert failed_document.failure_reason == error_message
    assert stored_chunks == []

    print(
        json.dumps(
            {
                "knowledge_base_id": knowledge_base.id,
                "document_id": failed_document.id,
                "status": failed_document.status,
                "failure_reason": failed_document.failure_reason,
                "chunk_count": len(stored_chunks),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 4 无文本 PDF 边界验证失败。"
}
```

### 预期结果

- HTTP 状态码或异常：今天未接 HTTP；调用方收到 `ValueError`，消息包含“没有提取到文本”。
- 数据库应该保留：一个动态 ID 的 Document，`status=failed`，`failure_reason` 为安全的 PDF 业务错误。
- 数据库不应该存在：该 Document 下任何 Chunk；`chunk_count` 必须为 `0`。
- 响应不能泄露：数据库密码、连接 URL、SQL、Python 堆栈、模型缓存路径或真实环境变量。
- `processing` 先提交、失败后再写 `failed` 是今天的最小状态方案；数据库中途断连和 failed 二次写入失败的统一治理留到 Day 8。

## 九、常见错误与解决办法

| 错误现象                                   | 最可能原因                                              | 检查命令或位置                                                                                                                         | 解决方法                                                       |                                                                                                                |                                               |
| -------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 导入 Service 时提示缺少 `POSTGRES_*`          | `app.db` 创建 Engine 时发现必需配置为空，或没有在项目根目录运行           | `python -c "from app.db import build_database_url; print(build_database_url().render_as_string(hide_password=True))"`；只确认脱敏 URL | 在本机 `.env` 或进程环境中补齐自己的数据库配置；不要把真实值写进计划、终端截图或 Git。          |                                                                                                                |                                               |
| `docker compose up --wait postgres` 超时 | Docker Desktop 未运行、5432 映射端口冲突或 PostgreSQL 健康检查失败  | `docker compose ps` 和 `docker compose logs postgres --tail 50`                                                                  | 启动 Docker Desktop；核对公开 Compose 端口和容器日志，不删除 Volume。         |                                                                                                                |                                               |
| 首次构造 `EmbeddingService` 很慢或模型下载失败      | `BAAI/bge-small-zh-v1.5` 尚未缓存，或当前网络无法访问模型源         | `python -c "from app.services.embedding_service import MODEL_NAME; print(MODEL_NAME)"`                                          | 保持模型名不变，在网络可用时重试；不要为了跳过下载改成随机向量并声称通过。                      |                                                                                                                |                                               |
| PostgreSQL 报 `expected 512 dimensions` | 模型输出维度与 `Vector(512)` 不一致，或绕过 Service 直接构造错误向量     | `rg -n "MODEL_NAME                                                                                                              | EMBEDDING_DIMENSION                                        | Vector\(512\)" app/services/embedding_service.py app/services/document_ingestion_service.py app/orm_models.py` | 使用当前固定 BGE 模型；保留 Service 数量/维度校验，不截断、不补零真实向量。 |
| 文本 PDF 得到“没有提取到文本”                     | PDF 是扫描件、文字层损坏或内容只有图片                              | 使用 `PDFService.extract_pages_from_bytes()` 单独定位；核对 PDF 是否能复制文本                                                                  | 换用文本型 PDF；OCR 明确不在本轮 17 天范围内。                              |                                                                                                                |                                               |
| 异常后出现 `PendingRollbackError`           | 某个 flush/commit 失败后继续复用 Session，缺少 rollback        | `app/services/document_ingestion_service.py` 的 `except` 分支                                                                      | 确保先 `session.rollback()` 再更新 failed；不要把异常吞掉后继续在失败事务上查询。    |                                                                                                                |                                               |
| 失败文档仍是 `processing`                    | failed 状态的第二次数据库提交也失败，或 Document 在首次 commit 前就创建失败 | Service 的 `_mark_document_failed()` 与 PostgreSQL 日志                                                                             | 先恢复数据库并确认 Document 是否存在；这是 Day 8 要统一处理的可靠性边界，今天不要伪造 ready。 |                                                                                                                |                                               |
| 调用现有 `/upload` 后 PostgreSQL 没有新 Chunk  | `/upload` 当前仍走 FAISS，是今天刻意保留的旧入口                   | `rg -n "FAISSVectorStore                                                                                                        | @app.post\(\"/upload\"" app/main.py`                       | 今天用第七节直接调用新 Service；Day 6 再把数据库入库接到新知识库/文档 API。                                                                |                                               |
| `alembic check` 提示新迁移操作                | 意外修改了 ORM 或 metadata 注册，而 Day 4 本不需要 schema 变化     | `git diff -- app/orm_models.py migrations/env.py migrations/versions`                                                           | 保留并核对用户修改；不要为 Day 4 自动生成迁移来掩盖无关 schema 漂移。                 |                                                                                                                |                                               |

## 十、检查最终代码差异

执行目录：项目根目录。新文件在暂存前不会出现在普通 `git diff` 内容中，因此先检查状态和完整文件，再只查看今日路径。

```powershell
git status --short
Get-Content -LiteralPath app/services/document_ingestion_service.py
git diff -- app/services/document_ingestion_service.py docs/17天每日学习/Day04.md
```

重点检查：

- 只有 `app/services/document_ingestion_service.py` 与 `docs/17天每日学习/Day04.md` 属于今日范围。
- 没有修改 `app/main.py`、ORM、Repository、迁移、FAISS、真实 `.env` 或用户无关文件。
- Service 使用注入的同一个 Session；Repository 仍然没有 `commit/rollback/close`。
- `chunk_index` 跨页连续、页码从 1 开始、向量数量先检查、维度固定 512。
- 只有 Chunk 与 `ready` 完整成功后才提交；失败路径先 rollback 再标记 `failed`。
- 未运行的命令仍只描述为预期结果，没有伪造模型下载、数据库记录或测试通过。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。如果实际执行验证并发现已知失败，应先修复再提交。

```powershell
git add app/services/document_ingestion_service.py docs/17天每日学习/Day04.md
git diff --cached -- app/services/document_ingestion_service.py docs/17天每日学习/Day04.md
git commit -m "feat: persist PDF chunks with pgvector"
```

不要使用 `git add .`。若 `git status --short` 还有其他文件，只保留在工作区，不加入这次提交。

## 十二、面试高频问题与参考答案

### 问题 1：为什么文档入库要放在 Service，而不是写进 Repository 或 FastAPI 路由？

#### 30 秒参考答案

当前入库包含知识库检查、Document 状态流转、PDF 解析、分页切块、批量 Embedding、Chunk 写入和事务控制，这是业务编排，不是单一数据访问动作。项目让三个 Repository 只负责 ORM 的 get/create/update/bulk_create，`DocumentIngestionService` 组合它们，未来 FastAPI 只负责请求读取和异常到 HTTP 的映射。这样同一套入库逻辑也能被脚本、测试或后台任务复用。

#### 继续追问：Service 为什么不关闭 Session？

Session 生命周期由调用方或未来 FastAPI 依赖管理，Service 只控制当前业务的 commit/rollback。这样调用方能确保 `with SessionLocal()` 退出时统一 close，同时避免 Service 关闭一个调用方还需要使用的 Session。

#### 回答时要引用的项目依据

- `app/services/document_ingestion_service.py` 组合处理服务与 Repository，不导入 FastAPI。
- `app/repositories/*.py` 只使用注入的 Session 和 `flush/refresh`。
- `app/db.py` 提供全局 Engine 与 Session 工厂。

### 问题 2：为什么先提交 processing，再把 Chunk 和 ready 放在另一个事务中？

#### 30 秒参考答案

Day 4 先实现最小可观察状态：Document 的 processing 先持久化，PDF 或 Embedding 失败后才能回滚未完成 Chunk，并把同一 Document 记录为 failed。成功路径则把全部 Chunk 与 ready 放在同一事务中提交，避免出现 ready 但 Chunk 不完整。这个方案清楚展示状态流，完整的数据库故障与 failed 二次写入失败治理会在 Day 8 加固。

#### 继续追问：这是不是一个完全原子的事务？

不是。processing 已经先提交，目的是保留可观察的任务记录；后续处理是第二个事务。如果进程在两次提交之间崩溃，可能留下 processing，这正是可靠性阶段需要处理的恢复边界。今天不把它夸大为完整事务方案。

#### 回答时要引用的项目依据

- `ingest_pdf()` 创建 processing 后第一次 `commit()`。
- Chunk `bulk_create()`、`update_status(..., "ready")` 后第二次 `commit()`。
- `except` 分支先 rollback，再调用 `_mark_document_failed()`。

### 问题 3：为什么页码和 `chunk_index` 都要保存？

#### 30 秒参考答案

页码用于把检索结果追溯到原 PDF，`chunk_index` 用于在一份文档内保持稳定顺序。一个页面可能切出多个 Chunk，所以页码不能替代顺序；同一 Document 下 `chunk_index` 从 0 连续且受唯一约束保护，后续回答可以同时展示文档、页码和原文证据。

#### 继续追问：为什么不等检索时再推断页码？

切块后文本可能失去页面边界，而且仅凭内容很难可靠反推出来源。入库时 PDFService 正好保有页序，因此此时保存成本最低、证据最准确。

#### 回答时要引用的项目依据

- `_prepare_chunks()` 对页面 `enumerate(..., start=1)`。
- `chunk_index=len(prepared_chunks)` 形成跨页连续顺序。
- `app/orm_models.py` 的页码检查约束和 `(document_id, chunk_index)` 唯一约束。

### 问题 4：批量 Embedding 和批量写库怎样避免文本与向量错位？

#### 30 秒参考答案

Service 先按固定顺序构造 `_PreparedChunk`，再把同一顺序的 content 列表一次交给 `embed_documents()`。写库前先检查向量数量等于 Chunk 数量，并逐个检查 512 维，然后才按相同顺序组合 `ChunkCreate`。这样避免 `zip()` 静默截断，也避免错误维度直到数据库 flush 才被动发现。

#### 继续追问：为什么不逐个 Chunk 调模型和 commit？

逐个调用模型与数据库会增加大量往返，也更容易留下部分结果。当前实现批量生成向量、`add_all+flush` 整批 Chunk，并与 ready 一起 commit；出错时可以整体 rollback 当前批次。

#### 回答时要引用的项目依据

- `EmbeddingService.embed_documents()` 的批量接口。
- `_validate_embeddings()` 的数量与 512 维检查。
- `ChunkRepository.bulk_create()` 的 `add_all()` 与 `flush()`。

### 问题 5：为什么 Day 4 不直接替换现有 `/upload` 和 FAISS？

#### 30 秒参考答案

17 天计划把能力按依赖拆开：Day 4 只证明数据库入库 Service 能产生真实 Document、Chunk 和向量；Day 5 再实现 pgvector 检索；Day 6 才建立知识库和文档 API。如果今天直接替换 `/upload`，会同时引入 API 契约、检索兼容和错误映射，扩大故障面，也会让唯一核心产物失焦。

#### 继续追问：今天怎样证明新链路可用？

通过 Service 级脚本创建知识库并传入内存 PDF，随后用 Repository 从 PostgreSQL 重新查询 ready Document、Chunk 数、页码和 512 维向量。这已经验证入库闭环，不需要提前开放 HTTP。

#### 回答时要引用的项目依据

- `app/main.py` 当前 `/upload` 仍使用 `FAISSVectorStore`。
- `app/services/document_ingestion_service.py` 是今天独立建立的数据库入库入口。
- 第七、八节的真实 PostgreSQL 查询脚本。

## 十三、今天的完整数据流

### 正常路径

```text
调用方创建一次 Session
→ 创建 DocumentIngestionService，并注入 PDFService / EmbeddingService
→ KnowledgeBaseRepository.get(knowledge_base_id)
→ DocumentRepository.create(status="processing")
→ commit，使 processing 可观察
→ PDFService.extract_pages_from_bytes(pdf_bytes)
→ 每页 split_text(chunk_size=200, overlap=40)
→ 生成 page_number + 连续 chunk_index + content
→ EmbeddingService.embed_documents(contents)
→ 校验向量数量和每个向量 512 维
→ ChunkRepository.bulk_create(document_id, ChunkCreate[])
→ DocumentRepository.update_status(status="ready")
→ commit Chunk 与 ready
→ Repository 重新查询 PostgreSQL
→ 返回 ready Document、分页 Chunk、原文与 pgvector 向量
```

### 失败路径

```text
调用方创建一次 Session
→ 知识库存在
→ 创建并提交 processing Document
→ PDFService 收到无文本 PDF
→ 抛出 ValueError
→ Service rollback 当前未完成事务
→ DocumentRepository.update_status(status="failed", safe reason)
→ commit failed
→ 原异常继续交给调用方
→ 数据库保留 failed Document
→ 该 Document 下 Chunk 数为 0，绝不能成为 ready
```

## 十四、完成标准

```text
[ ] 能解释 Service 与 Repository 的职责边界，以及为什么三个 Repository 共享同一个 Session
[ ] 能解释 processing 先提交、Chunk 与 ready 一起提交的最小方案及其 Day 8 待加固边界
[ ] 已新建 app/services/document_ingestion_service.py，且完整编排知识库检查、PDF 解析、分页切块、Embedding 与 Repository
[ ] 每个成功 Chunk 保存从 1 开始的真实页码、文档内连续 chunk_index、非空原文和 512 维向量
[ ] 成功路径只在 Chunk 批量 flush 与 ready 状态都完成后 commit
[ ] 已提供真实 PostgreSQL 正常路径命令，预期可查询 ready Document、多个 Chunk、页码和 512 维；实际执行与记录可选
[ ] 已提供无文本 PDF 失败路径命令，预期得到 failed Document 且 Chunk 数为 0；实际执行与记录可选
[ ] 没有修改 app/main.py、ORM、Repository、迁移或 FAISS，也没有提前实现 Day 5、Day 6 或 Day 8
[ ] 能不看代码复述 PDF → processing Document → 分页 Chunk → Embedding → Repository → PostgreSQL → ready/failed 的完整数据流
[ ] git diff 与暂存区只包含 app/services/document_ingestion_service.py 和 docs/17天每日学习/Day04.md，不含秘密和无关修改
[ ] 核心实现完成并检查差异后可执行边界清晰的 Git commit，不要求提交验证输出
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：已完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
