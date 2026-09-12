# Day 17：完成模拟面试和最终复现

今天将直接完成两轮连续项目复现和一轮基于真实代码证据的模拟面试复盘，使项目获得可演示、可解释、可追问的最终验收记录，并为面试中的架构、事务、检索、评测和工程化追问提供可信回答。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：`docs/final-reproduction-and-interview-review.md` 最终复现与模拟面试复盘  
> 当前真实状态：未开始  
> 对应总体安排：Day 17

## 一、今天完成后的项目变化

### 升级前

```text
Day 1～Day 15 的代码、数据、评测与项目说明已经存在
→ Day 16 计划已经生成，但演示脚本、视频和简历条目尚未实际完成
→ 还没有连续两轮演示结果
→ 还没有一分钟、三分钟和深入追问三个层次的统一口述稿
→ 项目事实、限制、失败案例与后续方向尚未形成最终面试复盘
```

### 升级后

```text
Day 16 的演示脚本、视频和简历条目先真实完成
→ 不看代码完成一分钟和三分钟项目介绍
→ 连续两轮执行多文档入库、跨文档来源、拒答和重启恢复
→ 查询数据库结构与真实数据摘要
→ 运行 pytest、数据集校验和独立输出的最终评测
→ 回答数据库、pgvector、事务、RAG、测试、评测和 Docker 追问
→ 记录卡顿、事实错误、限制和最小修复
→ 形成唯一的最终复现与模拟面试复盘文档
```

### 今天在完整项目中的位置

- 所属阶段：求职输出。
- 所属链路：最终验收与口头表达，覆盖文档入库和知识库问答两条主链路。
- 今天的输入：Day 1～Day 15 的当前实现与证据，以及之后需要完成的 Day 16 演示脚本、视频和独立简历条目。
- 今天的输出：`docs/final-reproduction-and-interview-review.md`，包含两轮复现清单、事实卡、一分钟/三分钟口述、问题提纲、限制与复盘。
- 给后续阶段留下什么：一个可持续优化的可信项目基线；后续只根据真实失败、岗位要求或使用反馈迭代，不继续无目的堆框架。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 15 均有核心产物、用户完成标记和匹配提交，当前 `HEAD` 为 `f5e3d2a Day15`。
- `[当前事实]` `README.md`、`docs/architecture.md` 和 `docs/evaluation-report.md` 已形成互相一致的项目说明、架构图和评测摘要。
- `[当前事实]` 当前企业知识库主链路是 `FastAPI → Service → Repository → SQLAlchemy → PostgreSQL + pgvector`。
- `[当前事实]` 文档入库保存 `KnowledgeBase → Document → Chunk`、页码、原文和 `vector(512)`，文档状态只允许 pending/processing/ready/failed。
- `[当前事实]` 检索在 SQL 层同时过滤请求知识库和 `Document.status='ready'`，并按余弦距离排序返回 Top-K。
- `[当前事实]` 当前生产代码默认 `Top-K=3`、拒答阈值 `0.55`；离线评测推荐阈值 `0.65` 尚未部署。
- `[当前事实]` 固定评测使用 4 份两页虚构制度和 18 道题，其中 12 道可回答、6 道无答案；Top-3 Recall 为 `0.972222`、MRR 为 `0.958333`。
- `[当前事实]` 36 个预热后 Query Embedding + pgvector 检索样本的 P95 为 `15.2546 ms`，不包含 HTTP、模型初始化和 LLM 生成。
- `[当前事实]` 当前测试代码收集为 7 个 pytest case，覆盖输入边界、来源映射、低分拒答、知识库隔离、文档状态、Top-K 和排序。
- `[当前事实]` Day 13 已有重启持久化完成标记与匹配提交 `0b15e88`；Day 14 已有 Docker/干净环境完成标记与匹配提交 `923ffcc`。
- `[当前事实]` 生成本计划时 `docs/17天每日学习/Day16.md` 是未提交的用户工作区文件，必须保留且不能加入 Day 17 的提交。

### 仍然缺少

- `[当前事实]` Day 16 当前尚未完成：`scripts/run_enterprise_rag_demo.ps1`、`docs/demo-script.md`、`docs/resume-project-entry.md` 和本地演示视频都不存在。
- `[当前事实]` 当前不存在 `docs/final-reproduction-and-interview-review.md`。
- `[当前事实]` 当前没有连续两轮演示结果，不能提前写“两次演示通过”。
- `[当前事实]` 当前没有一轮完整模拟面试的卡顿、错误和改进记录。
- `[当前事实]` `app/main.py` 的 FastAPI 标题和根提示仍保留 “Mini RAG Backend”，旧 SQLite/FAISS 路由也仍与企业知识库路由共存；这不是 Day 17 要扩展的新功能，但面试时必须能如实说明。

### 待实测

- `[待实测]` Day 16 完成后，其四阶段脚本能否在同一环境连续执行两轮且稳定断言来源、拒答和重启恢复。
- `[待实测]` 两轮演示的实际用时、卡顿位置和外部 LLM 波动。
- `[待实测]` 当前环境重新运行数据集校验和 7 个 pytest case 的实际结果。
- `[待实测]` 使用第二轮动态知识库重新生成到独立本地路径的最终评测结果；不得覆盖已提交基线报告。
- `[待实测]` 用户能否不看代码完成一分钟和三分钟口述，并在追问中区分已实现事实、离线建议和后续设想。

### 需要保护的用户修改

- `docs/17天每日学习/Day16.md` 是当前未提交文件，Day 17 只读取其前置要求，不修改、不暂存、不提交它。
- 只创建 `docs/17天每日学习/Day17.md` 和计划中明确的新复盘文档；不读取或修改被生成器禁止的 `docs/简历.md`，不处理 `.codex-day15-fix.patch`、`test_260908.py` 或其他历史文件。

## 三、今天必须理解的核心知识

### 1. 最终验收是“可运行、可解释、可追问”三项同时成立

- 一句话解释：代码能跑不等于能面试，口述流畅也不能替代真实证据。
- 在当前项目中的职责：两轮演示证明可运行，一分钟和三分钟口述证明可解释，固定追问与证据索引证明可追问。
- 与其他组件的关系：演示依赖 Day 16 脚本；解释依赖 README/架构图；追问依赖 ORM、Service、Repository、测试和评测报告。
- 容易混淆的点：只背组件名称没有说明数据流，只展示结果没有说明失败边界，都不算完整验收。
- 面试一句话：我用两轮真实演示、分层口述和代码/数据证据索引分别验证系统可运行、可解释和可追问。

### 2. 面试回答应使用“结论—原因—项目证据—限制”结构

- 一句话解释：先直接回答，再解释设计原因，引用当前文件或指标，最后主动划定边界。
- 在当前项目中的职责：例如解释 pgvector 时，先说它解决持久化和范围过滤，再引用 `ChunkRepository`，最后说明当前没有 ANN 索引和大规模压测。
- 与其他组件的关系：每个回答都应落到代码职责、数据库约束、测试、评测或运行记录，而不是通用定义。
- 容易混淆的点：限制不是自我否定；明确没有认证、异步任务或生产 SLA，反而能防止夸大。
- 面试一句话：我的回答先给设计结论，再用当前仓库证据说明为什么，最后主动交代适用范围和下一步。

