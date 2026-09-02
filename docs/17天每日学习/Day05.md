# Day 5：实现带范围过滤的 pgvector Top-K 检索

今天将直接完成一个接收知识库 ID、问题和 Top-K 的数据库检索入口，使项目能从指定知识库的 `ready` 文档中返回按相关性排序且来源完整的 Chunk，并为面试中的 pgvector 排序、数据隔离和检索边界问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：`RetrievalService.search(knowledge_base_id, question, top_k)` 与它调用的 pgvector 范围检索  
> 当前真实状态：已完成  
> 对应总体安排：Day 5

## 一、今天完成后的项目变化

### 升级前

```text
问题
→ EmbeddingService 可以生成 512 维 Query Embedding
→ 现有 RAGService 只能调用进程内 FAISSVectorStore
→ PostgreSQL 已保存 KnowledgeBase / Document / Chunk / Vector
→ ChunkRepository 只能批量写入或按 document_id 列出 Chunk
→ 没有按 knowledge_base_id 和 Document.status 限定范围的 pgvector 查询
```

### 升级后

```text
knowledge_base_id + question + top_k
→ RetrievalService 校验问题、Top-K 和知识库是否存在
→ EmbeddingService.embed_query() 生成 512 维 Query Embedding
→ ChunkRepository 在同一条 SQL 中联结 Chunk / Document / KnowledgeBase
→ WHERE KnowledgeBase.id = 指定知识库
→ AND Document.status = 'ready'
→ ORDER BY Chunk.embedding <=> Query Embedding ASC
→ LIMIT top_k
→ 把 cosine distance 转成 score = 1 - distance
→ 返回 Chunk ID、Document ID、知识库 ID、文件名、页码、顺序、原文和分数
```

今天不调用 LLM，也不改现有 `/rag/chat`；数据库版回答编排属于 Day 7，HTTP 管理接口属于 Day 6。

### 今天在完整项目中的位置

- 所属阶段：核心 MVP。
- 所属链路：用户问答链路中的检索阶段。
- 今天的输入：Day 4 已持久化的 `Chunk.embedding`、用户问题、指定 `knowledge_base_id` 和 `top_k`。
- 今天的输出：只来自指定知识库 `ready` 文档的有序 `ChunkSearchResult` 列表。
- 下一天为什么需要它：Day 6 可以继续开放知识库和文档管理入口；Day 7 可以直接把今天的检索结果组装为 Context 和来源。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 4 的计划均有用户完成标记，Git 历史存在匹配提交 `ac14dd5`、`e156828`、`9cc6d60` 和 `ff8c529`，当前代码也保留对应核心产物。
- `[当前事实]` `app/orm_models.py` 已定义 `KnowledgeBase 1:N Document 1:N Chunk`，`Document.status` 支持 `pending/processing/ready/failed`，并有 `(knowledge_base_id, status)` 索引。
- `[当前事实]` `Chunk.embedding` 使用 `Vector(512)`；迁移 `e780fe92751b` 已定义三张业务表、外键、约束和向量字段。
- `[当前事实]` `EmbeddingService.embed_query()` 使用 `BAAI/bge-small-zh-v1.5` 的查询指令并返回归一化向量，`embed_documents()` 使用同一模型生成文档向量。
- `[当前事实]` `DocumentIngestionService` 能在成功路径写入分页 Chunk 和向量，且只有完成写入后才把文档置为 `ready`。
- `[当前事实]` 固定依赖为 SQLAlchemy 2.0.52、pgvector 0.5.0 和 psycopg 3.3.4；pgvector SQLAlchemy 列支持 `cosine_distance()` 表达式。
- `[当前事实]` 生成本计划时 `git status --short` 为空。

### 仍然缺少

- `[当前事实]` `app/repositories/chunk_repository.py` 没有相似度查询，只能写入 Chunk 或按文档顺序列出。
- `[当前事实]` 仓库中没有 `RetrievalService`、`search_similar()` 或任何使用 `Chunk.embedding.cosine_distance()` 的新架构代码。
- `[当前事实]` 当前 `app/services/rag_service.py` 仍依赖 `FAISSVectorStore`，不能按知识库或文档状态隔离结果。
- `[当前事实]` 没有稳定 DTO(Data Transfer Object) , 同时返回 Chunk、文档名、页码和 pgvector 分数。
- `[当前事实]` 当前迁移没有 HNSW/IVFFlat 近似索引；今天使用精确扫描建立正确性基线，不提前做大规模性能优化。

### 待实测

- `[待实测]` 本机 PostgreSQL 是否正在运行、当前 revision 是否为 `e780fe92751b (head)`。
- `[待实测]` 当前学习数据库是否已有至少两个知识库以及 `ready/processing/failed` 多状态文档；本计划的边界脚本会在单个事务内临时构造完整场景并回滚，因此不依赖既有数据。
- `[待实测]` 真实 BGE 模型对“年假申请”固定问题的 Top-K 排序和实际分数。
- `[待实测]` pgvector 返回的 cosine distance 经 `1 - distance` 转换后是否按预期降序展示。

### 需要保护的用户修改

- 生成本计划时工作区干净；执行时仍应先运行 `git status --short`，只处理今日文件清单，不恢复、不覆盖、不暂存后来出现的无关修改。
- 如果 `app/repositories/chunk_repository.py` 已被用户继续修改，应把 `ChunkSearchResult` 和 `search_similar()` 合并进去，不能机械覆盖额外逻辑。
- 不修改真实 `.env`、`app/main.py`、ORM、迁移、现有 FAISS Service、Day 1～Day 4 计划或数据库 Volume。

