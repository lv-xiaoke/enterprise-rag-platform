# Enterprise RAG Platform 评测报告

> 数据集版本：`2026-09-04-v1`  
> 语料版本：`2026-09-04-v1`  
> 源报告生成时间：`2026-09-06T02:10:21.856522+00:00`  
> 结构化事实来源：[`data/evaluation/enterprise_evaluation_report.json`](../data/evaluation/enterprise_evaluation_report.json)

## 1. 结论摘要

本次评测在 4 份两页虚构企业制度 PDF、12 道可回答题和 6 道无答案题上，复用当前 PostgreSQL + pgvector 检索链路完成了 Top-K、拒答阈值、排序稳定性和检索延迟实验。

- 18/18 道题完成，运行故障数为 0。
- Top-3 的 Recall@3 为 `0.972222`，MRR@3 为 `0.958333`，完整证据题占比为 `0.916667`。
- Top-5 没有比 Top-3 提高 Recall、MRR 或完整证据题占比，因此当前数据上没有增加 K 的收益。
- 固定选参规则推荐 `Top-K=3、threshold=0.65`。
- 推荐组合的平衡拒答准确率为 `0.958333`，总体拒答正确率为 `0.944444`。
- 36 个预热后检索样本的平均延迟为 `12.797136 ms`，P95 为 `15.2546 ms`。
- 18 道题两次重复检索的排序均稳定。
- 报告保留 2 个真实质量失败案例，没有删题或修改标签美化指标。

这些结论只适用于当前冻结小数据集。评测不调用 LLM，因此不能解释为最终答案正确率或端到端延迟。

## 2. 评测对象

### 语料

| 文件 | 页数 | 内容领域 |
| --- | ---: | --- |
| `员工请假与考勤制度.pdf` | 2 | 考勤、年假、病假、出差衔接 |
| `差旅与费用报销制度.pdf` | 2 | 差旅审批、住宿交通、报销、采购付款 |
| `采购与办公资产管理制度.pdf` | 2 | 采购报价、紧急采购、验收、资产登记 |
| `访客与会议室管理办法.pdf` | 2 | 访客预约、陪同、离场、会议室使用 |

全部资料位于 [`data/demo_policies/pdfs/`](../data/demo_policies/pdfs/)，内容均为公开演示而虚构。

### 问题集

[`data/evaluation/enterprise_questions.json`](../data/evaluation/enterprise_questions.json) 固定了：

- 12 道可回答题，覆盖直接事实、知识库隔离、综合题和跨文档题。
- 6 道无答案题，固定 `expected_refusal=true`。
- 每道可回答题使用文件名、页码和原文锚点定义预期证据，不依赖每次入库会变化的 Chunk ID。
- 候选参数在实验前固定为 `Top-K ∈ {1, 3, 5}`、`threshold ∈ {0.45, 0.55, 0.65}`。

## 3. 实验链路与口径

```text
固定问题
→ BAAI/bge-small-zh-v1.5 Query Embedding
→ 指定 KnowledgeBase + ready 状态过滤
→ pgvector 余弦距离 Top-5
→ 切分 Top-1 / Top-3 / Top-5
→ 匹配预期文件、页码和原文锚点
→ 计算 Recall@K、MRR@K 和完整证据率
→ 各 K 下应用三个阈值并计算拒答分类
→ 汇总延迟、重复稳定性、失败案例与选参结论
```

延迟范围只包括预热后的：

```text
Query Embedding + PostgreSQL/pgvector Top-K 查询
```

不包括模型首次加载、HTTP、LLM Prompt、LLM 生成和响应序列化。

每道题重复检索 2 次，共记录 36 个延迟样本。一次查询先取最大 Top-5，较小 K 使用同一排序前缀，避免为不同 K 重复查询造成不可比较的排序或计时。

## 4. 检索结果

| Top-K | Recall@K | MRR@K | 完整证据题占比 |
| ---: | ---: | ---: | ---: |
| 1 | 0.616667 | 0.916667 | 0.416667 |
| 3 | 0.972222 | 0.958333 | 0.916667 |
| 5 | 0.972222 | 0.958333 | 0.916667 |

解释：

- `Recall@K` 计算每道可回答题在前 K 条中找回的预期证据比例，再对 12 道可回答题求平均。
- `MRR@K` 使用第一条正确证据倒数排名，反映正确证据是否足够靠前。
- 完整证据题占比要求一道题的全部预期证据都进入前 K 条，跨文档题因此比单事实题更严格。
- Top-1 的 MRR 已较高，但 Recall 和完整证据率明显偏低，说明第一条正确证据常排得靠前，却不足以覆盖综合/跨文档题的全部证据。
- Top-5 与 Top-3 完全相同，说明当前冻结语料上增加两个 Context 没有提高证据覆盖，只会增加后续 Prompt 长度。

## 5. 拒答参数实验

