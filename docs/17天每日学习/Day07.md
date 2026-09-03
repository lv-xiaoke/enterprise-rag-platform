# Day 7：完成数据库版 RAG 问答与来源追溯

今天将直接完成指定知识库的 pgvector 检索、证据阈值拒答、LLM 生成与来源返回闭环，使项目获得数据库版 `answer + sources` 问答能力，并为面试中的 RAG 数据流、来源追溯和拒答设计提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一个指定知识库的数据库版 RAG 查询接口，返回 `answer + sources`，证据不足时在调用 LLM 前明确拒答  
> 当前真实状态：已完成  
> 对应总体安排：Day 7

## 一、今天完成后的项目变化

### 升级前

```text
POST /rag/chat
→ 只查询进程内最近一次上传形成的 FAISS 索引
→ 服务重启后索引丢失
→ 不按 knowledge_base_id 隔离
→ 来源只有 text、page、score

Day 5 RetrievalService
→ 已能在指定知识库内查询 ready Document 的 pgvector Chunk
→ 但还没有接入 LLM 和 HTTP 问答接口
```

### 升级后

```text
POST /knowledge-bases/{knowledge_base_id}/query
→ 校验 question 和 top_k
→ RetrievalService 生成 Query Embedding
→ pgvector 仅检索指定知识库中的 ready Document
→ 固定 similarity threshold 过滤证据
→ 无证据：直接返回 refused=true、sources=[]，不调用 LLM
→ 有证据：构造带文档名、页码和 Chunk ID 的 Context
→ LLMService 生成回答
→ 返回 answer、refused=false 和可核对 sources
```

### 今天在完整项目中的位置

- 所属阶段：核心 MVP。
- 所属链路：完整用户问答链路。
- 今天的输入：`knowledge_base_id`、用户问题、`top_k`、Day 5 的 `RetrievalService`、数据库中的 ready Chunk 和现有 `LLMService`。
- 今天的输出：数据库版知识库问答 HTTP 响应，包含回答、拒答标记和文档名、页码、Chunk ID、原文、分数等来源字段。
- 下一天为什么需要它：Day 8 要围绕这条已闭环的入库与问答链路统一加固事务、失败状态和输入边界；没有 Day 7 的完整问答入口，就无法验证失败是否会产生半成品或泄露内部细节。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 6 都有当前核心代码、用户完成标记和匹配 Git 提交；最新提交是 `70766da Day6`。
- `[当前事实]` 生成本计划前 `git status --short` 为空，没有发现需要合并的用户未提交代码。
- `[当前事实]` `app/db.py` 已提供应用级 Engine、`SessionLocal` 和 FastAPI 请求级 `get_db_session()`。
- `[当前事实]` `app/orm_models.py` 已定义 `KnowledgeBase → Document → Chunk`，Chunk 的 Embedding 是 512 维向量。
- `[当前事实]` `ChunkRepository.search_similar()` 已按 `knowledge_base_id` 和 `Document.status == "ready"` 过滤，并按余弦距离升序返回文档名、页码、Chunk ID、原文和 `score = 1 - distance`。
- `[当前事实]` `RetrievalService.search()` 已校验空白问题、`top_k` 的 1～20 边界、知识库存在性和 Query Embedding 的 512 维长度。
- `[当前事实]` Day 6 已提供创建/查询知识库、上传/列出/查询文档的数据库 API；上传成功后 Document 为 `ready`。
- `[当前事实]` 现有 `build_rag_prompt()`、`LLMService.chat()` 和旧 FAISS `/rag/chat` 可以保留并复用。
- `[当前事实]` 固定依赖包括 FastAPI 0.141.1、Pydantic 2.13.4、SQLAlchemy 2.0.52、pgvector 0.5.0、httpx 0.28.1 和 Uvicorn 0.52.1。
- `[当前事实]` 当前仓库没有 `tests/` 测试文件；Day 7 使用可复制的 HTTP、数据库和内存边界脚本验收，正式 pytest 属于 Day 12。

### 仍然缺少

- `[当前事实]` `app/models.py` 只有旧 FAISS RAG 响应，没有数据库版知识库查询请求、来源和响应模型。
- `[当前事实]` `app/services/rag_service.py` 的 `RAGService` 只接受 `FAISSVectorStore`，不能编排 Day 5 的 `RetrievalService`。
- `[当前事实]` 当前没有固定的证据阈值，也没有“低分或无结果时先拒答、不要调用 LLM”的业务分支。
- `[当前事实]` `app/main.py` 没有 `POST /knowledge-bases/{knowledge_base_id}/query`。
- `[当前事实]` 数据库版问答还不能把文档名、文档 ID、页码、Chunk ID、Chunk 序号、原文和分数一起返回给调用方。
- `[当前事实]` 还没有把知识库不存在、空白问题、LLM 未配置和 LLM 上游失败映射为明确 HTTP 状态。

### 待实测

- `[待实测]` PostgreSQL 容器是否健康，当前 revision 是否为 `e780fe92751b (head)`。
- `[待实测]` Day 6 创建的 ready 文档是否仍在数据库；若不存在，正常路径脚本会创建独立的 Day 7 测试知识库和两份内存 PDF。
- `[待实测]` 本机 `.env` 是否已配置可用的 LLM 服务；只能检查是否完整，不能打印 API Key。
- `[待实测]` 暂定 `0.55` 的余弦相似度阈值是否适合后续企业制度评测集；Day 7 先固定可复现基线，Day 11 再用 Recall、MRR 和拒答正确率调参。
- `[待实测]` 正常问题返回的第一条来源是否能定位到数据库里的相同 Document 和 Chunk。