### 3. 自动测试、离线评测和端到端演示解决不同问题

- 一句话解释：pytest 固定业务规则，评测衡量检索质量与参数，端到端演示验证真实组件能协同运行。
- 在当前项目中的职责：7 个 pytest case 覆盖边界与过滤；18 题评测计算 Recall/MRR/拒答/延迟；两轮演示覆盖 HTTP、真实 Embedding、LLM、数据库和重启。
- 与其他组件的关系：测试可使用假 LLM 或事务回滚，评测不调用 LLM，演示则依赖本地真实环境。
- 容易混淆的点：pytest 通过不能证明 PostgreSQL Volume 重启恢复，18 题检索 Recall 也不能证明最终答案准确率。
- 面试一句话：我用三种证据分别守住代码规则、检索质量和系统集成，不用一种测试替代所有质量维度。

### 4. 两轮演示的价值在于可重复，而不是重复制造数据

- 一句话解释：两轮都必须从明确输入走到相同稳定结论，但允许数据库 ID、LLM 措辞和耗时变化。
- 在当前项目中的职责：每轮创建独立知识库和状态文件，上传同一组冻结 PDF，核对 ready 数、目标来源、拒答和重启后的同一轮 ID。
- 与其他组件的关系：动态状态来自 Day 16 脚本，稳定规则来自数据库、检索过滤和拒答 Service。
- 容易混淆的点：第二轮不能复用第一轮结果假装重跑；同时也不应逐字比较非确定性的 LLM answer。
- 面试一句话：我让两轮使用独立运行状态，同时比较相同的业务不变量，从而验证流程可重复而非输出字面相同。

### 5. 最终复盘只修阻塞问题，不在最后一天扩展架构

- 一句话解释：最后一天发现问题时，先判断是否阻塞演示或构成事实错误，再决定最小修复。
- 在当前项目中的职责：API 不健康、来源缺失、拒答错误或文档数字错误必须修；新增认证、队列、reranker、ANN、监控不属于今天。
- 与其他组件的关系：非阻塞限制进入复盘“后续方向”，不临时修改已稳定的核心链路。
- 容易混淆的点：为了面试效果临时加功能会扩大风险，也可能让 README、测试和评测重新失配。
- 面试一句话：最终日只修复阻塞演示或明显事实错误的问题，其余改进按真实失败和岗位需求进入后续迭代。

## 四、升级涉及的文件

| 文件 | 操作 | 作用 |
| --- | --- | --- |
| `docs/final-reproduction-and-interview-review.md` | 新建 | 最终事实卡、一分钟/三分钟口述、两轮复现记录、问题提纲、限制和复盘 |
| `docs/17天每日学习/Day17.md` | 新建；执行后可选更新记录 | Day 17 完整执行手册、验证、排错、提交边界和参考答案 |
| `artifacts/demo/day17-run1-state.json` | Day 16 完成后由脚本本地生成，不提交 | 第一轮动态知识库与 Document 指纹 |
| `artifacts/demo/day17-run2-state.json` | Day 16 完成后由脚本本地生成，不提交 | 第二轮动态知识库与 Document 指纹 |
| `artifacts/demo/day17-final-evaluation.json` | 可选本地生成，不提交 | 使用第二轮知识库得到的独立最终评测结果 |

### 今日不做

- 不跳过 Day 16 的演示脚本、视频和简历条目前置条件，也不在 Day 17 重写 Day 16 全部内容。
- 不新增认证、Celery、消息队列、reranker、HNSW/IVFFlat、监控、前端或其他框架。
- 不为了让演示更好看而修改题目标签、删除失败案例、覆盖基线评测或伪造运行结果。
- 不清理旧 FAISS 路由或修改 FastAPI 标题，除非用户之后把它确定为独立修复任务。
- 不删除数据库 Volume、演示知识库、视频或批量文件。

## 五、按顺序完成项目升级

### 步骤 1：等待并检查 Day 16 最小前置条件（建议 5 分钟）

**目标**

确保最终复现真正基于已经完成的演示脚本、视频和简历条目；目前这些文件不存在，所以今天的计划可以先保存，但实际执行 Day 17 时必须先通过本步骤。

**修改位置**

- 文件：不修改文件
- 定位：Day 16 计划规定的四个核心产物
- 操作：在项目根目录执行完整前置检查

**复制下面的完整 PowerShell 检查**

```powershell
$day17Prerequisites = @(
    "scripts\run_enterprise_rag_demo.ps1",
    "docs\demo-script.md",
    "docs\resume-project-entry.md",
    "artifacts\demo\enterprise-rag-demo.mp4"
)

$day17MissingPrerequisites = @(
    $day17Prerequisites |
        Where-Object {
            -not (Test-Path -LiteralPath $_)
        }
)

if ($day17MissingPrerequisites.Count -gt 0) {
    throw (
        "Day 16 尚未完成，先按 Day16.md 完成这些产物：" +
        ($day17MissingPrerequisites -join ", ")
    )
}

$day17Video = Get-Item -LiteralPath `
    "artifacts\demo\enterprise-rag-demo.mp4"

if ($day17Video.Length -le 0) {
    throw "Day 16 视频文件为空，不能进入最终复现"
}

