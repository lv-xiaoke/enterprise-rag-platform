# Day 12：为企业 RAG 核心规则增加 pytest 回归测试

今天将直接建立覆盖 pgvector 检索隔离、来源映射、拒答和非法输入的新架构 pytest 测试集，使项目获得可重复的自动回归保护，并为面试中的测试分层、依赖替换和数据隔离问题提供可运行依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一组以真实 PostgreSQL/pgvector 集成测试和可控假依赖单元测试组成的新架构自动化测试集  
> 当前真实状态：已完成  
> 对应总体安排：Day 12

## 一、今天完成后的项目变化

### 升级前

```text
知识库隔离、ready 状态过滤、Top-K 排序
→ 主要依赖手工请求和 Day 11 评测脚本检查

RAG 来源映射、阈值拒答、非法输入
→ 已有实现，但没有自动回归测试

修改 Repository、Service 或 Pydantic 契约
→ 无法用一条固定命令快速发现关键行为回归
```

### 升级后

```text
确定性 512 维测试向量
→ 真实 PostgreSQL + pgvector 查询
→ 自动断言知识库隔离、ready 状态过滤、Top-K 数量与排序

固定检索结果 + 假 LLM
→ DatabaseRAGService
→ 自动断言来源字段、Prompt 上下文、阈值拒答和拒答时不调用 LLM

非法 question / top_k
→ KnowledgeBaseQueryRequest
→ 自动断言 Pydantic 拒绝边界输入

python -m pytest -q
→ 一条命令重复验证最关键业务规则
```

### 今天在完整项目中的位置

- 所属阶段：质量验收。
- 所属链路：文档入库与数据库版问答两条核心链路的自动回归保护。
- 今天的输入：Day 2～Day 8 已形成的 ORM、Repository、检索 Service、RAG Service、Pydantic 契约，以及 Day 11 固定下来的 Top-K/threshold 行为。
- 今天的输出：测试依赖清单、事务隔离 fixture、1 个真实 pgvector 集成测试、RAG 单元测试和输入校验测试。
- 下一天为什么需要它：Day 13 要进行多文档与重启持久化验收；自动测试先固定核心规则，才能区分代码回归和环境/重启问题。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `app/orm_models.py` 已定义 `KnowledgeBase → Document → Chunk`，Chunk 使用 `Vector(512)`。
- `[当前事实]` `app/repositories/chunk_repository.py` 的 `search_similar()` 已在 SQL 中限定知识库和 `Document.status == "ready"`，按余弦距离升序、Chunk ID 升序返回 Top-K。
- `[当前事实]` `app/services/database_rag_service.py` 已使用 `MIN_RELEVANCE_SCORE = 0.55` 做阈值过滤；无足够证据时返回固定拒答且不会进入 LLM 调用代码。
- `[当前事实]` `app/models.py` 已将 `top_k` 限定为 1～10，并通过 validator 拒绝只含空白字符的问题。
- `[当前事实]` `requirements.txt` 固定了 Python 运行依赖，其中包含 SQLAlchemy 2.0.52、pgvector 0.5.0、psycopg 3.3.4、Pydantic 2.13.4 和 FastAPI 0.141.1。
- `[当前事实]` Day 1～Day 11 的核心产物和匹配提交均存在；Day 11 对应提交为 `5663b07`，`docs/17天每日学习/Day11.md` 另有用户完成标记。

### 仍然缺少

- `[当前事实]` 仓库目前没有 `tests/` 目录，也没有任何 pytest 用例。
- `[当前事实]` `requirements.txt` 与其他依赖文件目前都没有声明 pytest。
- `[当前事实]` 知识库隔离、文档状态过滤和 pgvector 排序虽然已写入查询，但没有真实数据库自动断言。
- `[当前事实]` 来源映射、拒答时跳过 LLM 和 `question`/`top_k` 边界没有稳定测试保护。
- `[当前事实]` 当前没有明确的测试事务回滚策略。

### 待实测

- `[待实测]` 当前学习/测试 PostgreSQL 是否正在运行，Alembic 是否位于 `e780fe92751b (head)`。
- `[待实测]` `pytest==8.4.2` 是否已安装；未安装时按本计划的测试依赖文件安装。
- `[待实测]` 全套 7 个测试是否能在当前 Windows、Python 3.11 和 PostgreSQL 环境重复通过。
- `[待实测]` 集成测试成功或断言失败后，名称以 `day12-` 开头的知识库记录是否都被外层事务回滚。

### 需要保护的用户修改

- `docs/17天每日学习/Day11.md` 当前有未提交用户修改，内容包含完成标记；本计划不覆盖、不还原，也不把它放进 Day 12 的 `git add`。
- 只按今日文件清单操作，不处理其他修改；执行每一步前后都用 `git status --short` 核对边界。

## 三、今天必须理解的核心知识

### 1. 单元测试与数据库集成测试

- 一句话解释：单元测试隔离外部依赖验证一个业务单元，集成测试让多个真实组件协作以验证边界是否正确。
- 在当前项目中的职责：`DatabaseRAGService` 使用固定假检索结果和假 LLM 做单元测试；`ChunkRepository.search_similar()` 必须连接真实 PostgreSQL + pgvector，因为知识库过滤、状态过滤和向量排序都发生在 SQL 中。
- 与其他组件的关系：单元测试覆盖 Service 分支，集成测试覆盖 Repository → SQLAlchemy → psycopg → PostgreSQL/pgvector。
- 容易混淆的点：把 Repository 完全 mock 掉以后，只能证明 Service 怎样调用 mock，不能证明 SQL 的 JOIN、WHERE、ORDER BY 和 LIMIT 正确。
- 面试一句话：我把业务分支放在快速单元测试里，把只有真实 pgvector 才能证明的查询语义放在最小集成测试里。