### 需要保护的用户修改

- 生成计划前工作区干净；写入本文件后，开始编码时 `git status --short` 应至少出现新文件 `docs/17天每日学习/Day07.md`，这是今天的计划产物，不要误删。
- 只按今天的四个文件操作，不覆盖、不恢复、不暂存其他修改；若开始执行时这些文件已有新改动，先阅读并手工合并。
- 保留旧 `/upload`、`/rag/chat`、`RAGService` 和 FAISS 代码，作为项目技术演进基线；今天不做删除式重构。
- 不读取、显示或提交真实 `.env`、API Key、数据库密码和访问令牌。

## 三、今天必须理解的核心知识

### 1. RAG 的检索边界与生成边界

- 一句话解释：检索负责从可信数据中找到证据，生成负责把已找到的证据组织成自然语言回答。
- 在当前项目中的职责：`RetrievalService` 完成 Query Embedding 与 pgvector Top-K；新增 `DatabaseRAGService` 决定是否有足够证据、构造 Context，再调用 `LLMService`。
- 与其他组件的关系：API 只处理 HTTP 契约，RAG Service 编排流程，Retrieval Service 调 Repository，Repository 执行 SQL，LLM Service 只负责上游模型调用。
- 容易混淆的点：LLM 不会直接连接数据库；数据库检索结果必须先转换成明确 Context 才能进入 Prompt。
- 面试一句话：我把检索和生成拆开，先用指定知识库中的 ready Chunk 得到可核对证据，再把证据交给 LLM，避免模型把外部知识伪装成企业制度答案。

### 2. Top-K 与 similarity threshold

- 一句话解释：Top-K 决定最多取几条候选证据，threshold 决定候选证据是否足够相关。
- 在当前项目中的职责：`top_k` 继续使用 Day 5 的 1～20 校验；`MIN_RELEVANCE_SCORE = 0.55` 过滤 `score = 1 - cosine_distance` 的结果。
- 与其他组件的关系：Repository 负责排序和截断，DatabaseRAGService 负责阈值判断；二者不能互相替代。
- 容易混淆的点：即使问题完全无关，向量数据库通常仍会返回 Top-K；“有结果”不等于“有可靠证据”。
- 面试一句话：Top-K 控制 Context 数量和成本，阈值控制是否应该回答；我先 Top-K，再过滤低于固定阈值的来源。

### 3. 早拒答与失败的区别

- 一句话解释：拒答是系统成功判断证据不足的正常业务结果，上游超时或数据库异常才是技术失败。
- 在当前项目中的职责：无结果或所有分数低于阈值时返回 HTTP 200、`refused=true`、固定拒答文本和空来源；不进入 LLM 调用。
- 与其他组件的关系：知识库不存在返回 404，问题非法返回 400，LLM 未配置返回 503，LLM 上游失败返回 502，均不伪装成业务拒答。
- 容易混淆的点：拒答不应该返回无关来源；把所有异常都返回 200 会让客户端无法区分“没有答案”和“服务坏了”。
- 面试一句话：我把无证据拒答设计成可预测的成功响应，并在调用 LLM 前短路，从而同时降低幻觉和无效模型成本。

### 4. 来源追溯

- 一句话解释：来源追溯让调用方能从回答回到真实数据库记录和原始 PDF 页码核对事实。
- 在当前项目中的职责：每条来源返回 `chunk_id`、`document_id`、`filename`、`page_number`、`chunk_index`、`content` 和 `score`。
- 与其他组件的关系：这些字段来自 Day 5 的联表检索结果，不在 API 层重新猜测或拼接数据库 ID。
- 容易混淆的点：只返回相似度或只返回文档名都不足以核对具体证据；页码和原文必须在入库阶段保存，不能在回答后补猜。
- 面试一句话：我的来源能定位到具体文档、页码和 Chunk，同时返回原文与分数，便于人工审计回答依据。

## 四、升级涉及的文件

| 文件                                     | 操作  | 作用                                                 |
| -------------------------------------- | --- | -------------------------------------------------- |
| `app/models.py`                        | 修改  | 新增数据库版知识库查询请求、完整来源和问答响应模型，保留所有旧模型。                 |
| `app/services/database_rag_service.py` | 新建  | 编排 Retrieval、threshold、早拒答、Context 和 LLM，返回稳定领域结果。 |
| `app/main.py`                          | 修改  | 新增数据库版问答路由并把领域结果、输入错误和上游错误映射为 HTTP 契约。             |
| `docs/17天每日学习/Day07.md`                | 新建  | 保存今天可直接执行的升级、验证、排错和面试手册。                           |

### 今日不做

- 不修改 ORM、Repository、Alembic migration 或数据库 schema；Day 7 只消费已经存在的数据结构。
- 不删除或重写旧 FAISS `/upload`、`/rag/chat`；兼容清理不属于今天的核心产物。
- 不做流式回答、聊天记忆、Agent 工具调用、重排序器或复杂 Prompt 优化。
- 不把 threshold 做成公开配置或开始 Recall/MRR 参数实验；固定评测与调参属于 Day 10～Day 11。
- 不新增正式 pytest 文件；新架构自动测试集属于 Day 12。
- 不全面解决数据库异常、并发请求、上传大小、日志脱敏等组合问题；Day 8 统一加固可靠性边界。

## 五、按顺序完成项目升级

