# Day 8：完善事务、失败状态和输入校验

今天将直接补齐数据库版文档入库与问答链路的事务兜底、失败状态、输入边界和安全错误映射，使项目在非法输入与处理中断时保持数据一致，并为面试中的事务设计、异常分层和失败可观测性问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一套覆盖上传事务、failed 状态、`question`/`top_k` 边界和安全错误响应的统一失败处理方案  
> 当前真实状态：进行中  
> 对应总体安排：Day 8

## 一、今天完成后的项目变化

### 升级前

```text
合法 PDF
→ 创建 processing Document 并提交
→ 解析、切块、Embedding、批量写 Chunk
→ 成功后提交 ready

处理中失败
→ 已能 rollback Chunk
→ 已尝试另起事务保存 failed
→ 但输入错误与系统错误仍共用 ValueError/RuntimeError
→ API 仍可能把非预期 ValueError 原文返回给客户端

数据库异常
→ 各接口自行决定是否 rollback
→ 未捕获的 SQLAlchemyError 没有统一、安全的 HTTP 语义

问答参数
→ 空白问题由 Service 才识别
→ top_k 当前允许 1～20，与 Day 8 规定的 1～10 不一致
```

### 升级后

```text
HTTP/Pydantic 输入边界
→ question 先去除首尾空白
→ 空问题、top_k=0、top_k>10 在进入业务前返回 422

文档入库边界
→ 文件名、扩展名、空文件先返回安全的 400
→ 无文本/损坏 PDF 创建可观察的 failed Document
→ Chunk 写入与 ready 状态处于同一事务
→ 任一步失败先 rollback，保证没有部分 Chunk
→ rollback 后另起短事务持久化 failed 和安全原因

系统异常边界
→ 文档输入错误与处理错误使用不同异常类型
→ Embedding/数据库内部异常不直接返回客户端
→ Session 依赖在异常退出时统一 rollback
→ 未单独处理的 SQLAlchemyError 统一返回安全的 503

检索安全边界
→ Service 再次校验 question 与 top_k=1～10
→ Query Embedding 内部异常转换为安全 RuntimeError
→ SQL 查询继续只返回 ready 文档
```

### 今天在完整项目中的位置

- 所属阶段：可靠性与数据。
- 所属链路：同时加固“PDF 入库”和“指定知识库问答”两条链路的失败处理。
- 今天的输入：Day 7 已完成的数据库版 RAG MVP、`processing/ready/failed` 状态、请求级 Session、pgvector 检索。
- 今天的输出：输入错误、处理错误和数据库错误边界清楚；上传失败不留下可检索半成品。
- 下一天为什么需要它：Day 9 会反复上传演示 PDF；只有失败行为稳定，演示数据和后续评测才不会被半成品污染。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `docs/17天每日学习/Day01.md`～`Day07.md` 均有用户完成标记，Git reflog 中存在匹配的 Day 1～Day 7 提交；当前 HEAD 对应 `4e321bb`（Day7）。
- `[当前事实]` 生成本计划前 `git status --short` 无输出，工作区干净。
- `[当前事实]` `app/services/document_ingestion_service.py` 已先提交 `processing` Document，再在同一后续事务中写 Chunk 并更新 `ready`；异常时先 `rollback()`，再提交 `failed` 状态。
- `[当前事实]` `app/services/pdf_service.py` 已拒绝空字节、损坏 PDF 和没有可提取文本的 PDF，并使用固定的中文错误信息。
- `[当前事实]` `app/main.py` 已按扩展名拒绝非 PDF，已把不存在知识库映射为 404，把已知文档输入错误映射为 400。
- `[当前事实]` `app/services/database_rag_service.py` 和 `app/services/retrieval_service.py` 已对纯空白问题做 Service 层防御性校验。
- `[当前事实]` `app/repositories/chunk_repository.py` 的 SQL 已同时过滤指定知识库和 `Document.status == "ready"`，因此 failed/processing 文档不会参与检索。
- `[当前事实]` ORM 与迁移已有 `failure_reason`、文档状态检查约束、外键、Chunk 唯一约束和 `vector(512)`；今天不需要修改表结构。

### 仍然缺少

- `[当前事实]` `KnowledgeBaseQueryRequest.top_k` 和 `RetrievalService.MAX_TOP_K` 当前上限都是 20，与总体安排要求的 `top_k > 10` 非法不一致。
- `[当前事实]` Pydantic 只用 `min_length=1`，字符串 `"   "` 能通过请求模型，必须到 Service 才返回 400，尚未形成明确的请求模型边界。
- `[当前事实]` 上传端点捕获所有 `ValueError` 后原样返回 `str(exc)`；如果 Embedding 或其他内部组件抛出 ValueError，存在暴露内部实现信息的风险。
- `[当前事实]` 文档入库还没有“可公开的输入错误”和“不可公开的处理错误”两个明确异常类型。
- `[当前事实]` `get_db_session()` 只负责 yield/close，没有在请求异常退出时显式 rollback；未单独捕获的 SQLAlchemyError 也没有统一的安全 503 响应。
- `[当前事实]` 当前没有 Day 8 专用 pytest；这是 Day 12 的任务，今天使用 HTTP + 真实数据库查询 + 故障注入脚本完成可选验证，不提前建设测试框架。

### 待实测

- `[待实测]` 合法文本型 PDF 在加固后仍应返回 201，并产生一个 ready Document 和至少一个 Chunk。
- `[待实测]` 非 PDF、空文件、无文本 PDF、不存在知识库、空白问题、`top_k=0` 和 `top_k=11` 应分别得到明确的 400/404/422。
- `[待实测]` 模拟“已经 flush 一个 Chunk 后写入失败”时，该 Chunk 应被 rollback，Document 应保留为 failed。
- `[待实测]` 所有错误响应都不应出现连接 URL、密码、SQL、SQLAlchemy/psycopg 堆栈或 Python traceback。

### 需要保护的用户修改

- 生成本计划前工作区干净；执行时仍只按今天的五个代码文件和本计划文件操作。如果开始执行前 `git status --short` 出现其他修改，不恢复、不覆盖，也不放入 Day 8 的 `git add`。

## 三、今天必须理解的核心知识

### 1. rollback 与 failed 状态为什么需要两个事务阶段