### 2. pytest fixture 与事务隔离

- 一句话解释：fixture 统一准备测试依赖并在测试结束后可靠清理；事务隔离让测试数据可见于本次测试但不永久写入数据库。
- 在当前项目中的职责：`db_session` 在独立 Connection 上开启外层事务，把 Session 绑定到这条连接，并在 `finally` 中回滚事务和关闭连接。
- 与其他组件的关系：Repository 仍然使用真实 SQLAlchemy Session；测试只改变 Session 生命周期，不修改业务代码。
- 容易混淆的点：测试里的 `flush()` 会让当前事务查询到数据，但不等于持久化提交；PostgreSQL 序列号即使回滚也可能继续递增，所以测试绝不能断言固定 ID。
- 面试一句话：我的集成测试用真实数据库执行 SQL，但通过每用例外层事务回滚实现数据隔离，不靠批量删除清理数据。

### 3. Fake、Mock 与外部模型稳定性

- 一句话解释：Fake 是满足同一最小调用协议的可控实现，Mock 更强调调用行为验证；两者都用于替代慢、贵或不稳定的外部依赖。
- 在当前项目中的职责：`FakeRetrievalService` 固定返回来源和分数，`FakeLLMService` 记录 Prompt 并返回固定回答。
- 与其他组件的关系：测试仍执行真实 `DatabaseRAGService.answer()`、阈值判断、Context 构造和结果返回，只替换 Embedding/LLM 等外部不确定部分。
- 容易混淆的点：不调用真实 LLM 不是降低测试价值；对拒答分支而言，最重要的断言恰恰是 LLM 调用次数为 0。
- 面试一句话：回归测试断言的是可控业务契约，不把网络、模型下载和随机生成文本当成测试是否通过的条件。

### 4. 正常结果与失败结果都要断言

- 一句话解释：正常路径证明系统能工作，失败与边界路径证明系统不会悄悄做错事。
- 在当前项目中的职责：正常路径断言 Top-K 顺序和来源；边界路径断言跨知识库/非 ready 数据不会出现、低分证据会拒答、非法 `top_k` 和空白问题会校验失败。
- 与其他组件的关系：这些断言分别保护 Repository 查询边界、Service 拒答策略和 Pydantic API 契约。
- 容易混淆的点：pytest 退出码为 0 只说明现有断言通过；还要故意破坏一次关键排序断言，确认测试确实能捕获回归。
- 面试一句话：高价值测试既证明正确结果出现，也证明不属于当前知识库、状态不合法或证据不足的结果绝不会穿透边界。

## 四、升级涉及的文件

| 文件 | 操作 | 作用 |
| --- | --- | --- |
| `requirements-test.txt` | 新建 | 在不污染生产依赖职责的前提下固定 pytest 8.4.2，并复用 `requirements.txt`。 |
| `tests/conftest.py` | 新建 | 提供绑定真实数据库连接、测试结束必回滚的 SQLAlchemy Session fixture。 |
| `tests/test_chunk_repository_integration.py` | 新建 | 用真实 PostgreSQL + pgvector 验证知识库隔离、ready 状态过滤、Top-K 数量与排序。 |
| `tests/test_database_rag_service.py` | 新建 | 用可控假检索和假 LLM 验证来源映射、Context、拒答和拒答时不调用 LLM。 |
| `tests/test_models.py` | 新建 | 验证问题规范化以及空问题、`top_k=0`、`top_k=11` 被 Pydantic 拒绝。 |
| `docs/17天每日学习/Day12.md` | 新建 | 保存今日可直接执行的升级、验收、排错和面试手册。 |

### 今日不做

- 不修改 `app/` 业务代码；当前测试应先固定已有契约，测试暴露真实缺陷后再做最小修复并记录原因。
- 不追求形式上的 100% 覆盖率，也不测试无关 getter、字符串拼接工具或旧 FAISS 链路。
- 不调用真实 Embedding 模型或真实 LLM；模型质量已由 Day 11 评测，今天关注确定性回归。
- 不做多文档重启持久化验收；这是 Day 13。
- 不做 Docker 干净环境复现和 README 重写；分别属于 Day 14、Day 15。

## 五、按顺序完成项目升级

### 步骤 1：固定测试依赖（建议 5 分钟）

**目标**

建立独立测试依赖入口，让生产运行依赖和测试工具职责清楚，同时保证安装测试环境时仍复用仓库现有固定版本。

**修改位置**

- 文件：`requirements-test.txt`
- 定位：当前文件不存在。
- 操作：新建完整文件。

**复制下面的完整代码**

```text
-r requirements.txt
pytest==8.4.2
```

**这段配置怎样工作**

- 输入：项目已有 `requirements.txt`。
- 输出：完整运行依赖加固定版本 pytest 的测试环境。
- 调用谁：`python -m pip install -r requirements-test.txt` 由 pip 读取该文件，并继续读取 `requirements.txt`。
- 被谁调用：本计划的环境准备命令和后续本地/CI 测试命令。
- 正常路径：现有依赖保持原固定版本，只增加 pytest 8.4.2。
- 失败路径：若当前解释器或网络无法安装，pip 返回非 0；不要更改其他包版本掩盖错误，先确认 Python 3.11 虚拟环境和网络。

