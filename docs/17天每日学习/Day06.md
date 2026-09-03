# Day 6：完成知识库、上传和文档列表 API

今天将直接完成创建与查询知识库、向指定知识库上传 PDF、列出文档并查看状态的最小 FastAPI 接口，使 Day 3～5 的数据库能力可以通过 Swagger 和 HTTP 使用，并为面试中的 API 分层、Session 生命周期和错误状态码问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：围绕 `KnowledgeBase → Document` 的创建、上传、列表和状态查询 API  
> 当前真实状态：已完成  
> 对应总体安排：Day 6

## 一、今天完成后的项目变化

### 升级前

```text
外部调用方
→ 只能使用旧 POST /upload
→ 上传结果写入进程内 FAISS，只保留最近一次成功上传
→ 没有创建或查询知识库的 HTTP 入口
→ 没有向指定知识库上传多份 PDF 的 HTTP 入口
→ 没有列出 PostgreSQL Document 及其状态的 HTTP 入口

数据库内部已经具备：
KnowledgeBase / Document / Chunk ORM
→ Repository
→ DocumentIngestionService
→ RetrievalService
```

### 升级后

```text
POST /knowledge-bases
→ Pydantic 校验请求
→ KnowledgeBaseRepository.create()
→ commit
→ 返回固定 KnowledgeBaseResponse

POST /knowledge-bases/{knowledge_base_id}/documents
→ 校验 PDF 文件名
→ 读取上传字节
→ DocumentIngestionService.ingest_pdf()
→ PDF → Chunk → Embedding → PostgreSQL/pgvector
→ 返回 Document、页数、Chunk 数和 ready 状态

GET /knowledge-bases
GET /knowledge-bases/{knowledge_base_id}
GET /knowledge-bases/{knowledge_base_id}/documents
GET /knowledge-bases/{knowledge_base_id}/documents/{document_id}
→ Repository 查询
→ ORM 对象显式转换为 Pydantic 响应
```

旧 `/upload` 和 `/rag/chat` 今天保持不变，避免同时改写旧 FAISS 基线；指定知识库的数据库版问答属于 Day 7。

### 今天在完整项目中的位置

- 所属阶段：核心 MVP。
- 所属链路：文档入库链路的 HTTP 入口。
- 今天的输入：Day 3 Repository、Day 4 `DocumentIngestionService`、数据库 Session、上传的 PDF 字节和 Pydantic 请求。
- 今天的输出：可由 Swagger/HTTP 调用的知识库与文档管理契约，以及 PostgreSQL 中可查询的多文档状态。
- 下一天为什么需要它：Day 7 可以沿用 `/knowledge-bases/{id}` 范围增加问答接口，并复用 Day 5 检索结果形成完整数据库版 RAG。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 5 的核心代码、用户完成标记和匹配提交均存在；最新匹配提交为 `ac47322`（Day 5），生成计划时工作区干净。
- `[当前事实]` `app/db.py` 已有应用级 Engine 和 `SessionLocal`，但尚未提供 FastAPI 可注入的 Session 依赖。
- `[当前事实]` `KnowledgeBaseRepository` 支持 create/get/list；`DocumentRepository` 支持 create/get/list_by_knowledge_base/update_status。
- `[当前事实]` `DocumentIngestionService.ingest_pdf()` 接收 `knowledge_base_id + filename + pdf_bytes`，成功返回 ready Document 摘要，失败时保留安全的 failed 状态。
- `[当前事实]` `app/models.py` 已放置旧聊天、上传和 RAG 的 Pydantic 模型，可继续作为 API 请求/响应模型模块。
- `[当前事实]` `app/main.py` 已有 FastAPI 应用、全局 PDF/Embedding/LLM 实例和旧 FAISS 路由；新路由可以复用现有 `pdf_service` 与 `embedding_service`。
- `[当前事实]` 固定依赖包括 FastAPI 0.141.1、Pydantic 2.13.4、SQLAlchemy 2.0.52、python-multipart 0.0.32 和 Uvicorn 0.52.1。
- `[当前事实]` ORM 已用唯一约束保护知识库名称，并用状态检查约束保护 `pending/processing/ready/failed`。

### 仍然缺少

- `[当前事实]` 没有 `KnowledgeBaseCreateRequest`、`KnowledgeBaseResponse`、`DocumentResponse` 或数据库上传响应模型。
- `[当前事实]` 没有按请求创建并在结束时关闭 SQLAlchemy Session 的 FastAPI 依赖。
- `[当前事实]` `app/main.py` 没有任何 `/knowledge-bases` 路由，也没有调用 `DocumentIngestionService`。
- `[当前事实]` API 层尚未把重复名称、空白名称、不存在知识库、错误扩展名和 PDF 业务错误映射为 409、400、404 等明确状态码。
- `[当前事实]` 没有将 ORM KnowledgeBase/Document 显式映射为稳定响应字段的函数。

### 待实测

- `[待实测]` PostgreSQL 当前 revision 是否为 `e780fe92751b (head)`，以及容器是否健康。
- `[待实测]` Uvicorn 首次导入全局 EmbeddingService 时，BGE 模型是否已缓存；首次下载耗时不计入核心 60 分钟。
- `[待实测]` 两份文本型 PDF 是否能经新 HTTP 入口形成同一知识库下的两条 ready Document 与对应 Chunk。
- `[待实测]` Swagger 是否显示六个新接口的请求体、文件字段、响应模型和状态码。

### 需要保护的用户修改

- 生成计划时 `git status --short` 为空；执行时仍先检查状态，只处理今天的四个明确文件，不覆盖、不恢复、不暂存无关修改。
- `app/main.py` 已有旧聊天、历史、上传和 FAISS RAG 逻辑；按精确定位插入新代码，不能整文件覆盖或删除旧路由。
- 不修改真实 `.env`、Repository、DocumentIngestionService、RetrievalService、ORM、迁移或数据库 Volume。

## 三、今天必须理解的核心知识

### 1. API、Service 和 Repository 的分层边界