### 步骤 1：新增数据库版查询请求和响应模型（建议 8 分钟）

**目标**

为新接口固定 `question + top_k → answer + refused + sources` 的 HTTP 数据形状，并让来源字段完整对应 Day 5 的检索结果。

**修改位置**

- 文件：`app/models.py`
- 定位：搜索文件末尾的 `class DocumentUploadResponse(BaseModel):`。
- 操作：保留现有全部模型，在 `DocumentUploadResponse` 类定义结束后追加下面三个完整类。

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
        le=20,
        description="pgvector 最多返回的候选 Chunk 数量",
    )


class KnowledgeBaseQuerySource(BaseModel):
    """一条可以回查数据库和原 PDF 页码的 RAG 来源。"""

    chunk_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    filename: str = Field(min_length=1)
    page_number: int = Field(gt=0)
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)


class KnowledgeBaseQueryResponse(BaseModel):
    """数据库版 RAG 的回答、拒答标记和来源。"""

    answer: str = Field(min_length=1)
    refused: bool
    sources: list[KnowledgeBaseQuerySource]
```

**这段代码怎样工作**

- 输入：客户端 JSON 中的 `question` 和可选 `top_k`。
- 输出：FastAPI 可以校验和序列化的数据库版问答响应。
- 调用谁：不调用业务组件，只定义 HTTP 契约。
- 被谁调用：第三步新增的 `/knowledge-bases/{knowledge_base_id}/query` 路由。
- 正常路径：`top_k` 省略时为 3；返回非空 answer、布尔拒答标记和来源数组。
- 失败路径：空字符串、超过 1000 字或 `top_k` 不在 1～20 时，Pydantic/FastAPI 在业务服务之前返回 422；只包含空格的问题长度合法，但会在 Service 层返回 400。

**完成本步骤后的预期状态**

`app.models` 同时保留旧 FAISS 模型和新知识库问答模型；没有修改现有 API 的请求/响应结构。

### 步骤 2：新建数据库版 RAG 编排服务（建议 20 分钟）

**目标**

复用 Day 5 的 RetrievalService 与现有 Prompt/LLM 能力，把检索、阈值过滤、早拒答、Context 构造和生成收拢到一个清晰业务边界。

**修改位置**

- 文件：`app/services/database_rag_service.py`
- 定位：当天新文件。
- 操作：新建文件并复制下面的完整内容。

**复制下面的完整代码**

```python
from dataclasses import dataclass

from app.repositories.chunk_repository import ChunkSearchResult
from app.services.llm_service import LLMService
from app.services.rag_service import build_rag_prompt
from app.services.retrieval_service import (
    DEFAULT_TOP_K,
    RetrievalService,
)


MIN_RELEVANCE_SCORE = 0.55
REFUSAL_ANSWER = "当前知识库中没有找到足够的信息。"


class RAGConfigurationError(RuntimeError):
    """RAG 生成所需的外部配置不完整。"""


@dataclass(frozen=True)
class DatabaseRAGResult:
    answer: str
    refused: bool
    sources: list[ChunkSearchResult]


