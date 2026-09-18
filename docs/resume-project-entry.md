# 企业 RAG 项目简历条目

## 可直接使用版本

### 2026.08–2026.09｜企业制度与 SOP 智能知识库 RAG 后端｜独立开发

**技术栈**：Python、FastAPI、PostgreSQL、pgvector、SQLAlchemy、Alembic、BGE Embedding、pytest、Docker Compose  
**项目地址**：<https://github.com/lv-xiaoke/enterprise-rag-platform>

- 基于 FastAPI、BGE 和 PostgreSQL/pgvector 打通多知识库、多 PDF 的解析、`200/40` 重叠切分、512 维向量持久化、知识库范围 Top-K 检索和 LLM 问答，返回文档名、页码、Chunk 原文与相似度来源。
- 设计 `KnowledgeBase → Document → Chunk` 数据模型和 `processing/ready/failed` 状态边界，以 SQL 层知识库/状态过滤、事务回滚和阈值前置拒答避免跨库结果及不可检索半成品；使用 Alembic 与 Docker Compose 固化迁移和重启恢复流程。
- 建立 4 份两页虚构制度、18 道固定问题的离线评测：Top-3 Recall@3 为 `97.22%`、MRR@3 为 `95.83%`，36 个预热后 Query Embedding + pgvector 检索样本 P95 为 `15.25 ms`；编写 7 个 pytest case 覆盖输入边界、来源、拒答、知识库隔离、文档状态、Top-K 与排序。

## 面试时必须主动说明的指标口径

- `97.22%` 是固定小数据集上的证据 Recall@3，不是最终 LLM 答案准确率。
- `15.25 ms` 只包括预热后的 Query Embedding + pgvector 查询，不包括模型初始化、HTTP 和 LLM 生成，不是生产 SLA。
- 离线实验推荐 `Top-K=3、threshold=0.65`；当前生产代码仍使用阈值 `0.55`，不能说 `0.65` 已上线。
- 语料全部为公开虚构资料；系统当前只支持文本型 PDF，并且没有认证、异步任务、ANN 索引或大规模并发验证。

## 与企业办公 Agent 项目的边界

```text
本项目重点：数据模型、持久化、范围过滤、来源追溯、拒答、评测、测试和复现
Agent 项目重点：意图路由、工具选择、多步骤任务、结构化业务数据调用和交互
```

不要在两个项目中重复声称相同的 RAG、切分和 Top-K 成果；本条目回答的是“企业知识怎样可靠入库、检索、评测并跨重启保留”。

## 逐项证据映射

| 简历表述 | 仓库依据 |
| --- | --- |
| 多知识库、多文档 API | `app/main.py`、`app/models.py` |
| 三层数据模型与 `vector(512)` | `app/orm_models.py`、`migrations/versions/` |
| 入库事务和失败状态 | `app/services/document_ingestion_service.py` |
| 知识库与 ready 状态过滤 | `app/repositories/chunk_repository.py` |
| 来源与阈值前置拒答 | `app/services/database_rag_service.py` |
| 4 份两页虚构制度和 18 道题 | `data/demo_policies/`、`data/evaluation/enterprise_questions.json` |
| Recall、MRR 和 P95 | `data/evaluation/enterprise_evaluation_report.json`、`docs/evaluation-report.md` |
| 7 个 pytest case | `tests/test_models.py`、`tests/test_database_rag_service.py`、`tests/test_chunk_repository_integration.py` |
| Compose 迁移和持久化 | `docker-compose.yml`、`Dockerfile`、`docs/17天每日学习/Day13.md` |

## 视频完成后再做

只有在视频真实生成并逐帧检查后，才把实际上传后的公开链接加入投递版简历；未上传时保留 GitHub 项目链接即可，不填写虚假或占位视频地址。