- 一句话解释：API 处理 HTTP 契约，Service 编排业务流程，Repository 封装数据库读写。
- 在当前项目中的职责：新上传路由只读取文件、映射异常和组装响应；PDF 解析、切块、Embedding、状态流转仍由 DocumentIngestionService 负责。
- 与其他组件的关系：FastAPI 路由获得请求级 Session，Service 和 Repository 共用它，最终数据由 PostgreSQL 保存。
- 容易混淆的点：API 不应复制 `ingest_pdf()` 内部步骤，也不应直接手写 Chunk SQL；否则脚本、测试和后续任务无法复用同一业务规则。
- 面试一句话：当前路由只负责 HTTP 输入输出与错误映射，文档入库由 Service 编排，数据访问由 Repository 完成。

### 2. Pydantic 模型与 SQLAlchemy ORM 模型必须分离

- 一句话解释：Pydantic 固定外部 JSON 契约，ORM 描述数据库表和关系，两者面对的边界不同。
- 在当前项目中的职责：请求模型限制名称长度，响应模型只公开 ID、名称、文件名、状态和时间等稳定字段，不返回 ORM 内部状态或向量。
- 与其他组件的关系：转换函数把 KnowledgeBase/Document ORM 对象映射为 API Response；数据库向量绝不进入文档列表响应。
- 容易混淆的点：直接返回 ORM 对象会让懒加载关系、内部字段和未来 schema 变化意外影响 API。
- 面试一句话：我显式做 ORM 到 Pydantic 的转换，让数据库结构可以演进，同时保持 HTTP 契约稳定且不泄露 embedding 等内部数据。

### 3. 请求级 Session 和事务所有权

- 一句话解释：每个请求使用独立 Session，请求结束时统一关闭；具体业务层决定何时 commit/rollback。
- 在当前项目中的职责：`get_db_session()` 只负责创建、yield 和关闭；创建知识库路由负责提交；DocumentIngestionService 继续控制自己的 processing/ready/failed 事务。
- 与其他组件的关系：Engine 长期复用连接池，Session 只服务一次请求，Repository 不创建或关闭 Session。
- 容易混淆的点：关闭 Session 不等于关闭全局 Engine；多个并发请求也不能共享一个全局 Session。
- 面试一句话：项目全局复用 Engine，每个 FastAPI 请求注入独立 Session，事务由业务入口控制，请求结束后连接归还连接池。

### 4. HTTP 状态码表达不同失败语义

- 一句话解释：422 表示请求结构校验失败，400 表示结构合法但业务输入非法，404 表示范围资源不存在，409 表示唯一性冲突，500 表示未能安全归类的内部失败。
- 在当前项目中的职责：空字符串由 Pydantic 返回 422，纯空格名称返回 400，重复名称返回 409，不存在知识库返回 404，错误文件返回 400。
- 与其他组件的关系：API 把 Python 的 `ValueError`、`LookupError`、`IntegrityError` 映射为稳定 HTTP 契约，不把数据库堆栈返回客户端。
- 容易混淆的点：不能把所有异常都直接 `detail=str(exc)`；未知数据库或模型异常可能包含内部信息，Day 6 对它们保留通用 500。
- 面试一句话：我按客户端能否修正输入、资源是否存在和是否发生冲突区分状态码，同时让未知内部错误返回通用消息避免泄密。

## 四、升级涉及的文件

| 文件                      | 操作  | 作用                                         |
| ----------------------- | --- | ------------------------------------------ |
| `app/db.py`             | 修改  | 新增请求级 `get_db_session()`，统一 Session 创建与关闭。 |
| `app/models.py`         | 修改  | 新增知识库与文档请求/响应模型，保留旧 API 模型。                |
| `app/main.py`           | 修改  | 注入 Session、显式转换 ORM，并新增六个知识库/文档管理接口。       |
| `docs/17天每日学习/Day06.md` | 新建  | 保存今天可直接执行的升级、验证、排错和面试手册。                   |

### 今日不做

- 不新增前端页面或管理后台。
- 不新增数据库版 `/query`，不构造 Context、不调用 LLM、不实现拒答；这些属于 Day 7。
- 不全面重构旧 `/upload` 与 `/rag/chat`，不删除 FAISS；今天保留技术演进基线。
- 不修改 Repository、DocumentIngestionService、RetrievalService、ORM 或迁移。
- 不一次性解决所有异常组合、并发上传、文件大小限制和崩溃恢复；Day 8 统一加固事务、失败状态和输入边界。

## 五、按顺序完成项目升级

### 步骤 1：新增请求级数据库 Session 依赖（建议 5 分钟）

**目标**

让 FastAPI 每次请求获得独立 Session，并在请求结束时自动关闭，而不是创建全局共享 Session。

**修改位置**

- 文件：`app/db.py`
- 定位：完整文件较短，先保留自己的额外内容，再替换完整文件。
- 操作：在现有 Engine/SessionLocal 基础上增加 `Generator`、`Session` 和 `get_db_session()`。

**复制下面的完整代码**

```python
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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
            "缺少必需的数据库配置: "
            + ", ".join(missing_settings)
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


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def check_database_connection() -> int:
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise RuntimeError(
            "数据库连接失败，请检查 PostgreSQL 服务状态和 "
            "POSTGRES_* 配置。"
        ) from None
```

**这段代码怎样工作**

- 输入：FastAPI 的依赖注入系统进入 `get_db_session()`。
- 输出：yield 一个新的 Session；请求结束后 `with` 自动关闭它并归还连接。
- 调用谁：SessionLocal 使用全局 Engine 和连接池。
- 被谁调用：`app/main.py` 中 `Depends(get_db_session)`。
- 正常路径：路由和 Service 共用一次请求的 Session，提交后响应，请求结束关闭。
- 失败路径：未提交事务在 Session 关闭时不会被保留；显式业务失败仍由路由或 Service rollback。

**完成本步骤后的预期状态**

Engine 仍是应用级对象，原连接探针保持不变，项目新增了可复用的请求级 Session 生命周期入口。