class DatabaseRAGService:
    """编排指定知识库的检索、拒答和 LLM 生成。"""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        min_relevance_score: float = MIN_RELEVANCE_SCORE,
    ) -> None:
        if not -1.0 <= min_relevance_score <= 1.0:
            raise ValueError(
                "min_relevance_score 必须在 -1 到 1 之间"
            )

        self._retrieval_service = retrieval_service
        self._llm_service = llm_service
        self._min_relevance_score = min_relevance_score

    async def answer(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> DatabaseRAGResult:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("question 不能为空")

        search_results = self._retrieval_service.search(
            knowledge_base_id=knowledge_base_id,
            question=cleaned_question,
            top_k=top_k,
        )
        relevant_results = [
            result
            for result in search_results
            if result.score >= self._min_relevance_score
        ]

        if not relevant_results:
            return DatabaseRAGResult(
                answer=REFUSAL_ANSWER,
                refused=True,
                sources=[],
            )

        contexts = [
            self._build_context(result)
            for result in relevant_results
        ]
        prompt = build_rag_prompt(
            question=cleaned_question,
            contexts=contexts,
        )

        try:
            answer = await self._llm_service.chat(prompt)
        except ValueError as exc:
            raise RAGConfigurationError(
                "大模型服务配置不完整"
            ) from exc

        return DatabaseRAGResult(
            answer=answer.strip(),
            refused=False,
            sources=relevant_results,
        )

    @staticmethod
    def _build_context(result: ChunkSearchResult) -> str:
        return (
            f"文档：{result.filename}\n"
            f"页码：{result.page_number}\n"
            f"Chunk ID：{result.chunk_id}\n"
            f"原文：\n{result.content}"
        )
```

**这段代码怎样工作**

- 输入：已绑定请求级 Session 的 `RetrievalService`、共享 `LLMService`、`knowledge_base_id`、问题和 `top_k`。
- 输出：`DatabaseRAGResult`，明确区分正常回答与业务拒答。
- 调用谁：调用 `RetrievalService.search()`；有合格来源时调用现有 `build_rag_prompt()` 和 `LLMService.chat()`。
- 被谁调用：第三步的知识库 query 路由。
- 正常路径：检索结果按分数排序，保留 `score >= 0.55` 的来源，把来源元数据与原文放入 Context，调用 LLM 后原样返回同一批来源。
- 失败路径：空白问题抛 `ValueError`；知识库不存在由 RetrievalService 抛 `LookupError`；LLM 缺配置转成 `RAGConfigurationError`；LLM 网络、超时或响应格式错误继续使用安全的 `RuntimeError`。
- 早拒答：无结果或所有候选分数低于阈值时直接返回固定回答和空来源，代码不会执行 `LLMService.chat()`。
- 阈值说明：`0.55` 是 Day 7 的固定基线，不宣称已经最优；Day 11 再基于固定评测集调参。

**完成本步骤后的预期状态**

数据库版 RAG 编排可以脱离 HTTP 独立调用；旧 `app/services/rag_service.py` 和 `RAGService` 无需修改，旧 FAISS 路由继续可用。

### 步骤 3：把数据库版 RAG 接到知识库 API（建议 17 分钟）

**目标**

增加 `POST /knowledge-bases/{knowledge_base_id}/query`，并把领域异常映射为稳定、安全的 HTTP 状态和响应。

**修改位置 1：补充 API 模型 import**

- 文件：`app/main.py`
- 定位：搜索从 `from app.models import (` 开始、到 `)` 结束的现有完整 import 块。
- 操作：只替换该 import 块，不改其他 import。

**复制下面的完整替换代码**

```python
from app.models import (
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    KnowledgeBaseQuerySource,
    KnowledgeBaseResponse,
    Message,
    RAGChatRequest,
    RAGChatResponse,
    RAGSource,
    UploadResponse,
)
```

**修改位置 2：补充业务服务 import**

- 文件：`app/main.py`
- 定位：搜索现有的 `from app.services.chunk_service import split_text`。
- 操作：在这行之后、`DocumentIngestionService` import 之前插入下面代码。

**复制下面的完整插入代码**

```python
from app.services.database_rag_service import (
    DatabaseRAGService,
    RAGConfigurationError,
)
```

- 继续定位：搜索 `from app.services.rag_service import RAGService`。
- 操作：在该行之后插入下面代码。

```python
from app.services.retrieval_service import RetrievalService
```

**修改位置 3：新增 query 路由**

- 文件：`app/main.py`
- 定位：搜索旧接口装饰器 `@app.post("/upload", response_model=UploadResponse)`。
- 操作：在该装饰器之前插入下面完整路由；不要把它缩进到前一个函数内，也不要删除旧接口。

**复制下面的完整代码**

```python
@app.post(
    "/knowledge-bases/{knowledge_base_id}/query",
    response_model=KnowledgeBaseQueryResponse,
)
async def query_knowledge_base(
    knowledge_base_id: int,
    request: KnowledgeBaseQueryRequest,
    session: DatabaseSession,
) -> KnowledgeBaseQueryResponse:
    retrieval_service = RetrievalService(
        session=session,
        embedding_service=embedding_service,
    )
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
    )

    try:
        result = await service.answer(
            knowledge_base_id=knowledge_base_id,
            question=request.question,
            top_k=request.top_k,
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
    except RAGConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="大模型服务未配置",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="问答上游服务暂时不可用",
        ) from exc

    return KnowledgeBaseQueryResponse(
        answer=result.answer,
        refused=result.refused,
        sources=[
            KnowledgeBaseQuerySource(
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                filename=source.filename,
                page_number=source.page_number,
                chunk_index=source.chunk_index,
                content=source.content,
                score=round(source.score, 6),
            )
            for source in result.sources
        ],
    )
```

**这段代码怎样工作**

- 输入：路径中的知识库 ID，以及 JSON 请求体中的问题和 `top_k`。
- 输出：HTTP 200 的正常回答或业务拒答；输入与外部依赖失败使用明确非 200 状态。
- 调用谁：每次请求创建绑定当前 Session 的 RetrievalService，再交给 DatabaseRAGService 编排。
- 被谁调用：Swagger、PowerShell/httpx 客户端或后续前端。
- 正常路径：来源字段直接从 `ChunkSearchResult` 显式映射，分数只在 HTTP 边界四舍五入到 6 位，不影响阈值判断。
- 失败路径：知识库不存在为 404；空白问题为 400；结构或 `top_k` 校验失败为 422；LLM 配置缺失为 503；LLM 上游失败为 502。
- 事务边界：query 只执行查询，不调用 `commit()`；请求结束后 `get_db_session()` 自动关闭 Session。今天不吞掉数据库异常，统一异常加固留到 Day 8。

**完成本步骤后的预期状态**

Swagger 出现 `POST /knowledge-bases/{knowledge_base_id}/query`；旧接口仍存在；新接口既能返回可追溯回答，也能把无证据结果作为明确拒答返回。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成 migration，也不执行 downgrade；Day 7 只读取 Day 2 已建立的表和 Day 4 已写入的 Chunk。对有数据的学习数据库做无关回滚反而会破坏当前 ready 文档。

### 1. 检查当前状态

执行目录：项目根目录。先保护工作区边界，再确认数据库服务、迁移和连接状态；命令不会打印真实密码。

```powershell
git status --short
docker compose config --services
docker compose ps
alembic current
python -c "from app.db import check_database_connection; print({'database_probe': check_database_connection()})"
```

预期：除今天计划文件和自己正在实现的三个代码文件外没有无关改动；服务列表包含 `postgres`；数据库健康；revision 包含 `e780fe92751b (head)`；连接探针返回 1。

若失败：先运行 `docker compose ps` 和 `docker compose logs postgres --tail 50`；配置缺失时只核对 `.env.example` 中的变量名，不打印 `.env` 内容。

### 2. 执行升级

这里的“升级”只指准备依赖环境和检查代码 import，不执行 schema 升级。若 PostgreSQL 尚未运行，只启动现有服务：

```powershell
docker compose up -d --wait postgres
alembic check
python -c "from app.models import KnowledgeBaseQueryResponse; from app.services.database_rag_service import DatabaseRAGService; print('day07 imports ok')"
```

预期：PostgreSQL 健康；`alembic check` 退出码为 0 并提示没有新的 upgrade operations；Python 输出 `day07 imports ok`。首次真正启动 API 时才会实例化并加载 BGE 模型。

### 3. 回滚并恢复

```powershell
git diff -- app/models.py app/main.py app/services/database_rag_service.py docs/17天每日学习/Day07.md
```

Day 7 没有 migration，所以没有数据库 downgrade/upgrade 往返；这里用限定文件的 diff 检查实现边界。不要使用会覆盖用户修改的 Git 命令，也不要删除 PostgreSQL Volume。

### 预期结果

- 数据库 revision 保持 `e780fe92751b (head)`，Day 7 不产生新 revision 文件。
- `alembic check` 不发现 ORM schema 漂移。
- 新服务和响应模型可以被 Python 正常导入。
- 未运行的命令只能视为预期结果；是否执行和记录不影响计划本身。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。先确保自己的 `.env` 中 PostgreSQL 与 LLM 配置完整，但不要在终端打印或提交真实值。打开 PowerShell 窗口 A：

```powershell
docker compose up -d --wait postgres
uvicorn app.main:app --reload
```

预期：Uvicorn 启动在 `http://127.0.0.1:8000`。首次加载 `BAAI/bge-small-zh-v1.5` 可能较慢且可能需要模型缓存；外部下载耗时不计入核心 60 分钟。保持窗口 A 运行，验证结束后按 `Ctrl+C` 停止 API。