- 一句话解释：同一个失败事务必须先 rollback 才能继续使用 Session，而希望保留的 failed 状态必须在 rollback 之后由一个新的短事务提交。
- 在当前项目中的职责：`processing` Document 先独立提交；Chunk + ready 是一个原子事务；失败时它们全部回滚，然后 failed 状态单独提交。
- 与其他组件的关系：Service 拥有业务事务，Repository 只做 `add/flush/refresh`，不能擅自 commit；Session 依赖负责异常逃出端点后的最后 rollback 兜底。
- 容易混淆的点：如果把 failed 更新放在即将 rollback 的事务里，failed 也会被回滚；如果每写一个 Chunk 就 commit，则无法撤销已经提交的半成品。
- 面试一句话：当前项目用“processing 记录事务 + Chunk/ready 原子事务 + rollback 后 failed 事务”换取失败可观测性，同时保证失败文档没有可检索 Chunk。

### 2. 业务输入错误与系统处理错误

- 一句话解释：输入错误是客户端可以修正的 400/422，系统错误是客户端不能靠改请求解决的 500/502/503。
- 在当前项目中的职责：`DocumentInputError` 只承载经过确认可以公开的 PDF 输入提示；`DocumentProcessingError` 屏蔽 Embedding、SQL 和内部异常细节。
- 与其他组件的关系：PDFService 产生稳定的输入错误，DocumentIngestionService 完成分类，FastAPI 只负责映射状态码和公开文案。
- 容易混淆的点：不能因为某个底层库使用 ValueError，就直接把它当成客户端输入错误并回显原文。
- 面试一句话：我在 Service 层把内部异常收敛为领域异常，在 API 层只返回稳定、可公开的错误契约，原始异常只通过异常链保留给服务端排查。

### 3. Pydantic 校验与 Service 防御性校验

- 一句话解释：Pydantic 保护 HTTP 边界，Service 校验保护脚本、任务和未来其他调用方，两层作用不同。
- 在当前项目中的职责：请求模型把空白问题和 `top_k` 越界挡在端点之前；RetrievalService 仍保留相同规则，避免绕过 HTTP 后产生无界查询。
- 与其他组件的关系：请求模型返回 422；Service 的 ValueError 由 API 映射为 400；Repository 最终只接收已校验的 Top-K。
- 容易混淆的点：有了 Pydantic 仍不能删除 Service 校验，因为 Repository/Service 将来可能被评测脚本或后台任务直接调用。
- 面试一句话：边界校验负责快速反馈，业务层校验负责维持不变量，两层重复的是规则而不是职责。

### 4. ready 状态过滤是最后一道数据安全边界

- 一句话解释：事务防止产生半成品，状态过滤防止任何残留的 processing/failed 文档进入检索，两者共同保证失败安全。
- 在当前项目中的职责：`ChunkRepository.search_similar()` 在 SQL 中过滤 ready，而不是检索后再由 Python 丢弃。
- 与其他组件的关系：DocumentIngestionService 负责状态变化，ChunkRepository 负责在数据库查询阶段执行状态边界。
- 容易混淆的点：failed Document 可以作为失败审计记录保留，但它的 Chunk 数应为 0，而且无论如何都不能出现在检索结果里。
- 面试一句话：我同时使用事务原子性和 SQL 层 ready 过滤，避免异常上传污染 RAG 上下文。

## 四、升级涉及的文件

| 文件                                           | 操作  | 作用                                              |
| -------------------------------------------- | --- | ----------------------------------------------- |
| `app/db.py`                                  | 修改  | 请求异常退出时统一 rollback，Session 关闭仍由上下文管理器负责         |
| `app/models.py`                              | 修改  | 去除问题首尾空白，拒绝纯空白问题，并把 Top-K 上限固定为 10              |
| `app/services/retrieval_service.py`          | 修改  | 保持 Service 层 1～10 防御校验，并屏蔽 Query Embedding 内部异常 |
| `app/services/document_ingestion_service.py` | 修改  | 区分输入错误与处理错误，保留现有事务骨架并收紧 failed 原因               |
| `app/main.py`                                | 修改  | 映射新的领域异常，增加全局 SQLAlchemy 安全 503 响应              |
| `docs/17天每日学习/Day08.md`                      | 已生成 | 保存今天可直接参照执行的升级手册                                |

### 今日不做

- 不修改 ORM 或 Alembic 迁移；今天没有数据库结构变化。
- 不删除 failed Document；它是可观察的失败记录，且 ready 过滤已经阻止它参与检索。
- 不引入 Celery、后台 Worker、重试队列或补偿任务，这些超出 17 天最小范围。
- 不新增 pytest 依赖和测试目录；关键自动化测试属于 Day 12。
- 不制作正式企业制度 PDF；固定演示数据属于 Day 9。
- 不修改旧 `/upload` 与 `/rag/chat` FAISS 基线；今天只加固新的 `/knowledge-bases/...` 数据库链路。

## 五、按顺序完成项目升级

### 步骤 1：给请求级 Session 增加 rollback 兜底（建议 5 分钟）

**目标**

任何未被业务层消化的请求异常离开端点时，都先回滚当前 Session，再由 `with SessionLocal()` 关闭连接；业务 Service 仍负责自己的 commit 和 failed 状态事务。

**修改位置**

- 文件：`app/db.py`
- 定位：搜索 `def get_db_session()`。
- 操作：完整替换现有 `get_db_session()` 函数，不改 Engine、SessionLocal 和连接探针。

**复制下面的完整代码**

```python
def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
```

**这段代码怎样工作**

- 输入：FastAPI 为一次请求创建的 SQLAlchemy Session。
- 输出：向端点 yield 同一个 Session；请求结束后自动关闭。
- 调用谁：`Session.rollback()` 和 Session 上下文管理器。
- 被谁调用：所有使用 `DatabaseSession = Annotated[Session, Depends(get_db_session)]` 的新数据库接口。
- 正常路径：端点或 Service 显式 commit，依赖正常结束并关闭 Session。
- 失败路径：异常逃出端点时执行 rollback 后重新抛出，避免连接以失败事务状态回到连接池。

**完成本步骤后的预期状态**

Repository 仍不 commit；DocumentIngestionService 仍拥有入库业务事务；依赖只承担请求级最后兜底，事务所有权没有被混淆。

### 步骤 2：把问答输入边界固定为“非空问题 + Top-K 1～10”（建议 8 分钟）

**目标**

在 HTTP 模型层拒绝纯空白问题与非法 Top-K，并在 RetrievalService 中保留完全一致的防御性规则；Embedding 内部错误不得被当成客户端 ValueError 原样泄露。

**修改位置一**