### 步骤 2：增加稳定的知识库与文档 API 模型（建议 10 分钟）

**目标**

固定新接口的请求和响应字段，同时保留所有旧聊天、上传和 RAG 模型。

**修改位置**

- 文件：`app/models.py`
- 定位：从 `from datetime import datetime` 到文件末尾。
- 操作：核对用户额外模型后，用下面内容替换完整文件。

**复制下面的完整代码**

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal[
    "pending",
    "processing",
    "ready",
    "failed",
]


class Message(BaseModel):
    """一条聊天消息的数据结构。"""

    id: int = Field(gt=0)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)
    created_at: datetime


class ChatRequest(BaseModel):
    """客户端发送的聊天请求。"""

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="用户发送的消息",
    )


class ChatResponse(BaseModel):
    """服务器返回的聊天响应。"""

    reply: str


class UploadResponse(BaseModel):
    """旧 FAISS 上传接口的响应。"""

    filename: str
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)


class RAGChatRequest(BaseModel):
    """旧 FAISS RAG 问答请求。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对已上传 PDF 提出的问题",
    )


class RAGSource(BaseModel):
    """一条可供用户核对的旧 RAG 来源。"""

    text: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float


class RAGChatResponse(BaseModel):
    """旧 FAISS RAG 问答响应。"""

    answer: str
    sources: list[RAGSource]


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库的请求。"""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class KnowledgeBaseResponse(BaseModel):
    """对外公开的知识库字段。"""

    id: int = Field(gt=0)
    name: str
    description: str | None
    created_at: datetime


class DocumentResponse(BaseModel):
    """对外公开的文档元数据和处理状态。"""

    id: int = Field(gt=0)
    knowledge_base_id: int = Field(gt=0)
    filename: str
    status: DocumentStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """数据库版 PDF 上传成功后的响应。"""

    document: DocumentResponse
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)
```

**这段代码怎样工作**

- 输入：创建知识库 JSON 请求和内部 ORM 数据。
- 输出：FastAPI/OpenAPI 可见的固定请求、知识库响应、文档响应和上传响应。
- 调用谁：Pydantic 在进入路由前检查类型、名称长度和响应结构。
- 被谁调用：第三步新增的路由和转换函数。
- 正常路径：合法输入进入路由，ORM 数据只映射到声明字段。
- 失败路径：空字符串、超长名称或错误类型在进入路由前得到 422；纯空格由路由清洗后返回 400。

**完成本步骤后的预期状态**

`app/models.py` 同时兼容旧接口和新数据库管理接口，且不公开 `Chunk.embedding`、ORM relationship 或连接信息。

### 步骤 3：扩展 main.py 的导入与 ORM 映射（建议 5 分钟）

**目标**

为新路由准备 FastAPI 依赖、数据库异常、Repository、入库 Service 和稳定响应转换函数。

**修改位置**

- 文件：`app/main.py`
- 定位：从文件第一行 `from fastapi import (` 到 `app = FastAPI(` 前一行。
- 操作：只替换该导入区域；下面的 `app = FastAPI(...)` 和全部旧路由保留。

**复制下面的完整替换代码**

```python
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_messages, init_database, save_message
from app.db import get_db_session
from app.models import (
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    Message,
    RAGChatRequest,
    RAGChatResponse,
    RAGSource,
    UploadResponse,
)
from app.orm_models import (
    Document as DocumentModel,
    KnowledgeBase as KnowledgeBaseModel,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.chunk_service import split_text
from app.services.document_ingestion_service import (
    DocumentIngestionService,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
)


DatabaseSession = Annotated[Session, Depends(get_db_session)]


def to_knowledge_base_response(
    knowledge_base: KnowledgeBaseModel,
) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=knowledge_base.id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        created_at=knowledge_base.created_at,
    )


def to_document_response(
    document: DocumentModel,
) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        filename=document.filename,
        status=document.status,
        failure_reason=document.failure_reason,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
```

**这段代码怎样工作**

- 输入：请求依赖提供的 Session，以及 Repository 返回的 ORM 对象。
- 输出：`DatabaseSession` 类型别名和两个显式响应转换函数。
- 调用谁：FastAPI Depends、SQLAlchemy Session、Pydantic Response。
- 被谁调用：下一步骤的六个管理路由。
- 正常路径：每次请求获得独立 Session，映射函数只复制允许公开的稳定字段。
- 失败路径：响应值不符合 Pydantic 契约时由 FastAPI 暴露为服务端响应校验错误，不静默返回错误结构。

**完成本步骤后的预期状态**

旧服务和路由 import 仍完整存在，新管理接口需要的依赖已就位，没有创建全局 Session。

### 步骤 4：新增六个知识库与文档管理路由（建议 20 分钟）

**目标**

把创建、查询、上传和状态查看串成一个可通过 Swagger 连续执行的 HTTP 闭环。

**修改位置**

- 文件：`app/main.py`
- 定位：搜索旧路由装饰器 `@app.post("/upload", response_model=UploadResponse)`。
- 操作：把下面完整代码块插入该装饰器之前；不要替换或删除旧 `/upload`。

**复制下面的完整代码**

```python
@app.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=201,
)
def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    session: DatabaseSession,
) -> KnowledgeBaseResponse:
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=400,
            detail="知识库名称不能只包含空格",
        )

    description = (
        request.description.strip()
        if request.description is not None
        else None
    )
    if description == "":
        description = None

    try:
        knowledge_base = KnowledgeBaseRepository(session).create(
            name=name,
            description=description,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="知识库名称已存在",
        ) from exc

    return to_knowledge_base_response(knowledge_base)


@app.get(
    "/knowledge-bases",
    response_model=list[KnowledgeBaseResponse],
)
def list_knowledge_bases(
    session: DatabaseSession,
) -> list[KnowledgeBaseResponse]:
    knowledge_bases = KnowledgeBaseRepository(session).list_all()
    return [
        to_knowledge_base_response(knowledge_base)
        for knowledge_base in knowledge_bases
    ]