"OK：Day 16 脚本、说明、简历条目和非空视频均存在"
```

**这段检查怎样工作**

- 输入：Day 16 的三个可提交文本文件和一个本地 MP4。
- 输出：全部存在且视频非空时输出 OK；否则列出精确缺失路径并非零退出。
- 调用谁：PowerShell 文件系统只读检查。
- 被谁调用：Day 17 后续两轮复现。
- 正常路径：Day 16 完成后才继续。
- 失败路径：目前执行应发现缺失文件并停止；这是已知前置未完成，不是伪造 Day 17 阻塞记录的理由。

**完成本步骤后的预期状态**

Day 16 后续真实完成时，Day 17 获得稳定演示入口；在此之前只保留本计划，不声称已运行最终验收。

### 步骤 2：新建最终复现与模拟面试复盘（建议 15 分钟）

**目标**

把项目事实、两层口述、两轮演示记录、面试追问、限制和后续方向集中到一个可持续更新的最终文档。

**修改位置**

- 文件：`docs/final-reproduction-and-interview-review.md`
- 定位：新文件
- 操作：复制下面的完整文件内容；所有实际运行项初始化为“未执行”，不得提前勾选

**复制下面的完整内容**

````markdown
# Enterprise RAG Platform 最终复现与模拟面试复盘

> 当前记录状态：未执行  
> 代码基线：Day 15 提交 `f5e3d2a`；Day 16 实际提交完成后再记录其真实 commit  
> 评测数据集：`2026-09-04-v1`  
> 说明：动态 ID、耗时、LLM 措辞和实际运行结果均在执行时产生，不预填、不伪造

## 1. 项目事实卡

| 主题 | 当前事实 | 证据 |
| --- | --- | --- |
| 业务目标 | 企业制度与 SOP 多知识库 RAG 后端 | `README.md` |
| 主链路 | 文档入库、指定知识库问答 | `docs/architecture.md` |
| 数据模型 | KnowledgeBase 1:N Document 1:N Chunk | `app/orm_models.py` |
| 向量 | BGE 512 维，PostgreSQL + pgvector 持久化 | `app/services/embedding_service.py`、迁移 |
| 切块 | `chunk_size=200`、`overlap=40` | `app/main.py`、入库 Service |
| 检索 | SQL 层过滤知识库与 ready 状态，余弦 Top-K | `app/repositories/chunk_repository.py` |
| 当前参数 | 默认 Top-K=3，生产拒答阈值 0.55 | `app/services/retrieval_service.py`、`app/services/database_rag_service.py` |
| 离线建议 | Top-K=3、threshold=0.65，尚未部署 | `docs/evaluation-report.md` |
| 评测规模 | 4 份两页 PDF，12 道可回答题，6 道无答案题 | `data/evaluation/enterprise_questions.json` |
| 检索结果 | Recall@3=0.972222，MRR@3=0.958333 | `data/evaluation/enterprise_evaluation_report.json` |
| 延迟口径 | 36 个预热检索样本 P95=15.2546 ms，不含 HTTP/LLM | `docs/evaluation-report.md` |
| 自动测试 | 7 个 pytest case，覆盖关键边界与检索规则 | `tests/` |
| 当前限制 | 文本型 PDF、同步入库、无认证、无 ANN、无生产压测 | `README.md` |

## 2. 一分钟项目介绍

我独立实现了一个面向企业制度与 SOP 的 RAG 后端。用户先创建知识库并上传多份文本型 PDF，FastAPI 调用 Service 完成按页解析、200/40 重叠切分和 BGE 512 维向量化，再通过 Repository 与 SQLAlchemy 把 Document、页码、Chunk 原文和向量持久化到 PostgreSQL + pgvector。提问时，系统在 SQL 层只检索指定知识库的 ready 文档，按余弦相似度返回 Top-3；证据低于当前 0.55 阈值就会在调用 LLM 前拒答，否则返回回答以及文档名、页码、Chunk 和分数。我还建立了 4 份虚构制度、18 道固定题的评测集，Top-3 Recall 为 97.22%、MRR 为 95.83%，并用 pytest、Alembic 和 Docker Compose 验证关键规则、迁移与重启持久化。当前系统适合本地演示和小规模实验，尚未实现认证、异步任务、ANN 索引和生产级压测。

## 3. 三分钟项目介绍提纲

### 0:00～0:30：问题与目标

- 早期内存 FAISS Demo 只能保留最近一次上传，重启丢失且难以按知识库和文档状态过滤。
- 目标是把企业制度做成多知识库、多文档、可持久化、可追溯、可评测的 RAG 后端。

### 0:30～1:15：文档入库链路

```text
POST /knowledge-bases/{id}/documents
→ FastAPI 校验 PDF
→ DocumentIngestionService 创建 processing Document
→ PDFService 按页解析
→ 200/40 重叠切块
→ EmbeddingService 生成归一化 512 维向量
→ ChunkRepository 批量写入
→ Document 切换为 ready
```

- processing Document 先提交以保留可观察 ID。
- Chunk 与 ready 更新在同一后续事务提交。
- 失败时 rollback 半成品，再安全标记 failed；检索永远过滤非 ready 文档。

### 1:15～2:00：问答链路

```text
POST /knowledge-bases/{id}/query
→ Pydantic 校验 question 与 top_k=1..10
→ Query Embedding
→ SQL 过滤 KnowledgeBase + ready
→ pgvector 余弦 Top-K
→ 0.55 阈值
→ 拒答，或 Context → LLM
→ answer + filename + page + chunk + score
```

- Repository 负责数据库查询，Service 负责阈值、Prompt 和 LLM 编排，API 负责 HTTP 映射。
- score 是语义相似度，不是答案正确概率。

### 2:00～2:35：质量证据

- 4 份两页虚构制度，18 道固定题。
- Top-3 Recall 97.22%，MRR 95.83%。
- 36 个预热 Query Embedding + pgvector 样本 P95 15.25 ms。
- 7 个 pytest case 覆盖输入、来源、拒答、隔离、状态、Top-K 和排序。
- 保留 `cross-trip-01` 证据不完整和 `direct-hotel-01` 高阈值误拒答两个失败案例。

### 2:35～3:00：工程化与限制

- Alembic 管理 vector 扩展和三表迁移；Compose 编排 PostgreSQL、migrate 和 API，命名 Volume 保存数据库与模型缓存。
- 当前没有认证、异步任务、ANN 索引和大规模并发验证；离线建议阈值 0.65 尚未部署。
- 后续优化必须从失败案例和目标岗位需求出发，而不是继续堆技术名词。

## 4. 两轮最终演示记录

### 第一轮

| 检查项 | 当前记录 |
| --- | --- |
| 开始/结束时间 | 未执行 |
| 一分钟口述是否脱稿 | 未执行 |
| 4 个 Document 是否全部 ready | 未执行 |
| 跨文档题是否包含两个目标来源 | 未执行 |
| 无答案题是否 refused=true、sources=[] | 未执行 |
| API 重启后 Document ID 是否不变 | 未执行 |
| 实际卡顿或错误 | 未执行 |
| 是否完整成功 | 未执行 |

### 第二轮

| 检查项 | 当前记录 |
| --- | --- |
| 开始/结束时间 | 未执行 |
| 三分钟口述是否脱稿 | 未执行 |
| 4 个 Document 是否全部 ready | 未执行 |
| 跨文档题是否包含两个目标来源 | 未执行 |
| 无答案题是否 refused=true、sources=[] | 未执行 |
| API 重启后 Document ID 是否不变 | 未执行 |
| 实际卡顿或错误 | 未执行 |
| 是否完整成功 | 未执行 |

实际输出、截图和详细日志均可选；若不填写，不能把“未执行”改成“已通过”。

## 5. 高频追问速答卡

### 5.1 为什么从 FAISS 改成 PostgreSQL + pgvector？

核心目的不是声称 pgvector 一定更快，而是让知识库、文档状态、页码、Chunk 原文和向量处在同一持久化与查询体系中，支持范围过滤、事务和重启恢复。代价是增加迁移、连接和数据库运维；当前小数据集仍用精确余弦查询，没有 ANN 索引。

### 5.2 SQLAlchemy 为什么还需要 psycopg？

SQLAlchemy 提供 ORM、查询构造、Session 和连接池抽象，psycopg 是实际与 PostgreSQL 通信的 DBAPI 驱动。Engine 使用 psycopg 建立连接；每个请求通过 Session 管理 ORM 工作单元，两者不是替代关系。

### 5.3 为什么使用 Alembic，而不是 `create_all()`？

`create_all()` 只能按当前 metadata 补建不存在的表，不能表达可审核的历史变化和可靠 downgrade。Alembic 把 vector 扩展、三表、外键、约束和索引变成有顺序的版本链，支持从空库复现和受控回滚。

### 5.4 Repository 与 Service 怎样分工？

Repository 只负责 create/get/list/update、批量 Chunk 写入和 pgvector 查询；Service 编排 PDF、切块、Embedding、事务状态、拒答和 LLM。FastAPI 负责协议校验、依赖注入和安全 HTTP 错误映射，避免 SQL 与业务流程散落在路由中。

### 5.5 上传失败怎样避免半成品被检索？

系统先提交 processing Document，随后在一个事务中批量写 Chunk 并更新 ready。处理失败时先 rollback 未提交 Chunk 和 ready 更新，再单独保存 failed 状态；检索 SQL固定只选择 ready 文档。因此保留可观察失败记录，但半成品不会进入 Context。

### 5.6 怎样保证不跨知识库检索？

`ChunkRepository.search_similar()` 联结 Document，在 SQL 中同时约束 `knowledge_base_id` 和 `status='ready'`，再按余弦距离排序和 limit。不是先全库搜索再在 Python 过滤；集成测试还创建第二知识库的高分 Chunk，断言它不会返回。

### 5.7 为什么需要阈值拒答？

向量检索即使面对无答案问题也会返回最近的 Chunk。当前 Service 只保留 score 大于等于 0.55 的来源；如果没有可靠来源，就在调用 LLM 前返回固定拒答和空来源，避免不相关 Context 诱导生成，也减少无效外部调用。

### 5.8 0.65 为什么没有直接上线？

固定实验中 0.65 提高无答案拒答率，但 `direct-hotel-01` 的最高分是 0.638058，导致真实可回答题被误拒答。报告把 0.65作为离线建议，生产仍保留 0.55；上线前需要扩大验证集、独立配置变更并重跑回归。

### 5.9 Recall@K 与 MRR 有什么区别？

Recall@K 衡量预期证据是否进入前 K 条，本项目对一道题的多个证据分别计算后再平均；MRR 关注第一条正确证据排得多靠前。Top-1 MRR 已较高但完整证据率低，说明第一条常正确，却不足以覆盖综合和跨文档问题。

### 5.10 pytest、评测和端到端验收为什么都需要？

pytest 快速固定输入、来源、拒答和过滤规则；离线评测用固定问题比较 Recall、MRR、阈值和检索延迟且不调用 LLM；端到端验收覆盖 HTTP、真实模型、PostgreSQL、LLM 和重启。它们回答不同质量问题，不能互相替代。

### 5.11 怎样证明持久化与可复现？

持久化验收在不重新上传的情况下比较 API 和 PostgreSQL 重启前后的知识库、Document、Chunk 和来源稳定字段；可复现验收从公开 `.env.example`、固定依赖和空数据库执行 Compose 与 Alembic 到 head。前者证明已有数据能恢复，后者证明新环境能构建，两者不同。

### 5.12 当前最重要的限制和后续方向是什么？

当前只支持文本型 PDF，同步入库，没有认证授权、异步任务、ANN 索引、可观测性和生产压测，旧 FAISS 路由与旧 FastAPI 标题仍保留。优先方向应根据真实使用选择：大文档先异步任务，真实租户先认证授权，语料规模扩大后再评估 ANN/reranker 和性能监控。

## 6. 不能说成事实的内容

- 不能说“最终答案准确率 97.22%”；这是证据 Recall@3。
- 不能说“接口 P95 15.25 ms”；这是预热后的 Query Embedding + pgvector 检索。
- 不能说“生产阈值已是 0.65”；当前代码仍为 0.55。
- 不能说“系统已生产可用”；没有认证、备份、监控、限流和生产压测。
- 不能说“pgvector 一定比 FAISS 快”；当前选择主要解决一致性、过滤和持久化。
- 不能说“所有跨文档题都完整命中”；`cross-trip-01` 仍缺少一部分预期证据。
- 不能说“pytest 证明重启持久化”；重启恢复由独立端到端验收证明。

## 7. 最终测试与评测摘要

| 项目 | 已提交基线 | 本次最终运行 |
| --- | --- | --- |
| 数据集校验 | 4 份 PDF、18 道题 | 未执行 |
| pytest | 预期收集 7 个 case | 未执行 |
| 完成题数 | 18/18，运行故障 0 | 未执行 |
| Recall@3 | 0.972222 | 未执行 |
| MRR@3 | 0.958333 | 未执行 |
| 检索 P95 | 15.2546 ms | 未执行 |
| 质量失败案例 | 2 个，已保留 | 未执行 |

## 8. 模拟面试复盘

| 维度 | 首轮表现 | 次轮表现 | 证据不足或卡顿 | 最小改进 |
| --- | --- | --- | --- | --- |
| 一分钟项目定位 | 未执行 | 未执行 | 未执行 | 未执行 |
| 文档入库数据流 | 未执行 | 未执行 | 未执行 | 未执行 |
| 问答与拒答数据流 | 未执行 | 未执行 | 未执行 | 未执行 |
| 事务和失败状态 | 未执行 | 未执行 | 未执行 | 未执行 |
| pgvector 与 FAISS 取舍 | 未执行 | 未执行 | 未执行 | 未执行 |
| 测试与评测口径 | 未执行 | 未执行 | 未执行 | 未执行 |
| Docker 与持久化 | 未执行 | 未执行 | 未执行 | 未执行 |
| 限制与后续方向 | 未执行 | 未执行 | 未执行 | 未执行 |

## 9. 最终结论

- 两轮演示：未执行。
- 一分钟与三分钟脱稿口述：未执行。
- 高频问题回答：未执行。
- 已知阻塞：Day 16 演示脚本、视频和简历条目尚未完成。
- 最终状态：未完成；只有真实完成前置条件和两轮验收后才能更新。
````

**这份文档怎样工作**

- 输入：当前代码、Day 15 说明、Day 16 产物、两轮演示、pytest、评测和口述表现。
- 输出：一个唯一、可审计的最终复现与面试复盘。
- 调用谁：不调用运行时代码；其中的事实索引指向当前仓库文件。
- 被谁调用：Day 17 两轮演示、模拟面试和之后的求职复习。
- 正常路径：实际执行后只更新动态记录与真实结论。
- 失败路径：任何未执行或失败项保持原样并记录原因，不能为了完成 17 天计划而提前改成通过。

**完成本步骤后的预期状态**

最终文档已经提供完整口述框架和问题卡，但所有运行记录仍是“未执行”；只有后续真实执行才能更新。

### 步骤 3：完成第一轮连续演示和模拟追问（建议 15 分钟）

**目标**

在不看代码的前提下先说一分钟介绍，再完整跑一次 Day 16 固定演示，并回答至少 6 个随机追问，找出真实卡顿。

**修改位置**

- 文件：`docs/final-reproduction-and-interview-review.md`
- 定位：第 4 节“第一轮”和第 8 节“模拟面试复盘”
- 操作：执行后可选把真实时间、卡顿和最小改进更新进去；不要求粘贴完整日志

**复制下面的完整 PowerShell 命令**

```powershell
$day17Run1State = `
    "artifacts\demo\day17-run1-state.json"

$day17Run1StartedAt = Get-Date

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode prepare `
    -StatePath $day17Run1State

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode answerable `
    -StatePath $day17Run1State

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode refusal `
    -StatePath $day17Run1State