- 文件：`app/models.py`
- 定位：搜索 `from pydantic import BaseModel, Field`。
- 操作：把这一行替换为下面的 import。

**复制下面的完整代码**

```python
from pydantic import BaseModel, Field, field_validator
```

**修改位置二**

- 文件：`app/models.py`
- 定位：搜索 `class KnowledgeBaseQueryRequest(BaseModel):`。
- 操作：完整替换这个类，后面的 `KnowledgeBaseQuerySource` 保持不变。

**复制下面的完整代码**

```python
class KnowledgeBaseQueryRequest(BaseModel):
    """在指定知识库内执行数据库版 RAG 问答。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对指定知识库提出的问题",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="pgvector 最多返回的候选 Chunk 数量",
    )

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("question 不能为空")
        return cleaned_value
```

**修改位置三**

- 文件：`app/services/retrieval_service.py`
- 定位：文件首行。
- 操作：用下面内容完整替换文件；这样常量、校验和异常边界不会只改一半。

**复制下面的完整代码**

```python
from sqlalchemy.orm import Session

from app.repositories.chunk_repository import (
    ChunkRepository,
    ChunkSearchResult,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.embedding_service import EmbeddingService


DEFAULT_TOP_K = 3
MAX_TOP_K = 10
EMBEDDING_DIMENSION = 512


class RetrievalService:
    """生成 Query Embedding 并执行限定范围的 pgvector 检索。"""

    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService,
    ) -> None:
        self._embedding_service = embedding_service
        self._knowledge_bases = KnowledgeBaseRepository(session)
        self._chunks = ChunkRepository(session)

    def search(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[ChunkSearchResult]:
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError("question 不能为空")
        if top_k <= 0 or top_k > MAX_TOP_K:
            raise ValueError(
                f"top_k 必须在 1 到 {MAX_TOP_K} 之间"
            )

        knowledge_base = self._knowledge_bases.get(
            knowledge_base_id
        )
        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        try:
            query_embedding = self._embedding_service.embed_query(
                cleaned_question
            )
        except Exception as exc:
            raise RuntimeError("问题向量生成失败") from exc

        self._validate_query_embedding(query_embedding)

        return self._chunks.search_similar(
            knowledge_base_id=knowledge_base.id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

    @staticmethod
    def _validate_query_embedding(
        query_embedding: list[float],
    ) -> None:
        actual_dimension = len(query_embedding)
        if actual_dimension != EMBEDDING_DIMENSION:
            raise RuntimeError(
                "Query Embedding 维度应为 "
                f"{EMBEDDING_DIMENSION}，实际为 "
                f"{actual_dimension}"
            )
```

**这段代码怎样工作**

- 输入：HTTP 请求模型中的 `question`、`top_k`，或其他调用方直接传给 Service 的同类参数。
- 输出：合法请求继续生成 512 维 Query Embedding；非法 HTTP 输入返回 422，绕过 HTTP 的非法调用得到 ValueError。
- 调用谁：Pydantic `field_validator`、EmbeddingService、KnowledgeBaseRepository 和 ChunkRepository。
- 被谁调用：`POST /knowledge-bases/{knowledge_base_id}/query` 和 DatabaseRAGService。
- 正常路径：问题先被 trim，Top-K 限制为 1～10，检索返回不超过该数量的 ready Chunk。
- 失败路径：空白问题、0 或 11 先被 Pydantic 拒绝；直接调用 Service 时仍由 Service 拒绝；模型内部异常只向 API 暴露固定上游错误。

**完成本步骤后的预期状态**

请求模型与 Service 的 Top-K 上限一致，后续不会出现 HTTP 允许 20、Service 又使用另一个上限的规则漂移。

### 步骤 3：收紧入库事务与失败原因边界（建议 15 分钟）

**目标**

保留已有正确的分阶段事务设计，但明确区分可公开的文件输入错误和必须隐藏细节的处理错误；非法文件在进入数据库前失败，无文本或处理中断则留下 failed Document，且不留下 Chunk。

**修改位置**

- 文件：`app/services/document_ingestion_service.py`
- 定位：文件首行。
- 操作：用下面内容完整替换文件；不要只复制异常类而遗漏 `ingest_pdf()` 的重新抛出规则。

**复制下面的完整代码**

```python
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
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
MAX_FILENAME_LENGTH = 255


class DocumentInputError(ValueError):
    """客户端修改文件输入后可以解决的错误。"""


class DocumentProcessingError(RuntimeError):
    """不能向客户端公开底层细节的文档处理错误。"""


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
        cleaned_filename = self._validate_upload(
            filename=filename,
            pdf_bytes=pdf_bytes,
        )

        try:
            knowledge_base = self._knowledge_bases.get(
                knowledge_base_id
            )
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise DocumentProcessingError(
                "数据库服务暂时不可用"
            ) from exc

        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        try:
            document = self._documents.create(
                knowledge_base_id=knowledge_base.id,
                filename=cleaned_filename,
                status="processing",
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise DocumentProcessingError(
                "无法创建文档处理记录"
            ) from exc

        document_id = document.id

        try:
            pages = self._extract_pdf_pages(pdf_bytes)
            prepared_chunks = self._prepare_chunks(pages)

            if not prepared_chunks:
                raise DocumentInputError(
                    "PDF 没有生成任何 Chunk"
                )

            try:
                embeddings = (
                    self._embedding_service.embed_documents(
                        [
                            chunk.content
                            for chunk in prepared_chunks
                        ]
                    )
                )
            except Exception as exc:
                raise DocumentProcessingError(
                    "文档向量生成失败"
                ) from exc

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
                raise DocumentProcessingError(
                    "Document 状态更新失败"
                )

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
                raise DocumentProcessingError(
                    "文档处理失败，且无法保存 failed 状态"
                ) from status_error

            if isinstance(
                exc,
                (DocumentInputError, DocumentProcessingError),
            ):
                raise

            raise DocumentProcessingError(
                "文档处理失败"
            ) from exc

    @staticmethod
    def _validate_upload(
        filename: str,
        pdf_bytes: bytes,
    ) -> str:
        cleaned_filename = filename.strip()
        if not cleaned_filename:
            raise DocumentInputError("文件名不能为空")
        if len(cleaned_filename) > MAX_FILENAME_LENGTH:
            raise DocumentInputError(
                "文件名不能超过 255 个字符"
            )
        if not cleaned_filename.lower().endswith(".pdf"):
            raise DocumentInputError("只支持上传 PDF 文件")
        if not pdf_bytes:
            raise DocumentInputError("PDF 文件不能为空")
        return cleaned_filename

    def _extract_pdf_pages(
        self,
        pdf_bytes: bytes,
    ) -> list[str]:
        try:
            return self._pdf_service.extract_pages_from_bytes(
                pdf_bytes
            )
        except ValueError as exc:
            safe_message = str(exc).strip()
            if not safe_message:
                safe_message = "PDF 文件无法处理"
            raise DocumentInputError(
                safe_message[:500]
            ) from exc

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
            raise DocumentProcessingError(
                "Chunk 与 Embedding 数量不一致"
            )

        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIMENSION:
                raise DocumentProcessingError(
                    "Embedding 维度不符合入库约定"
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
            raise DocumentProcessingError(
                "找不到需要标记失败的 Document"
            )
        self._session.commit()

    @staticmethod
    def _safe_failure_reason(error: Exception) -> str:
        if isinstance(error, DocumentInputError):
            message = str(error).strip()
            if message:
                return message[:500]
        return "文档处理失败"
```