@app.get(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
def get_knowledge_base(
    knowledge_base_id: int,
    session: DatabaseSession,
) -> KnowledgeBaseResponse:
    knowledge_base = KnowledgeBaseRepository(session).get(
        knowledge_base_id
    )
    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        )
    return to_knowledge_base_response(knowledge_base)


@app.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
async def upload_knowledge_base_document(
    knowledge_base_id: int,
    file: UploadFile,
    session: DatabaseSession,
) -> DocumentUploadResponse:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="只支持上传 PDF 文件",
        )

    pdf_bytes = await file.read()
    service = DocumentIngestionService(
        session=session,
        pdf_service=pdf_service,
        embedding_service=embedding_service,
    )

    try:
        result = service.ingest_pdf(
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            pdf_bytes=pdf_bytes,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="文档处理失败",
        ) from exc

    document = DocumentRepository(session).get(result.document_id)
    if document is None:
        raise HTTPException(
            status_code=500,
            detail="文档处理完成但无法读取结果",
        )

    return DocumentUploadResponse(
        document=to_document_response(document),
        page_count=result.page_count,
        chunk_count=result.chunk_count,
    )


@app.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=list[DocumentResponse],
)
def list_knowledge_base_documents(
    knowledge_base_id: int,
    session: DatabaseSession,
) -> list[DocumentResponse]:
    knowledge_base = KnowledgeBaseRepository(session).get(
        knowledge_base_id
    )
    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        )

    documents = DocumentRepository(
        session
    ).list_by_knowledge_base(knowledge_base.id)
    return [
        to_document_response(document)
        for document in documents
    ]


@app.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_knowledge_base_document(
    knowledge_base_id: int,
    document_id: int,
    session: DatabaseSession,
) -> DocumentResponse:
    document = DocumentRepository(session).get(document_id)
    if (
        document is None
        or document.knowledge_base_id != knowledge_base_id
    ):
        raise HTTPException(
            status_code=404,
            detail="文档不存在",
        )
    return to_document_response(document)
```

**这段代码怎样工作**

- 输入：知识库 JSON、路径 ID、multipart PDF 和请求级 Session。
- 输出：201 创建结果、200 列表/详情，或 400/404/409/422/500 的稳定错误响应。
- 调用谁：知识库路由调用 KnowledgeBaseRepository；文档路由调用 DocumentIngestionService 和 DocumentRepository。
- 被谁调用：Swagger、HTTP 客户端和后续 Day 7 的演示流程。
- 正常路径：同一知识库可连续上传多份 PDF，列表和详情从 PostgreSQL 读取 ready 状态。
- 失败路径：不存在资源返回 404；错误文件返回 400；重复名称回滚并返回 409；未知内部错误不把异常文本返回客户端。
- 隔离边界：文档详情同时比较 `document_id` 与 `knowledge_base_id`，不会通过其他知识库路径暴露文档。

**完成本步骤后的预期状态**

Swagger 中出现六个新接口；旧 `/upload`、`/rag/chat` 仍存在，新接口的文档数据以 PostgreSQL 为准。

### 步骤 5：做静态与路由清单检查（建议 5 分钟）

**目标**

在启动服务前发现语法、导入、路由遗漏或越界修改。

**修改位置**

- 本步骤只检查，发现错误时回到对应代码块修正。
- 执行目录：项目根目录。

```powershell
python -c "import ast, pathlib; files = ('app/db.py', 'app/models.py', 'app/main.py'); [ast.parse(pathlib.Path(path).read_text(encoding='utf-8')) for path in files]; print('Day 6 Python syntax OK')"
rg -n "def get_db_session|DatabaseSession|KnowledgeBaseCreateRequest|DocumentUploadResponse" app/db.py app/models.py app/main.py
rg -n "@app\.(get|post)\(|/knowledge-bases|/upload|/rag/chat" app/main.py
git diff -- app/db.py app/models.py app/main.py
```

预期结果：语法命令退出码为 0；新知识库接口、旧 `/upload` 和旧 `/rag/chat` 都能定位；diff 不包含 Repository、Service、ORM 或迁移。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成新 migration，也不执行 downgrade；现有表、外键、状态约束和 `Vector(512)` 已满足 API 使用。

### 1. 检查当前状态

执行目录：项目根目录。先检查工作区、数据库服务、连接与 revision，不打印真实密码。

```powershell
git status --short
docker compose config --services
docker compose ps
alembic current
python -c "from app.db import check_database_connection; print({'database_probe': check_database_connection()})"
```

预期：服务包含 `postgres`；运行中的数据库应健康；revision 包含 `e780fe92751b (head)`；探针返回 1。

### 2. 执行升级

如果数据库未运行，只启动 PostgreSQL；随后检查代码没有引入 schema 漂移。

```powershell
docker compose up -d --wait postgres
alembic current
alembic check
```

预期：`alembic check` 退出码为 0 并提示没有新的 upgrade operations。若出现结构变化，不要为 Day 6 生成迁移，应先检查是否误改 ORM。

### 3. 回滚并恢复

今天没有 migration 往返。HTTP 正常验证会有意持久化一个测试知识库和两份 ready 文档，作为多文档证据；不要通过删除记录、表或 Volume 来“恢复”。如不希望保留测试数据，改用自己的正式文本 PDF 和知识库名称完成同一流程。

```powershell
alembic current
```

### 预期结果

- 数据库始终位于 `e780fe92751b (head)`。
- 没有新增 migration 文件或 ORM 差异。
- API 启动和验证不要求配置或调用 LLM。
- 日志与响应不包含真实密码、数据库 URL 或 `.env` 内容。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。打开 PowerShell 窗口 A，启动 API；首次加载 BGE 模型可能较慢。看到 Uvicorn 启动信息后保持窗口运行，全部验证结束后按 `Ctrl+C` 停止。

```powershell
docker compose up -d --wait postgres
uvicorn app.main:app --reload
```

可在浏览器打开 `http://127.0.0.1:8000/docs`，确认六个 `/knowledge-bases` 接口可见；也可以在窗口 B 执行下面的完整 HTTP 验证。