**完成本步骤后的预期状态**

仓库出现独立的测试依赖清单，`requirements.txt` 本身不需要改动。

### 步骤 2：建立每个测试必回滚的数据库 fixture（建议 10 分钟）

**目标**

让真实 pgvector 集成测试使用当前学习/测试数据库，但无论测试通过、断言失败还是抛出异常，都不留下 `day12-` 业务记录。

**修改位置**

- 文件：`tests/conftest.py`
- 定位：当前 `tests/` 目录不存在。
- 操作：新建目录和完整文件；不要创建批量清理脚本。

**复制下面的完整代码**

```python
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import engine


@pytest.fixture
def db_session() -> Iterator[Session]:
    """为单个集成测试提供真实 Session，并在结束后回滚。"""
    connection = engine.connect()
    transaction = connection.begin()
    testing_session_factory = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
    )
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
```

**这段代码怎样工作**

- 输入：`app.db.engine` 根据现有公开配置规则创建的 PostgreSQL Engine。
- 输出：每个使用 `db_session` 的测试都会得到独立 Session。
- 调用谁：fixture 调用 SQLAlchemy Engine、Connection、Transaction 和 `sessionmaker`。
- 被谁调用：`tests/test_chunk_repository_integration.py` 的集成测试参数。
- 正常路径：测试 `flush()` 后能在同一事务内执行真实 pgvector 查询，测试结束统一 rollback。
- 失败路径：即使断言失败，pytest 仍会进入生成器 fixture 的 `finally`，关闭 Session、回滚活动事务并关闭 Connection。

**完成本步骤后的预期状态**

集成测试不需要 `DELETE`、`TRUNCATE` 或删除数据库 Volume；测试不能在生产数据库执行，只能使用当前学习/测试数据库。

### 步骤 3：用真实 pgvector 固定检索边界（建议 15 分钟）

**目标**

一次性覆盖知识库隔离、`processing/failed` 状态过滤、Top-K 数量、余弦相似度排序和来源元数据。

**修改位置**

- 文件：`tests/test_chunk_repository_integration.py`
- 定位：当前文件不存在。
- 操作：新建完整文件。

**复制下面的完整代码**

```python
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.repositories.chunk_repository import (
    ChunkCreate,
    ChunkRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)


EMBEDDING_DIMENSION = 512


def build_test_vector(
    first_value: float,
    second_value: float = 0.0,
) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = first_value
    vector[1] = second_value
    return vector


def test_search_similar_applies_scope_status_and_top_k(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    knowledge_bases = KnowledgeBaseRepository(db_session)
    documents = DocumentRepository(db_session)
    chunks = ChunkRepository(db_session)

    knowledge_base_a = knowledge_bases.create(
        name=f"day12-kb-a-{suffix}",
    )
    knowledge_base_b = knowledge_bases.create(
        name=f"day12-kb-b-{suffix}",
    )

    best_document = documents.create(
        knowledge_base_id=knowledge_base_a.id,
        filename="day12-best.pdf",
        status="ready",
    )
    second_document = documents.create(
        knowledge_base_id=knowledge_base_a.id,
        filename="day12-second.pdf",
        status="ready",
    )
    processing_document = documents.create(
        knowledge_base_id=knowledge_base_a.id,
        filename="day12-processing.pdf",
        status="processing",
    )
    failed_document = documents.create(
        knowledge_base_id=knowledge_base_a.id,
        filename="day12-failed.pdf",
        status="failed",
    )
    other_knowledge_base_document = documents.create(
        knowledge_base_id=knowledge_base_b.id,
        filename="day12-other-kb.pdf",
        status="ready",
    )

    best_chunk = chunks.bulk_create(
        document_id=best_document.id,
        chunks=[
            ChunkCreate(
                page_number=2,
                chunk_index=0,
                content="最佳匹配且属于知识库 A 的 ready 文档。",
                embedding=build_test_vector(1.0),
            )
        ],
    )[0]
    second_chunk = chunks.bulk_create(
        document_id=second_document.id,
        chunks=[
            ChunkCreate(
                page_number=5,
                chunk_index=0,
                content="次优匹配且属于知识库 A 的 ready 文档。",
                embedding=build_test_vector(0.8, 0.6),
            )
        ],
    )[0]
    chunks.bulk_create(
        document_id=processing_document.id,
        chunks=[
            ChunkCreate(
                page_number=1,
                chunk_index=0,
                content="高分但 processing，绝不能参与检索。",
                embedding=build_test_vector(1.0),
            )
        ],
    )
    chunks.bulk_create(
        document_id=failed_document.id,
        chunks=[
            ChunkCreate(
                page_number=1,
                chunk_index=0,
                content="高分但 failed，绝不能参与检索。",
                embedding=build_test_vector(1.0),
            )
        ],
    )
    chunks.bulk_create(
        document_id=other_knowledge_base_document.id,
        chunks=[
            ChunkCreate(
                page_number=1,
                chunk_index=0,
                content="高分但属于知识库 B，绝不能越界返回。",
                embedding=build_test_vector(1.0),
            )
        ],
    )

    results = chunks.search_similar(
        knowledge_base_id=knowledge_base_a.id,
        query_embedding=build_test_vector(1.0),
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [
        best_chunk.id,
        second_chunk.id,
    ]
    assert [result.filename for result in results] == [
        "day12-best.pdf",
        "day12-second.pdf",
    ]
    assert all(
        result.knowledge_base_id == knowledge_base_a.id
        for result in results
    )
    assert [result.page_number for result in results] == [2, 5]
    assert results[0].score == pytest.approx(1.0, abs=1e-6)
    assert results[1].score == pytest.approx(0.8, abs=1e-6)
```