docker compose restart api
if ($LASTEXITCODE -ne 0) {
    throw "第一轮 API 重启失败"
}

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode verify-after-restart `
    -StatePath $day17Run1State

$day17Run1FinishedAt = Get-Date

[pscustomobject]@{
    Run = 1
    StartedAt = $day17Run1StartedAt
    FinishedAt = $day17Run1FinishedAt
    DurationSeconds = [math]::Round(
        ($day17Run1FinishedAt - $day17Run1StartedAt).TotalSeconds,
        1
    )
    StatePath = $day17Run1State
    Completed = $true
} | Format-List
```

**这一步怎样工作**

- 输入：Day 16 的演示脚本、当前 Compose 服务和第一轮独立状态路径。
- 输出：第一轮动态知识库、四文档状态、跨文档来源、拒答和 API 重启后指纹。
- 调用谁：现有 FastAPI、Embedding、LLM、PostgreSQL/pgvector 和 Docker Compose。
- 被谁调用：最终复盘第一轮记录。
- 正常路径：四个阶段均以 0 退出，且不重新上传便通过重启验证。
- 失败路径：任何阶段非零即停止；记录真实错误，不进入第二轮制造“连续两次成功”。

**完成本步骤后的预期状态**

第一轮暴露出的口述卡顿、命令错误或事实不确定处已被识别；没有为追求“通过”隐藏失败。