### 执行正常请求或测试

下面脚本只使用已固定的 httpx，通过内存构造两份可提取英文文本的单页 PDF，不创建临时文件。它创建唯一名称知识库、上传两份 PDF、列出文档并逐条查询状态。

```powershell
@'
import json
from uuid import uuid4

import httpx


def build_text_pdf(text: str) -> bytes:
    escaped = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    stream = (
        f"BT /F1 14 Tf 72 720 Td ({escaped}) Tj ET"
    ).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        ),
        (
            b"<< /Type /Font /Subtype /Type1 "
            b"/BaseFont /Helvetica >>"
        ),
        (
            f"<< /Length {len(stream)} >>\nstream\n".encode(
                "ascii"
            )
            + stream
            + b"\nendstream"
        ),
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(
        f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    )
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} "
            "/Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


base_url = "http://127.0.0.1:8000"
knowledge_base_name = f"day06_http_{uuid4().hex[:12]}"
documents_to_upload = [
    (
        "employee-leave-policy.pdf",
        "Annual leave requests must be submitted three working days in advance.",
    ),
    (
        "travel-reimbursement-policy.pdf",
        "Travel reimbursement requires an invoice within ten working days.",
    ),
]

with httpx.Client(base_url=base_url, timeout=300.0) as client:
    create_response = client.post(
        "/knowledge-bases",
        json={
            "name": knowledge_base_name,
            "description": "Day 6 multi-document API verification",
        },
    )

    print("\n=== CREATE KNOWLEDGE BASE ===")
    print("status:", create_response.status_code)
    print("headers:", create_response.headers)
    print("body:", create_response.text)

    assert create_response.status_code == 201, (
        f"Create KB failed: "
        f"status={create_response.status_code}, "
        f"body={create_response.text}"
    )

    knowledge_base = create_response.json()

    upload_results = []

    for filename, text in documents_to_upload:
        upload_response = client.post(
            f"/knowledge-bases/{knowledge_base['id']}/documents",
            files={
                "file": (
                    filename,
                    build_text_pdf(text),
                    "application/pdf",
                )
            },
        )

        print(f"\n=== UPLOAD {filename} ===")
        print("status:", upload_response.status_code)
        print("headers:", upload_response.headers)
        print("body:", upload_response.text)

        assert upload_response.status_code == 201, (
            f"Upload failed: "
            f"status={upload_response.status_code}, "
            f"body={upload_response.text}"
        )

        upload_result = upload_response.json()

        assert upload_result["document"]["status"] == "ready"
        assert upload_result["page_count"] == 1
        assert upload_result["chunk_count"] > 0

        upload_results.append(upload_result)

    list_response = client.get(
        f"/knowledge-bases/{knowledge_base['id']}/documents"
    )
    assert list_response.status_code == 200, list_response.text
    listed_documents = list_response.json()
    expected_filenames = {
        filename for filename, _ in documents_to_upload
    }
    matching_documents = [
        document
        for document in listed_documents
        if document["filename"] in expected_filenames
    ]
    assert len(matching_documents) == 2
    assert all(
        document["status"] == "ready"
        for document in matching_documents
    )

    for document in matching_documents:
        detail_response = client.get(
            "/knowledge-bases/"
            f"{knowledge_base['id']}/documents/{document['id']}"
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == document["id"]

    print(
        json.dumps(
            {
                "knowledge_base": knowledge_base,
                "uploads": upload_results,
                "listed_ready_documents": matching_documents,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 6 HTTP 正常路径验证失败。"
}
```

随后用真实 SQLAlchemy 查询确认 HTTP 返回的数据已经持久化到 PostgreSQL，而不是只存在于进程内对象：

```powershell
@'
import json

from sqlalchemy import func, select

from app.db import SessionLocal
from app.orm_models import Chunk, Document, KnowledgeBase


with SessionLocal() as session:
    knowledge_base = session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.name.like("day06_http_%"))
        .order_by(
            KnowledgeBase.created_at.desc(),
            KnowledgeBase.id.desc(),
        )
        .limit(1)
    )
    assert knowledge_base is not None

    documents = list(
        session.scalars(
            select(Document)
            .where(
                Document.knowledge_base_id == knowledge_base.id
            )
            .order_by(Document.id)
        )
    )
    assert len(documents) >= 2

    rows = []
    for document in documents:
        chunk_count = session.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.document_id == document.id)
        )
        rows.append(
            {
                "document_id": document.id,
                "filename": document.filename,
                "status": document.status,
                "chunk_count": chunk_count,
            }
        )

    matching_rows = [
        row
        for row in rows
        if row["filename"]
        in {
            "employee-leave-policy.pdf",
            "travel-reimbursement-policy.pdf",
        }
    ]
    assert len(matching_rows) == 2
    assert all(row["status"] == "ready" for row in matching_rows)
    assert all(row["chunk_count"] > 0 for row in matching_rows)

    print(
        json.dumps(
            {
                "knowledge_base_id": knowledge_base.id,
                "knowledge_base_name": knowledge_base.name,
                "documents": matching_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 6 PostgreSQL 持久化查询失败。"
}
```

### 预期状态码或输出结构

- 创建知识库：HTTP 201。
- 两次上传：各自 HTTP 201，Document 均为 `ready`，页数和 Chunk 数为正数。
- 文档列表与详情：HTTP 200，能找到同一知识库下两份文档。
- 数据库脚本：退出码 0，查询到两条 ready Document 和各自大于 0 的 Chunk 数。
- ID、时间戳和实际 Chunk 数都是动态值。

```json
{
  "knowledge_base": {
    "id": "动态正整数",
    "name": "day06_http_加随机后缀",
    "description": "Day 6 multi-document API verification",
    "created_at": "动态 ISO 时间"
  },
  "uploads": [
    {
      "document": {
        "id": "动态正整数",
        "knowledge_base_id": "与知识库 ID 相同",
        "filename": "employee-leave-policy.pdf",
        "status": "ready",
        "failure_reason": null,
        "created_at": "动态 ISO 时间",
        "updated_at": "动态 ISO 时间"
      },
      "page_count": 1,
      "chunk_count": "动态正整数"
    }
  ]
}
```