**这段代码怎样工作**

- 输入：知识库 ID、上传文件名和 PDF 字节。
- 输出：成功时返回 ready Document 的 ID、页数和 Chunk 数；可修正输入错误抛出 DocumentInputError；内部处理失败抛出 DocumentProcessingError。
- 调用谁：KnowledgeBaseRepository、DocumentRepository、ChunkRepository、PDFService、split_text 和 EmbeddingService。
- 被谁调用：数据库版文档上传 API。
- 正常路径：先独立提交 processing；解析、Embedding、Chunk 写入和 ready 更新完成后一次 commit。
- 失败路径：非法扩展名和空文件在建 Document 前失败；无文本或损坏 PDF 在 processing 记录之后失败；任何处理中断都先 rollback Chunk/ready 事务，再提交 failed 状态。

**完成本步骤后的预期状态**

输入错误只公开固定的安全文案；Embedding、数据库和未知异常只能形成通用 failure_reason 与通用 HTTP 500，不会把底层消息传给客户端。

### 步骤 4：在 API 层统一映射安全错误响应（建议 12 分钟）

**目标**

让 FastAPI 只负责 HTTP 语义：领域输入错误返回 400，不存在知识库返回 404，文档处理错误返回安全 500，未被局部处理的数据库错误统一返回安全 503。

**修改位置一**

- 文件：`app/main.py`
- 定位：文件开头的 FastAPI 与 SQLAlchemy import。
- 操作：把当前 `from fastapi import (...)` 和紧随其后的 `from sqlalchemy.exc import IntegrityError` 替换为下面完整 import 段；`from sqlalchemy.orm import Session` 保持在后面。

**复制下面的完整代码**

```python
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
```

**修改位置二**

- 文件：`app/main.py`
- 定位：搜索 `from app.services.document_ingestion_service import (`。
- 操作：完整替换该 import 段。

**复制下面的完整代码**

```python
from app.services.document_ingestion_service import (
    DocumentIngestionService,
    DocumentInputError,
    DocumentProcessingError,
)
```

**修改位置三**

- 文件：`app/main.py`
- 定位：搜索 `app = FastAPI(`，在完整的 `app = FastAPI(...)` 语句之后、服务实例初始化之前插入下面处理器。
- 操作：插入完整处理器。

**复制下面的完整代码**

```python
@app.exception_handler(SQLAlchemyError)
async def handle_database_error(
    _request: Request,
    _error: SQLAlchemyError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "数据库服务暂时不可用"},
    )
```

**修改位置四**

- 文件：`app/main.py`
- 定位：从装饰器 `@app.post(` 且下一行路径为 `"/knowledge-bases/{knowledge_base_id}/documents"` 开始。
- 操作：完整替换该装饰器和 `upload_knowledge_base_document()` 函数，直到下一个 `@app.get(` 之前。

**复制下面的完整代码**

```python
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
    except DocumentInputError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except DocumentProcessingError as exc:
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
```

**这段代码怎样工作**

- 输入：上传 API 和所有数据库 API 抛出的异常。
- 输出：400/404/500/503 的稳定 JSON `detail`，不回显数据库、Embedding 或堆栈细节。
- 调用谁：DocumentIngestionService、DocumentRepository 和 FastAPI 的异常处理机制。
- 被谁调用：`POST /knowledge-bases/{id}/documents`；全局 SQLAlchemy handler 覆盖所有未局部处理的数据库接口。
- 正常路径：上传成功仍返回原有 DocumentUploadResponse，API 契约不变。
- 失败路径：只有 DocumentInputError 的经过筛选文案可以返回 400；DocumentProcessingError 永远返回固定 500；SQLAlchemyError 返回固定 503。

**完成本步骤后的预期状态**

API 层不再把任意 ValueError 当成公开输入错误；数据库错误拥有统一响应，而请求级依赖会在响应前完成 rollback。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成 Alembic revision，不执行 upgrade/downgrade 往返；现有 `failure_reason`、状态约束和索引已经满足 Day 8。下面只检查环境、迁移位置和 Python 语法。

### 1. 检查当前状态

执行目录：项目根目录。目的：先确认没有覆盖用户修改，并确认数据库服务名、依赖版本和当前 migration head。按顺序执行：

```powershell
git status --short
docker compose config --services
python --version
python -c "import fastapi, pydantic, sqlalchemy; print('fastapi', fastapi.__version__); print('pydantic', pydantic.__version__); print('sqlalchemy', sqlalchemy.__version__)"
alembic heads
alembic current
```

预期结果：

- 开始修改前 `git status --short` 应为空；如果不为空，先记下已有文件，不要恢复它们。
- Compose 服务列表包含 `postgres`，命令不会打印数据库密码。
- 版本应与 `requirements.txt` 的 FastAPI 0.141.1、Pydantic 2.13.4、SQLAlchemy 2.0.52 对应。
- `alembic heads` 应显示 `e780fe92751b (head)`；`alembic current` 需要数据库可连接，未启动时失败不代表代码语法错误。
- 如果 `alembic current` 失败，只检查 PostgreSQL 状态和公开的 `POSTGRES_*` 变量名是否齐全，不输出变量值。

### 2. 执行升级

今天的“升级”是复制第五节代码，不是执行迁移。复制完成后运行只读语法检查和 import 检查：

```powershell
python -m compileall app
python -c "from app.models import KnowledgeBaseQueryRequest; print(KnowledgeBaseQueryRequest(question='  valid question  ', top_k=10).model_dump())"
python -c "from app.services.document_ingestion_service import DocumentInputError, DocumentProcessingError; print(DocumentInputError.__name__, DocumentProcessingError.__name__)"
```