**这段代码怎样工作**

- 输入：两个临时知识库、五种文档范围/状态组合，以及维度固定为 512 的确定性向量。
- 输出：只允许知识库 A 的两条 ready Chunk 按相似度从高到低返回。
- 调用谁：测试调用真实 `KnowledgeBaseRepository`、`DocumentRepository`、`ChunkRepository.search_similar()`、SQLAlchemy、psycopg 和 pgvector。
- 被谁调用：pytest 收集并执行该测试；`db_session` fixture 管理事务。
- 正常路径：精确向量的相似度约为 1.0，`[0.8, 0.6]` 已归一化且与查询向量相似度约为 0.8，因此顺序稳定。
- 失败路径：如果 SQL 删除知识库过滤、ready 过滤、升序距离或 LIMIT 中任意一项，ID、文件名、数量或分数断言会失败。

**完成本步骤后的预期状态**

最关键的 pgvector 查询不再只靠人工观察；测试也不会依赖真实 Embedding 模型下载或浮动语义结果。

### 步骤 4：固定来源映射和拒答分支（建议 15 分钟）

**目标**

用可控假依赖验证 `DatabaseRAGService` 的真实业务编排：高分证据进入 Context 并原样成为来源，低分证据触发拒答且不调用 LLM。

**修改位置**

- 文件：`tests/test_database_rag_service.py`
- 定位：当前文件不存在。
- 操作：新建完整文件。

**复制下面的完整代码**

```python
import asyncio

from app.repositories.chunk_repository import ChunkSearchResult
from app.services.database_rag_service import (
    DatabaseRAGService,
    REFUSAL_ANSWER,
)


class FakeRetrievalService:
    def __init__(self, results: list[ChunkSearchResult]) -> None:
        self._results = results
        self.calls: list[tuple[int, str, int]] = []

    def search(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int,
    ) -> list[ChunkSearchResult]:
        self.calls.append((knowledge_base_id, question, top_k))
        return list(self._results)


class FakeLLMService:
    def __init__(self, answer: str = "员工需要先提交申请。") -> None:
        self._answer = answer
        self.messages: list[str] = []

    async def chat(self, message: str) -> str:
        self.messages.append(message)
        return self._answer


def build_source(score: float) -> ChunkSearchResult:
    return ChunkSearchResult(
        chunk_id=101,
        document_id=21,
        knowledge_base_id=7,
        filename="员工请假与考勤制度.pdf",
        page_number=2,
        chunk_index=4,
        content="员工请假应提前提交申请并等待审批。",
        score=score,
    )


def test_answer_maps_source_and_builds_traceable_context() -> None:
    source = build_source(score=0.9)
    retrieval_service = FakeRetrievalService([source])
    llm_service = FakeLLMService()
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
        min_relevance_score=0.55,
    )

    result = asyncio.run(
        service.answer(
            knowledge_base_id=7,
            question="  员工如何请假？  ",
            top_k=3,
        )
    )

    assert result.refused is False
    assert result.answer == "员工需要先提交申请。"
    assert result.sources == [source]
    assert retrieval_service.calls == [(7, "员工如何请假？", 3)]
    assert len(llm_service.messages) == 1

    prompt = llm_service.messages[0]
    assert "员工如何请假？" in prompt
    assert "员工请假与考勤制度.pdf" in prompt
    assert "页码：2" in prompt
    assert "Chunk ID：101" in prompt
    assert "员工请假应提前提交申请并等待审批。" in prompt


def test_answer_refuses_low_score_without_calling_llm() -> None:
    retrieval_service = FakeRetrievalService(
        [build_source(score=0.54)]
    )
    llm_service = FakeLLMService()
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
        min_relevance_score=0.55,
    )

    result = asyncio.run(
        service.answer(
            knowledge_base_id=7,
            question="知识库里没有答案的问题",
            top_k=3,
        )
    )

    assert result.answer == REFUSAL_ANSWER
    assert result.refused is True
    assert result.sources == []
    assert llm_service.messages == []
```

**这段代码怎样工作**

- 输入：固定 `ChunkSearchResult`、固定分数和记录调用内容的假 LLM。
- 输出：高分场景返回回答与完整来源，低分场景返回固定拒答、空来源和零次 LLM 调用。
- 调用谁：测试执行真实 `DatabaseRAGService.answer()` 和 `build_rag_prompt()`；只替换检索和 LLM 外部边界。
- 被谁调用：pytest 作为普通同步测试执行，异步 Service 通过标准库 `asyncio.run()` 驱动，不增加异步 pytest 插件。
- 正常路径：0.9 高于 0.55，来源字段进入 Context，LLM 返回值被去空白后成为回答。
- 失败路径：0.54 低于 0.55，Service 在 LLM 前直接拒答；若以后代码错误地仍调用 LLM，`llm_service.messages == []` 会失败。

**完成本步骤后的预期状态**

来源可追溯和拒答短路拥有确定性测试，不会因真实 LLM 响应措辞或网络状态波动。

### 步骤 5：固定 API 请求模型的输入边界（建议 5 分钟）

**目标**

证明合法问题会被去除首尾空白，空白问题和越界 Top-K 会在进入数据库/模型前被 Pydantic 拒绝。

**修改位置**

- 文件：`tests/test_models.py`
- 定位：当前文件不存在。
- 操作：新建完整文件。