### 为什么它能证明今天已经完成

HTTP 脚本从外部执行创建知识库、两次 multipart 上传、列表和详情查询；数据库脚本再绕过 API 直接核对 Document 和 Chunk，证明响应不是内存假象。两份文档属于同一知识库且都为 ready，覆盖了 Day 6 的完整管理闭环，但没有调用 LLM 或提前实现问答。

## 八、验证失败和边界路径

### 场景：重复/非法知识库名称、不存在知识库和错误文件

执行目录：项目根目录，API 保持运行。脚本创建一个边界测试知识库，然后触发四种不同失败，并确认错误 `.txt` 没有留下 Document。

```powershell
@'
import json
from uuid import uuid4

import httpx


base_url = "http://127.0.0.1:8000"
name = f"day06_boundary_{uuid4().hex[:12]}"

with httpx.Client(base_url=base_url, timeout=60.0) as client:
    first_create = client.post(
        "/knowledge-bases",
        json={"name": name, "description": "boundary"},
    )
    assert first_create.status_code == 201, first_create.text
    knowledge_base = first_create.json()

    duplicate = client.post(
        "/knowledge-bases",
        json={"name": name, "description": "duplicate"},
    )
    assert duplicate.status_code == 409, duplicate.text

    empty_name = client.post(
        "/knowledge-bases",
        json={"name": "", "description": None},
    )
    assert empty_name.status_code == 422, empty_name.text

    whitespace_name = client.post(
        "/knowledge-bases",
        json={"name": "   ", "description": None},
    )
    assert whitespace_name.status_code == 400, whitespace_name.text

    existing_ids = [
        item["id"]
        for item in client.get("/knowledge-bases").json()
    ]
    missing_id = max(existing_ids, default=0) + 1000000
    missing_list = client.get(
        f"/knowledge-bases/{missing_id}/documents"
    )
    assert missing_list.status_code == 404, missing_list.text

    wrong_file = client.post(
        f"/knowledge-bases/{knowledge_base['id']}/documents",
        files={
            "file": (
                "not-a-pdf.txt",
                b"plain text is not a PDF",
                "text/plain",
            )
        },
    )
    assert wrong_file.status_code == 400, wrong_file.text

    documents = client.get(
        f"/knowledge-bases/{knowledge_base['id']}/documents"
    )
    assert documents.status_code == 200
    assert documents.json() == []

    print(
        json.dumps(
            {
                "duplicate": {
                    "status": duplicate.status_code,
                    "body": duplicate.json(),
                },
                "empty_name": {
                    "status": empty_name.status_code,
                    "detail_type": type(
                        empty_name.json()["detail"]
                    ).__name__,
                },
                "whitespace_name": {
                    "status": whitespace_name.status_code,
                    "body": whitespace_name.json(),
                },
                "missing_knowledge_base": {
                    "id": missing_id,
                    "status": missing_list.status_code,
                    "body": missing_list.json(),
                },
                "wrong_file": {
                    "status": wrong_file.status_code,
                    "body": wrong_file.json(),
                },
                "stored_documents_after_wrong_file": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 6 HTTP 失败路径验证失败。"
}
```

### 预期结果

- HTTP 状态码或异常：重复名称 409；空字符串名称 422；纯空格名称 400；不存在知识库列表 404；错误扩展名 400。
- 数据库应该保留：第一次创建成功的边界知识库，便于证明 409 来自唯一性冲突而非首次创建失败。
- 数据库不应该存在：该边界知识库下任何 Document；错误扩展名在调用 DocumentIngestionService 之前被拒绝。
- 响应不能泄露：唯一约束 SQL、数据库 URL、密码、堆栈、模型路径、真实环境变量或其他知识库的文档内容。
- 404 文档详情不能区分“文档不存在”和“文档属于另一个知识库”，避免跨知识库枚举。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| 启动时提示缺少 `POSTGRES_*` | `app.db` 创建 Engine 时公开数据库配置不完整 | `rg -n "POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD" app/config.py app/db.py .env.example` | 在本机 `.env` 或进程环境补齐自己的值；不把真实值写进代码、计划或 Git。 |
| `docker compose up --wait postgres` 超时 | Docker Desktop 未运行、端口冲突或健康检查失败 | `docker compose ps`；`docker compose logs postgres --tail 50` | 启动 Docker Desktop，核对 Compose 端口和健康检查；不要删除 Volume。 |
| FastAPI 报 `Invalid args for response field` | `DatabaseSession` 没有使用 `Annotated[Session, Depends(...)]`，或参数注解拼错 | `rg -n "DatabaseSession|get_db_session|Depends" app/main.py app/db.py` | 复制第三步的类型别名，并让所有新路由参数使用 `session: DatabaseSession`。 |
| Swagger 没有新路由 | 路由代码插在 `app` 创建之前、缩进到其他函数内，或 Uvicorn 未重载 | `rg -n "/knowledge-bases" app/main.py` | 确认代码位于模块顶层且 `app = FastAPI(...)` 之后；保存文件并查看窗口 A 的重载日志。 |
| 创建知识库返回 500 而不是重复名称 409 | `IntegrityError` 在 Repository 的 flush 阶段抛出但 try 范围不完整，或没有 rollback | `create_knowledge_base()` 的 create/commit/except | 保证 Repository.create 和 commit 都在同一个 try 内，捕获后先 `session.rollback()` 再抛 409。 |
| 上传有效 PDF 返回“没有提取到文本” | PDF 是扫描件、空白页或内存 PDF 构造被改坏 | `app/services/pdf_service.py` 的 `_extract_text()`；先运行第七节原样脚本 | 使用含可复制文字的 PDF；OCR 不在本轮范围，不能把图片 PDF 伪装成成功。 |
| 上传首次耗时很长 | 全局 EmbeddingService 正在下载或加载 BGE 模型 | 查看 Uvicorn 日志；`rg -n "MODEL_NAME" app/services/embedding_service.py` | 等待首次模型缓存完成；不改成随机向量或不同维度模型来跳过。 |
| 文档上传失败后仍出现 Document | DocumentIngestionService 会先提交 processing，再在解析失败时保留 failed 记录 | 查询文档列表的 `status` 和 `failure_reason` | 对 `.txt` 扩展名应在 Service 前拒绝且不留记录；对损坏的 `.pdf` 保留 failed 是 Day 4 的既定可观察状态，不应伪装为 ready。 |
| 文档详情可从错误知识库路径读到 | 只按 document_id 查询，没有比较 knowledge_base_id | `get_knowledge_base_document()` | 保留 `document is None or document.knowledge_base_id != knowledge_base_id` 的统一 404 条件。 |
| 响应校验报 status 不是允许值 | 数据库存在绕过约束的脏数据，或 ORM/迁移漂移 | `app/models.py` 的 DocumentStatus；ORM 与迁移状态约束 | 先核对迁移和真实数据来源；不要放宽响应为任意字符串来隐藏数据问题。 |
| `alembic check` 提示结构变化 | Day 6 误改 ORM 或 metadata | `git diff -- app/orm_models.py migrations/env.py migrations/versions` | Day 6 不生成迁移；保留用户改动并找出越界来源。 |