预期结果：

- `compileall` 退出码为 0，不出现 SyntaxError 或 ImportError。
- 请求模型输出中的 question 已去除首尾空格，`top_k` 为 10。
- 两个领域异常类都能正常导入。

### 3. 回滚并恢复

今天没有 migration，因此不运行 `alembic downgrade`。如果语法检查失败，只按报错行修正当天五个代码文件；不要使用 `git reset --hard`、`git checkout --` 或删除数据库 Volume。

### 预期结果

- 数据库 revision 在修改前后都保持 `e780fe92751b`。
- `documents` 和 `chunks` 表结构不发生变化。
- 只有 Python 事务边界、错误类型、HTTP 映射和输入上限发生变化。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。先在 PowerShell 窗口 A 启动 PostgreSQL，确认健康后启动 API；首次加载 BGE 模型可能额外耗时。保持窗口 A 运行，完成验证后按 `Ctrl+C` 停止 Uvicorn。

```powershell
docker compose up -d --wait postgres
alembic upgrade head
uvicorn app.main:app --reload
```

预期结果：PostgreSQL 健康、数据库处于 head、Uvicorn 监听 `http://127.0.0.1:8000`。这些是待执行的预期，不在本计划中声称已经成功。

### 执行正常请求或测试

在 PowerShell 窗口 B、项目根目录执行。脚本只使用已固定的 httpx，在内存中构造一份可提取英文文本的 PDF，不创建或删除临时文件；它创建唯一知识库并验证合法上传仍返回 ready。

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
knowledge_base_name = f"day08_normal_{uuid4().hex[:12]}"
pdf_bytes = build_text_pdf(
    "Expense claims require an invoice and manager approval."
)

with httpx.Client(base_url=base_url, timeout=300.0) as client:
    create_response = client.post(
        "/knowledge-bases",
        json={
            "name": knowledge_base_name,
            "description": "Day 8 normal-path verification",
        },
    )
    assert create_response.status_code == 201, create_response.text
    knowledge_base = create_response.json()

    upload_response = client.post(
        f"/knowledge-bases/{knowledge_base['id']}/documents",
        files={
            "file": (
                "day08-policy.pdf",
                pdf_bytes,
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 201, upload_response.text
    body = upload_response.json()
    assert body["document"]["status"] == "ready"
    assert body["document"]["failure_reason"] is None
    assert body["page_count"] == 1
    assert body["chunk_count"] > 0

    print(json.dumps(body, ensure_ascii=False, indent=2))
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 8 正常 HTTP 路径验证失败。"
}
```

随后查询真实 PostgreSQL，确认 ready Document 和 Chunk 已持久化。命令只输出 ID、状态和数量，不输出连接 URL或密码：

```powershell
@'
from sqlalchemy import func, select

from app.db import SessionLocal
from app.orm_models import Chunk, Document, KnowledgeBase


with SessionLocal() as session:
    knowledge_base = session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.name.like("day08_normal_%"))
        .order_by(
            KnowledgeBase.created_at.desc(),
            KnowledgeBase.id.desc(),
        )
        .limit(1)
    )
    assert knowledge_base is not None

    document = session.scalar(
        select(Document)
        .where(
            Document.knowledge_base_id == knowledge_base.id,
            Document.filename == "day08-policy.pdf",
        )
        .order_by(Document.id.desc())
        .limit(1)
    )
    assert document is not None
    assert document.status == "ready"
    assert document.failure_reason is None

    chunk_count = session.scalar(
        select(func.count(Chunk.id)).where(
            Chunk.document_id == document.id
        )
    )
    assert chunk_count is not None and chunk_count > 0
    print(
        {
            "knowledge_base_id": knowledge_base.id,
            "document_id": document.id,
            "status": document.status,
            "chunk_count": chunk_count,
        }
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 8 正常路径数据库验证失败。"
}
```

### 预期状态码或输出结构

创建知识库的动态 ID、Document ID、时间戳和实际 Chunk 数由数据库与切块结果决定；稳定结构应为：

```json
{
  "document": {
    "id": "动态正整数",
    "knowledge_base_id": "动态正整数",
    "filename": "day08-policy.pdf",
    "status": "ready",
    "failure_reason": null,
    "created_at": "动态时间戳",
    "updated_at": "动态时间戳"
  },
  "page_count": 1,
  "chunk_count": "动态正整数"
}
```

### 为什么它能证明今天已经完成

HTTP 201 证明新增异常分类没有破坏合法上传；数据库查询进一步证明 ready 状态和全部 Chunk 已经提交，而不是只构造了一个成功响应。实际执行与记录可选，不影响核心代码完成后的提交。

## 八、验证失败和边界路径

### 场景一：非 PDF、空文件、无文本 PDF、无效知识库和非法问答参数

执行目录：项目根目录，API 必须保持运行。下面脚本创建一个独立知识库，逐项触发边界，并检查响应不包含常见内部敏感标记；脚本不删除数据。

```powershell
@'
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


def assert_safe(response: httpx.Response) -> None:
    response_text = response.text.lower()
    forbidden_markers = (
        "traceback",
        "postgresql+psycopg",
        "password=",
        "sqlalchemy.exc",
        "psycopg.errors",
    )
    for marker in forbidden_markers:
        assert marker not in response_text, response.text


base_url = "http://127.0.0.1:8000"
knowledge_base_name = f"day08_boundary_{uuid4().hex[:12]}"