### 执行正常请求或测试

在 PowerShell 窗口 B、项目根目录执行。脚本只使用固定依赖 httpx，在内存构造两份英文文本 PDF，不创建临时文件；随后创建唯一知识库、上传两份 ready 文档、调用数据库版 query，并用 SQLAlchemy 按返回 ID 核对真实 Document 和 Chunk。

```powershell
@'
import json
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.orm_models import Chunk, Document


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


def assert_source_matches_database(
    session: Session,
    source: dict[str, object],
) -> None:
    chunk = session.get(Chunk, source["chunk_id"])
    assert chunk is not None
    document = session.get(Document, source["document_id"])
    assert document is not None
    assert chunk.document_id == document.id
    assert document.knowledge_base_id == knowledge_base["id"]
    assert document.status == "ready"
    assert document.filename == source["filename"]
    assert chunk.page_number == source["page_number"]
    assert chunk.chunk_index == source["chunk_index"]
    assert chunk.content == source["content"]


base_url = "http://127.0.0.1:8000"
knowledge_base_name = f"day07_http_{uuid4().hex[:12]}"
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
            "description": "Day 7 database RAG verification",
        },
    )
    assert create_response.status_code == 201, create_response.text
    knowledge_base = create_response.json()

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
        assert upload_response.status_code == 201, upload_response.text
        assert upload_response.json()["document"]["status"] == "ready"

    query_response = client.post(
        f"/knowledge-bases/{knowledge_base['id']}/query",
        json={
            "question": (
                "How many working days in advance must annual leave "
                "requests be submitted?"
            ),
            "top_k": 3,
        },
    )
    print("query status:", query_response.status_code)
    print("query body:", query_response.text)
    assert query_response.status_code == 200, query_response.text
    result = query_response.json()
    assert result["refused"] is False
    assert isinstance(result["answer"], str)
    assert result["answer"].strip()
    assert result["sources"]
    assert result["sources"][0]["filename"] == (
        "employee-leave-policy.pdf"
    )
    assert "three working days" in (
        result["sources"][0]["content"].lower()
    )

with SessionLocal() as session:
    for source in result["sources"]:
        assert_source_matches_database(session, source)

print(
    json.dumps(
        {
            "knowledge_base_id": knowledge_base["id"],
            "answer": result["answer"],
            "refused": result["refused"],
            "source_count": len(result["sources"]),
            "first_source": result["sources"][0],
            "database_source_check": "passed",
        },
        ensure_ascii=False,
        indent=2,
    )
)
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 7 数据库版 RAG 正常路径验证失败。"
}
```

### 预期状态码或输出结构

- 创建知识库与两次上传：HTTP 201，两份 Document 均为 `ready`。
- 数据库版 query：HTTP 200，`refused` 为 `false`，`answer` 非空，`sources` 至少一条。
- 第一条来源预期是 `employee-leave-policy.pdf`，原文包含 `three working days`。
- SQLAlchemy 回查：每个响应来源的 Chunk、Document、知识库、页码、序号和原文都与 PostgreSQL 记录一致。
- ID、时间戳、实际分数、回答措辞和来源数量是动态值。

```json
{
  "answer": "动态生成的非空回答",
  "refused": false,
  "sources": [
    {
      "chunk_id": "动态正整数",
      "document_id": "动态正整数",
      "filename": "employee-leave-policy.pdf",
      "page_number": 1,
      "chunk_index": 0,
      "content": "Annual leave requests must be submitted three working days in advance.",
      "score": "动态浮点数，预期大于等于 0.55"
    }
  ]
}
```

### 为什么它能证明今天已经完成