**复制下面的完整代码**

```python
import pytest
from pydantic import ValidationError

from app.models import KnowledgeBaseQueryRequest


def test_query_request_normalizes_valid_question() -> None:
    request = KnowledgeBaseQueryRequest(
        question="  员工如何请假？  ",
        top_k=3,
    )

    assert request.question == "员工如何请假？"
    assert request.top_k == 3


@pytest.mark.parametrize(
    ("question", "top_k"),
    [
        ("   ", 3),
        ("合法问题", 0),
        ("合法问题", 11),
    ],
)
def test_query_request_rejects_invalid_input(
    question: str,
    top_k: int,
) -> None:
    with pytest.raises(ValidationError):
        KnowledgeBaseQueryRequest(
            question=question,
            top_k=top_k,
        )
```

**这段代码怎样工作**

- 输入：一个合法请求和三组非法边界输入。
- 输出：合法请求被规范化；非法请求抛出 `pydantic.ValidationError`。
- 调用谁：测试直接执行当前 API 使用的 `KnowledgeBaseQueryRequest`。
- 被谁调用：pytest；FastAPI 在真实请求中也复用同一 Pydantic 模型完成请求体验证。
- 正常路径：首尾空格被 `normalize_question()` 去除，Top-K 3 保留。
- 失败路径：空白问题、0 和 11 都不能创建请求模型，因此不会进入 Retrieval 或 LLM。

**完成本步骤后的预期状态**

输入边界不再只依赖 Swagger 手测，参数化用例在 pytest 汇总中按三条测试分别显示。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不创建 Alembic revision，也不执行 downgrade。测试使用现有三张业务表和 `vector(512)`；只确认 PostgreSQL 可用并把当前学习/测试数据库升级到已有 head。

### 1. 检查当前状态

执行目录：项目根目录 `D:\my_develop\A_work_program\AI-study-2609\enterprise-rag-platform`。先确认工作区、Python 和 Compose 状态；不要输出 `.env` 内容。

```powershell
git status --short
python --version
docker compose config --services
docker compose ps postgres
```

预期结果：

- `git status --short` 至少会显示用户已修改的 `docs/17天每日学习/Day11.md`；完成上述文件创建后还会显示本日 6 个新文件。
- Python 应为 Dockerfile 对应的 3.11 系列，或与当前固定依赖兼容的解释器。
- Compose 服务列表包含 `postgres`。
- `postgres` 若尚未运行，先执行下一节启动命令；不要删除 Volume。

失败时检查：

- `python` 找不到：激活项目虚拟环境后重新执行，不要在多个解释器之间混装依赖。
- `docker compose` 找不到：确认 Docker Desktop 已安装并已启动。
- Compose 报缺少变量：只确认 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_PORT` 是否已配置，不输出变量值。

### 2. 执行环境准备

按顺序启动已有数据库、应用已有迁移，再安装测试依赖；首次安装/模型依赖下载时间不计入核心 60 分钟。

```powershell
docker compose up -d postgres
python -m alembic upgrade head
python -m pip install -r requirements-test.txt
python -m pytest --version
```

预期结果：

- PostgreSQL 健康检查最终为 healthy。
- Alembic 升级到当前已有 `e780fe92751b` head；没有生成新迁移。
- pytest 版本显示 `pytest 8.4.2`。

失败时检查：

- PostgreSQL 未 healthy：运行 `docker compose ps postgres` 和 `docker compose logs --tail 50 postgres`，不要输出或复制数据库密码。
- Alembic 连接失败：检查 PostgreSQL 是否已就绪、当前 Python 是否加载项目根目录的公开配置入口。
- pip 安装失败：确认虚拟环境、Python 3.11 和网络；不要先升级所有固定依赖。

### 3. 回滚并恢复

今天没有数据库结构变化，因此不做 Alembic downgrade。数据回滚由 `tests/conftest.py` 的每测试外层事务自动完成。

执行集成测试后，可以只读核对是否遗留 Day 12 测试知识库：

```powershell
$postgresUser = (docker compose exec postgres printenv POSTGRES_USER).Trim()
$postgresDb = (docker compose exec postgres printenv POSTGRES_DB).Trim()
docker compose exec postgres psql -U $postgresUser -d $postgresDb -c "SELECT count(*) AS day12_leftovers FROM knowledge_bases WHERE name LIKE 'day12-%';"
```

### 预期结果

- 查询返回 `day12_leftovers = 0`。
- 这个查询不显示密码，不修改数据，也不依赖批量删除。
- 如果结果不是 0，先停止提交并检查 fixture 是否执行到 `finally`；不要用批量删除命令掩盖测试隔离问题。

## 七、验证正常路径

### 启动或准备服务

今天不需要启动 FastAPI，也不需要真实 LLM/Embedding；只需保证 PostgreSQL healthy 且现有迁移位于 head。

```powershell
docker compose up -d postgres
docker compose ps postgres
python -m alembic current
```

预期结果：PostgreSQL 为 healthy，Alembic 当前 revision 显示 `e780fe92751b (head)` 或等价 head 标记。

### 执行正常请求或测试

先运行无需真实模型输出的 Service/Pydantic 测试，再运行真实 pgvector 集成测试，最后运行全套测试：

```powershell
python -m pytest tests/test_models.py 
python -m pytest tests/test_database_rag_service.py -q
python -m pytest tests/test_chunk_repository_integration.py -q
python -m pytest -q
```

### 预期状态码或输出结构

这里没有 HTTP 请求；pytest 进程预期退出码为 0。全套汇总的稳定结构应类似：

```text
.......
7 passed in <动态秒数>s
```

- 7 个用例来自：合法模型 1 个、参数化非法输入 3 个、RAG Service 2 个、真实 pgvector 集成测试 1 个。
- 运行耗时是动态值；不把尚未运行的秒数写成事实。
- 测试不下载 Embedding 模型、不调用真实 LLM，也不需要 API Key。

随后核对测试数据回滚：

```powershell
$postgresUser = (docker compose exec postgres printenv POSTGRES_USER).Trim()
$postgresDb = (docker compose exec postgres printenv POSTGRES_DB).Trim()
docker compose exec postgres psql -U $postgresUser -d $postgresDb -c "SELECT count(*) AS day12_leftovers FROM knowledge_bases WHERE name LIKE 'day12-%';"
```

预期结构：

```text
 day12_leftovers