### 步骤 4：只修阻塞与事实错误，再完成第二轮（建议 15 分钟）

**目标**

对第一轮问题进行最小修正，然后使用独立状态从头再跑一轮，并完成三分钟脱稿介绍。

**修改位置**

- 文件：优先只修改 `docs/final-reproduction-and-interview-review.md` 中的表述或 Day 16 演示材料
- 定位：第一轮真实记录中的卡顿或错误
- 操作：只修会阻塞演示或明显错误的内容；如果发现应用代码缺陷，停止并另行评估，不在未知范围内临时大改

第一轮修正前先检查边界：

```powershell
git status --short

git diff -- `
    docs\final-reproduction-and-interview-review.md `
    scripts\run_enterprise_rag_demo.ps1 `
    docs\demo-script.md `
    docs\resume-project-entry.md
```

第二轮执行：

```powershell
$day17Run2State = `
    "artifacts\demo\day17-run2-state.json"

$day17Run2StartedAt = Get-Date

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode prepare `
    -StatePath $day17Run2State

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode answerable `
    -StatePath $day17Run2State

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode refusal `
    -StatePath $day17Run2State

docker compose restart api
if ($LASTEXITCODE -ne 0) {
    throw "第二轮 API 重启失败"
}

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode verify-after-restart `
    -StatePath $day17Run2State

$day17Run2FinishedAt = Get-Date

[pscustomobject]@{
    Run = 2
    StartedAt = $day17Run2StartedAt
    FinishedAt = $day17Run2FinishedAt
    DurationSeconds = [math]::Round(
        ($day17Run2FinishedAt - $day17Run2StartedAt).TotalSeconds,
        1
    )
    StatePath = $day17Run2State
    Completed = $true
} | Format-List
```

**这一步怎样工作**

- 输入：第一轮复盘与第二轮独立状态路径。
- 输出：一套不复用第一轮动态 ID 的第二轮演示结果。
- 调用谁：与第一轮相同的真实组件。
- 被谁调用：最终文档第二轮记录与最终结论。
- 正常路径：第二轮独立创建数据并通过相同不变量。
- 失败路径：第二轮失败仍必须记录为失败；不能只保留第一轮或重新定义完成标准。

**完成本步骤后的预期状态**

如果两轮均完整成功且口述达标，最终文档可以把对应记录更新为真实结果；否则保持未完成并列出一个最小下一步。

### 步骤 5：核对数据库、测试、评测和最终表达（建议 10 分钟）

**目标**

用第二轮知识库做最终数据库与评测核对，再完成剩余随机追问，避免只凭演示印象给出结论。

**修改位置**

- 文件：`docs/final-reproduction-and-interview-review.md`
- 定位：第 7～9 节
- 操作：可选填入真实摘要、复盘和最终状态

**执行说明**

命令在项目根目录依次执行；评测输出写到本地演示目录，绝不覆盖已提交基线 JSON。

```powershell
$day17Run2 = Get-Content `
    -LiteralPath "artifacts\demo\day17-run2-state.json" `
    -Raw |
    ConvertFrom-Json

$day17KnowledgeBaseId = [int]$day17Run2.knowledge_base_id

$day17DatabaseUser = (
    docker compose exec -T postgres printenv POSTGRES_USER
).Trim()
$day17DatabaseName = (
    docker compose exec -T postgres printenv POSTGRES_DB
).Trim()

$day17DatabaseSql = @"
SELECT
    kb.id AS knowledge_base_id,
    COUNT(DISTINCT d.id) AS document_count,
    COUNT(DISTINCT d.id) FILTER (
        WHERE d.status = 'ready'
    ) AS ready_document_count,
    COUNT(c.id) AS chunk_count,
    MIN(vector_dims(c.embedding)) AS min_vector_dims,
    MAX(vector_dims(c.embedding)) AS max_vector_dims
FROM knowledge_bases AS kb
JOIN documents AS d
    ON d.knowledge_base_id = kb.id
JOIN chunks AS c
    ON c.document_id = d.id
WHERE kb.id = $day17KnowledgeBaseId
GROUP BY kb.id;
"@

$day17DatabaseSql |
    docker compose exec -T postgres `
        psql `
        -v ON_ERROR_STOP=1 `
        -U $day17DatabaseUser `
        -d $day17DatabaseName

if ($LASTEXITCODE -ne 0) {
    throw "Day 17 数据库摘要查询失败"
}

.\.venv\Scripts\python.exe `
    scripts\validate_enterprise_questions.py
if ($LASTEXITCODE -ne 0) {
    throw "固定数据集校验失败"
}

.\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "pytest 存在失败用例"
}

.\.venv\Scripts\python.exe `
    scripts\run_evaluation.py `
    --knowledge-base-id $day17KnowledgeBaseId `
    --dataset data\evaluation\enterprise_questions.json `
    --output artifacts\demo\day17-final-evaluation.json `
    --repetitions 2
if ($LASTEXITCODE -ne 0) {
    throw "最终评测存在运行故障"
}

$day17FinalReport = Get-Content `
    -LiteralPath `
        "artifacts\demo\day17-final-evaluation.json" `
    -Raw |
    ConvertFrom-Json

[pscustomobject]@{
    CaseCount = $day17FinalReport.summary.case_count
    CompletedCaseCount = `
        $day17FinalReport.summary.completed_case_count
    FailedCaseCount = `
        $day17FinalReport.summary.failed_case_count
    RecallAt3 = `
        $day17FinalReport.summary.retrieval.'3'.recall_at_k
    MrrAt3 = `
        $day17FinalReport.summary.retrieval.'3'.mrr_at_k
    P95Milliseconds = `
        $day17FinalReport.summary.retrieval_latency_ms.p95_ms
    QualityFailureCount = @(
        $day17FinalReport.failure_cases
    ).Count
} | Format-List
```

**这一步怎样工作**

- 输入：第二轮动态知识库、冻结 PDF/问题集和当前代码。
- 输出：真实 Document/Chunk/vector 维度摘要、pytest 结果和独立最终评测。
- 调用谁：PostgreSQL、pgvector、数据校验脚本、pytest 和评测脚本。
- 被谁调用：最终文档的测试/评测摘要和结论。
- 正常路径：4 个 Document 都 ready，Chunk 大于 0，向量维度最小/最大都是 512，数据校验/pytest/评测退出码为 0。
- 失败路径：任何命令失败都保留输出并停止更新“最终完成”；不能覆盖已提交报告或改题美化指标。

**完成本步骤后的预期状态**

最终文档的结论可以回溯到本次真实运行与当前仓库；实际结果是否详细回填可选，但不得把未执行写成通过。

## 六、运行数据库迁移或环境命令

今天不涉及数据库结构变更，不生成 Alembic revision，不执行 downgrade。Day 17 只检查现有迁移 head、运行环境和第二轮演示数据。

### 1. 检查当前状态

Day 16 完成后，在项目根目录执行：

```powershell
git status --short
docker compose config --quiet
docker compose ps --all
docker compose exec -T api alembic current