## 十、检查最终代码差异

执行目录：项目根目录。Day06.md 是新文件，普通 diff 在暂存前可能不展示其内容，因此同时读取文件并核对状态。

```powershell
git status --short
Get-Content -Path app/db.py
Get-Content -Path app/models.py
Get-Content -Path app/main.py
Get-Content -Path docs/17天每日学习/Day06.md
git diff -- app/db.py app/models.py app/main.py docs/17天每日学习/Day06.md
```

重点检查：

- 只有 `app/db.py`、`app/models.py`、`app/main.py` 和 `docs/17天每日学习/Day06.md` 属于今天范围。
- 旧聊天、历史、`/upload` 和 `/rag/chat` 路由仍完整存在。
- 每个新请求使用 `DatabaseSession`，没有全局共享 Session。
- 创建知识库由路由 commit/rollback；DocumentIngestionService 的事务边界没有被 API 重复实现。
- Response 只包含声明字段，不返回 ORM relationship、Chunk embedding 或内部异常。
- 文档列表按知识库查询，文档详情同时校验 knowledge_base_id 和 document_id。
- 没有 Repository、Service、Retrieval、ORM、迁移、真实 `.env` 或数据库 Volume 差异。
- 所有未运行验证仍只描述预期结果，没有虚构 HTTP、数据库、模型或 Git 成功。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。如果用户选择运行验证并发现已知失败，应先修复再提交。

```powershell
git add app/db.py app/models.py app/main.py docs/17天每日学习/Day06.md
git diff --cached -- app/db.py app/models.py app/main.py docs/17天每日学习/Day06.md
git commit -m "feat: add knowledge base document APIs"
```

不要使用 `git add .`。如果状态中还有其他文件，让它们留在工作区，不加入本次提交。

## 十二、面试高频问题与参考答案

### 问题 1：一次 PDF 上传请求在当前项目中怎样流转？

#### 30 秒参考答案

客户端向 `/knowledge-bases/{id}/documents` 发送 multipart 文件，FastAPI 先取得路径 ID、UploadFile 和请求级 Session，校验扩展名后读取字节。路由把这些参数交给 DocumentIngestionService；Service 检查知识库、创建 processing Document、解析 PDF、切 Chunk、生成 512 维向量、调用 Repository 写 PostgreSQL，成功后置为 ready。API 最后把 ORM Document 显式转换为 Pydantic 响应。

#### 继续追问：为什么不把解析和写库直接放进路由？

解析、切块、Embedding、状态和事务属于可复用业务流程。放在 Service 后，HTTP、脚本、测试或未来后台任务都能调用同一规则；路由只处理协议和异常映射，避免和数据库细节耦合。

#### 回答时要引用的项目依据

- `app/main.py` 的 `upload_knowledge_base_document()`。
- `app/services/document_ingestion_service.py` 的 `ingest_pdf()`。
- `app/repositories/` 的知识库、文档和 Chunk 数据访问接口。

### 问题 2：Pydantic 模型和 SQLAlchemy ORM 模型为什么不能混用？

#### 30 秒参考答案

ORM 模型服务数据库，包含表、外键、关系和向量字段；Pydantic 模型服务外部契约，负责请求校验和响应字段。当前 API 用转换函数只返回知识库和文档的公开元数据，不返回 embedding 或 relationship。这样数据库结构可以独立演进，也避免把内部对象和敏感细节直接暴露给客户端。

#### 继续追问：为什么不用自动 `from_attributes` 直接转换？

自动转换可以使用，但当前字段少，我选择显式函数，让每个公开字段一眼可审计，并避免未来给 ORM 增加字段后被误认为 API 应自动暴露。后续响应模型增多时可以统一为 schema mapper，但边界不变。

#### 回答时要引用的项目依据

- `app/models.py` 的 KnowledgeBaseResponse、DocumentResponse。
- `app/orm_models.py` 的关系和 Vector 字段。
- `app/main.py` 的两个 `to_*_response()` 函数。

### 问题 3：Engine、Session 和一次 FastAPI 请求的生命周期怎样对应？

#### 30 秒参考答案

Engine 在应用模块中长期存在并管理连接池；`get_db_session()` 为每次请求创建独立 Session，Repository 和 Service 共用它，请求结束后关闭并归还连接。创建知识库的事务由路由提交或回滚，文档入库的多阶段事务由 DocumentIngestionService 控制，Repository 不取得事务所有权。

#### 继续追问：为什么不能使用全局 Session？