## 三、今天必须理解的核心知识

### 1. 余弦距离、余弦相似度和排序方向

- 一句话解释：pgvector 的余弦距离越小越相关，而便于展示的余弦相似度 `score = 1 - distance` 越大越相关。
- 在当前项目中的职责：Repository 用 `Chunk.embedding.cosine_distance(query_vector)` 生成 SQL 的 `<=>` 距离表达式，按距离升序取前 K 个，再转换为 score。
- 与其他组件的关系：EmbeddingService 让问题与文档使用同一 512 维语义空间；Repository 排序；RetrievalService 负责生成并校验查询向量。
- 容易混淆的点：score 不是“答案正确概率”，也不应为了看起来像概率而强制截断到 `[0, 1]`；余弦相似度理论上可为负值。
- 面试一句话：当前项目在数据库中按 cosine distance 升序检索，再返回 `1 - distance` 作为可读相似度，因此结果列表表现为 score 降序。

### 2. 过滤必须发生在 Top-K 之前

- 一句话解释：知识库和文档状态必须进入同一条 SQL 的 `WHERE`，数据库应先限定候选集合，再在合法集合中取 Top-K。
- 在当前项目中的职责：查询联结三张表，并同时限定 `KnowledgeBase.id` 与 `Document.status == "ready"`。
- 与其他组件的关系：外键保证 Chunk 能追溯到 Document 和 KnowledgeBase；状态字段决定 Document 是否有检索资格。
- 容易混淆的点：先对全库取 Top-K、再用 Python 删除越权或非 ready 结果，会造成跨知识库泄漏，而且过滤后可能不足 K 条或完全为空。
- 面试一句话：范围过滤不是展示层逻辑，而是检索候选集的安全边界，所以必须位于数据库 Top-K 之前。

### 3. Repository 与 RetrievalService 的职责边界

- 一句话解释：Repository 描述“怎样查询数据库”，Service 描述“怎样把业务输入变成一次可用检索”。
- 在当前项目中的职责：`ChunkRepository.search_similar()` 只接收已验证的向量和范围参数；`RetrievalService.search()` 清洗问题、限制 Top-K、检查知识库、调用 Embedding 并校验 512 维。
- 与其他组件的关系：调用方创建和关闭 Session；RetrievalService 不提交事务；Repository 只执行只读 SQL。
- 容易混淆的点：今天的检索 Service 不构造 Prompt、不调用 LLM、不决定拒答阈值，避免提前混入 Day 7 和 Day 11 的职责。
- 面试一句话：我把向量 SQL 封装在 Repository，把输入校验与 Query Embedding 编排放在 Service，使检索既可独立验证，也能被后续 RAG 复用。

### 4. 精确检索是小数据阶段的正确性基线

- 一句话解释：没有近似索引时，PostgreSQL 仍能对合法候选 Chunk 做精确排序，只是数据量大后扫描成本会上升。
- 在当前项目中的职责：Day 5 先证明过滤、排序和来源映射正确，不用 HNSW/IVFFlat 增加迁移和参数变量。
- 与其他组件的关系：Day 11 的评测和未来真实数据规模会决定是否值得添加近似索引。
- 容易混淆的点：索引是性能策略，不是让 `<=>` 或 `cosine_distance()` 能工作的前置条件。
- 面试一句话：当前演示数据量较小，我先用精确检索建立结果正确性基线，只有真实规模和延迟证据支持时才引入近似索引。

## 四、升级涉及的文件

| 文件                                     | 操作  | 作用                                                         |
| -------------------------------------- | --- | ---------------------------------------------------------- |
| `app/repositories/chunk_repository.py` | 修改  | 保留现有写入/列表方法，新增检索结果 DTO 和单条 SQL 的 pgvector 范围 Top-K 查询。     |
| `app/services/retrieval_service.py`    | 新建  | 校验知识库、问题和 Top-K，生成并检查 Query Embedding，调用 Chunk Repository。 |
| `docs/17天每日学习/Day05.md`                | 新建  | 保存今天可直接执行的升级、验证、排错和面试手册。                                   |

`app/repositories/__init__.py` 和 `app/services/__init__.py` 今天保持不变：RetrievalService 从具体 Repository 模块导入类型，后续调用方也从具体 Service 模块导入。

### 今日不做

- 不修改 `app/main.py`，不新增或替换 HTTP API；知识库和文档管理 API 属于 Day 6。
- 不调用 LLM、不构造 Prompt、不实现最终回答、来源响应或拒答阈值；这些属于 Day 7 和 Day 11。
- 不新增 HNSW/IVFFlat 索引，不生成 Alembic revision，不进行大规模性能调优。
- 不编写完整 pytest 回归测试集；自动化测试属于 Day 12，今天使用可复制的事务内验证脚本。
- 不删除 FAISS 文件或改变旧 `/upload`、`/rag/chat` 行为。

## 五、按顺序完成项目升级

### 步骤 1：确认 Day 5 前置接口没有漂移（建议 5 分钟）

**目标**

确认数据库字段、Embedding 契约和现有 Repository 仍与本计划一致，并再次保护执行时可能出现的用户修改。

**修改位置**

- 本步骤不修改文件。
- 执行目录：项目根目录。