$day17Health = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get

$day17Health | ConvertTo-Json
```

执行顺序：先确认 Git 边界，再核对 Compose 配置和容器，最后确认迁移及数据库感知健康检查。

失败时检查：如果 `migrate` 未成功或 API 未健康，查看 `docker compose logs --tail 100 migrate api`；不删除 Volume，不打印真实 `.env`。

### 2. 执行升级

Day 17 没有代码或 Schema 升级。需要的环境启动命令是：

```powershell
docker compose up --build -d
docker compose ps --all
```

随后严格执行第五节的 Day 16 前置检查、两轮演示和最终数据库/测试/评测核对。

### 3. 回滚并恢复

今天不执行数据库回滚。两轮演示知识库和本地评测报告可以保留给复盘，不删除数据库 Volume，也不批量删除文件。

如果只修正文档口述错误，直接编辑明确文档并重新复述；如果发现应用代码缺陷，先停止最终验收，单独定位和修复后只重跑受影响测试，再从失败的完整演示轮次重新开始。

### 预期结果

- Alembic 当前 head 仍为 `e780fe92751b`。
- `/health` 预期 `status=ok`、`database_connected=true`；生成式回答还需要 `llm_configured=true`。
- 今天不新增表、列、索引或迁移文件。
- 本地 Day 17 状态与评测 JSON 不进入 Git。

## 七、验证正常路径

### 启动或准备服务

先完成 Day 16 并确认其四个产物存在，再启动现有 Compose 环境：

```powershell
docker compose up --build -d
docker compose ps --all
```

首次模型加载或容器构建等待不计入核心口述时间，但必须等 API 真实健康后再开始。

### 执行正常请求或测试

正常路径由以下四部分组成，必须按顺序执行：

```powershell
# 1. 第一轮完整演示
$day17Run1State = "artifacts\demo\day17-run1-state.json"
.\scripts\run_enterprise_rag_demo.ps1 -Mode prepare -StatePath $day17Run1State
.\scripts\run_enterprise_rag_demo.ps1 -Mode answerable -StatePath $day17Run1State
.\scripts\run_enterprise_rag_demo.ps1 -Mode refusal -StatePath $day17Run1State
docker compose restart api
.\scripts\run_enterprise_rag_demo.ps1 -Mode verify-after-restart -StatePath $day17Run1State

# 2. 第二轮完整演示，使用独立状态
$day17Run2State = "artifacts\demo\day17-run2-state.json"
.\scripts\run_enterprise_rag_demo.ps1 -Mode prepare -StatePath $day17Run2State
.\scripts\run_enterprise_rag_demo.ps1 -Mode answerable -StatePath $day17Run2State
.\scripts\run_enterprise_rag_demo.ps1 -Mode refusal -StatePath $day17Run2State
docker compose restart api
.\scripts\run_enterprise_rag_demo.ps1 -Mode verify-after-restart -StatePath $day17Run2State

# 3. 固定数据和自动测试
.\.venv\Scripts\python.exe scripts\validate_enterprise_questions.py
.\.venv\Scripts\python.exe -m pytest -q

# 4. 核对最终文档仍诚实记录当前状态
Select-String `
    -LiteralPath "docs\final-reproduction-and-interview-review.md" `
    -Pattern "两轮演示|最终状态|当前限制|0.55|0.65"
```

### 预期状态码或输出结构

两轮的 ID、回答、分数与耗时属于动态值；每轮的稳定不变量应是：

```json
{
  "run_1": {
    "ready_document_count": 4,
    "answerable_refused": false,
    "required_source_document_count": 2,
    "unanswerable_refused": true,
    "unanswerable_source_count": 0,
    "document_ids_unchanged_after_api_restart": true
  },
  "run_2": {
    "ready_document_count": 4,
    "answerable_refused": false,
    "required_source_document_count": 2,
    "unanswerable_refused": true,
    "unanswerable_source_count": 0,
    "document_ids_unchanged_after_api_restart": true
  },
  "dataset_validation": "预期退出码 0",
  "pytest": "预期 7 passed",
  "oral_review": "一分钟和三分钟均能不看代码完成"
}
```

### 为什么它能证明今天已经完成

两轮独立状态排除偶然成功；回答题、拒答题和重启指纹覆盖核心正常与边界数据流；数据库查询证明四文档和 512 维向量真实存在；pytest 和评测分别核对业务规则与质量结果；脱稿口述及随机追问验证用户不是只会运行脚本。它们共同支撑“可演示、可解释、可追问”。

## 八、验证失败和边界路径

### 场景：面试中把离线建议阈值 `0.65` 说成已部署，事实防伪检查必须失败

在项目根目录执行下面的只读检查。它从当前源码和结构化报告提取两个阈值，并故意验证错误声明，不修改应用或数据库：

```powershell
$day17ServiceSource = Get-Content `
    -LiteralPath `
        "app\services\database_rag_service.py" `
    -Raw

$day17ThresholdMatch = [regex]::Match(
    $day17ServiceSource,
    'MIN_RELEVANCE_SCORE\s*=\s*([0-9.]+)'
)
if (-not $day17ThresholdMatch.Success) {
    throw "无法从当前 Service 提取生产阈值"
}

$day17ProductionThreshold = [double](
    $day17ThresholdMatch.Groups[1].Value
)

$day17CommittedReport = Get-Content `
    -LiteralPath `
        "data\evaluation\enterprise_evaluation_report.json" `
    -Raw |
    ConvertFrom-Json

$day17OfflineThreshold = [double](
    $day17CommittedReport.summary.selected_parameters.threshold
)

$day17IntentionallyWrongClaim = 0.65