脚本从 HTTP 外部创建知识库并上传两份 PDF，再通过新 query 入口完成 pgvector 检索、阈值筛选与 LLM 生成；最后绕过 API 用 SQLAlchemy 按返回 ID 回查数据库，证明来源不是 API 层虚构，也证明结果属于指定知识库中的 ready 文档。

## 八、验证失败和边界路径

### 场景：空知识库早拒答、空白问题、知识库不存在，以及低分时绝不调用 LLM

执行目录：项目根目录，API 保持运行。第一段脚本验证 HTTP 契约；第二段纯内存脚本用一个“调用即失败”的 LLM 替身，确定低分分支没有触发模型调用。

```powershell
@'
from uuid import uuid4

import httpx


base_url = "http://127.0.0.1:8000"
name = f"day07_empty_{uuid4().hex[:12]}"

with httpx.Client(base_url=base_url, timeout=300.0) as client:
    create_response = client.post(
        "/knowledge-bases",
        json={"name": name, "description": "empty boundary"},
    )
    assert create_response.status_code == 201, create_response.text
    knowledge_base_id = create_response.json()["id"]

    refusal_response = client.post(
        f"/knowledge-bases/{knowledge_base_id}/query",
        json={
            "question": "What is the stock option policy?",
            "top_k": 3,
        },
    )
    print("refusal:", refusal_response.status_code, refusal_response.text)
    assert refusal_response.status_code == 200
    refusal = refusal_response.json()
    assert refusal == {
        "answer": "当前知识库中没有找到足够的信息。",
        "refused": True,
        "sources": [],
    }

    blank_response = client.post(
        f"/knowledge-bases/{knowledge_base_id}/query",
        json={"question": "   ", "top_k": 3},
    )
    print("blank:", blank_response.status_code, blank_response.text)
    assert blank_response.status_code == 400
    assert blank_response.json()["detail"] == "question 不能为空"

    missing_response = client.post(
        "/knowledge-bases/2147483647/query",
        json={"question": "Does this knowledge base exist?", "top_k": 3},
    )
    print("missing:", missing_response.status_code, missing_response.text)
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "知识库不存在"
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 7 HTTP 失败与边界路径验证失败。"
}
```

继续执行低分早拒答的确定性检查：

```powershell
@'
import asyncio

from app.repositories.chunk_repository import ChunkSearchResult
from app.services.database_rag_service import (
    DatabaseRAGService,
    REFUSAL_ANSWER,
)


class LowScoreRetrievalService:
    def search(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int,
    ) -> list[ChunkSearchResult]:
        return [
            ChunkSearchResult(
                chunk_id=1,
                document_id=1,
                knowledge_base_id=knowledge_base_id,
                filename="unrelated.pdf",
                page_number=1,
                chunk_index=0,
                content="This content is unrelated to the question.",
                score=0.10,
            )
        ]


class MustNotCallLLMService:
    async def chat(self, message: str) -> str:
        raise AssertionError("低分拒答分支不应该调用 LLM")


async def main() -> None:
    service = DatabaseRAGService(
        retrieval_service=LowScoreRetrievalService(),
        llm_service=MustNotCallLLMService(),
    )
    result = await service.answer(
        knowledge_base_id=1,
        question="What is the stock option policy?",
        top_k=3,
    )
    assert result.answer == REFUSAL_ANSWER
    assert result.refused is True
    assert result.sources == []
    print("low-score early refusal passed; LLM was not called")


asyncio.run(main())
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 7 低分早拒答验证失败。"
}
```

### 预期结果

- 空知识库：HTTP 200；`answer` 为固定拒答文案；`refused=true`；`sources=[]`。
- 空白问题：HTTP 400；detail 只说明 `question 不能为空`。
- 不存在知识库：HTTP 404；detail 为 `知识库不存在`。
- 人工低分来源：脚本退出码 0，并输出 `LLM was not called`；如果业务代码错误调用 LLM，替身会抛 `AssertionError`。
- 数据库应该保留：边界脚本显式创建的空知识库，以及此前正常路径创建的 ready Document/Chunk。
- 数据库不应该存在：空知识库下不应新增 Document 或 Chunk；query 本身不写入任何业务表。
- 响应不能泄露：LLM API Key、数据库密码、连接 URL、SQL、Python traceback、上游完整响应体或内部异常堆栈。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| 启动时报 `No module named app.services.database_rag_service` | 新文件路径或文件名写错，或从错误目录启动 | `rg --files app/services`；确认当前目录是项目根目录 | 把完整文件保存为 `app/services/database_rag_service.py`，再从项目根目录运行 Uvicorn。 |
| Swagger 没有新的 query 路由 | 路由缩进到了上一函数内、放在 `app` 创建前，或服务未重载 | `rg -n "knowledge-bases.*query|query_knowledge_base" app/main.py` | 把完整路由放在模块顶层、旧 `/upload` 之前；保存后查看 Uvicorn 重载日志。 |
| 请求返回 422 | `question` 缺失/为空字符串/过长，或 `top_k` 不在 1～20 | 查看响应 `detail`；核对 `KnowledgeBaseQueryRequest` | 按模型发送 `{"question":"非空问题","top_k":3}`；不要放宽 Day 5 的边界。 |
| 明明有文档却返回拒答 | Document 不是 `ready`、知识库 ID 错误、Embedding 检索不相关，或 `0.55` 对当前数据过高 | 先调用文档列表；运行 `RetrievalService.search()` 打印不含秘密的 filename/page/score | 修正知识库或文档状态；若是阈值问题先记录分数，不在 Day 7 随意反复调参，Day 11 用固定评测集决定。 |
| 相关问题返回 503 | `.env` 中 `LLM_API_KEY`、`LLM_BASE_URL` 或 `LLM_MODEL` 至少一项为空 | 只运行 `python -c "from app.services.llm_service import LLMService; print(LLMService().is_configured())"` | 在本机补齐自己的 LLM 配置；不要打印值，不要提交 `.env`。 |
| query 返回 502 | LLM 超时、网络不可达、上游状态异常或响应结构变化 | 查看 Uvicorn 的安全错误摘要；检查 `app/services/llm_service.py` | 确认上游服务可访问、模型名正确；不要把上游响应体或 Key 放进 HTTP detail。 |
| 来源分数导致响应校验错误 | 没有在 HTTP 边界 round，或自行改变了 pgvector 距离/相似度公式 | `app/repositories/chunk_repository.py` 的 `score=1.0-float(distance)`；query 映射代码 | 保留余弦相似度定义，并在构造 `KnowledgeBaseQuerySource` 时 `round(source.score, 6)`。 |
| 返回了其他知识库或 failed 文档 | Day 5 Repository 的知识库/状态过滤被误删 | `rg -n "KnowledgeBase.id ==|Document.status ==" app/repositories/chunk_repository.py` | 恢复两项 where 条件；不要在 RAG Service 中事后用 Python 代替数据库范围过滤。 |
| 第一次 query 很慢 | 全局 EmbeddingService 首次加载 BGE 模型，或首次请求触发模型缓存 | 查看 Uvicorn 日志；核对 `MODEL_NAME` | 等待首次加载完成；不要改向量维度或使用随机向量绕过。 |
| query 后 Session 没有 commit | query 是纯读操作，这是预期行为 | `app/main.py` 的 `query_knowledge_base()` 与 `app/db.py` 的 `get_db_session()` | 不为只读查询增加 commit；请求结束由依赖关闭 Session。事务/数据库异常统一加固留到 Day 8。 |