```powershell
git status --short
rg -n "class KnowledgeBase|class Document|class Chunk|Vector\(512\)|ix_documents_knowledge_base_id_status" app/orm_models.py
rg -n "def embed_query|QUERY_INSTRUCTION|normalize_embeddings=True" app/services/embedding_service.py
rg -n "class ChunkRepository|def bulk_create|def list_by_document|cosine_distance|search_similar" app/repositories/chunk_repository.py
rg -n "class RetrievalService|def search" app/services
```

预期结果：ORM 和 Embedding 定位命令有输出；最后两组只能看到现有 Chunk 方法，尚未看到 `cosine_distance`、`search_similar` 或 `RetrievalService`。如果执行时已经出现这些实现，先保留它们并逐项与下面的数据范围、排序和返回字段契约合并。

### 步骤 2：给 Chunk Repository 增加范围 Top-K 查询（建议 20 分钟）

**目标**

在一条 SQL 中完成三表联结、知识库过滤、`ready` 状态过滤、余弦距离排序和 Top-K 限制，并返回稳定的来源 DTO。

**修改位置**

- 文件：`app/repositories/chunk_repository.py`
- 定位：搜索文件开头的 `from collections.abc import Sequence` 和 `class ChunkRepository`。
- 操作：先核对并保留自己的额外修改，然后用下面内容替换当前完整文件。

**复制下面的完整代码**

```python
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Chunk, Document, KnowledgeBase


@dataclass(frozen=True)
class ChunkCreate:
    page_number: int
    chunk_index: int
    content: str
    embedding: list[float]


@dataclass(frozen=True)
class ChunkSearchResult:
    chunk_id: int
    document_id: int
    knowledge_base_id: int
    filename: str
    page_number: int
    chunk_index: int
    content: str
    score: float


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

    def search_similar(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[ChunkSearchResult]:
        query_vector = list(query_embedding)
        distance_expression = Chunk.embedding.cosine_distance(
            query_vector
        )

        statement = (
            select(
                Chunk.id,
                Chunk.document_id,
                Document.knowledge_base_id,
                Document.filename,
                Chunk.page_number,
                Chunk.chunk_index,
                Chunk.content,
                distance_expression.label("distance"),
            )
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .join(
                KnowledgeBase,
                Document.knowledge_base_id == KnowledgeBase.id,
            )
            .where(
                KnowledgeBase.id == knowledge_base_id,
                Document.status == "ready",
            )
            .order_by(
                distance_expression.asc(),
                Chunk.id.asc(),
            )
            .limit(top_k)
        )

        rows = self._session.execute(statement)
        results: list[ChunkSearchResult] = []

        for (
            chunk_id,
            document_id,
            result_knowledge_base_id,
            filename,
            page_number,
            chunk_index,
            content,
            distance,
        ) in rows:
            results.append(
                ChunkSearchResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    knowledge_base_id=result_knowledge_base_id,
                    filename=filename,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    content=content,
                    score=1.0 - float(distance),
                )
            )

        return results
```

**这段代码怎样工作**

- 输入：已存在的知识库 ID、经过 Service 校验的 512 维向量和正整数 `top_k`。
- 输出：按 score 从高到低等价排序的 `ChunkSearchResult`；每项都有来源定位所需的 IDs、文件名、页码、顺序和原文。
- 调用谁：SQLAlchemy 生成三表 `JOIN`、两项 `WHERE`、pgvector `<=>` 排序和 `LIMIT` SQL，由 PostgreSQL 执行。
- 被谁调用：今天新增的 `RetrievalService.search()`；Day 7 的 RAG Service 后续也应复用它。
- 正常路径：数据库先限定指定知识库和 `ready` 文档，再计算距离并取前 K 个。
- 失败路径：数据库或 SQL 执行异常原样交给 Service/调用方；Repository 不吞异常、不提交、不回滚，也不返回伪造空对象。
- `Chunk.id` 是距离相同时的稳定次级排序键，不改变主要相关性顺序。

**完成本步骤后的预期状态**

`ChunkRepository` 仍兼容 Day 3、Day 4 的写入和列表调用，同时已经具备可独立复用的 pgvector 范围检索能力。

### 步骤 3：新增检索业务 Service（建议 15 分钟）

**目标**

提供今天唯一的业务入口，把问题转换成合格的 Query Embedding，并明确区分非法输入、不存在知识库和合法空结果。

**修改位置**

- 文件：`app/services/retrieval_service.py`
- 操作：新建文件。
- 调用边界：今天由验证脚本直接调用；Day 7 再由数据库版 RAG 编排调用。

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
MAX_TOP_K = 20
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

        query_embedding = self._embedding_service.embed_query(
            cleaned_question
        )
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

- 输入：`knowledge_base_id`、去除首尾空格后非空的 `question`，以及 `1～20` 的 `top_k`。
- 输出：合法但没有 ready Chunk 的知识库返回 `[]`；不存在的知识库抛出 `LookupError`，非法问题或 Top-K 抛出 `ValueError`。
- 调用谁：先用 `KnowledgeBaseRepository.get()` 确认范围存在，再用 `EmbeddingService.embed_query()` 生成向量，最后调用 `ChunkRepository.search_similar()`。
- 被谁调用：今天的脚本；Day 7 的数据库版 RAG Service。
- 正常路径：问题向量恰好为 512 维，Repository 返回不超过 K 条有序来源。
- 失败路径：维度漂移会在发 SQL 前抛出 `RuntimeError`，不会把错误向量交给 PostgreSQL。
- 事务边界：这是只读 Service，不执行 `commit()`、`rollback()` 或 `close()`；Session 生命周期仍由调用方管理。