with httpx.Client(base_url=base_url, timeout=300.0) as client:
    create_response = client.post(
        "/knowledge-bases",
        json={"name": knowledge_base_name},
    )
    assert create_response.status_code == 201, create_response.text
    knowledge_base_id = create_response.json()["id"]
    upload_path = (
        f"/knowledge-bases/{knowledge_base_id}/documents"
    )

    non_pdf = client.post(
        upload_path,
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert non_pdf.status_code == 400, non_pdf.text
    assert non_pdf.json()["detail"] == "只支持上传 PDF 文件"

    empty_pdf = client.post(
        upload_path,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty_pdf.status_code == 400, empty_pdf.text
    assert empty_pdf.json()["detail"] == "PDF 文件不能为空"

    no_text_pdf = client.post(
        upload_path,
        files={
            "file": (
                "no-text.pdf",
                build_text_pdf(""),
                "application/pdf",
            )
        },
    )
    assert no_text_pdf.status_code == 400, no_text_pdf.text
    assert "没有提取到文本" in no_text_pdf.json()["detail"]

    missing_knowledge_base = client.post(
        "/knowledge-bases/2147483647/documents",
        files={
            "file": (
                "valid.pdf",
                build_text_pdf("Valid text"),
                "application/pdf",
            )
        },
    )
    assert missing_knowledge_base.status_code == 404

    whitespace_question = client.post(
        f"/knowledge-bases/{knowledge_base_id}/query",
        json={"question": "   ", "top_k": 3},
    )
    assert whitespace_question.status_code == 422

    zero_top_k = client.post(
        f"/knowledge-bases/{knowledge_base_id}/query",
        json={"question": "policy", "top_k": 0},
    )
    assert zero_top_k.status_code == 422

    excessive_top_k = client.post(
        f"/knowledge-bases/{knowledge_base_id}/query",
        json={"question": "policy", "top_k": 11},
    )
    assert excessive_top_k.status_code == 422

    responses = (
        non_pdf,
        empty_pdf,
        no_text_pdf,
        missing_knowledge_base,
        whitespace_question,
        zero_top_k,
        excessive_top_k,
    )
    for response in responses:
        assert_safe(response)

    documents_response = client.get(
        f"/knowledge-bases/{knowledge_base_id}/documents"
    )
    assert documents_response.status_code == 200
    documents = documents_response.json()
    failed_documents = [
        document
        for document in documents
        if document["filename"] == "no-text.pdf"
    ]
    assert len(failed_documents) == 1
    assert failed_documents[0]["status"] == "failed"
    assert "没有提取到文本" in (
        failed_documents[0]["failure_reason"] or ""
    )
    assert all(
        document["filename"] not in {"notes.txt", "empty.pdf"}
        for document in documents
    )

    print(
        {
            "non_pdf": non_pdf.status_code,
            "empty_pdf": empty_pdf.status_code,
            "no_text_pdf": no_text_pdf.status_code,
            "missing_knowledge_base": (
                missing_knowledge_base.status_code
            ),
            "whitespace_question": whitespace_question.status_code,
            "zero_top_k": zero_top_k.status_code,
            "excessive_top_k": excessive_top_k.status_code,
            "failed_document": failed_documents[0],
        }
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 8 输入边界验证失败。"
}
```

再用数据库查询确认 no-text Document 为 failed 且没有 Chunk；非 PDF 和空文件在建 Document 之前就已拒绝，所以不应留下对应记录：

```powershell
@'
from sqlalchemy import func, select

from app.db import SessionLocal
from app.orm_models import Chunk, Document, KnowledgeBase


with SessionLocal() as session:
    knowledge_base = session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.name.like("day08_boundary_%"))
        .order_by(
            KnowledgeBase.created_at.desc(),
            KnowledgeBase.id.desc(),
        )
        .limit(1)
    )
    assert knowledge_base is not None

    documents = list(
        session.scalars(
            select(Document).where(
                Document.knowledge_base_id == knowledge_base.id
            )
        )
    )
    assert [document.filename for document in documents] == [
        "no-text.pdf"
    ]

    failed_document = documents[0]
    assert failed_document.status == "failed"
    chunk_count = session.scalar(
        select(func.count(Chunk.id)).where(
            Chunk.document_id == failed_document.id
        )
    )
    assert chunk_count == 0
    print(
        {
            "document_id": failed_document.id,
            "status": failed_document.status,
            "failure_reason": failed_document.failure_reason,
            "chunk_count": chunk_count,
        }
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 8 失败状态数据库验证失败。"
}
```

### 场景二：已经 flush 一个 Chunk 后模拟数据库写入失败

执行目录：项目根目录。下面脚本直接调用 Service，用固定 512 维向量避免外部模型波动，并让测试 Repository 在真实 flush 第一个 Chunk 后抛出模拟数据库错误；它验证 rollback 确实撤销已 flush 的 Chunk。该命令只写入一个唯一名称知识库和一个 failed Document，不删除任何数据。

```powershell
@'
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.orm_models import Chunk, Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.document_ingestion_service import (
    DocumentIngestionService,
    DocumentProcessingError,
)
from app.services.pdf_service import PDFService


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


class FixedEmbeddingService:
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [[0.0] * 512 for _ in texts]


class FlushThenFailChunkRepository(ChunkRepository):
    def bulk_create(self, document_id: int, chunks):
        super().bulk_create(
            document_id=document_id,
            chunks=list(chunks)[:1],
        )
        raise SQLAlchemyError("simulated chunk write failure")


knowledge_base_name = f"day08_rollback_{uuid4().hex[:12]}"
filename = "rollback-check.pdf"
long_text = (
    "A document ingestion transaction must not keep partial chunks. "
    * 12
)