-----------------
               0
```

### 为什么它能证明今天已经完成

- 真实 pgvector 测试经过 Repository、SQLAlchemy、psycopg 和 PostgreSQL，能够证明 SQL 范围过滤与向量排序，而不是只证明一个 mock 返回了预期列表。
- RAG Service 测试证明来源字段没有丢失、Context 可以回查文档/页码/Chunk，并证明低分证据不会触发 LLM。
- Pydantic 测试证明关键非法输入在进入数据库与模型前被拒绝。
- 事务后查询为 0 证明测试可重复运行且没有遗留业务行。

## 八、验证失败和边界路径

### 场景：故意破坏 Top-K 顺序断言，确认测试真的能发现回归

只在 `tests/test_chunk_repository_integration.py` 中临时修改这一段：

```python
assert [result.chunk_id for result in results] == [
    best_chunk.id,
    second_chunk.id,
]
```

临时反转为：

```python
assert [result.chunk_id for result in results] == [
    second_chunk.id,
    best_chunk.id,
]
```

然后只运行目标测试：

```powershell
python -m pytest tests/test_chunk_repository_integration.py -q
```

### 预期结果

- 进程退出码：1。
- pytest 结果：1 failed，失败位置是 Chunk ID 顺序断言；差异应显示真实顺序为 best → second。
- 数据库应该保留：用户原有知识库、文档和 Chunk 完全不变。
- 数据库不应该存在：名称以 `day12-` 开头的测试知识库，以及它们的 Document/Chunk。
- 响应不能泄露：`.env`、数据库密码、LLM API Key、Authorization Header 或完整数据库 URL。

即使测试失败，fixture 也应回滚。用只读查询确认：

```powershell
$postgresUser = (docker compose exec postgres printenv POSTGRES_USER).Trim()
$postgresDb = (docker compose exec postgres printenv POSTGRES_DB).Trim()
docker compose exec postgres psql -U $postgresUser -d $postgresDb -c "SELECT count(*) AS day12_leftovers FROM knowledge_bases WHERE name LIKE 'day12-%';"
```

预期 `day12_leftovers = 0`。

随后必须把断言恢复为原始 best → second 顺序，并再次执行：

```powershell
python -m pytest tests/test_chunk_repository_integration.py -q
python -m pytest -q
```

恢复后的预期结果：目标测试 1 passed，全套 7 passed，退出码均为 0。提交前用下面命令确认临时错误没有保留：

```powershell
Select-String -Path 'tests/test_chunk_repository_integration.py' -Pattern 'best_chunk.id|second_chunk.id' -Context 1,1
```

### 场景：非法问题和 Top-K 被稳定拒绝

```powershell
python -m pytest tests/test_models.py -q
```

预期结果：4 passed、退出码 0；其中三组非法输入均通过 `pytest.raises(ValidationError)` 证明“创建请求模型失败”是预期业务边界，而不是测试崩溃。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `No module named pytest` | 当前解释器未安装测试依赖，或 pip 与 python 不是同一环境 | `python -m pip show pytest`、`python -c "import sys; print(sys.executable)"` | 激活项目虚拟环境，执行 `python -m pip install -r requirements-test.txt`，始终用 `python -m pytest`。 |
| 收集测试时提示缺少 `POSTGRES_DB/USER/PASSWORD` | `app.db` 在导入时校验数据库配置，当前进程未加载项目配置 | `python -c "from app.db import build_database_url; print(build_database_url().render_as_string(hide_password=True))"` | 在项目根目录使用自己的学习/测试数据库配置；命令只允许渲染隐藏密码的 URL，不输出 `.env`。 |
| 集成测试出现 `connection refused` | PostgreSQL 未启动或尚未健康 | `docker compose ps postgres`、`docker compose logs --tail 50 postgres` | 执行 `docker compose up -d postgres`，等 health 状态正常后重跑。 |
| 报 `relation ... does not exist` 或 `type vector does not exist` | 当前数据库未升级到已有 Alembic head | `python -m alembic current` | 在学习/测试数据库执行 `python -m alembic upgrade head`，不要用 `Base.metadata.create_all()` 绕过迁移。 |
| pgvector 报向量维度错误 | 测试向量不是 512 维，或模型字段被错误修改 | `tests/test_chunk_repository_integration.py` 的 `EMBEDDING_DIMENSION`；`app/orm_models.py` 的 `Vector(512)` | 保持两处都为 512；不要用截断向量让测试勉强通过。 |
| Top-K 顺序断言偶发失败 | 测试向量不确定、相似度相同或排序二级键被改动 | `ChunkRepository.search_similar()` 的 `order_by(distance.asc(), Chunk.id.asc())` | 使用计划中的确定性单位向量；相同距离仍由 Chunk ID 稳定排序。 |
| 低分拒答测试意外调用 LLM | 阈值判断位置被移动，或比较符号改变 | `app/services/database_rag_service.py` 的 `result.score >= self._min_relevance_score` | 保持先过滤、无结果先返回拒答，再构造 Prompt 和调用 LLM。 |
| 全套测试通过但数据库出现 `day12-` 记录 | fixture 没有绑定外层 Connection，或清理阶段未回滚 | `tests/conftest.py` 的 `connection.begin()` 与 `finally` | 恢复本计划完整 fixture；停止提交并先解决隔离问题，不运行批量删除命令。 |
| 只跑单个文件成功，全套收集失败 | 测试依赖隐式共享全局状态或导入顺序 | `python -m pytest -vv` | 每个测试自行创建 Fake 和数据；不要在模块级共享可变列表、Session 或 LLM 对象。 |

## 十、检查最终代码差异

执行目录：项目根目录。先看状态，再逐项检查今日文件；新文件未暂存前 `git diff` 不显示正文，因此同时使用 `Get-Content` 核对。

```powershell
git status --short
Get-Content -Path 'requirements-test.txt'
Get-Content -Path 'tests/conftest.py'
Get-Content -Path 'tests/test_chunk_repository_integration.py'
Get-Content -Path 'tests/test_database_rag_service.py'
Get-Content -Path 'tests/test_models.py'
git diff -- 'requirements-test.txt' 'tests/conftest.py' 'tests/test_chunk_repository_integration.py' 'tests/test_database_rag_service.py' 'tests/test_models.py' 'docs/17天每日学习/Day12.md'
```

重点检查：

- Day 12 只新增测试依赖、fixture、三组测试和本计划，没有修改 `app/` 业务代码或迁移。
- `tests/conftest.py` 在 `finally` 中关闭 Session、回滚活动事务并关闭 Connection。
- 集成测试创建的知识库名都有 `day12-` 前缀且使用 UUID，不断言固定数据库 ID。
- 真实数据库只用于 pgvector 查询；RAG 测试没有加载真实 Embedding 模型或调用真实 LLM。
- 故意反转的排序断言已经恢复为 `best_chunk.id` 在前、`second_chunk.id` 在后。
- `docs/17天每日学习/Day11.md` 的用户修改仍然存在，但没有被覆盖，也不属于 Day 12 暂存范围。
- 所有代码和命令都不包含 `.env`、数据库密码、API Key 或 Token。

## 十一、Git 提交

核心测试文件完成并检查 Git diff 边界后即可执行；不要求提供验收结果。如果已知测试失败，应先修复再提交。

先只暂存 Day 12 的明确文件：

```powershell
git add 'requirements-test.txt' 'tests/conftest.py' 'tests/test_chunk_repository_integration.py' 'tests/test_database_rag_service.py' 'tests/test_models.py' 'docs/17天每日学习/Day12.md'
git diff --cached -- 'requirements-test.txt' 'tests/conftest.py' 'tests/test_chunk_repository_integration.py' 'tests/test_database_rag_service.py' 'tests/test_models.py' 'docs/17天每日学习/Day12.md'
git status --short
```

确认暂存区没有 `docs/17天每日学习/Day11.md` 后提交：

```powershell
git commit -m "Day12: add critical RAG regression tests"
```

不要使用 `git add .`；不要为了得到干净状态还原或覆盖 Day 11 的用户修改。

## 十二、面试高频问题与参考答案

### 问题 1：哪些测试必须使用真实数据库，哪些依赖应该替换？

#### 30 秒参考答案

当前项目的知识库隔离、Document 状态过滤和 Top-K 排序都写在 `ChunkRepository.search_similar()` 的 SQLAlchemy 查询里，并依赖 PostgreSQL 的 pgvector 余弦距离，所以这部分必须用真实 PostgreSQL + pgvector 集成测试。`DatabaseRAGService` 的阈值分支、Context 构造和来源返回属于确定性业务编排，可以用固定检索结果和假 LLM 做快速单元测试。这样既验证真实 SQL，又避免模型下载、网络和随机回答让回归测试不稳定。

#### 继续追问：为什么不把 Repository 也全部 mock 掉？

如果完全 mock Repository，测试只能证明 Service 调用了一个预设返回值，无法发现 JOIN 缺失、知识库 WHERE 条件被删、`ready` 过滤失效、距离排序方向写反或 LIMIT 丢失。当前最有价值的一条集成测试正是为了覆盖这些数据库语义。

#### 回答时要引用的项目依据

- `app/repositories/chunk_repository.py`：JOIN、知识库过滤、ready 过滤、余弦距离排序和 LIMIT。
- `tests/test_chunk_repository_integration.py`：两个知识库、三种文档状态和确定性 512 维向量。
- `tests/test_database_rag_service.py`：固定 Fake 边界。

### 问题 2：测试怎样做到不污染现有数据库？

#### 30 秒参考答案

`tests/conftest.py` 为每个集成测试独占一条 Connection，在其上开启外层事务，再把 SQLAlchemy Session 绑定到这条 Connection。Repository 的 `flush()` 会让测试在当前事务内查到数据，但 fixture 在 `finally` 中总会关闭 Session 并回滚外层事务，所以正常通过和断言失败都不留下 KnowledgeBase、Document 或 Chunk。测试也不依赖固定自增 ID，因为 PostgreSQL 序列通常不会随事务回滚。

#### 继续追问：为什么不用测试结束后批量 DELETE 或 TRUNCATE？

删除式清理在测试中途崩溃时可能根本没有机会执行，也可能误删同库的用户数据；外层事务回滚把清理与事务生命周期绑定，范围更明确。当前计划还用 `day12-%` 的只读计数验证没有遗留记录，但不生成批量删除命令。

#### 回答时要引用的项目依据

- `tests/conftest.py`：Connection、Transaction、Session 和 `finally`。
- `app/repositories/knowledge_base_repository.py`：`create()` 只 flush，不自行 commit。
- 回滚后的 `day12_leftovers = 0` 可选查询结果。

### 问题 3：为什么自动测试不应该调用真实 Embedding 和 LLM？

#### 30 秒参考答案

今天测试的目标是固定业务契约，不是重复 Day 11 的模型质量实验。真实 Embedding 会增加模型下载和运行时间，真实 LLM 还受网络、配置、费用和生成随机性影响。测试用确定性 512 维向量验证 pgvector，用假检索和假 LLM 验证阈值、来源和 Prompt；特别是拒答测试直接断言 LLM 调用次数为 0，这比比较一段随机回答稳定得多。

#### 继续追问：那模型质量由什么保证？

模型质量不能由几条单元测试保证。当前项目用 Day 10 固定评测集和 Day 11 的 Recall@1/3/5、MRR、拒答率和延迟报告评估质量；pytest 负责防止实现行为意外回归，两者职责互补。

#### 回答时要引用的项目依据

- `app/services/embedding_service.py`：真实 BGE 模型和 512 维输出。
- `scripts/run_evaluation.py`：Day 11 参数实验与指标。
- `tests/test_database_rag_service.py`：Fake 调用记录与固定回答。

### 问题 4：这组测试能防止哪些真实回归？

#### 30 秒参考答案

它可以发现五类高风险回归：删除知识库过滤导致跨库数据泄露；删除 ready 过滤导致 processing/failed 文档被检索；把余弦距离排序方向写反或丢失 Top-K；RAG 来源丢失文档名、页码、Chunk 或原文；阈值不足时仍调用 LLM 或返回无关来源。另外 Pydantic 参数化测试保护空白问题和 `top_k` 越界。

#### 继续追问：为什么不追求 100% 覆盖率？

覆盖率只说明代码行被执行，不说明关键业务边界被正确断言。Day 12 的时间盒优先保护跨知识库、状态、来源和拒答这些高损失行为；旧 FAISS 工具函数或简单 getter 的形式覆盖不能替代这些断言。

#### 回答时要引用的项目依据

- `tests/test_chunk_repository_integration.py`：范围、状态、数量和顺序断言。
- `tests/test_database_rag_service.py`：来源、Context、拒答和 LLM 零调用断言。
- `tests/test_models.py`：Pydantic 输入边界。

## 十三、今天的完整数据流

### 正常路径

```text
python -m pytest
→ pytest 收集 tests/
→ db_session 开启真实 PostgreSQL 外层事务
→ Repository 创建两个知识库和不同状态 Document/Chunk
→ pgvector 执行知识库 + ready 过滤、余弦距离排序和 LIMIT
→ pytest 断言 Top-K 顺序、来源和分数
→ fixture rollback，不留下测试记录