**完成本步骤后的预期状态**

项目获得独立于 HTTP 和 LLM 的数据库检索入口，可以直接对知识库范围、状态过滤、Top-K 和来源映射做确定性验证。

### 步骤 4：做静态检查并确认没有越界修改（建议 5 分钟）

**目标**

在连接数据库前先发现拼写、缩进或文件范围问题。

**修改位置**

- 本步骤不再修改代码，除非检查发现错误。
- 执行目录：项目根目录。

```powershell
python -c "import ast, pathlib; paths = ('app/repositories/chunk_repository.py', 'app/services/retrieval_service.py'); [ast.parse(pathlib.Path(path).read_text(encoding='utf-8')) for path in paths]; print('Day 5 Python syntax OK')"
rg -n "cosine_distance|KnowledgeBase.id|Document.status|order_by|limit" app/repositories/chunk_repository.py
rg -n "question 不能为空|MAX_TOP_K|EMBEDDING_DIMENSION|def search" app/services/retrieval_service.py
git diff -- app/repositories/chunk_repository.py app/services/retrieval_service.py
```

预期结果：Python 语法检查退出码为 `0`；定位命令能看到过滤、排序、限制和输入校验；diff 不应包含 `app/main.py`、迁移或 FAISS 改动。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成或执行新 Alembic migration；Day 2 的 `Vector(512)`、外键、状态约束和范围索引已经满足 Day 5。下面只确认现有数据库与代码基线。

### 1. 检查当前状态

执行目录：项目根目录。先确认公开 Compose 配置、数据库容器和当前 revision；命令不应打印真实密码。

```powershell
docker compose config --services
docker compose ps
alembic current
python -c "from app.db import check_database_connection; print({'database_probe': check_database_connection()})"
```

预期结果：服务列表包含 `postgres`；数据库若已运行应显示健康；Alembic 当前版本应包含 `e780fe92751b (head)`；连接探针打印 `database_probe: 1`。

如果 `postgres` 尚未运行，只启动今天依赖的数据库服务：

```powershell
docker compose up -d --wait postgres
alembic current
```

### 2. 执行升级

今天的升级是两个 Python 文件，不是 schema 升级。代码复制完成后执行只读 schema 漂移检查：

```powershell
alembic check
```

预期结果：退出码为 `0`，提示没有新的 upgrade operations；若出现建表、删表或字段变化，说明执行时意外修改了 ORM 或 metadata，不要为 Day 5 生成迁移来掩盖漂移。

### 3. 回滚并恢复

今天没有 migration 可 downgrade。第七、八节的验证数据全部放在一个未提交事务中，并在 `finally` 中调用 `session.rollback()`，因此不用删除记录或数据库 Volume。验证后再次确认 revision 未变化：

```powershell
alembic current
```

### 预期结果

- 数据库仍位于 `e780fe92751b (head)`，没有新 revision 文件。
- ORM 与迁移没有 schema 差异。
- 验证脚本退出后不会留下以 `day05_` 开头的临时知识库、Document 或 Chunk。
- 任何错误日志都不应包含真实连接 URL、密码或 `.env` 内容。

## 七、验证正常路径

### 启动或准备服务

执行目录：项目根目录。只需要 PostgreSQL，不需要启动 FastAPI 或配置 LLM。首次构造 EmbeddingService 可能下载模型，这段外部耗时不计入核心 60 分钟。

```powershell
docker compose up -d --wait postgres
alembic current
```

### 执行正常请求或测试

下面脚本使用真实 `EmbeddingService` 生成三条文档向量和一个 Query Embedding，在 PostgreSQL 的单个事务中创建 `ready` 数据并调用 `RetrievalService`。它验证返回数量、score 顺序、来源字段和最相关 Chunk，最后无论成功失败都回滚临时数据。

```powershell
@'
import json
from dataclasses import asdict
from uuid import uuid4

from app.db import SessionLocal
from app.repositories.chunk_repository import (
    ChunkCreate,
    ChunkRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


contents = [
    "员工年假申请：员工应至少提前三个工作日提交申请，由直属主管审批。",
    "机房温度应保持在二十二摄氏度，值班人员每日巡检空调设备。",
    "采购固定资产需要填写采购申请单，并经财务负责人审批。",
]

embedding_service = EmbeddingService()
document_vectors = embedding_service.embed_documents(contents)
assert all(len(vector) == 512 for vector in document_vectors)

with SessionLocal() as session:
    try:
        knowledge_base = KnowledgeBaseRepository(session).create(
            name=f"day05_normal_{uuid4().hex[:12]}",
            description="Day 5 normal retrieval verification",
        )
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            filename="day05-employee-policy.pdf",
            status="ready",
        )
        ChunkRepository(session).bulk_create(
            document_id=document.id,
            chunks=[
                ChunkCreate(
                    page_number=index + 1,
                    chunk_index=index,
                    content=content,
                    embedding=vector,
                )
                for index, (content, vector) in enumerate(
                    zip(contents, document_vectors)
                )
            ],
        )

        results = RetrievalService(
            session=session,
            embedding_service=embedding_service,
        ).search(
            knowledge_base_id=knowledge_base.id,
            question="员工申请年假需要提前多久？",
            top_k=2,
        )

        assert len(results) == 2
        assert all(
            result.knowledge_base_id == knowledge_base.id
            for result in results
        )
        assert all(
            result.document_id == document.id
            for result in results
        )
        assert results[0].score >= results[1].score
        assert "年假" in results[0].content

        print(
            json.dumps(
                {
                    "knowledge_base_id": knowledge_base.id,
                    "result_count": len(results),
                    "results": [
                        {
                            **asdict(result),
                            "score": round(result.score, 6),
                        }
                        for result in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        session.rollback()
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 5 正常路径验证失败。"
}
```

