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