| Top-K | Threshold |  总体拒答正确率 |   可回答接受率 |   无答案拒答率 |  平衡拒答准确率 |
| ----: | --------: | -------: | -------: | -------: | -------: |
|     1 |      0.45 | 0.777778 | 1.000000 | 0.333333 | 0.666667 |
|     1 |      0.55 | 0.888889 | 1.000000 | 0.666667 | 0.833333 |
|     1 |      0.65 | 0.944444 | 0.916667 | 1.000000 | 0.958333 |
|     3 |      0.45 | 0.777778 | 1.000000 | 0.333333 | 0.666667 |
|     3 |      0.55 | 0.888889 | 1.000000 | 0.666667 | 0.833333 |
|     3 |      0.65 | 0.944444 | 0.916667 | 1.000000 | 0.958333 |
|     5 |      0.45 | 0.777778 | 1.000000 | 0.333333 | 0.666667 |
|     5 |      0.55 | 0.888889 | 1.000000 | 0.666667 | 0.833333 |
|     5 |      0.65 | 0.944444 | 0.916667 | 1.000000 | 0.958333 |

选参规则依次最大化：

1. 平衡拒答准确率。
2. Recall@K。
3. 总体拒答正确率。
4. 与当前参考阈值 `0.55` 的距离。
5. 更小的 Top-K。

因此报告推荐：

```text
Top-K = 3
threshold = 0.65
```

重要边界：`app/services/database_rag_service.py` 当前仍定义 `MIN_RELEVANCE_SCORE = 0.55`。`0.65` 是离线实验建议，并未自动写回生产代码；在独立参数变更、测试与回归完成前，不能把它描述成已上线配置。

## 6. 检索延迟

| 指标 | 毫秒 |
| --- | ---: |
| 样本数 | 36 |
| Mean | 12.797136 |
| P50 | 12.863950 |
| P95 | 15.254600 |
| Max | 15.385700 |

这是一组本地小样本基线，只能用于当前版本比较。报告没有记录可支撑生产容量结论的并发、硬件隔离、长时间稳定性或大规模语料数据，因此不能把 P95 写成服务 SLA。

## 7. 稳定性与失败案例

两次重复中，18 道题的检索结果均稳定，`unstable_case_ids` 为空。

报告仍保留两个质量失败案例：

### `cross-trip-01`

- 类型：跨文档题。
- 原因：`incomplete_evidence_recall:0.666667`。
- 含义：Top-3 已找回部分相关证据，但只覆盖了预期证据的三分之二，说明跨制度问题仍可能缺少一条关键来源。
- 后续方向：检查 Chunk 边界、查询表达和跨文档证据召回；不能只因首条来源相关就把整题判为完全命中。

### `direct-hotel-01`

- 类型：直接事实题。
- 原因：`refusal_classification_mismatch`。
- 最高来源分数：`0.638058`。
- 含义：在推荐阈值 `0.65` 下，这道实际可回答题会被错误拒答，体现“提高无答案拒答率”与“保留可回答题”之间的真实权衡。
- 后续方向：扩大验证集后再决定是否把阈值同步到生产，必要时按题型、校准分数或加入 reranker，而不是静默修改标签。

## 8. 怎样复现

前提：PostgreSQL 已迁移到 head，目标知识库中 4 份冻结 PDF 均为 `ready`。

```powershell
.\.venv\Scripts\python.exe scripts\validate_enterprise_questions.py

.\.venv\Scripts\python.exe scripts\run_evaluation.py `
    --knowledge-base-id <目标知识库的动态整数ID> `
    --dataset data\evaluation\enterprise_questions.json `
    --output data\evaluation\enterprise_evaluation_report.json `
    --repetitions 2
```

运行前若要保留现有基线，请把 `--output` 改为一个新的明确文件名，不要覆盖已提交报告。退出码为 0 表示 18 题都完成；质量失败案例允许存在并必须保留。检索异常导致 `failed_case_count > 0` 时脚本退出码应为 1，不能把该报告当作成功基线。

## 9. 结果适用范围

可以据此说明：

- 当前 PostgreSQL + pgvector 检索链路能在固定知识库内稳定返回可追溯来源。
- Top-3 在当前语料上明显优于 Top-1，并且与 Top-5 达到相同证据覆盖。
- 更高阈值提高无答案拒答率，但已出现一个可回答题被错误拒答。
- 当前环境中的预热检索延迟为十几毫秒量级。

不能据此说明：

- 最终 LLM 答案达到 `97.22%` 正确率。
- 任何真实企业文档或长文档都会得到同样结果。
- 当前 P95 是生产 SLA。
- 推荐阈值 `0.65` 已部署。
- 系统已完成认证、权限、高并发或大规模向量索引验证。

## 10. 证据索引

- 固定数据集：[`data/evaluation/enterprise_questions.json`](../data/evaluation/enterprise_questions.json)
- 结构化报告：[`data/evaluation/enterprise_evaluation_report.json`](../data/evaluation/enterprise_evaluation_report.json)
- 评测脚本：[`scripts/run_evaluation.py`](../scripts/run_evaluation.py)
- 数据校验脚本：[`scripts/validate_enterprise_questions.py`](../scripts/validate_enterprise_questions.py)
- 检索 Service：[`app/services/retrieval_service.py`](../app/services/retrieval_service.py)
- pgvector 查询：[`app/repositories/chunk_repository.py`](../app/repositories/chunk_repository.py)
- 当前拒答阈值：[`app/services/database_rag_service.py`](../app/services/database_rag_service.py)