### 预期状态码或输出结构

今天尚未接入 HTTP，因此以 Python 进程退出码 `0` 和真实数据库查询结果为准。动态 ID 和实际分数不能预先固定，稳定结构如下：

```json
{
  "knowledge_base_id": "动态正整数",
  "result_count": 2,
  "results": [
    {
      "chunk_id": "动态正整数",
      "document_id": "动态正整数",
      "knowledge_base_id": "与顶层动态 ID 相同",
      "filename": "day05-employee-policy.pdf",
      "page_number": 1,
      "chunk_index": 0,
      "content": "包含年假申请规则的原文",
      "score": "动态浮点数，且不小于下一条"
    }
  ]
}
```

### 为什么它能证明今天已经完成

脚本没有调用 FAISS，而是把真实 512 维向量写入 PostgreSQL 当前事务，再通过 `RetrievalService → ChunkRepository → pgvector` 取回结果；断言同时覆盖了 Query Embedding、Top-K 上限、相关性顺序和来源映射。`finally` 回滚只撤销临时验证数据，不影响已有业务数据。

## 八、验证失败和边界路径

### 场景：高相似度 Chunk 属于其他知识库或非 ready 文档

执行目录：项目根目录。下面使用确定性的 512 维单位向量，把“错误知识库”“processing”“failed”三条 Chunk 都设置成与 Query 完全相同；如果过滤发生在 Top-K 之后，它们极易进入结果。正确实现必须只返回目标知识库中两份 `ready` 文档，并让完全相同向量排在正交向量之前；同时验证空知识库返回 `[]`、`top_k=0` 被拒绝。所有临时数据最终回滚。

```powershell
@'
import json
from uuid import uuid4

from app.db import SessionLocal
from app.repositories.chunk_repository import (
    ChunkCreate,
    ChunkRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.retrieval_service import RetrievalService


def unit_vector(axis: int) -> list[float]:
    vector = [0.0] * 512
    vector[axis] = 1.0
    return vector


class FixedEmbeddingService:
    def embed_query(self, query: str) -> list[float]:
        return unit_vector(0)


with SessionLocal() as session:
    try:
        suffix = uuid4().hex[:12]
        knowledge_bases = KnowledgeBaseRepository(session)
        documents = DocumentRepository(session)
        chunks = ChunkRepository(session)

        target_kb = knowledge_bases.create(
            name=f"day05_target_{suffix}",
            description="Day 5 filter target",
        )
        other_kb = knowledge_bases.create(
            name=f"day05_other_{suffix}",
            description="Day 5 cross-KB boundary",
        )
        empty_kb = knowledge_bases.create(
            name=f"day05_empty_{suffix}",
            description="Day 5 empty result boundary",
        )

        ready_exact = documents.create(
            target_kb.id,
            "target-ready-exact.pdf",
            status="ready",
        )
        ready_orthogonal = documents.create(
            target_kb.id,
            "target-ready-orthogonal.pdf",
            status="ready",
        )
        processing = documents.create(
            target_kb.id,
            "target-processing.pdf",
            status="processing",
        )
        failed = documents.create(
            target_kb.id,
            "target-failed.pdf",
            status="failed",
        )
        other_ready = documents.create(
            other_kb.id,
            "other-ready.pdf",
            status="ready",
        )

        cases = [
            (ready_exact, "目标库 ready 完全相同向量", unit_vector(0)),
            (ready_orthogonal, "目标库 ready 正交向量", unit_vector(1)),
            (processing, "目标库 processing 完全相同向量", unit_vector(0)),
            (failed, "目标库 failed 完全相同向量", unit_vector(0)),
            (other_ready, "其他库 ready 完全相同向量", unit_vector(0)),
        ]

        for document, content, embedding in cases:
            chunks.bulk_create(
                document_id=document.id,
                chunks=[
                    ChunkCreate(
                        page_number=1,
                        chunk_index=0,
                        content=content,
                        embedding=embedding,
                    )
                ],
            )

        service = RetrievalService(
            session=session,
            embedding_service=FixedEmbeddingService(),
        )
        results = service.search(
            knowledge_base_id=target_kb.id,
            question="固定查询",
            top_k=5,
        )

        expected_document_ids = {
            ready_exact.id,
            ready_orthogonal.id,
        }
        assert len(results) == 2
        assert {result.document_id for result in results} == (
            expected_document_ids
        )
        assert results[0].document_id == ready_exact.id
        assert abs(results[0].score - 1.0) < 0.000001
        assert abs(results[1].score - 0.0) < 0.000001

        empty_results = service.search(
            knowledge_base_id=empty_kb.id,
            question="固定查询",
            top_k=5,
        )
        assert empty_results == []

        try:
            service.search(
                knowledge_base_id=target_kb.id,
                question="固定查询",
                top_k=0,
            )
        except ValueError as exc:
            top_k_error = str(exc)
        else:
            raise AssertionError("top_k=0 应被拒绝")

        print(
            json.dumps(
                {
                    "returned_filenames": [
                        result.filename for result in results
                    ],
                    "returned_scores": [
                        round(result.score, 6) for result in results
                    ],
                    "excluded_filenames": [
                        processing.filename,
                        failed.filename,
                        other_ready.filename,
                    ],
                    "empty_knowledge_base_result": empty_results,
                    "invalid_top_k_error": top_k_error,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        session.rollback()
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Day 5 范围与状态过滤验证失败。"
}
```

