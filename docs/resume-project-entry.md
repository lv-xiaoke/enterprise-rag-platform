# 企业 RAG 项目简历条目

本文件只提供可核对的项目表述与证据索引。**不要自动合并到任何现有简历**，按需整段复制。

---

## 一、可直接使用版本（主推 4 条）

### 2026.08–2026.09｜企业制度与 SOP 智能知识库 RAG 后端｜独立开发

**技术栈**：Python、FastAPI、PostgreSQL 16、pgvector、SQLAlchemy 2.0、Alembic、BGE Embedding、pytest、Docker Compose  
**项目地址**：<https://github.com/lv-xiaoke/enterprise-rag-platform>

- 独立实现多知识库 RAG 后端：PDF 按页解析、`200/40` 重叠切分、512 维归一化向量持久化到 PostgreSQL + pgvector，在指定知识库内完成余弦 Top-K 检索，对外提供 7 个知识库相关接口，响应携带文档名、页码与 Chunk 原文来源。
- 设计 `KnowledgeBase → Document → Chunk` 三层模型与 `pending/processing/ready/failed` 状态机，用 Alembic 管理建表、约束与索引迁移；入库采用两阶段提交——先落 `processing` 记录取得稳定 ID，再于同一事务批量写入 Chunk 并切 `ready`——失败时回滚半成品并单独提交安全的 `failed` 状态，使失败文档被检索层直接排除。
- 把知识库范围与 `status='ready'` 下推到 pgvector 查询的 SQL 层，而非先全库检索再在应用层过滤，避免跨库与未完成文档污染上下文；检索证据低于阈值时在调用 LLM 前拒答，返回固定文本与空来源，减少无证据生成和无效外部调用。
- 建立 4 份虚构制度、18 道固定问题（12 可答 + 6 无答案）的离线评测，完成 Top-K × 阈值参数网格实验：Top-3 的 Recall@3 `97.22%`、MRR@3 `95.83%`，优于 Top-1 的 `61.67%` / `91.67%` 且 Top-5 无额外增益，据此选定 `Top-K=3`；预热后检索样本 P95 `15.25 ms`，两次重复 18/18 排序稳定，保留 2 个真实失败案例未做删题美化；配 7 个 pytest case 覆盖输入边界、来源映射、阈值拒答、知识库隔离与文档状态过滤。

**投递建议**：如果一页简历空间紧张，优先保留第 2、4 条（可靠性设计 + 可核对的量化评测），它们最难被其他候选人复制。

## 二、压缩版（3 条，简历空间不足时用）

- 基于 FastAPI、BGE 与 PostgreSQL/pgvector 打通多知识库、多 PDF 的解析、`200/40` 重叠切分、512 维向量持久化、知识库范围 Top-K 检索与带来源问答，响应返回文档名、页码、Chunk 原文与相似度。
- 设计 `KnowledgeBase → Document → Chunk` 模型和 `processing/ready/failed` 状态边界，以 SQL 层范围过滤、两阶段入库事务和阈值前置拒答保证失败安全与来源可追溯；用 Alembic 与 Docker Compose 固化迁移和重启恢复流程。
- 建立 4 份两页虚构制度、18 道固定问题的离线评测：Top-3 Recall@3 `97.22%`、MRR@3 `95.83%`，预热后检索 P95 `15.25 ms`；编写 7 个 pytest case。

## 三、一行版（技能条或项目列表用）

独立开发企业制度 RAG 后端（FastAPI + PostgreSQL/pgvector + BGE）：三层数据模型与两阶段入库事务保证失败安全，SQL 层知识库/状态隔离与阈值前置拒答保证来源可追溯，18 题离线评测 Top-3 Recall@3 `97.22%`、检索 P95 `15.25 ms`，7 个 pytest case 回归。

---

## 四、简历表述 ↔ 代码/报告证据对照表

面试前对着这张表逐行核。**任何一行你无法在仓库里当场指出依据的，就从简历里删掉。**