固定 ChunkSearchResult
→ FakeRetrievalService
→ DatabaseRAGService 阈值过滤
→ 构造包含文档名、页码、Chunk ID 和原文的 Context
→ FakeLLMService 返回固定回答
→ pytest 断言 answer + sources + Prompt

合法/非法请求数据
→ KnowledgeBaseQueryRequest
→ 合法值规范化 / 非法值 ValidationError
→ pytest 汇总退出码 0
```

### 失败路径

```text
临时反转预期 Chunk 顺序
→ 真实 pgvector 仍返回 best → second
→ pytest 精确指出顺序断言失败并返回退出码 1
→ db_session finally 回滚测试事务
→ day12_leftovers 仍为 0
→ 恢复正确断言
→ 目标测试与全套测试再次通过

低于 0.55 的固定来源
→ DatabaseRAGService 过滤后无有效证据
→ 返回固定拒答 + refused=true + sources=[]
→ 不调用 FakeLLMService
```

## 十四、完成标准

```text
[ ] 能解释为什么 pgvector 查询需要真实数据库集成测试，而 RAG 生成边界适合使用 Fake
[ ] 能解释 Connection、外层事务、Session、flush 和 rollback 在测试隔离中的关系
[ ] 已新增 requirements-test.txt、事务 fixture 和三组测试文件，未修改无关业务代码
[ ] 知识库 A 的查询只返回自身 ready 文档，processing、failed 和知识库 B 的 Chunk 均被过滤
[ ] Top-K 数量、相似度顺序、文档名、页码、Chunk ID 和内容来源都有明确断言
[ ] 高分证据进入 Context，低分证据返回固定拒答、空来源且不调用 LLM
[ ] 空白问题、top_k=0 和 top_k=11 均有可执行 pytest 边界测试和预期结果
[ ] 已提供全套 7 passed 的正常验证命令以及故意破坏断言后 1 failed 的失败验证命令；实际执行与记录可选
[ ] 能不看代码复述 pytest → fixture → Repository/Service → 断言 → rollback 的完整数据流
[ ] git diff 和暂存区不包含秘密、无关修改或 docs/17天每日学习/Day11.md，核心实现完成后可执行边界清晰的提交
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