### 预期结果

- HTTP 状态码或异常：今天未接 HTTP；脚本退出码为 `0`，`top_k=0` 单独得到 `ValueError: top_k 必须在 1 到 20 之间`。
- 检索应该返回：仅 `target-ready-exact.pdf` 和 `target-ready-orthogonal.pdf`，分数依次约为 `1.0`、`0.0`。
- 检索不应该返回：目标知识库中的 `processing`/`failed` 文档，以及其他知识库中即使相似度更高的 `ready` 文档。
- 空知识库：返回明确的空列表 `[]`，不抛异常，也不伪造来源。
- 数据库应该保留：脚本运行前已有的业务数据保持不变。
- 数据库不应该存在：脚本退出后任何 `day05_target_`、`day05_other_`、`day05_empty_` 临时记录，因为同一事务已回滚。
- 响应不能泄露：真实数据库连接 URL、密码、环境变量、SQL 堆栈、模型缓存路径或其他知识库内容。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| 导入检索 Service 时提示缺少 `POSTGRES_*` | `app.db` 在创建 Engine 前发现必需配置为空，或命令不在项目根目录执行 | `rg -n "POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD" app/config.py app/db.py .env.example` | 在本机 `.env` 或当前进程环境中填写自己的值；不要把真实值复制进计划、日志或 Git。 |
| `docker compose up --wait postgres` 超时 | Docker Desktop 未运行、映射端口冲突或数据库健康检查失败 | `docker compose ps`；`docker compose logs postgres --tail 50` | 启动 Docker Desktop，核对 `docker-compose.yml` 的端口和健康检查；不要删除 Volume。 |
| `AttributeError`：Vector 列没有 `cosine_distance` | 使用了错误的列类型、导入了非 pgvector Vector，或实际环境依赖没有按 `requirements.txt` 安装 | `rg -n "from pgvector.sqlalchemy import Vector|Vector\(512\)" app/orm_models.py requirements.txt` | 保持 `Chunk.embedding` 为 `pgvector.sqlalchemy.Vector(512)`，确认当前环境使用固定的 pgvector 0.5.0；不要改成字符串列。 |
| PostgreSQL 报向量维度错误 | Query Embedding 不是 512 维，或绕过了 Service 直接调用 Repository | `rg -n "EMBEDDING_DIMENSION|_validate_query_embedding|Vector\(512\)" app/services/retrieval_service.py app/orm_models.py` | 通过 RetrievalService 调用，保留发 SQL 前的 512 维校验；不要截断或补零真实模型向量。 |
| 最相关结果排在最后 | 把 cosine distance 当成 similarity 做降序，或返回 score 时没有执行 `1 - distance` | `app/repositories/chunk_repository.py` 的 `order_by()` 和 `score=` | 距离使用 `.asc()`；展示 score 使用 `1.0 - float(distance)`，并验证 score 为降序。 |
| 返回了其他知识库或非 ready 文档 | 在 Python 中事后过滤，或 `WHERE` 缺少知识库/状态条件 | `rg -n "KnowledgeBase.id|Document.status|where" app/repositories/chunk_repository.py` | 把两个条件都保留在执行 `ORDER BY/LIMIT` 的同一条 SQL 中，不能先全库 Top-K 再过滤。 |
| 明明有 Chunk 却返回空列表 | 查询使用了错误知识库 ID，或对应 Document 不是 `ready` | 使用 `DocumentRepository.list_by_knowledge_base()` 查看 ID 与 status；核对入库结果 | 使用正确的动态 ID；只有 Day 4 成功置为 `ready` 的文档有检索资格，不能放宽状态过滤掩盖入库失败。 |
| 真实语义验证首次运行很慢 | BGE 模型尚未缓存或当前网络不能访问模型源 | `python -c "from app.services.embedding_service import MODEL_NAME; print(MODEL_NAME)"` | 保持模型名和归一化方式不变，在网络可用时完成首次下载；边界脚本可先验证 SQL，但不能用随机向量冒充语义检索结果。 |
| `alembic check` 提示新增或删除表字段 | 执行 Day 5 时误改了 ORM 或 metadata | `git diff -- app/orm_models.py migrations/env.py migrations/versions` | 保留用户改动并核对来源；Day 5 不应生成 migration，不要用新 revision 掩盖无关 schema 漂移。 |
| 验证后出现 `day05_` 数据 | 在脚本中增加了 `commit()`，或移除了 `finally: session.rollback()` | 搜索验证脚本中的 `commit`、`rollback` | 恢复单事务与 finally rollback；不要为了清理而批量删除表数据或 Volume。 |

## 十、检查最终代码差异