| # | 简历表述 | 仓库依据 | 可核对的原始值 / 行为 |
| ---: | --- | --- | --- |
| 1 | 多知识库、多 PDF 上传与查询，7 个知识库接口 | `app/main.py:196-430`、`app/models.py` | `POST/GET /knowledge-bases`、文档上传与列表、`POST .../query`；README 接口表 |
| 2 | `200/40` 重叠切分 | `app/services/document_ingestion_service.py:17-18` | `DEFAULT_CHUNK_SIZE = 200`、`DEFAULT_CHUNK_OVERLAP = 40` |
| 3 | 512 维归一化向量 | `app/services/document_ingestion_service.py:19,271`、`app/services/retrieval_service.py:15,73` | `EMBEDDING_DIMENSION = 512`，写入前后各校验一次维度 |
| 4 | 三层数据模型与 `vector(512)` | `app/orm_models.py`、`migrations/versions/` | `751357b5d274`（vector 扩展）→ `e780fe92751b`（三张业务表） |
| 5 | 状态机与数据库约束 | `app/orm_models.py`、`docs/architecture.md` §5 | `ck_documents_status`、`uq_knowledge_bases_name`、`knowledge_base_id + status` 组合索引、同文档 `chunk_index` 唯一、级联删除 |
| 6 | 两阶段入库事务 | `app/services/document_ingestion_service.py:105,183,276` | 先提交 `status="processing"` 拿稳定 ID；Chunk 批量写入与切 `ready` 同事务；失败走 `_mark_document_failed` 只存安全原因 |
| 7 | SQL 层知识库 + `ready` 过滤 | `app/repositories/chunk_repository.py:66,73,98` | `search_similar()` 内 `Document.status == "ready"` 与知识库条件同时下推，`cosine_distance` 排序，`score = 1 - distance` |
| 8 | 阈值前置拒答 | `app/services/database_rag_service.py:12-13,68` | `MIN_RELEVANCE_SCORE = 0.55`；低于阈值直接返回 `REFUSAL_ANSWER`，**在 LLM 调用之前** |
| 9 | 失败安全与不泄漏内部信息 | `app/main.py:100-108,293-307`、`app/db.py:48-52` | 数据库异常统一 503 固定文本；处理失败返回 `文档处理失败` 而非驱动堆栈；`pool_pre_ping=True` |
| 10 | 4 份虚构制度 + 18 道题 | `data/demo_policies/pdfs/`、`data/evaluation/enterprise_questions.json` | 数据集版本 `2026-09-04-v1`；12 可答 + 6 无答案（`expected_refusal=true`） |
| 11 | Top-3 Recall@3 `97.22%` / MRR@3 `95.83%` | `docs/evaluation-report.md` §4、`data/evaluation/enterprise_evaluation_report.json` | `0.972222` / `0.958333`（12 道可答题平均） |
| 12 | Top-1 `61.67%` / `91.67%`，Top-5 无增益 | 同上 | `0.616667` / `0.916667`；Top-5 与 Top-3 三项指标完全相同 |
| 13 | 完整证据题占比 `91.67%` | 同上 | `0.916667`（全部预期证据进入前 K 的题占比） |
| 14 | 参数网格与选参规则 | `docs/evaluation-report.md` §5、`scripts/run_evaluation.py` | 3 个 Top-K × 3 个阈值共 9 组；五级 tie-break 规则；推荐 `Top-K=3, threshold=0.65` |
| 15 | P95 `15.25 ms` | `docs/evaluation-report.md` §6 | 36 个预热后样本，Mean `12.797136`、P50 `12.86395`、P95 `15.2546` |
| 16 | 两次重复 18/18 稳定 | `docs/evaluation-report.md` §7 | `unstable_case_ids` 为空 |
| 17 | 保留 2 个失败案例 | 同上 | `cross-trip-01`（`incomplete_evidence_recall:0.666667`）、`direct-hotel-01`（`refusal_classification_mismatch`，最高分 `0.638058`） |
| 18 | 7 个 pytest case | `tests/` | 5 个 `def test_` 函数，其中输入边界用例经 `@pytest.mark.parametrize` 展开 3 例，共 7 例；集成测试用外层事务 + 回滚 |
| 19 | Compose 迁移与重启持久化 | `docker-compose.yml`、`Dockerfile`、`docs/17天每日学习/Day13.md` | `postgres` healthy → `migrate` 执行 `alembic upgrade head` 后退出 → `api` 启动；命名卷 `postgres_data`、`huggingface_cache`；已完成三轮指纹一致的持久化验证 |

## 五、绝对不能写进简历的说法（红线）

| 禁止写法 | 为什么不能写 |
| --- | --- |
| 「答案准确率 97%」「问答准确率 97.22%」 | `97.22%` 是**检索 Recall@3**，评测链路不调用 LLM，衡量的是证据召回而非答案正确性 |
| 「有效降低幻觉」「显著提升准确率」 | 没有任何实验测量过加上拒答前后的幻觉率变化 |
| 「支持 OCR / 扫描件 / 复杂表格 / 多模态」 | `PDFService` 只调用 pypdf 抽取文字层 |
| 「高并发」「生产级」「QPS」「支撑千万级向量」 | 无并发压测、无硬件隔离、无 ANN 索引；评测是 4 份 PDF 的小样本基线 |
| 「权限控制」「租户隔离」 | 当前没有认证授权；知识库 ID 过滤是数据范围规则，不是访问控制 |
| 「已部署上线」「服务 SLA」 | 仅本地 Docker Compose 运行；P95 是本地小样本基线，报告明确写明不能当 SLA |
| 「阈值 0.65 已上线」 | 生产代码仍是 `0.55`；`0.65` 只是离线实验建议，未完成参数同步与回归 |
| 「异步任务 / Celery / 任务队列」 | 上传是同步请求，无后台任务状态机 |
| 「Elasticsearch / Milvus / Redis」等未使用的组件 | 技术栈里写没跑过的组件，一面就穿 |

## 六、面试时必须主动说明的指标口径

- `97.22%` 是固定小数据集上的**证据 Recall@3**，不是最终 LLM 答案准确率。
- `15.25 ms` 只包括预热后的 Query Embedding + pgvector 查询，不包括模型初始化、HTTP 和 LLM 生成，不是生产 SLA。
- 离线实验推荐 `Top-K=3、threshold=0.65`；当前生产代码仍使用阈值 `0.55`，不能说 `0.65` 已上线。
- 语料全部为公开虚构资料；系统当前只支持文本型 PDF，并且没有认证、异步任务、ANN 索引或大规模并发验证。
- 评测里 `direct-hotel-01` 在推荐阈值 `0.65` 下会被错误拒答（最高分 `0.638058`），这正是「提高无答案拒答率」与「保留可回答题」之间的真实权衡——主动讲这个案例比被追问出来好。

## 七、与企业办公 Agent 项目的边界

```text
本项目重点：数据模型、持久化、范围过滤、来源追溯、拒答、评测、测试和复现
Agent 项目重点：意图路由、工具选择、多步骤任务、结构化业务数据调用和交互
```

不要在两个项目中重复声称相同的 RAG、切分和 Top-K 成果；本条目回答的是「企业知识怎样可靠入库、检索、评测并跨重启保留」。

## 八、视频完成后再做

只有在视频真实生成并逐帧检查后，才把实际上传后的公开链接加入投递版简历；未上传时保留 GitHub 项目链接即可，不填写虚假或占位视频地址。