## 十、检查最终代码差异

执行目录：项目根目录。只检查今天四个明确文件：

```powershell
git status --short
git diff -- app/models.py app/main.py app/services/database_rag_service.py docs/17天每日学习/Day07.md
```

重点检查：

- `app/models.py` 只追加三个数据库版查询模型，旧请求/响应模型仍在。
- 新文件完整包含阈值、固定拒答文本、结果 dataclass、早拒答和 Context 构造，不含关键省略、TODO 或秘密。
- `app/main.py` 只增加 import 与一个 query 路由，没有删除旧知识库、上传和 FAISS 路由。
- `RAGConfigurationError` 的 catch 位于一般 `RuntimeError` 之前，503 不会被错误映射成 502。
- threshold 判断使用未 round 的原始 score；只在 HTTP 响应边界 round。
- query 没有数据库写入和无意义 commit，也没有把 LLM 或 Session 做成每请求之外的错误全局状态。
- diff 不包含 `.env`、模型缓存、数据库文件、旧学习资料或其他无关修改。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。先确认新文件路径准确：

```powershell
git status --short
git diff -- app/models.py app/main.py app/services/database_rag_service.py docs/17天每日学习/Day07.md
git add app/models.py app/main.py app/services/database_rag_service.py docs/17天每日学习/Day07.md
git diff --cached -- app/models.py app/main.py app/services/database_rag_service.py docs/17天每日学习/Day07.md
git commit -m "Day7: add database-backed RAG query"
```

不要使用 `git add .`。如果实际验证发现已知失败，先修复代码再提交；不需要提交终端输出、真实配置或测试数据。

## 十二、面试高频问题与参考答案

### 问题 1：你的数据库版 RAG 从问题到回答经历了什么？

#### 30 秒参考答案

客户端调用 `POST /knowledge-bases/{id}/query`。API 校验问题和 Top-K，并用请求级 Session 创建 RetrievalService。RetrievalService 先确认知识库存在，再用 BGE 模型生成 512 维 Query Embedding，通过 ChunkRepository 在指定知识库和 ready 文档范围内做 pgvector 余弦检索。DatabaseRAGService 用固定阈值过滤证据；没有合格证据就提前拒答，有证据才构造 Context 并调用 LLM，最后返回回答与可回查的来源。

#### 继续追问：为什么不让 API 直接查询数据库并拼 Prompt？

API 应只负责 HTTP 契约和异常映射；检索逻辑已经由 RetrievalService/Repository 封装，RAG 编排属于 Service。这样阈值、拒答和 Prompt 可以脱离 HTTP 独立验证，也避免同一业务流程散落在路由函数中。

#### 回答时要引用的项目依据

- `app/main.py` 的 `query_knowledge_base()`。
- `app/services/database_rag_service.py` 的 `DatabaseRAGService.answer()`。
- `app/services/retrieval_service.py` 与 `app/repositories/chunk_repository.py`。

### 问题 2：Top-K 和检索阈值分别解决什么问题？

#### 30 秒参考答案

Top-K 控制最多从向量库取多少个候选 Chunk，主要影响 Context 长度、延迟和模型成本；阈值判断候选是否真的足够相关，主要影响拒答和幻觉。我的 Repository 先按余弦距离排序并限制 Top-K，RAG Service 再保留相似度不低于 0.55 的来源；所以向量库即使总能返回最近邻，也不会强迫系统回答。

#### 继续追问：为什么阈值是 0.55，它是最优值吗？