并发请求共享全局 Session 会混合事务和对象状态，一个请求 rollback 可能影响另一个请求。请求级 Session 把工作单元隔离，而全局 Engine 仍能复用连接池，不会为每次请求重建整个数据库配置。

#### 回答时要引用的项目依据

- `app/db.py` 的 Engine、SessionLocal 和 get_db_session。
- `app/main.py` 的 DatabaseSession。
- Repository 构造函数接收 Session，但不关闭它。

### 问题 4：为什么重复名称是 409，而不存在知识库是 404？

#### 30 秒参考答案

重复名称表示请求格式和目标操作都合法，但与当前唯一资源状态冲突，所以返回 409；不存在的知识库表示路径指定的资源范围不存在，所以返回 404。空字符串在 Pydantic 层返回 422，纯空格是清洗后的业务非法输入返回 400。这样客户端能根据状态码决定修改请求、换资源还是停止重试。

#### 继续追问：怎样避免把数据库细节放进 409 响应？

路由捕获 IntegrityError 后先 rollback，再返回固定的“知识库名称已存在”，不返回原始 SQL、约束堆栈或连接信息。当前创建操作只有名称唯一性冲突，Day 8 会进一步统一未知数据库异常的日志和错误边界。

#### 回答时要引用的项目依据

- `KnowledgeBase` 的唯一约束 `uq_knowledge_bases_name`。
- `create_knowledge_base()` 的 try/except/rollback。
- 第八节对 409、422、400、404 的固定断言。

### 问题 5：为什么今天保留旧 `/upload`，没有直接替换？

#### 30 秒参考答案

Day 6 的唯一目标是开放新数据库架构的管理入口。旧 `/upload` 和 `/rag/chat` 仍代表 FAISS 基线；今天新增带知识库范围的独立路由，可以避免破坏已有演示，同时清楚比较技术演进。Day 7 再把 RetrievalService、Context 和 LLM 接到指定知识库问答，完成新 MVP 后再决定旧入口的迁移策略。

#### 继续追问：两个入口并存会不会造成混淆？

会，所以这是有时间边界的迁移状态。路径语义已经区分：旧 `/upload` 是单文档 FAISS，新入口位于 `/knowledge-bases/{id}/documents` 并持久化 PostgreSQL。README 最终会在 Day 15 根据完成事实说明新旧关系。

#### 回答时要引用的项目依据

- `app/main.py` 中两个不同上传路由。
- Day 4 的 DocumentIngestionService 与旧 FAISSVectorStore。
- 总体安排 Day 7 和 Day 15 的后续边界。

## 十三、今天的完整数据流

### 正常路径

```text
客户端 POST /knowledge-bases
→ Pydantic 校验 JSON
→ 请求级 Session
→ KnowledgeBaseRepository.create()
→ flush / refresh
→ API commit
→ ORM 显式映射为 KnowledgeBaseResponse
→ HTTP 201

客户端 POST /knowledge-bases/{id}/documents + PDF
→ FastAPI 解析路径参数和 multipart UploadFile
→ API 校验 .pdf 并读取 bytes
→ DocumentIngestionService.ingest_pdf()
→ KnowledgeBaseRepository.get()
→ processing Document commit
→ PDFService → split_text → EmbeddingService
→ ChunkRepository.bulk_create()
→ Document status = ready
→ commit
→ DocumentRepository.get()
→ ORM 显式映射为 DocumentUploadResponse
→ HTTP 201

客户端 GET 文档列表/详情
→ 请求级 Session
→ 按 knowledge_base_id 查询并校验范围
→ DocumentResponse[] / DocumentResponse
→ HTTP 200
→ 请求结束关闭 Session
```

### 失败路径

```text
空字符串名称
→ Pydantic 拒绝
→ HTTP 422

纯空格名称
→ 路由 strip 后为空
→ HTTP 400

重复名称
→ Repository flush 触发唯一约束 IntegrityError
→ session.rollback()
→ 固定 HTTP 409，不返回 SQL

不存在 knowledge_base_id
→ Repository.get() 返回 None / Service 抛 LookupError
→ HTTP 404

错误扩展名
→ API 在调用入库 Service 前拒绝
→ HTTP 400
→ 数据库不新增 Document

损坏但扩展名为 .pdf
→ Service 已创建 processing Document
→ PDF 解析抛 ValueError
→ rollback 未完成工作并保存 failed
→ API 返回 HTTP 400
→ failed 文档不能被 Day 5 检索
```

## 十四、完成标准

```text
[ ] 能解释 API、Service、Repository 的职责边界，以及上传路由为什么不复制 PDF/Chunk/Embedding 逻辑
[ ] 能解释 Pydantic 响应与 ORM 模型分离的安全和演进原因
[ ] app/db.py 已提供请求级 get_db_session()，且没有创建全局共享 Session
[ ] app/models.py 已提供知识库创建、知识库响应、文档响应和上传响应模型，同时保留旧 API 模型
[ ] app/main.py 已提供创建/列表/详情知识库、上传/列表/详情文档六个接口，并显式映射 ORM 响应
[ ] 同一知识库可通过 HTTP 上传两份文本 PDF，预期两条 Document 均为 ready 且 Chunk 数大于 0；实际执行与记录可选
[ ] 已提供 SQLAlchemy 数据库查询命令，预期能核对两份 ready 文档和真实 Chunk；实际执行与记录可选
[ ] 已提供重复名称、非法名称、不存在知识库和错误文件边界命令，预期分别得到 409/422/400/404 且不泄密；实际执行与记录可选
[ ] 文档详情同时校验 knowledge_base_id 和 document_id，错误知识库路径不能读取其他知识库文档
[ ] 没有修改 Repository、Service、Retrieval、ORM、迁移、FAISS 或真实 .env，没有提前实现 Day 7/Day 8
[ ] 能不看代码复述 HTTP → Pydantic → API → Service → Repository → PostgreSQL → Response 的完整数据流
[ ] git diff 与暂存区只包含今天四个明确文件，不含秘密和无关修改，核心实现完成后可执行边界清晰的 commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