if (
    $day17IntentionallyWrongClaim -ne
    $day17ProductionThreshold
) {
    throw (
        "检测到错误面试表述：声称生产阈值=" +
        "$day17IntentionallyWrongClaim，实际生产阈值=" +
        "$day17ProductionThreshold，离线建议=" +
        "$day17OfflineThreshold"
    )
}
```

### 预期结果

- HTTP 状态码或异常：PowerShell 抛出“检测到错误面试表述”，并明确生产 `0.55`、离线建议 `0.65`；退出状态为非零。
- 数据库应该保留：所有知识库、Document、Chunk、向量和迁移版本原样保留。
- 数据库不应该存在：该只读检查不创建或修改任何记录，也不执行 commit/rollback。
- 响应不能泄露：不得出现 `.env`、LLM API Key、数据库密码、完整数据库 URL、真实企业内容或驱动堆栈。

这条失败路径验证 Day 17 的核心边界：面对面试追问必须区分代码当前事实、离线实验建议和未来设想，不能为了显得完成度更高而合并三者。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| 前置检查立即失败 | Day 16 只生成了计划，脚本、视频或简历条目尚未完成 | 执行步骤 1 的路径清单；查看 `Day16.md` 可选记录 | 先按 Day16 手册完成真实产物；不要绕过检查或创建空视频文件 |
| 第一轮成功、第二轮失败 | 外部 LLM 波动、API 重启未恢复、状态路径混用或数据处理失败 | `docker compose logs --tail 100 api`；核对两个 state 路径 | 记录第二轮失败，修复真实原因后从第二轮 prepare 重新完整运行，不复用第一轮结果 |
| 跨文档题少一个目标来源 | PDF/模型/切块变化，或不是固定 Top-3 问题 | `validate_enterprise_questions.py`；源报告中的 `cross-procurement-payment-01` | 停止验收，确认冻结语料哈希与当前模型；不删来源断言、不换简单题掩盖问题 |
| 无答案题触发 LLM 或返回来源 | 阈值/拒答逻辑变化，或请求用了旧 FAISS 路由 | `app/services/database_rag_service.py`；检查 URL 必须是知识库 query 路由 | 修复或恢复数据库版拒答路径并重跑相关 pytest，再重跑完整演示轮次 |
| API 重启后 Document ID 改变 | 重跑了 prepare、状态文件被覆盖或数据库/Compose 项目切换 | 比较 `day17-runN-state.json` 与同轮文档列表 | 同一轮只在最开始 prepare；重启后禁止上传，不能手改状态 JSON |
| 数据库查询没有 4 个 ready 文档 | 第二轮入库未完成、选择错知识库 ID或存在 failed 状态 | 步骤 5 SQL；文档列表 API | 保留 failed 证据并定位入库日志；修复后新开一轮，不把状态直接改成 ready |
| pytest 收集数不是 7 | 测试文件后来变化、依赖不一致或参数化未收集 | `python -m pytest --collect-only -q`；`requirements-test.txt` | 以当前真实收集数为准更新文档；任何失败用例先修复，不能只改预期数字 |
| 最终评测 P95 与基线不同 | 机器负载、缓存或环境变化；延迟本来就是动态值 | 对比两份报告的 `experiment` 和 `retrieval_latency_ms` | 如实记录本次值和环境，不为了对齐 15.2546 ms 重跑筛选最好结果 |
| 口述时把 Recall 说成准确率 | 混淆证据召回与答案质量 | 复盘第 1、6 节；`docs/evaluation-report.md` | 固定说“18 题小数据集上的证据 Recall@3”，并说明评测不调用 LLM |
| 说 pgvector 一定比 FAISS 快 | 把架构选择误说成性能结论 | README 的关键选择和限制 | 改为“主要解决持久化、过滤和一致性”；性能必须用同规模基准另行比较 |
| 被问生产能力时过度承诺 | 没有主动说明认证、异步、ANN、监控和压测缺失 | 复盘第 6 节“不能说成事实” | 用“当前适用范围 + 风险 + 按真实需求排序的下一步”回答，不临时加功能 |
| Git diff 混入 Day16 或本地产物 | Day16 仍未提交，或没有按明确文件 add | `git status --short`、`git check-ignore -v artifacts\demo\day17-run1-state.json` | Day17 只 add 两个明确 Markdown；先单独完成/提交 Day16，不使用 `git add .` |

## 十、检查最终代码差异

```powershell
git status --short

git diff -- `
    docs\final-reproduction-and-interview-review.md `
    docs\17天每日学习\Day17.md

git check-ignore -v `
    artifacts\demo\day17-run1-state.json `
    artifacts\demo\day17-run2-state.json `
    artifacts\demo\day17-final-evaluation.json
```

重点检查：

- Day 17 diff 只包含最终复盘和 Day17 手册，不包含未提交的 Day16 计划、Day16 脚本/文档、MP4 或其他用户文件。
- 实际未运行的项仍为“未执行”，没有提前勾选两轮演示成功、pytest 通过或评测完成。
- 一分钟和三分钟口述与当前代码一致，包含两条主链路、事务、拒答、来源、评测和限制。
- 文档明确区分生产阈值 `0.55` 与离线建议 `0.65`。
- `97.22%` 只称为证据 Recall@3，`15.25 ms` 只称为预热检索 P95。
- 保留两个真实质量失败案例，没有声称所有跨文档问题都完整命中。
- 未读取、打印或提交 `.env`、密码、API Key、完整数据库 URL 或个人隐私。

## 十一、Git 提交

Day 17 最终文档完成并检查 diff 边界后即可执行；Day 16 应由用户之后按其独立文件清单先行完成和提交，当前未提交的 `Day16.md` 不属于本次 `git add`：

```powershell
git status --short

git diff -- `
    docs\final-reproduction-and-interview-review.md `
    docs\17天每日学习\Day17.md

git add `
    docs\final-reproduction-and-interview-review.md `
    docs\17天每日学习\Day17.md

git commit -m "docs: complete final RAG reproduction and interview review"
```

如果 Day 16 文件此时仍未提交，它们会继续出现在 `git status`，但上面的明确文件清单不会暂存它们；不要使用 `git add .`。实际运行若发现已知失败，应先修复并重跑对应完整轮次，再提交最终“完成”结论。

## 十二、面试高频问题与参考答案

### 问题 1：请从一次 PDF 上传讲清整个数据流和事务边界？

#### 30 秒参考答案

FastAPI 收到指定知识库的 PDF 后，先做文件名、扩展名和空内容校验，再由 DocumentIngestionService 创建并提交 processing Document，获得稳定 ID。随后 PDFService 按页解析，使用 200/40 重叠切块，EmbeddingService 批量生成归一化 512 维向量，Repository 在一个事务中写入全部 Chunk 并把 Document 更新为 ready。任何处理中异常都会先 rollback 未提交 Chunk 和 ready 更新，再单独保存 failed 状态；检索只查 ready 文档，因此半成品不会进入回答。

#### 继续追问：为什么不把 processing Document 也放在同一个事务？

当前同步实现希望处理失败后仍保留稳定 Document ID 和可观察失败记录，所以先提交 processing。代价是它不是单一大事务，但核心一致性由“Chunk + ready 同事务、失败先 rollback、failed 单独提交、检索只看 ready”保证。若后续异步化，应进一步引入任务状态、幂等键和重试策略。

#### 回答时要引用的项目依据

- `app/services/document_ingestion_service.py`
- `app/repositories/document_repository.py`
- `app/repositories/chunk_repository.py`
- `docs/architecture.md` 的入库时序

### 问题 2：为什么选择 PostgreSQL + pgvector，而不是继续使用 FAISS？

#### 30 秒参考答案

早期 FAISS 版本只在内存保存最近一次上传，重启丢失，而且向量位置与 Python 元数据依赖额外映射。pgvector 让知识库、文档状态、页码、Chunk 原文和向量进入同一 PostgreSQL 体系，可以在 SQL 层同时做知识库范围、ready 状态和相似度排序，并复用事务、迁移和 Volume 持久化。这个选择主要解决一致性、过滤和恢复，不是声称 pgvector 一定比 FAISS 快。

#### 继续追问：语料扩大后会怎样优化？