不是。0.55 是 Day 7 为了形成可复现闭环而固定的初始基线，不能声称最优。Day 10 建固定可回答/无答案数据集，Day 11 比较 Recall@1/3/5、MRR、拒答正确率和延迟后，才根据证据选择参数。

#### 回答时要引用的项目依据

- `app/services/database_rag_service.py` 的 `MIN_RELEVANCE_SCORE`。
- `app/repositories/chunk_repository.py` 的余弦距离和 score 转换。
- `app/services/retrieval_service.py` 的 Top-K 边界。

### 问题 3：为什么无答案时要在调用 LLM 前拒答？

#### 30 秒参考答案

没有可靠证据时调用 LLM，只会增加幻觉、延迟和成本。我的服务在检索结果为空或所有分数低于阈值时，直接返回固定拒答、`refused=true` 和空来源，不构造 Prompt，也不调用 LLM。这是成功的业务判断，不是 5xx 技术错误。

#### 继续追问：怎样证明 LLM 确实没被调用？

Day 7 的边界脚本注入一个“只要调用就抛 AssertionError”的 LLM 替身，同时让检索替身返回 0.10 的低分来源。脚本仍成功得到拒答，说明控制流在模型调用前已经短路；Day 12 再把同类断言沉淀成 pytest。

#### 回答时要引用的项目依据

- `DatabaseRAGService.answer()` 的 `if not relevant_results` 分支。
- 第八节 `MustNotCallLLMService` 可选验证脚本。
- `KnowledgeBaseQueryResponse.refused` 与空 `sources` 契约。

### 问题 4：你的回答来源为什么可信且不会跨知识库？

#### 30 秒参考答案

来源不是 LLM 生成的，而是 pgvector 查询返回的结构化字段。ChunkRepository 在 SQL 中联结 Chunk、Document 和 KnowledgeBase，同时约束目标 `knowledge_base_id` 与 `Document.status == ready`。API 返回文档 ID、文件名、页码、Chunk ID、序号、原文和分数，调用方可以直接回查数据库和 PDF 核对。

#### 继续追问：只在 Python 中对检索结果按知识库过滤可以吗？

不理想。范围过滤应该进入 SQL，让数据库从源头排除其他知识库和非 ready 文档；事后过滤既可能过取敏感数据，也会浪费 Top-K 名额，并增加误返回风险。Service 负责业务阈值，Repository 负责数据范围，这是两层不同边界。

#### 回答时要引用的项目依据

- `ChunkRepository.search_similar()` 的两个 where 条件。
- `ChunkSearchResult` 与 `KnowledgeBaseQuerySource` 的字段映射。
- 第七节按 source ID 回查 PostgreSQL 的验证脚本。

## 十三、今天的完整数据流

### 正常路径

```text
POST /knowledge-bases/{knowledge_base_id}/query
→ Pydantic 校验 question 长度和 top_k=1..20
→ FastAPI 注入请求级 SQLAlchemy Session
→ RetrievalService 先查询 KnowledgeBase
→ EmbeddingService 生成 512 维 Query Embedding
→ ChunkRepository 执行 pgvector 余弦检索
→ SQL 限定 knowledge_base_id 和 Document.status=ready
→ 返回按 score 排序的 Top-K ChunkSearchResult
→ DatabaseRAGService 过滤 score >= 0.55 的来源
→ 构造包含文档名、页码、Chunk ID 和原文的 Context
→ build_rag_prompt
→ LLMService.chat
→ KnowledgeBaseQueryResponse
→ answer + refused=false + sources
→ 请求结束关闭 Session
```

### 失败路径

```text
知识库不存在
→ RetrievalService 在生成 Query Embedding 前抛 LookupError
→ API 返回 404，不调用 LLM

问题只含空格
→ DatabaseRAGService 抛 ValueError
→ API 返回 400

无 Chunk 或所有 score < 0.55
→ DatabaseRAGService 在构造 Prompt 前短路
→ HTTP 200 + 固定拒答 + refused=true + sources=[]
→ 不调用 LLM、不写数据库

有可靠证据但 LLM 配置缺失
→ RAGConfigurationError
→ HTTP 503 + 安全 detail

LLM 超时、网络或返回格式异常
→ RuntimeError
→ HTTP 502 + 通用安全 detail
→ 不泄露 Key、连接串、上游响应体或 traceback
```

## 十四、完成标准

```text
[ ] 能解释 RetrievalService 与 DatabaseRAGService 为什么分层，以及 LLM 为什么不直接访问数据库
[ ] 能说明 Top-K 控制候选数量、threshold 控制是否回答，二者不能互相替代
[ ] app/models.py 已新增 question/top_k 请求与完整 answer/refused/sources 响应契约，同时保留旧模型
[ ] app/services/database_rag_service.py 已完成 pgvector 检索编排、0.55 阈值、早拒答、Context 和 LLM 调用
[ ] app/main.py 已新增 POST /knowledge-bases/{knowledge_base_id}/query，且旧知识库、上传和 FAISS 接口仍保留
[ ] 已提供可执行的 HTTP + PostgreSQL 正常路径命令和预期结构；实际执行与记录可选
[ ] 已提供空知识库、空白问题、不存在知识库和低分不调用 LLM 的边界命令与预期结果；实际执行与记录可选
[ ] 能不看代码复述 Question → Query Embedding → pgvector → threshold → Context → LLM → Answer + Sources
[ ] git diff 只包含今天四个明确文件，不包含 .env、秘密、测试数据或无关修改
[ ] 核心实现完成并检查暂存差异后，可执行边界清晰的 Day 7 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