执行目录：项目根目录。新文件在暂存前不会出现在普通 `git diff` 内容中，因此同时查看状态与两个新文件的完整内容。

```powershell
git status --short
Get-Content -Path app/repositories/chunk_repository.py
Get-Content -Path app/services/retrieval_service.py
Get-Content -Path docs/17天每日学习/Day05.md
git diff -- app/repositories/chunk_repository.py app/services/retrieval_service.py docs/17天每日学习/Day05.md
```

重点检查：

- 只有 `app/repositories/chunk_repository.py`、`app/services/retrieval_service.py` 和 `docs/17天每日学习/Day05.md` 属于今天的提交范围。
- `bulk_create()` 与 `list_by_document()` 没有被删改坏，Day 4 入库仍可调用。
- 知识库 ID 与 `ready` 状态位于 `ORDER BY/LIMIT` 同一条 SQL 的 `WHERE` 中。
- 距离升序、score 转换和稳定次级排序方向一致。
- 返回 DTO 包含 Chunk ID、Document ID、知识库 ID、文件名、页码、顺序、原文和分数。
- RetrievalService 不导入 FastAPI、不调用 LLM、不提交或关闭 Session。
- 没有 ORM、migration、`app/main.py`、FAISS、真实 `.env` 或无关文件差异。
- 未运行内容仍只写“预期结果”，没有伪造数据库、模型、HTTP、pytest 或提交结果。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供验收结果。如果用户选择运行验证并发现已知失败，应先修复失败再提交。

```powershell
git add app/repositories/chunk_repository.py app/services/retrieval_service.py docs/17天每日学习/Day05.md
git diff --cached -- app/repositories/chunk_repository.py app/services/retrieval_service.py docs/17天每日学习/Day05.md
git commit -m "feat: add scoped pgvector retrieval"
```

不要使用 `git add .`。如果 `git status --short` 还有其他文件，让它们保留在工作区，不加入本次提交。

## 十二、面试高频问题与参考答案

### 问题 1：pgvector 中 cosine distance 和返回给业务的 score 有什么区别？

#### 30 秒参考答案

当前项目使用 `Chunk.embedding.cosine_distance(query_vector)`，数据库实际按 `<=>` 余弦距离升序排序，距离越小越相关。为了让调用方更直观，我返回 `score = 1 - distance`，因此列表中的 score 越大越相关。这个 score 只是向量相似度，不是答案正确概率，也可能在语义相反时出现负值。

#### 继续追问：为什么文档和问题都做归一化？

`EmbeddingService` 对文档和 Query 都使用 `normalize_embeddings=True`，能让旧 FAISS 的内积与余弦相似度行为更一致，也让向量尺度不主导比较。pgvector 的余弦距离本身按向量夹角计算，但入库和查询仍必须保持相同模型、维度和预处理方式。

#### 回答时要引用的项目依据

- `app/services/embedding_service.py` 的 `embed_query()`、`embed_documents()` 和归一化参数。
- `app/repositories/chunk_repository.py` 的 `cosine_distance()`、升序排序和 `1 - distance`。
- `app/orm_models.py` 的 `Vector(512)`。

### 问题 2：为什么知识库和 ready 状态过滤必须在 SQL 中、并且发生在 LIMIT 之前？

#### 30 秒参考答案

Top-K 的候选集合本身就是权限和业务边界。当前查询先联结 Chunk、Document、KnowledgeBase，在 `WHERE` 中限定目标知识库和 `ready` 状态，再对合法候选做距离排序和 LIMIT。若先全库 Top-K 再在 Python 中过滤，既可能把其他知识库内容带出数据库，也可能让非法结果占满 K 个名额，最终返回不足或错误来源。

#### 继续追问：为什么仅依赖 Service 已检查知识库存在还不够？

存在性检查只说明目标知识库有效，不能约束每条 Chunk 属于它。真正的数据隔离仍要由检索 SQL 沿外键关系过滤；Repository 是所有调用方共享的数据访问边界，不能依赖上层“记得过滤”。

#### 回答时要引用的项目依据

- `ChunkRepository.search_similar()` 的两次 JOIN、两项 WHERE、ORDER BY 和 LIMIT 顺序。
- `app/orm_models.py` 的 KnowledgeBase → Document → Chunk 外键关系。
- 第八节中相同向量的跨知识库和非 ready 边界脚本。

### 问题 3：RetrievalService 和 ChunkRepository 各负责什么？

#### 30 秒参考答案

RetrievalService 接收业务输入，负责问题清洗、Top-K 边界、知识库存在性、Query Embedding 和 512 维契约；ChunkRepository 只负责把已验证参数转换成数据库查询并映射结果。这样 pgvector SQL 不会散落到 API 或 RAG 编排中，后续 Day 7 可以直接复用检索 Service，而脚本也能在不启动 HTTP、LLM 的情况下验证它。

#### 继续追问：只读 Service 为什么仍然接收 Session？

Repository 需要用 Session 执行 ORM/SQL。Session 由调用方创建并关闭，Service 与其内部 Repository 共用它，但只读检索不取得事务提交权；测试可以利用同一个 Session 查询尚未提交的临时数据，并在最后整体回滚。

#### 回答时要引用的项目依据

- `app/services/retrieval_service.py` 的校验和调用顺序。
- `app/repositories/chunk_repository.py` 的纯数据访问逻辑。
- 第七、八节的 `with SessionLocal()` 与 `finally: session.rollback()`。