当前查询是精确余弦距离，没有 HNSW/IVFFlat。语料扩大后我会先建立真实规模基线，比较 Recall、P95、索引构建、内存和带过滤查询行为，再选择 pgvector ANN、reranker 或独立向量服务；不能只因为技术流行就提前加索引。

#### 回答时要引用的项目依据

- `app/orm_models.py` 的 `Vector(512)`
- `app/repositories/chunk_repository.py`
- `docker-compose.yml` 的 `postgres_data`
- README 的已知限制

### 问题 3：怎样解释评测指标，又不夸大结果？

#### 30 秒参考答案

我的固定语料是 4 份两页虚构制度，问题集有 12 道可回答题和 6 道无答案题。Top-3 的证据 Recall 是 97.22%，MRR 是 95.83%；36 个预热 Query Embedding 加 pgvector 查询样本 P95 是 15.25 毫秒。评测不调用 LLM，所以这些数值不是最终答案准确率或端到端 SLA；报告还保留一个跨文档证据不完整和一个高阈值误拒答案例。

#### 继续追问：为什么报告推荐 0.65，生产仍是 0.55？

0.65 在候选参数中提高无答案拒答表现，但 `direct-hotel-01` 的最高来源分数只有 0.638058，会让可回答题误拒答。离线建议需要扩大样本并经过独立代码配置和回归后才能上线，所以当前代码仍是 0.55，不能把报告建议写成部署事实。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json`
- `data/evaluation/enterprise_evaluation_report.json`
- `docs/evaluation-report.md`
- `app/services/database_rag_service.py`

### 问题 4：自动测试、离线评测和两轮演示分别证明什么？

#### 30 秒参考答案

7 个 pytest case 快速固定输入范围、来源映射、低分拒答、知识库隔离、状态过滤、Top-K 和排序；18 题离线评测在不调用 LLM 的情况下比较 Recall、MRR、阈值分类和检索延迟；两轮演示则覆盖真实 HTTP、Embedding、LLM、PostgreSQL 和 API 重启。它们分别证明代码规则、检索质量和系统集成，不能用 pytest 通过代替持久化，也不能用一次视频代替质量评测。

#### 继续追问：为什么集成测试使用事务回滚？

每个集成测试需要真实 PostgreSQL + pgvector 行为，但不应污染共享数据库。测试由外层事务创建数据并在结束时 rollback，既能验证真实 SQL、过滤与排序，又能保持重复运行相对隔离。它仍不替代 Compose 重启和 Volume 恢复验收。

#### 回答时要引用的项目依据

- `tests/conftest.py`
- `tests/test_chunk_repository_integration.py`
- `scripts/run_evaluation.py`
- Day 13 与 Day 17 两轮演示记录

### 问题 5：你认为这个项目距离生产可用还差什么？

#### 30 秒参考答案

当前项目是可复现的小规模企业 RAG 后端，不是生产系统。主要缺口包括认证授权和租户边界、异步入库与幂等重试、备份恢复、日志指标和告警、限流与上游降级、ANN/reranker 及真实规模压测、LLM 答案质量评测。旧 FAISS 路由和旧 FastAPI 标题也需要后续清理。我会根据真实文档规模和岗位场景排序，而不是一次加入所有框架。

#### 继续追问：如果只能优先做一项，你选什么？

要看目标场景。如果先面向真实多用户，优先认证授权，因为知识库 ID 过滤不是访问控制；如果先接入大文档，优先异步任务、幂等和进度状态；如果语料规模已经让精确查询变慢，才根据基准选择 ANN。优先级应由风险和测量数据决定。

#### 回答时要引用的项目依据

- README 的安全边界与已知限制
- `app/main.py` 当前路由与 FastAPI metadata
- `docker-compose.yml`
- `docs/evaluation-report.md` 的结果适用范围

## 十三、今天的完整数据流

### 正常路径

```text
Day 16 脚本、视频和简历条目真实完成
→ Day 17 前置检查通过
→ 不看代码完成一分钟介绍
→ 第一轮独立知识库：4 PDF 入库 → 跨文档来源 → 拒答 → API 重启恢复
→ 回答随机追问并记录卡顿
→ 只修阻塞或事实错误
→ 不看代码完成三分钟介绍
→ 第二轮独立知识库重复完整流程
→ PostgreSQL 查询 4 个 ready Document、Chunk 和 512 维向量
→ 数据集校验 + 7 个 pytest case + 独立最终评测
→ 结合代码、报告和限制完成模拟面试
→ 更新最终复现与复盘文档
→ Git 只提交 Day 17 两个 Markdown 文件
```

### 失败路径

```text
Day 16 前置缺失，或任一轮出现服务、来源、拒答、重启、测试、评测或事实错误
→ 立即停止“最终完成”结论
→ 保留真实失败和数据库状态，不删 Volume、不改题、不伪造输出
→ 判断是环境、外部 LLM、脚本、口述事实还是应用缺陷
→ 只修阻塞或明显事实错误
→ 重跑受影响测试
→ 从失败的完整轮次重新开始
→ 未连续两次成功则最终状态保持未完成
```

## 十四、完成标准

```text
[ ] 能用“结论—原因—项目证据—限制”结构回答问题，并解释为什么限制不是失败而是适用范围
[ ] 能不看代码讲清 PDF 入库与知识库问答两条数据流，以及 API、Service、Repository、SQLAlchemy、psycopg、PostgreSQL/pgvector 和 Alembic 的职责
[ ] Day 16 的演示脚本、视频和独立简历条目已真实存在；Day 17 没有绕过前置检查
[ ] docs/final-reproduction-and-interview-review.md 已包含事实卡、一分钟/三分钟口述、两轮记录、追问卡、限制和复盘
[ ] 已连续完成两轮独立演示，每轮均有 4 个 ready 文档、两个目标跨文档来源、正确拒答和 API 重启后不变的 Document ID
[ ] 已提供 PostgreSQL 数据摘要、数据集校验、pytest 和独立最终评测命令及预期结果；详细实际输出和回填可选
[ ] 已提供“0.65 已部署”错误表述的只读失败验证，预期非零退出、数据库零写入且不泄露秘密
[ ] 能准确解释 Recall@K、MRR、拒答正确率和检索 P95，不把它们说成答案准确率或生产 SLA
[ ] 能主动说明文本型 PDF、同步入库、无认证、无 ANN、无生产压测和旧路由/标题等当前限制，并给出按场景排序的后续方向
[ ] 能不看代码复述“Day16 前置 → 两轮演示 → 数据库/测试/评测 → 模拟追问 → 最终复盘”的完整验收数据流
[ ] git diff 只包含 Day17 手册和最终复盘，不包含未提交 Day16 文件、本地产物、秘密或无关修改
[ ] 核心复盘完成后可使用明确文件清单提交，不以粘贴完整日志、截图或评测输出为前提
```

## 十五、可选执行记录

- 实际完成：未执行
- Day 16 前置检查：未执行
- 第一轮演示：未执行
- 第二轮演示：未执行
- 一分钟 / 三分钟脱稿口述：未执行
- 数据库 / pytest / 评测摘要：可选，不要求填写
- 模拟面试卡顿与改进：可选，不要求填写
- 用户完成标记：待用户自行填写
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：未提交