with SessionLocal() as session:
    knowledge_base = KnowledgeBaseRepository(session).create(
        name=knowledge_base_name,
        description="Day 8 rollback verification",
    )
    session.commit()

    service = DocumentIngestionService(
        session=session,
        pdf_service=PDFService(),
        embedding_service=FixedEmbeddingService(),
    )
    service._chunks = FlushThenFailChunkRepository(session)

    try:
        service.ingest_pdf(
            knowledge_base_id=knowledge_base.id,
            filename=filename,
            pdf_bytes=build_text_pdf(long_text),
        )
    except DocumentProcessingError as exc:
        assert str(exc) == "文档处理失败"
    else:
        raise AssertionError("模拟数据库错误没有触发失败路径")

    failed_document = session.scalar(
        select(Document)
        .where(
            Document.knowledge_base_id == knowledge_base.id,
            Document.filename == filename,
        )
        .order_by(Document.id.desc())
        .limit(1)
    )
    assert failed_document is not None
    assert failed_document.status == "failed"
    assert failed_document.failure_reason == "文档处理失败"

    chunk_count = session.scalar(
        select(func.count(Chunk.id)).where(
            Chunk.document_id == failed_document.id
        )
    )
    assert chunk_count == 0
    print(
        {
            "document_id": failed_document.id,
            "status": failed_document.status,
            "failure_reason": failed_document.failure_reason,
            "chunk_count": chunk_count,
        }
    )
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 8 部分 Chunk 回滚验证失败。"
}
```

### 预期结果

- HTTP 状态码或异常：非 PDF、空文件、无文本 PDF 为 400；不存在知识库为 404；空白问题、`top_k=0`、`top_k=11` 为 422；故障注入脚本捕获 DocumentProcessingError。
- 数据库应该保留：无文本 PDF 和模拟写入失败各保留一个 failed Document，`failure_reason` 只含安全文案。
- 数据库不应该存在：非 PDF/空文件对应的 Document；任一 failed Document 对应的 Chunk；任何 ready 状态的失败上传。
- 响应不能泄露：数据库 URL、用户名/密码、SQL 文本、SQLAlchemy/psycopg 类型名、Python traceback、Embedding 模型内部异常。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `ImportError: cannot import name field_validator` | 当前虚拟环境不是 `requirements.txt` 固定的 Pydantic 2.13.4 | `python -c "import pydantic; print(pydantic.__version__)"` | 激活项目正确虚拟环境；如依赖确实未安装，再按项目固定文件执行 `pip install -r requirements.txt`，不要单独升级到不一致版本 |
| `top_k=11` 没有返回 422 | 只改了 RetrievalService，没有把请求模型的 `le` 改为 10，或 Uvicorn 未重载 | 检查 `app/models.py` 的 `KnowledgeBaseQueryRequest`；观察窗口 A 重载日志 | 同时保持模型 `le=10` 和 Service `MAX_TOP_K=10`，保存文件并确认 Uvicorn reload 完成 |
| 空白 question 返回 400 而不是 422 | `field_validator` 没有放在 `KnowledgeBaseQueryRequest` 内，或仍在运行旧进程 | `python -c "from app.models import KnowledgeBaseQueryRequest; KnowledgeBaseQueryRequest(question='   ')"` | 按步骤 2 完整替换类；停止旧 Uvicorn 后重新启动 |
| 无文本 PDF 返回 400，但文档一直是 processing | `_mark_document_failed()` 没有在 rollback 后执行，或保存 failed 的第二个事务也失败 | GET 文档列表；检查 `app/services/document_ingestion_service.py` 的 except 顺序 | 必须先 rollback，再 update_status(failed)，最后单独 commit；若数据库不可用，先恢复数据库连接再重试新上传 |
| 故障注入后 failed Document 仍有 Chunk | Repository 中出现了逐 Chunk commit，或异常路径没有 rollback | 搜索 `app/repositories` 中的 `commit(`；运行场景二脚本 | Repository 只允许 add/flush/refresh；commit/rollback 保留在 Service/请求依赖边界 |
| 上传内部错误响应出现底层异常原文 | `app/main.py` 仍捕获任意 ValueError 并 `detail=str(exc)` | 搜索数据库版上传端点的 `except ValueError` | 只对 DocumentInputError 使用 `str(exc)`；DocumentProcessingError 固定返回“文档处理失败” |
| 数据库断开时返回 HTML 或异常类型名 | SQLAlchemyError handler 未放在 `app = FastAPI(...)` 之后，或 import 不完整 | 查看 `app/main.py` 的 handler 与 Uvicorn 启动日志 | 导入 SQLAlchemyError、Request、JSONResponse，注册 handler 后重启 API；不要把异常对象放进响应 |
| `alembic current` 连接失败 | PostgreSQL 未健康或公开变量缺失 | `docker compose ps`；检查 `.env` 中变量名是否存在但不要输出值 | 先执行 `docker compose up -d --wait postgres`；错误日志中不要复制或展示真实密码 |
| 正常上传首次运行很慢 | SentenceTransformer 首次加载或下载模型 | 窗口 A 日志、模型缓存是否存在 | 等待模型完成加载；外部下载耗时不计入今日核心 60 分钟，不要把慢启动误判为事务失败 |

## 十、检查最终代码差异

执行目录：项目根目录。先检查全部状态，再只查看当天文件：

```powershell
git status --short
git diff -- app/db.py app/models.py app/services/retrieval_service.py app/services/document_ingestion_service.py app/main.py "docs/17天每日学习/Day08.md"
```

重点检查：

- `get_db_session()` 只做异常 rollback 兜底，没有自动 commit。
- `KnowledgeBaseQueryRequest` 和 RetrievalService 的 Top-K 上限都为 10。
- 只有 DocumentInputError 原文可以进入 400 响应；DocumentProcessingError 和 SQLAlchemyError 使用固定公开文案。
- Chunk 写入与 ready 状态仍只有一次 commit，Repository 中没有新增 commit。
- failed 更新发生在 rollback 之后，并使用另一次 commit。
- `ChunkRepository.search_similar()` 的知识库和 ready 过滤没有被删除。
- diff 中没有 `.env`、连接 URL、密码、令牌、临时数据库文件或无关学习资料。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。先再次确认下面六个路径就是当天全部文件：

```powershell
git status --short
git diff -- app/db.py app/models.py app/services/retrieval_service.py app/services/document_ingestion_service.py app/main.py "docs/17天每日学习/Day08.md"
git add app/db.py app/models.py app/services/retrieval_service.py app/services/document_ingestion_service.py app/main.py "docs/17天每日学习/Day08.md"
git commit -m "完善文档入库事务与输入校验"
```

不要使用 `git add .`。如果执行验证后发现已知失败，先修复失败再提交；不需要把 HTTP、数据库或故障注入的输出保存进提交。

## 十二、面试高频问题与参考答案

### 问题 1：为什么不能把 processing、Chunk、ready 和 failed 全放在一个事务里？

#### 30 秒参考答案

如果全部放在一个事务里，处理中断后 rollback 会连最初的 Document 一起撤销，系统就失去失败记录。当前项目先提交 processing Document，再把全部 Chunk 和 ready 更新放进一个原子事务；失败时先回滚这个事务，确保没有部分 Chunk，然后用一个新的短事务保存 failed。这样同时得到数据一致性和失败可观测性。

#### 继续追问：这种设计还有什么限制？

进程如果在 processing 提交后直接崩溃，来不及执行 failed 更新，可能留下长期 processing 记录。生产系统可以用超时扫描和幂等重试修复，但本轮明确不引入后台 Worker；Day 8 先保证可捕获异常下的 rollback 与 failed 状态正确。

#### 回答时要引用的项目依据

- `app/services/document_ingestion_service.py` 的第一次 processing commit、Chunk/ready commit、异常 rollback 和 `_mark_document_failed()`。
- `app/repositories/chunk_repository.py` 只有 flush，没有 commit。
- 场景二故障注入的 `failed + chunk_count=0` 预期结果。

### 问题 2：Repository、Service 和 FastAPI 各自应该负责哪部分异常处理？

#### 30 秒参考答案

Repository 负责数据库读写并让 SQLAlchemy 异常向上冒泡；Service 知道业务阶段，所以负责 commit、rollback、状态转换以及把底层异常分类成领域异常；FastAPI 不参与 PDF 或事务细节，只把领域异常映射为稳定状态码和公开响应。当前项目再由 Session 依赖和 SQLAlchemy 全局 handler 提供最后兜底。

#### 继续追问：为什么不在 Repository 中捕获所有异常并返回 None？

None 应只表示“查询不到”，不能同时表示数据库断线或约束失败；否则 Service 会把系统故障误判成业务不存在，也无法决定是否 rollback。保留异常类型才能正确映射 404、400、500 和 503。

#### 回答时要引用的项目依据

- `app/repositories/document_repository.py` 的 get/update_status 返回约定。
- `app/services/document_ingestion_service.py` 的 DocumentInputError 和 DocumentProcessingError。
- `app/main.py` 的上传异常映射与 SQLAlchemyError handler。

### 问题 3：为什么 Pydantic 已经限制 top_k，RetrievalService 还要再校验？

#### 30 秒参考答案

Pydantic 只保护 HTTP 请求入口，而 RetrievalService 还可能被评测脚本、后台任务或直接 Python 调用。模型层尽早返回 422，Service 层维护 `1 <= top_k <= 10` 的业务不变量。两层保持同一常量语义，避免绕过 API 后对数据库发出无界或异常查询。

#### 继续追问：top_k 与检索阈值有什么区别？

Top-K 控制数据库最多返回多少候选，阈值判断候选证据是否足够可靠。当前 RetrievalService 限制数量，DatabaseRAGService 使用 `MIN_RELEVANCE_SCORE` 决定拒答；一个解决候选规模，一个解决证据质量。

#### 回答时要引用的项目依据

- `app/models.py` 的 `KnowledgeBaseQueryRequest.top_k`。
- `app/services/retrieval_service.py` 的 MAX_TOP_K 和 search 校验。
- `app/services/database_rag_service.py` 的 MIN_RELEVANCE_SCORE 与拒答分支。

### 问题 4：如何保证失败上传不会进入 RAG 检索？

#### 30 秒参考答案

项目有两道边界。第一道是事务：Chunk 批量写入与 ready 更新一起提交，中间任何异常都会 rollback，所以 failed 文档不应保留部分 Chunk。第二道是查询过滤：pgvector SQL 只联结指定知识库中 status=ready 的 Document，即使存在 processing/failed 记录也不会进入 Top-K 和 LLM Context。

#### 继续追问：为什么不只依赖 ready 过滤？

只过滤虽然能暂时避免错误检索，但数据库仍可能堆积孤立或部分 Chunk，影响存储、审计和后续修复；只依赖事务又无法防止历史脏数据或异常状态被误查。事务保证写入一致，状态过滤保证读取安全，两者不能互相替代。

#### 回答时要引用的项目依据

- `app/services/document_ingestion_service.py` 的 Chunk/ready 原子事务。
- `app/repositories/chunk_repository.py` 的 `Document.status == "ready"` SQL 条件。
- Day 8 数据库验证中的 failed Document 和 `chunk_count == 0`。

## 十三、今天的完整数据流

### 正常路径

```text
POST /knowledge-bases/{id}/documents
→ FastAPI 读取 filename 与 bytes
→ DocumentIngestionService 校验文件名、.pdf 和非空字节
→ KnowledgeBaseRepository 确认知识库存在
→ 创建 processing Document
→ commit：留下可观察的处理记录
→ PDFService 解析每页文本
→ split_text 生成带页码和顺序的 Chunk
→ EmbeddingService 生成 512 维向量
→ ChunkRepository 批量 add + flush
→ DocumentRepository 更新 ready
→ commit：Chunk 与 ready 一起生效
→ API 返回 201 + DocumentUploadResponse
```

```text
POST /knowledge-bases/{id}/query
→ Pydantic trim question，并校验 top_k=1～10
→ DatabaseRAGService
→ RetrievalService 再次校验
→ Query Embedding
→ pgvector SQL 同时过滤知识库和 ready 状态
→ Top-K Context
→ 阈值拒答或 LLM 回答
→ 返回 answer + refused + sources
```

### 失败路径

```text
非 PDF / 空文件
→ DocumentInputError
→ 建 Document 前终止
→ HTTP 400
→ 数据库没有对应 Document 和 Chunk
```

```text
无文本 PDF / Embedding 失败 / Chunk 写入失败
→ processing Document 已提交
→ 当前 Chunk/ready 事务 rollback
→ 新事务更新 Document.status=failed
→ failure_reason 只保留安全输入提示或“文档处理失败”
→ commit failed
→ HTTP 400 或安全 500
→ Chunk 数为 0
→ ready SQL 过滤保证不可检索
```

```text
空白 question / top_k=0 / top_k=11
→ Pydantic 请求校验失败
→ HTTP 422
→ 不生成 Query Embedding
→ 不执行 pgvector SQL
→ 不调用 LLM
```

```text
未局部处理的 SQLAlchemyError
→ get_db_session 异常出口 rollback
→ 全局 SQLAlchemy handler
→ HTTP 503 + 固定 detail
→ 响应不包含连接信息、SQL 或堆栈
```

## 十四、完成标准

```text
[ ] 能解释为什么 rollback 后要用新事务保存 failed，以及这种设计可能留下长期 processing 的崩溃窗口
[ ] 能解释 Pydantic 边界校验与 Service 防御性校验为什么都需要
[ ] `get_db_session()` 已在异常退出时 rollback，Repository 仍没有 commit/rollback
[ ] 文档入库已区分 DocumentInputError 与 DocumentProcessingError，并只保存安全 failure_reason
[ ] Chunk 写入与 ready 更新仍在同一事务，失败后可由数据库命令确认 failed Document 的 Chunk 数为 0
[ ] 空白 question、top_k=0 和 top_k=11 有可执行的 422 验证命令与预期结果，实际执行和记录可选
[ ] 非 PDF、空文件、无文本 PDF和不存在知识库有可执行的 400/404 验证命令与预期结果，实际执行和记录可选
[ ] 能不看代码复述“processing 提交 → Chunk/ready 原子提交 → rollback → failed 单独提交”的完整失败数据流
[ ] HTTP 错误响应使用固定安全文案，不包含数据库密码、URL、SQL、底层异常类型或 traceback
[ ] git diff 只包含当天五个代码文件和 Day08.md，核心实现完成后可执行边界清晰的 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