### 问题 4：空知识库、不存在的知识库和没有足够证据有什么区别？

#### 30 秒参考答案

不存在的知识库是资源错误，当前 RetrievalService 抛出 `LookupError`；存在但没有 ready Chunk 的知识库是合法空集合，返回 `[]`。至于“已有检索结果但证据是否足够”，需要结合相似度阈值和固定评测决定，属于后续数据库版 RAG 与参数实验，Day 5 不把空结果伪造成答案，也不提前写死拒答阈值。

#### 继续追问：未来 API 应怎样映射这些结果？

Day 6/7 可以把不存在资源映射成 404，把非法问题或 Top-K 映射成 400/422；合法空检索由 RAG 层生成明确拒答，而不是让 LLM 在没有 Context 时自由发挥。具体契约要由后续当天计划固定，今天保持内部 Service 语义清楚。

#### 回答时要引用的项目依据

- `RetrievalService.search()` 的 `LookupError`、`ValueError` 和空列表行为。
- 第八节的 `empty_knowledge_base_result` 断言。
- 总体安排中 Day 7 的拒答与来源契约。

### 问题 5：为什么今天不创建 HNSW 或 IVFFlat 索引？

#### 30 秒参考答案

今天的唯一目标是建立范围正确、排序可解释的检索基线，当前演示数据量小，精确扫描足够。近似索引会引入召回损失、索引参数、额外迁移和实验变量；应该先在 Day 11 获得真实 Recall、MRR 和延迟，再判断数据规模是否值得用 HNSW/IVFFlat，而不是为了展示技术数量提前优化。

#### 继续追问：没有向量索引，查询还能使用 `<=>` 吗？

可以。`Vector(512)` 和 pgvector 扩展已经提供余弦距离运算，索引只影响候选搜索性能和近似策略，不是运算符能工作的前提。当前 SQL 仍会在过滤后的候选集合上计算距离并精确排序。

#### 回答时要引用的项目依据

- `migrations/versions/e780fe92751b_create_core_rag_tables.py` 只有普通范围/来源索引，没有 HNSW/IVFFlat。
- `ChunkRepository.search_similar()` 的精确距离排序。
- 总体安排 Day 5 的“今日不做”和 Day 11 的参数实验。

## 十三、今天的完整数据流

### 正常路径

```text
调用方创建 Session
→ RetrievalService.search(knowledge_base_id, question, top_k)
→ 清洗 question，校验 top_k 在 1～20
→ KnowledgeBaseRepository.get() 确认知识库存在
→ EmbeddingService.embed_query() 加查询指令并生成归一化 512 维向量
→ RetrievalService 校验 Query Embedding 维度
→ ChunkRepository.search_similar()
→ JOIN Chunk → Document → KnowledgeBase
→ WHERE 指定 knowledge_base_id AND Document.status = 'ready'
→ ORDER BY cosine distance ASC、Chunk.id ASC
→ LIMIT top_k
→ score = 1 - distance
→ 返回带完整来源元数据的 ChunkSearchResult[]
→ 调用方关闭 Session
```

### 失败路径

```text
空白 question 或 top_k 越界
→ RetrievalService 在模型和数据库检索前抛出 ValueError

不存在的 knowledge_base_id
→ KnowledgeBaseRepository.get() 返回 None
→ RetrievalService 抛出 LookupError，不查询全库

Query Embedding 不是 512 维
→ RetrievalService 抛出 RuntimeError
→ 不执行 pgvector SQL

其他知识库或 processing/failed 文档拥有更高相似度
→ SQL WHERE 在 ORDER BY/LIMIT 前排除它们
→ 只返回目标知识库 ready 文档

知识库存在但没有 ready Chunk
→ SQL 返回零行
→ Service 返回 []，不调用 LLM、不伪造来源
```

## 十四、完成标准

```text
[ ] 能解释 cosine distance 为什么升序，以及返回 score 为什么使用 1 - distance 且不是正确概率
[ ] 能解释知识库与 ready 状态过滤为什么必须和 ORDER BY/LIMIT 位于同一条 SQL
[ ] 已完整修改 app/repositories/chunk_repository.py，且保留 Day 3、Day 4 的 bulk_create() 与 list_by_document()
[ ] 已新建 app/services/retrieval_service.py，能校验问题、Top-K、知识库存在性和 512 维 Query Embedding
[ ] 检索结果包含 Chunk ID、Document ID、知识库 ID、文件名、页码、顺序、原文和 score，数量不超过 top_k
[ ] 已提供真实 Embedding + PostgreSQL 正常路径命令，预期“年假”Chunk 排首位且 score 有序；实际执行与记录可选
[ ] 已提供确定性边界命令，预期跨知识库、processing 和 failed 文档均被排除，空知识库返回 []；实际执行与记录可选
[ ] 验证数据使用单事务 finally rollback，不要求删除数据、表或数据库 Volume
[ ] 没有修改 HTTP、LLM、Prompt、拒答阈值、ORM 或 migration，没有提前实现 Day 6、Day 7、Day 11 或 Day 12
[ ] 能不看代码复述 question → Query Embedding → SQL 范围过滤 → cosine distance Top-K → 来源 DTO 的完整数据流
[ ] git diff 与暂存区只包含今天三个明确文件，不含秘密和无关修改
[ ] 核心实现完成并检查差异后可执行边界清晰的 Git commit，不要求提交验证输出
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：已完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
