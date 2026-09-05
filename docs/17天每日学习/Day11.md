# Day 11：改造企业版评测脚本并完成参数实验

今天将直接把旧的单 PDF FAISS 评测脚本改造成可重复运行的 PostgreSQL + pgvector 企业制度评测工具，使项目获得 Recall@1/3/5、MRR、拒答正确率与检索延迟报告，并为面试中的离线评测、阈值选择和实验可复现性问题提供可运行项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一个复用数据库检索链路的企业评测脚本，以及它生成的结构化参数实验报告  
> 当前真实状态：未开始  
> 对应总体安排：Day 11

## 一、今天完成后的项目变化

### 升级前

```text
scripts/run_evaluation.py
→ 读取旧 data/evaluation/questions.json
→ 调用旧 /upload 与 /rag/chat
→ 只面向最近一次内存 FAISS 索引
→ retrieval_hit 与 answer_correct 仍需人工填写
→ 不认识 KnowledgeBase、Document、Chunk 或 ready 状态
→ 不计算 Recall@1/3/5、MRR、阈值拒答正确率或 P95 延迟

data/evaluation/enterprise_questions.json
→ 已冻结 4 份企业制度 PDF、12 道可回答题、6 道无答案题
→ 已声明 Top-K 候选 1/3/5 和 threshold 候选 0.45/0.55/0.65
→ 尚无新架构运行结果
```

### 升级后

```text
冻结企业评测集 + 指定 KnowledgeBase
→ 校验 PDF 哈希、标签和候选参数
→ 确认该知识库恰好有 4 份 ready 冻结文档
→ SessionLocal + RetrievalService + pgvector
→ 每题重复检索两次并记录来源、分数与延迟
→ 由文件名 + 页码 + 原文锚点自动匹配 Ground truth
→ 计算 Recall@1/3/5、MRR@1/3/5
→ 比较 Top-K × threshold 的拒答分类结果
→ 输出平均、P50、P95、最大检索延迟
→ 自动保存失败案例、参数选择与选择理由
→ data/evaluation/enterprise_evaluation_report.json
```

### 今天在完整项目中的位置

- 所属阶段：质量验收。
- 所属链路：检索与拒答质量评测。
- 今天的输入：Day 9 冻结的 4 份 PDF、Day 10 固定评测集、已入库且状态为 `ready` 的 Document/Chunk，以及 Day 5/Day 7 的 pgvector 检索与拒答规则。
- 今天的输出：可重复运行的 `scripts/run_evaluation.py` 和包含逐题来源、参数矩阵、指标、延迟、失败案例与选参理由的 JSON 报告。
- 下一天为什么需要它：Day 12 要把已经明确的知识库隔离、状态过滤、Top-K、来源映射和拒答行为固化为 pytest 回归测试。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `data/evaluation/enterprise_questions.json` 已固定语料版本 `2026-09-04-v1`，包含 12 道可回答题、6 道无答案题、稳定证据锚点和参数候选。
- `[当前事实]` `scripts/validate_enterprise_questions.py` 能离线校验 JSON 结构、PDF SHA-256、证据页、原文锚点、题型数量和拒答标签，公开入口为 `validate_dataset(Path)`。
- `[当前事实]` `app/db.py` 提供 `SessionLocal`；`app/services/retrieval_service.py` 提供限定知识库的 Query Embedding 与 pgvector Top-K 检索。
- `[当前事实]` `app/repositories/chunk_repository.py` 只检索指定知识库中 `Document.status == "ready"` 的 Chunk，并把余弦距离转换为“越大越相关”的 `score = 1 - distance`。
- `[当前事实]` 当前 Query Embedding 模型是 `BAAI/bge-small-zh-v1.5`，输出 512 维归一化向量。
- `[当前事实]` 生产问答当前默认 `top_k=3`，参考拒答阈值为 `0.55`；Day 11 只比较参数并记录实验结论，不提前虚构更优值。
- `[当前事实]` Day 1～Day 10 均存在核心产物、用户完成标记和匹配提交；Day 10 匹配提交为 `6213618`。
- `[当前事实]` 生成本计划前 `git status --short` 无输出，工作区无已识别的未提交修改。

### 仍然缺少

- `[当前事实]` `scripts/run_evaluation.py` 仍调用旧 `/upload` 和 `/rag/chat`，只支持旧单 PDF FAISS 数据集。
- `[当前事实]` 当前脚本没有 `knowledge_base_id` 输入，不能验证评测语料是否属于同一个知识库，也不能复用 ready 状态过滤。
- `[当前事实]` 当前脚本没有自动证据匹配、Recall@K、MRR、拒答分类矩阵或延迟统计。
- `[当前事实]` 尚不存在 `data/evaluation/enterprise_evaluation_report.json`，仓库中也没有最终 Top-K、threshold、失败案例和选择理由的新架构报告。
- `[当前事实]` README 仍主要展示旧 FAISS 流程；README 与架构图的求职版更新属于 Day 15，不在今天扩展。

### 待实测

- `[待实测]` 学习数据库中用于评测的真实 `knowledge_base_id`、4 个动态 `document_id`、各文档 Chunk 数量和 ready 状态。
- `[待实测]` 18 道固定问题在当前 CPU/GPU 与 PostgreSQL 环境中的实际 Recall@1/3/5、MRR、拒答分类结果和延迟分布。
- `[待实测]` 两次重复检索的来源顺序是否稳定，以及哪些题属于未召回、部分召回、错误接受或错误拒答。
- `[待实测]` 候选参数中最终被脚本选中的 Top-K 和 threshold；生成计划时不能提前填写实际数值。

### 需要保护的用户修改

- 当前工作区干净；仍只操作今天的三个明确文件，不覆盖 `questions.json`、`baseline_results.json`、`top_k_comparison.json`、应用服务、迁移、演示 PDF 或其他学习笔记。
- `data/evaluation/enterprise_evaluation_report.json` 使用同名输出时会被新一次实验覆盖；需要保留历史运行时，应通过 `--output` 指定另一个明确文件名。

## 三、今天必须理解的核心知识

### 1. Recall@K 与 MRR 衡量的不是同一件事

- 一句话解释：Recall@K 衡量前 K 个结果找回了多少预期证据，MRR 衡量第一条正确证据排得有多靠前。
- 在当前项目中的职责：脚本用 `expected_evidence` 的文件名、页码和原文锚点匹配 `ChunkSearchResult`，不依赖每次入库都会变化的 Chunk ID。
- 与其他组件的关系：`RetrievalService` 给出排序结果，评测脚本切出 Top-1、Top-3、Top-5，再对相同排序计算指标。
- 容易混淆的点：跨文档题可能有多条预期证据；第一条正确证据排第 1 时 MRR 很高，但只找回其中一条时 Recall 仍可能小于 1。
- 面试一句话：我的 Recall@K 用“已命中证据数 / 预期证据数”衡量覆盖，MRR 用第一条命中证据的倒数排名衡量排序质量，两者组合可以区分“找得全”和“排得前”。

手算例子：一题有两条预期证据，分别出现在第 2 和第 5 名，则 `Recall@1=0`、`Recall@3=1/2`、`Recall@5=1`，`MRR@5=1/2`。

### 2. threshold 是拒答分类边界

- 一句话解释：即使问题没有答案，向量库通常仍会返回 Top-K；只有最高候选达到 threshold，系统才认为存在可用证据。
- 在当前项目中的职责：脚本对每个 `Top-K × threshold` 组合计算是否拒答，再与 `expected_refusal` 比较。
- 与其他组件的关系：这复现了 `DatabaseRAGService` 中 `score >= min_relevance_score` 的过滤语义，但不调用 LLM，因此不会把生成波动混入检索与拒答实验。
- 容易混淆的点：提高 threshold 通常减少错误回答，却可能增加对可回答题的错误拒答；只报告无答案题拒答率会掩盖后一种问题。
- 面试一句话：我同时报告可回答题接受率和无答案题拒答率，并以两者平均值作为平衡拒答准确率，避免单纯把阈值调高得到虚假的好看结果。

### 3. 控制变量与重复实验

- 一句话解释：比较参数时，语料、题目、Embedding、排序结果和评分规则必须固定，只改变 Top-K 与 threshold。
- 在当前项目中的职责：一次查询取最大 Top-K=5，较小 K 只切同一排序前缀；每题默认重复两次，模型预热不计入延迟。
- 与其他组件的关系：Day 9 固定 PDF 字节，Day 10 固定 Ground truth，Day 11 固定计算规则并记录模型名、参数候选和知识库文档状态。
- 容易混淆的点：模型首次下载和初始化耗时不属于单次检索延迟；报告记录的是预热后的 Query Embedding + pgvector 查询耗时。
- 面试一句话：我用同一份冻结语料和排序结果派生 Top-1/3/5，并在预热后重复测量，减少数据变化与冷启动对参数比较的干扰。

### 4. 平均延迟、P50 与 P95

- 一句话解释：平均值描述总体成本，P50 描述典型请求，P95 描述较慢尾部，单次最快结果不能代表用户体验。
- 在当前项目中的职责：脚本收集所有成功检索的毫秒样本，输出 `mean`、`p50`、`p95` 和 `max`。
- 与其他组件的关系：计时覆盖 `embed_query()` 和 `ChunkRepository.search_similar()`，不覆盖模型构造、API 网络和 LLM 生成。
- 容易混淆的点：当前只有 18 题、默认 2 次重复，P95 只是小样本基线，不能宣称为生产 SLA。
- 面试一句话：我把检索延迟口径限定为预热后的 Query Embedding 加 pgvector 查询，并同时报告平均与 P95，明确小样本结果只用于项目基线。

## 四、升级涉及的文件

| 文件                                                  | 操作      | 作用                                   |
| --------------------------------------------------- | ------- | ------------------------------------ |
| `scripts/run_evaluation.py`                         | 整文件替换   | 从旧 FAISS HTTP 脚本改为企业制度 pgvector 评测脚本 |
| `data/evaluation/enterprise_evaluation_report.json` | 运行脚本后生成 | 保存逐题来源、指标、参数矩阵、延迟、失败案例和最终参数建议        |
| `docs/17天每日学习/Day11.md`                             | 已生成，保留  | 今日升级手册与可选执行记录                        |

### 今日不做

- 不修改 Day 10 已冻结的题目、证据或 PDF，以免根据结果反向调整 Ground truth。
- 不调用 LLM，也不把答案措辞评分混进今天的检索与拒答实验；生成质量评测不属于今天的唯一产物。
- 不修改 `RetrievalService`、`ChunkRepository`、生产 API、默认 Top-K 或 `MIN_RELEVANCE_SCORE`；报告先记录真实选参结论，不能在结果出现前编造生产参数改动。
- 不建立 HNSW/IVFFlat 索引或做数据库性能调优。
- 不新增 pytest；自动回归测试属于 Day 12。
- 不更新求职版 README、架构图或评测结论摘要；这些属于 Day 15。

## 五、按顺序完成项目升级

### 步骤 1：整文件替换企业评测脚本（建议 35 分钟）

**目标**

保留 `scripts/run_evaluation.py` 这个统一入口，但完全替换旧的单 PDF FAISS 行为，使它直接复用当前数据库检索服务、自动计算指标并输出不含秘密的 JSON 报告。

**修改位置**

- 文件：`scripts/run_evaluation.py`
- 定位：旧文件开头的 `BASE_URL = "http://127.0.0.1:8000"`、`QUESTIONS_PATH = Path("data/evaluation/questions.json")`
- 操作：保留文件路径，整文件替换；不要覆盖旧的三个 JSON 基线文件

**复制下面的完整代码**

```python
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import SessionLocal
from app.repositories.chunk_repository import ChunkSearchResult
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.embedding_service import EmbeddingService, MODEL_NAME
from app.services.retrieval_service import RetrievalService
from scripts.validate_enterprise_questions import validate_dataset


DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "evaluation" / "enterprise_questions.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "enterprise_evaluation_report.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "在指定知识库上运行 Day 11 企业制度 pgvector 参数实验。"
        )
    )
    parser.add_argument(
        "--knowledge-base-id",
        type=int,
        required=True,
        help="已经包含 4 份冻结 PDF 的知识库 ID。",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Day 10 固定评测集路径。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="结构化 JSON 报告输出路径。",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=2,
        help="每道题重复检索次数，默认 2。",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return payload


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def round_metric(value: float) -> float:
    return round(float(value), 6)


def percentile_95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def summarize_latency(values: list[float]) -> dict[str, int | float | None]:
    if not values:
        return {
            "sample_count": 0,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    return {
        "sample_count": len(values),
        "mean_ms": round_metric(fmean(values)),
        "p50_ms": round_metric(median(values)),
        "p95_ms": round_metric(percentile_95(values) or 0.0),
        "max_ms": round_metric(max(values)),
    }


def serialize_source(
    result: ChunkSearchResult,
    rank: int,
) -> dict[str, Any]:
    return {
        "rank": rank,
        "chunk_id": result.chunk_id,
        "document_id": result.document_id,
        "knowledge_base_id": result.knowledge_base_id,
        "filename": result.filename,
        "page_number": result.page_number,
        "chunk_index": result.chunk_index,
        "content": result.content,
        "score": round_metric(result.score),
    }


def source_matches_evidence(
    result: ChunkSearchResult,
    evidence: dict[str, Any],
) -> bool:
    return (
        result.filename == evidence["filename"]
        and result.page_number == evidence["page_number"]
        and normalize_text(evidence["evidence_contains"])
        in normalize_text(result.content)
    )


def calculate_retrieval_metrics(
    results: list[ChunkSearchResult],
    expected_evidence: list[dict[str, Any]],
    top_k: int,
) -> dict[str, int | float | None]:
    selected_results = results[:top_k]
    matching_ranks: list[int] = []
    matched_evidence_count = 0

    for evidence in expected_evidence:
        evidence_ranks = [
            rank
            for rank, result in enumerate(selected_results, start=1)
            if source_matches_evidence(result, evidence)
        ]
        if evidence_ranks:
            matched_evidence_count += 1
            matching_ranks.append(min(evidence_ranks))

    expected_count = len(expected_evidence)
    if expected_count == 0:
        recall = None
        reciprocal_rank = None
    else:
        recall = matched_evidence_count / expected_count
        first_relevant_rank = min(matching_ranks, default=None)
        reciprocal_rank = (
            0.0
            if first_relevant_rank is None
            else 1.0 / first_relevant_rank
        )

    return {
        "top_k": top_k,
        "expected_evidence_count": expected_count,
        "matched_evidence_count": matched_evidence_count,
        "recall": None if recall is None else round_metric(recall),
        "reciprocal_rank": (
            None
            if reciprocal_rank is None
            else round_metric(reciprocal_rank)
        ),
    }


def result_signature(
    results: list[ChunkSearchResult],
) -> list[tuple[int, int, float]]:
    return [
        (
            result.document_id,
            result.chunk_id,
            round_metric(result.score),
        )
        for result in results
    ]


def evaluate_case(
    service: RetrievalService,
    case: dict[str, Any],
    top_k_candidates: list[int],
    threshold_candidates: list[float],
    repetitions: int,
) -> dict[str, Any]:
    max_top_k = max(top_k_candidates)
    repeated_results: list[list[ChunkSearchResult]] = []
    latency_samples: list[float] = []

    for _ in range(repetitions):
        started_at = time.perf_counter()
        try:
            results = service.search(
                knowledge_base_id=case["knowledge_base_id"],
                question=case["question"],
                top_k=max_top_k,
            )
        except Exception as exc:
            latency_samples.append(
                (time.perf_counter() - started_at) * 1000
            )
            return {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "answerable": case["answerable"],
                "expected_refusal": case["expected_refusal"],
                "status": "failed",
                "error_type": type(exc).__name__,
                "latency_ms_samples": [
                    round_metric(value) for value in latency_samples
                ],
                "retrieval_stable_across_repetitions": False,
                "retrieved_sources": [],
                "retrieval_by_top_k": {},
                "threshold_outcomes": [],
            }
        latency_samples.append((time.perf_counter() - started_at) * 1000)
        repeated_results.append(results)

    first_results = repeated_results[0]
    first_signature = result_signature(first_results)
    stable = all(
        result_signature(results) == first_signature
        for results in repeated_results[1:]
    )

    expected_evidence = case["expected_evidence"]
    retrieval_by_top_k = {
        str(top_k): calculate_retrieval_metrics(
            results=first_results,
            expected_evidence=expected_evidence,
            top_k=top_k,
        )
        for top_k in top_k_candidates
    }

    threshold_outcomes: list[dict[str, Any]] = []
    for top_k in top_k_candidates:
        selected_results = first_results[:top_k]
        for threshold in threshold_candidates:
            kept_ranks = [
                rank
                for rank, result in enumerate(selected_results, start=1)
                if result.score >= threshold
            ]
            predicted_refusal = not kept_ranks
            threshold_outcomes.append(
                {
                    "top_k": top_k,
                    "threshold": threshold,
                    "predicted_refusal": predicted_refusal,
                    "correct": (
                        predicted_refusal == case["expected_refusal"]
                    ),
                    "kept_source_ranks": kept_ranks,
                }
            )

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "answerable": case["answerable"],
        "expected_refusal": case["expected_refusal"],
        "status": "completed",
        "error_type": None,
        "latency_ms_samples": [
            round_metric(value) for value in latency_samples
        ],
        "retrieval_stable_across_repetitions": stable,
        "retrieved_sources": [
            serialize_source(result, rank)
            for rank, result in enumerate(first_results, start=1)
        ],
        "retrieval_by_top_k": retrieval_by_top_k,
        "threshold_outcomes": threshold_outcomes,
    }


def find_threshold_outcome(
    case_result: dict[str, Any],
    top_k: int,
    threshold: float,
) -> dict[str, Any] | None:
    for outcome in case_result["threshold_outcomes"]:
        if (
            outcome["top_k"] == top_k
            and float(outcome["threshold"]) == threshold
        ):
            return outcome
    return None


def aggregate_metrics(
    case_results: list[dict[str, Any]],
    top_k_candidates: list[int],
    threshold_candidates: list[float],
    reference_threshold: float,
) -> dict[str, Any]:
    answerable_cases = [case for case in case_results if case["answerable"]]
    unanswerable_cases = [
        case for case in case_results if not case["answerable"]
    ]

    retrieval: dict[str, Any] = {}
    for top_k in top_k_candidates:
        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        full_evidence_cases = 0

        for case in answerable_cases:
            if case["status"] != "completed":
                recall = 0.0
                reciprocal_rank = 0.0
            else:
                case_metrics = case["retrieval_by_top_k"][str(top_k)]
                recall = float(case_metrics["recall"])
                reciprocal_rank = float(case_metrics["reciprocal_rank"])
            recalls.append(recall)
            reciprocal_ranks.append(reciprocal_rank)
            if recall == 1.0:
                full_evidence_cases += 1

        retrieval[str(top_k)] = {
            "recall_at_k": round_metric(fmean(recalls)),
            "mrr_at_k": round_metric(fmean(reciprocal_ranks)),
            "full_evidence_case_rate": round_metric(
                full_evidence_cases / len(answerable_cases)
            ),
        }

    parameter_grid: list[dict[str, Any]] = []
    total_cases = len(case_results)
    for top_k in top_k_candidates:
        for threshold in threshold_candidates:
            correct_count = 0
            answerable_accept_count = 0
            unanswerable_refusal_count = 0

            for case in case_results:
                if case["status"] != "completed":
                    continue
                outcome = find_threshold_outcome(
                    case_result=case,
                    top_k=top_k,
                    threshold=threshold,
                )
                if outcome is None:
                    continue
                if outcome["correct"]:
                    correct_count += 1
                if case["answerable"] and not outcome["predicted_refusal"]:
                    answerable_accept_count += 1
                if (
                    not case["answerable"]
                    and outcome["predicted_refusal"]
                ):
                    unanswerable_refusal_count += 1

            answerable_acceptance_rate = (
                answerable_accept_count / len(answerable_cases)
            )
            unanswerable_refusal_rate = (
                unanswerable_refusal_count / len(unanswerable_cases)
            )
            parameter_grid.append(
                {
                    "top_k": top_k,
                    "threshold": threshold,
                    "refusal_accuracy": round_metric(
                        correct_count / total_cases
                    ),
                    "answerable_acceptance_rate": round_metric(
                        answerable_acceptance_rate
                    ),
                    "unanswerable_refusal_rate": round_metric(
                        unanswerable_refusal_rate
                    ),
                    "balanced_refusal_accuracy": round_metric(
                        (
                            answerable_acceptance_rate
                            + unanswerable_refusal_rate
                        )
                        / 2
                    ),
                    "recall_at_k": retrieval[str(top_k)]["recall_at_k"],
                }
            )

    selected = max(
        parameter_grid,
        key=lambda item: (
            item["balanced_refusal_accuracy"],
            item["recall_at_k"],
            item["refusal_accuracy"],
            -abs(float(item["threshold"]) - reference_threshold),
            -int(item["top_k"]),
        ),
    )
    selected_parameters = {
        "top_k": selected["top_k"],
        "threshold": selected["threshold"],
        "selection_rule": (
            "依次最大化 balanced_refusal_accuracy、Recall@K 和 "
            "refusal_accuracy；仍相同时优先接近当前参考阈值，"
            "再选择更小的 Top-K。"
        ),
        "reason": (
            f"候选组合中 Top-K={selected['top_k']}、"
            f"threshold={selected['threshold']} 的平衡拒答准确率为 "
            f"{selected['balanced_refusal_accuracy']}，Recall@K 为 "
            f"{selected['recall_at_k']}，总体拒答正确率为 "
            f"{selected['refusal_accuracy']}。"
        ),
    }

    latency_values = [
        float(value)
        for case in case_results
        for value in case["latency_ms_samples"]
        if case["status"] == "completed"
    ]
    return {
        "case_count": total_cases,
        "answerable_count": len(answerable_cases),
        "unanswerable_count": len(unanswerable_cases),
        "completed_case_count": sum(
            case["status"] == "completed" for case in case_results
        ),
        "failed_case_count": sum(
            case["status"] == "failed" for case in case_results
        ),
        "retrieval": retrieval,
        "parameter_grid": parameter_grid,
        "selected_parameters": selected_parameters,
        "retrieval_latency_ms": summarize_latency(latency_values),
    }


def build_failure_cases(
    case_results: list[dict[str, Any]],
    selected_parameters: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_top_k = int(selected_parameters["top_k"])
    selected_threshold = float(selected_parameters["threshold"])
    failures: list[dict[str, Any]] = []

    for case in case_results:
        reasons: list[str] = []
        if case["status"] == "failed":
            reasons.append(f"retrieval_error:{case['error_type']}")
        else:
            if case["answerable"]:
                recall = case["retrieval_by_top_k"][
                    str(selected_top_k)
                ]["recall"]
                if float(recall) < 1.0:
                    reasons.append(f"incomplete_evidence_recall:{recall}")

            outcome = find_threshold_outcome(
                case_result=case,
                top_k=selected_top_k,
                threshold=selected_threshold,
            )
            if outcome is None or not outcome["correct"]:
                reasons.append("refusal_classification_mismatch")
            if not case["retrieval_stable_across_repetitions"]:
                reasons.append("retrieval_order_not_stable")

        if reasons:
            failures.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "reasons": reasons,
                    "top_source": (
                        case["retrieved_sources"][0]
                        if case["retrieved_sources"]
                        else None
                    ),
                }
            )
    return failures


def validate_knowledge_base(
    session: Any,
    knowledge_base_id: int,
    dataset: dict[str, Any],
) -> dict[str, Any]:
    knowledge_base = KnowledgeBaseRepository(session).get(
        knowledge_base_id
    )
    if knowledge_base is None:
        raise LookupError(f"知识库不存在：{knowledge_base_id}")

    documents = DocumentRepository(session).list_by_knowledge_base(
        knowledge_base_id
    )
    ready_documents = [
        document for document in documents if document.status == "ready"
    ]
    expected_filenames = [
        item["filename"] for item in dataset["corpus"]["documents"]
    ]
    expected_counts = Counter(expected_filenames)
    actual_counts = Counter(
        document.filename for document in ready_documents
    )

    if actual_counts != expected_counts:
        missing = list((expected_counts - actual_counts).elements())
        extra_or_duplicate = list(
            (actual_counts - expected_counts).elements()
        )
        raise ValueError(
            "评测知识库的 ready 文档必须与冻结语料一一对应；"
            f"缺少={missing}；多余或重复={extra_or_duplicate}"
        )

    return {
        "id": knowledge_base.id,
        "name": knowledge_base.name,
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "status": document.status,
            }
            for document in documents
        ],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.knowledge_base_id <= 0:
        raise ValueError("knowledge-base-id 必须是正整数")
    if args.repetitions < 2:
        raise ValueError("repetitions 至少为 2，才能检查重复稳定性")

    dataset_path = args.dataset.resolve()
    output_path = args.output.resolve()
    if dataset_path == output_path:
        raise ValueError("输出路径不能覆盖固定评测集")

    validate_dataset(dataset_path)
    dataset = read_json(dataset_path)
    evaluation = dataset["evaluation"]
    top_k_candidates = [
        int(value) for value in evaluation["top_k_candidates"]
    ]
    threshold_candidates = [
        float(value) for value in evaluation["threshold_candidates"]
    ]
    reference_threshold = float(
        evaluation["current_reference_threshold"]
    )
    max_top_k = max(top_k_candidates)

    with SessionLocal() as session:
        knowledge_base = validate_knowledge_base(
            session=session,
            knowledge_base_id=args.knowledge_base_id,
            dataset=dataset,
        )
        embedding_service = EmbeddingService()
        retrieval_service = RetrievalService(
            session=session,
            embedding_service=embedding_service,
        )

        cases = [dict(case) for case in dataset["cases"]]
        warmup_case = cases[0]
        retrieval_service.search(
            knowledge_base_id=args.knowledge_base_id,
            question=warmup_case["question"],
            top_k=max_top_k,
        )

        case_results: list[dict[str, Any]] = []
        for position, case in enumerate(cases, start=1):
            print(
                f"[{position}/{len(cases)}] "
                f"{case['id']}：{case['question']}"
            )
            case["knowledge_base_id"] = args.knowledge_base_id
            result = evaluate_case(
                service=retrieval_service,
                case=case,
                top_k_candidates=top_k_candidates,
                threshold_candidates=threshold_candidates,
                repetitions=args.repetitions,
            )
            if result["status"] == "failed":
                session.rollback()
            case_results.append(result)

    summary = aggregate_metrics(
        case_results=case_results,
        top_k_candidates=top_k_candidates,
        threshold_candidates=threshold_candidates,
        reference_threshold=reference_threshold,
    )
    selected_parameters = summary["selected_parameters"]
    unstable_case_ids = [
        case["id"]
        for case in case_results
        if case["status"] == "completed"
        and not case["retrieval_stable_across_repetitions"]
    ]
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(dataset_path.relative_to(PROJECT_ROOT)),
            "version": dataset["dataset_version"],
            "corpus_version": dataset["corpus"]["corpus_version"],
        },
        "knowledge_base": knowledge_base,
        "experiment": {
            "retrieval_backend": "PostgreSQL + pgvector",
            "embedding_model": MODEL_NAME,
            "score_semantics": evaluation["score_semantics"],
            "top_k_candidates": top_k_candidates,
            "threshold_candidates": threshold_candidates,
            "reference_threshold": reference_threshold,
            "repetitions": args.repetitions,
            "warmup_case_id": warmup_case["id"],
            "latency_scope": (
                "预热后的 Query Embedding + pgvector Top-K 检索；"
                "不含模型初始化、HTTP 和 LLM 生成。"
            ),
        },
        "summary": summary,
        "reproducibility": {
            "repetitions": args.repetitions,
            "stable_case_count": sum(
                case["status"] == "completed"
                and case["retrieval_stable_across_repetitions"]
                for case in case_results
            ),
            "unstable_case_ids": unstable_case_ids,
        },
        "failure_cases": build_failure_cases(
            case_results=case_results,
            selected_parameters=selected_parameters,
        ),
        "cases": case_results,
    }
    write_report(output_path, report)

    print(f"报告已保存：{output_path}")
    print(
        "选定参数："
        f"Top-K={selected_parameters['top_k']}，"
        f"threshold={selected_parameters['threshold']}"
    )
    print(
        "Recall@1/3/5：",
        {
            key: value["recall_at_k"]
            for key, value in summary["retrieval"].items()
        },
    )
    print(
        "MRR@1/3/5：",
        {
            key: value["mrr_at_k"]
            for key, value in summary["retrieval"].items()
        },
    )

    if summary["failed_case_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, LookupError, RuntimeError) as exc:
        print(f"ERROR：{exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as exc:
        print(
            "ERROR：评测执行失败（"
            f"{type(exc).__name__}）。请检查 PostgreSQL 状态、"
            "POSTGRES_* 配置、模型缓存和评测知识库。",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
```

**这段代码怎样工作**

- 输入：`--knowledge-base-id`、Day 10 固定 JSON、该知识库中 4 份 ready 文档，以及可选的输出路径和重复次数。
- 输出：`enterprise_evaluation_report.json`，其中包含逐题 Top-5 来源、每个 K 的 Recall/MRR、每个 `K × threshold` 的拒答结果、延迟分布、稳定性、失败案例和参数建议。
- 调用谁：`validate_dataset()`、`SessionLocal`、`KnowledgeBaseRepository`、`DocumentRepository`、`EmbeddingService` 和 `RetrievalService`。
- 被谁调用：项目根目录中的 `python scripts/run_evaluation.py ...` 命令；不经过 FastAPI 和 LLM。
- 正常路径：先校验固定数据与知识库，再预热模型；每题检索最大 K=5 两次，从同一排序前缀计算 K=1/3/5，最后统一聚合和写报告。
- 失败路径：无效 ID、ready 文档不一一对应、固定数据损坏或重复次数小于 2 时在写报告前退出；单题检索异常会记录安全的异常类型、按未命中计入汇总、保存报告并以退出码 1 结束。
- 事务边界：脚本只执行查询，不调用 `commit()`；单题数据库异常后调用 `rollback()` 恢复 Session，避免后续题被失败事务污染。
- 选参规则：先最大化可回答接受率与无答案拒答率的平衡值，再比较 Recall、总体拒答正确率、与当前阈值的距离和更小 K；真实选择由运行数据产生，计划不预填结果。

**完成本步骤后的预期状态**

`scripts/run_evaluation.py` 不再引用旧 `questions.json`、`/upload`、`/rag/chat`、`retrieval_hit=None` 或 `answer_correct=None`，并且没有修改生产检索或问答代码。

### 步骤 2：确认报告是运行产物而不是手写结论（建议 5 分钟）

**目标**

明确 `data/evaluation/enterprise_evaluation_report.json` 只能由步骤 1 的脚本在真实知识库上生成，不复制静态示例、不提前填写分数。

**修改位置**

- 文件：`data/evaluation/enterprise_evaluation_report.json`
- 定位：当前不存在
- 操作：不要手工新建；在第七部分运行正常命令后自动生成

**报告必须出现的稳定顶层结构**

```json
{
  "schema_version": 1,
  "generated_at_utc": "动态 UTC 时间",
  "dataset": {
    "path": "data\\evaluation\\enterprise_questions.json",
    "version": "2026-09-04-v1",
    "corpus_version": "2026-09-04-v1"
  },
  "knowledge_base": {
    "id": "动态正整数",
    "name": "动态名称",
    "documents": "动态文档数组"
  },
  "experiment": {
    "retrieval_backend": "PostgreSQL + pgvector",
    "embedding_model": "BAAI/bge-small-zh-v1.5",
    "top_k_candidates": [1, 3, 5],
    "threshold_candidates": [0.45, 0.55, 0.65],
    "repetitions": 2
  },
  "summary": {
    "retrieval": "动态指标对象",
    "parameter_grid": "动态参数矩阵",
    "selected_parameters": "动态选择与理由",
    "retrieval_latency_ms": "动态延迟统计"
  },
  "reproducibility": "动态重复运行稳定性",
  "failure_cases": "动态失败案例数组",
  "cases": "18 道逐题结果"
}
```

**这一步怎样工作**

- 输入：真实脚本运行结果。
- 输出：可提交、可在 Day 15 摘要引用、可在面试中解释的结构化证据。
- 正常路径：18 题均完成时脚本退出码为 0；指标值、ID、分数和延迟均为动态值。
- 失败路径：单题检索异常时仍保存失败类型和失败案例，但脚本最终退出码为 1，不能把该报告当作成功基线提交。

**完成本步骤后的预期状态**

计划文件中没有伪造任何真实分数；只有实际运行脚本后，报告文件才存在并包含真实动态值。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成或执行新迁移，也不做 downgrade；只确认 Day 1～Day 10 的数据库、迁移和固定数据前置条件。

### 1. 检查当前状态

执行目录：项目根目录。先确认工作区、固定数据和数据库配置入口；不要读取或打印 `.env`。

```powershell
git status --short
python scripts/validate_enterprise_questions.py
docker compose config --services
docker compose ps
alembic current
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

预期顺序与结果：

- `git status --short` 只应出现你刚修改的 Day 11 文件；若还有其他文件，先记下并保持不动。
- 数据集校验退出码应为 0，并报告 18 题、4 个 PDF 哈希一致；这是输入校验，不是新评测已经通过。
- `docker compose config --services` 应包含 `postgres`。
- `docker compose ps` 中 PostgreSQL 应为运行且健康；未运行时再执行下一小节的启动命令。
- `alembic current` 应指向当前 head；今天不创建 revision。
- 连接探针预期输出 `1`，且错误信息不能包含数据库密码。

失败时检查：

- 数据集校验失败时，根据错误中的 case ID、文件名或字段修复 Day 10 数据一致性，不要为了提高 Day 11 指标改题。
- 数据库连接失败时检查 Docker Desktop、`docker compose ps` 和 `POSTGRES_*` 是否已配置，但不要回显真实值。

### 2. 执行升级所需的环境准备

仅当 PostgreSQL 尚未运行时，在项目根目录执行：

```powershell
docker compose up -d postgres
docker compose ps
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

首次需要准备干净评测知识库时，在一个终端启动 API；该进程会持续运行，使用 `Ctrl+C` 退出：

```powershell
python -m uvicorn app.main:app --reload
```

在另一个 Windows PowerShell 5.1 终端中，从项目根目录创建一个新的隔离知识库并上传 4 份明确文件。使用新知识库可以避免旧文档或重复上传污染指标：

```powershell
$baseUrl = "http://127.0.0.1:8000"
$knowledgeBaseName = "day11-evaluation-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$payload = @{
    name = $knowledgeBaseName
    description = "Day 11 frozen enterprise policy evaluation corpus"
} | ConvertTo-Json
$utf8Payload = [System.Text.Encoding]::UTF8.GetBytes($payload)
$knowledgeBase = Invoke-RestMethod `
    -Method Post `
    -Uri "$baseUrl/knowledge-bases" `
    -ContentType "application/json; charset=utf-8" `
    -Body $utf8Payload
$knowledgeBaseId = [int]$knowledgeBase.id
$knowledgeBaseId

curl.exe -fS `
    -X POST `
    "$baseUrl/knowledge-bases/$knowledgeBaseId/documents" `
    -F "file=@data/demo_policies/pdfs/员工请假与考勤制度.pdf;type=application/pdf"

curl.exe -fS `
    -X POST `
    "$baseUrl/knowledge-bases/$knowledgeBaseId/documents" `
    -F "file=@data/demo_policies/pdfs/差旅与费用报销制度.pdf;type=application/pdf"

curl.exe -fS `
    -X POST `
    "$baseUrl/knowledge-bases/$knowledgeBaseId/documents" `
    -F "file=@data/demo_policies/pdfs/采购与办公资产管理制度.pdf;type=application/pdf"

curl.exe -fS `
    -X POST `
    "$baseUrl/knowledge-bases/$knowledgeBaseId/documents" `
    -F "file=@data/demo_policies/pdfs/访客与会议室管理办法.pdf;type=application/pdf"

$documents = Invoke-RestMethod `
    -Method Get `
    -Uri "$baseUrl/knowledge-bases/$knowledgeBaseId/documents"
$documents | Select-Object id, filename, status, failure_reason | Format-Table
```

预期结果：

- `$knowledgeBaseId` 是动态正整数，必须保留在这个 PowerShell 终端中供评测命令使用。
- 4 个上传响应都应为成功响应，每个 Document 最终状态应为 `ready`；Document ID 与 Chunk 数量是动态值。
- 列表应恰好有 4 份 ready 冻结文档。不要向同一个评测知识库重复上传，也不要混入其他 PDF。
- 首次下载 Embedding 模型的外部耗时不计入 60 分钟核心时间。

### 3. 回滚并恢复

今天无 schema 迁移，因此不执行 Alembic downgrade。需要确认迁移链未被修改时只执行：

```powershell
git diff -- alembic.ini migrations app/orm_models.py app/db.py
alembic current
```

### 预期结果

- `git diff` 对上述数据库基础文件无输出。
- `alembic current` 保持现有 head。
- 今天不删除数据库、不删除 Volume，也不通过清空数据证明实验可重复。

## 七、验证正常路径

### 启动或准备服务

评测脚本本身直接连接 PostgreSQL，不需要 LLM，也不要求 API 在评测期间继续运行；但第六部分上传 PDF 时 API 必须已启动。请在保存 `$knowledgeBaseId` 的 PowerShell 终端中执行：

```powershell
python scripts/validate_enterprise_questions.py
python scripts/run_evaluation.py `
    --knowledge-base-id $knowledgeBaseId `
    --repetitions 2 `
    --output data/evaluation/enterprise_evaluation_report.json
$LASTEXITCODE
```

执行顺序：先再次确认固定输入，再运行真实评测，最后查看退出码。脚本会用第一题做一次不计时预热，再对 18 题各检索两次。

### 执行正常请求或测试

读取稳定结构，不把任何数值写死为预期成功值：

```powershell
$reportPath = "data/evaluation/enterprise_evaluation_report.json"
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json

$report.schema_version
$report.dataset
$report.knowledge_base.documents | Format-Table id, filename, status
$report.summary.retrieval
$report.summary.parameter_grid | Format-Table `
    top_k, threshold, recall_at_k, refusal_accuracy, `
    answerable_acceptance_rate, unanswerable_refusal_rate, `
    balanced_refusal_accuracy
$report.summary.selected_parameters
$report.summary.retrieval_latency_ms
$report.reproducibility
$report.failure_cases | Format-List
$report.cases.Count
```

### 预期状态码或输出结构

```json
{
  "process_exit_code": 0,
  "schema_version": 1,
  "case_count": 18,
  "completed_case_count": 18,
  "failed_case_count": 0,
  "retrieval_keys": ["1", "3", "5"],
  "parameter_grid_count": 9,
  "latency_sample_count": 36,
  "selected_parameters": {
    "top_k": "动态候选值：1、3 或 5",
    "threshold": "动态候选值：0.45、0.55 或 0.65",
    "selection_rule": "稳定文本",
    "reason": "包含真实动态指标的文本"
  },
  "failure_cases": "允许为空，也允许保存真实失败案例"
}
```

额外说明：

- `Recall@1/3/5`、`MRR@1/3/5`、拒答率、分数、延迟、ID 和失败案例都必须以实际报告为准。
- `failure_cases` 非空不等于脚本执行失败；它也会保存“部分证据未召回”“错误接受/拒答”或重复排序不稳定等真实质量问题。
- 只有 `failed_case_count > 0` 代表某题检索调用异常，此时脚本退出码为 1，应先修复已知运行失败再提交。

### 为什么它能证明今天已经完成

同一条命令同时经过固定数据校验、真实知识库预检、Query Embedding、ready 文档过滤、pgvector 排序、自动 Ground truth 匹配、参数矩阵计算和 JSON 落盘；36 个计时样本与逐题来源让汇总值可以回查，因而不是手填结论。

## 八、验证失败和边界路径

### 场景：无效知识库 ID 必须快速失败，且不能伪造评测报告

在项目根目录执行，输出位置使用当前用户临时目录中的唯一文件名，不覆盖成功报告：

```powershell
$invalidReport = Join-Path `
    $env:TEMP `
    ("day11-invalid-" + [Guid]::NewGuid().ToString("N") + ".json")

python scripts/run_evaluation.py `
    --knowledge-base-id 0 `
    --repetitions 2 `
    --output $invalidReport

$LASTEXITCODE
Test-Path -LiteralPath $invalidReport
```

### 预期结果

- 进程退出码：`1`。
- 错误类型：安全的输入错误，提示 `knowledge-base-id 必须是正整数`。
- 数据库应该保留：原知识库、Document、Chunk 和成功评测报告全部不变。
- 数据库不应该存在：由失败评测创建、更新或删除的任何记录；脚本全程只读。
- 文件系统不应该存在：`$invalidReport`，`Test-Path` 预期为 `False`。
- 响应不能泄露：`POSTGRES_PASSWORD`、完整数据库 URL、LLM API Key、Python 内部对象或 SQL 参数。

### 边界补充：无答案题不能因为 Top-K 总有结果就自动算“已回答”

成功报告生成后执行：

```powershell
$report = Get-Content `
    -LiteralPath "data/evaluation/enterprise_evaluation_report.json" `
    -Raw | ConvertFrom-Json

$unanswerableCases = $report.cases | Where-Object {
    $_.answerable -eq $false
}
$unanswerableCases.Count
$unanswerableCases | ForEach-Object {
    [PSCustomObject]@{
        id = $_.id
        retrieved_source_count = $_.retrieved_sources.Count
        threshold_outcome_count = $_.threshold_outcomes.Count
    }
} | Format-Table
```

预期结果：无答案题数量为 6；它们仍可能拥有动态 Top-5 候选，但每题必须有 9 个 `Top-K × threshold` 判定，最终是否拒答由分数阈值而不是“是否返回候选”决定。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `ModuleNotFoundError: app` | 没有使用替换后的脚本，或不在项目根目录执行 | 检查 `PROJECT_ROOT` 和 `sys.path.insert`；运行 `Get-Location` | 切换到项目根目录，并确认脚本在导入 `app` 前插入项目根路径 |
| 提示缺少 `POSTGRES_DB/USER/PASSWORD` | Day 1 数据库环境变量没有提供 | `python -c "from app.db import build_database_url; print(build_database_url().render_as_string(hide_password=True))"` | 在本地环境配置缺失变量；只输出遮蔽密码的 URL，不把真实值写入计划或提交 |
| `数据库连接失败` 或泛化的 SQLAlchemy 错误 | PostgreSQL 未启动、端口不一致或健康检查未通过 | `docker compose ps`；`python -c "from app.db import check_database_connection; print(check_database_connection())"` | 先运行 `docker compose up -d postgres`，待健康后重新执行；不要删除 Volume |
| `知识库不存在` | 使用了错误或旧终端中的 ID | `Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/knowledge-bases"` | 从列表确认 ID，重新设置 `$knowledgeBaseId = [int]实际值` |
| 提示 ready 文档缺少、多余或重复 | 4 份 PDF 未全部成功、重复上传，或知识库混入其他 ready 文档 | 调用 `GET /knowledge-bases/{id}/documents`；查看 filename/status | 新建一个隔离评测知识库并各上传一次 4 个明确文件，不删除或篡改旧数据 |
| 固定数据校验失败 | PDF 字节、哈希、证据页、JSON 标签或候选参数被修改 | `python scripts/validate_enterprise_questions.py` | 恢复与 Day 10 提交一致的冻结输入；不要根据 Day 11 结果改题或改证据 |
| 首次运行很慢或尝试下载模型 | `SentenceTransformer` 本地尚无 `BAAI/bge-small-zh-v1.5` 缓存 | 查看终端模型加载日志；检查 `app/services/embedding_service.py` | 保持网络可用并等待一次性下载；模型构造和预热不计入报告延迟 |
| `failed_case_count` 大于 0，退出码为 1 | 某题 Embedding 或数据库检索异常 | 查看报告中该题的 `status`、`error_type` 和 `failure_cases` | 先处理模型或数据库故障后重跑；异常题按未命中计分，不能删题美化指标 |
| Recall 很低但来源看起来相关 | Ground truth 锚点跨 Chunk，或召回了相关说明但没有精确证据 | 查看逐题 `retrieved_sources.content`、文件名、页码和 `expected_evidence` | 先确认 Day 10 锚点与当前冻结 PDF/Chunk 真实对应；如评分规则确有缺陷，应单独记录版本变更，不能静默改标签 |
| 无答案拒答率高、可回答接受率低 | threshold 过高 | 查看 `parameter_grid` 的两类分项与平衡值 | 按报告选择规则比较，不只看无答案题；保留错误拒答案例 |
| 可回答接受率高、无答案拒答率低 | threshold 过低 | 查看无答案题最高分和 `threshold_outcomes` | 提高候选阈值时同时检查 Recall 与错误拒答，不以单项指标决定 |
| 重复运行来源顺序不稳定 | 相同距离的排序缺少稳定次序，或数据库内容在实验期间变化 | 查看 `retrieval_stable_across_repetitions`；检查 `ChunkRepository` 的 `Chunk.id.asc()` 次排序 | 实验期间不要上传新文档；若仍不稳定，保存案例并在 Day 12 前修复确定性问题 |
| 报告 JSON 被旧结果覆盖 | 使用了默认同名输出 | `git status --short`；查看 `generated_at_utc` | 需要保留历史时，用 `--output data/evaluation/明确的新文件名.json`，不要批量复制或删除结果 |

## 十、检查最终代码差异

在项目根目录执行：

```powershell
git status --short
git diff -- `
    scripts/run_evaluation.py `
    docs/17天每日学习/Day11.md
Get-Content `
    -LiteralPath "data/evaluation/enterprise_evaluation_report.json" `
    -TotalCount 80
```

重点检查：

- `scripts/run_evaluation.py` 已彻底离开旧 `/upload`、`/rag/chat` 和 FAISS 数据集，但没有修改旧 JSON 基线文件。
- 评测脚本只读数据库，不创建、更新或删除 KnowledgeBase、Document、Chunk，也不调用 LLM。
- Recall 分母只使用 12 道可回答题；失败检索按 0 计入而不是从分母剔除。
- MRR 来自第一条正确证据的倒数排名；跨文档多证据覆盖仍由 Recall 单独表达。
- 参数选择同时考虑可回答接受率与无答案拒答率，不能只优化单一类别。
- 报告包含 18 个 case、9 个参数组合、动态延迟和失败案例，没有密码、API Key 或完整数据库 URL。
- `git status` 不包含 `.env`、模型缓存、数据库文件、旧学习资料或无关修改。

## 十一、Git 提交

核心脚本完成、真实报告已生成、`failed_case_count=0` 且检查 Git diff 边界后即可执行；不要求额外提交终端截图或手工验收记录：

```powershell
git add `
    scripts/run_evaluation.py `
    data/evaluation/enterprise_evaluation_report.json `
    docs/17天每日学习/Day11.md

git status --short
git diff --cached -- `
    scripts/run_evaluation.py `
    data/evaluation/enterprise_evaluation_report.json `
    docs/17天每日学习/Day11.md

git commit -m "Day11"
```

如果实际运行存在 `failed_case_count > 0`，先修复已知运行故障再提交；Recall、MRR 或拒答正确率没有达到理想值本身不是运行故障，必须作为真实失败案例保留，不能删题或改标签美化结果。

## 十二、面试高频问题与参考答案

### 问题 1：Recall@K 和 MRR 有什么区别，为什么两个都要？

#### 30 秒参考答案

Recall@K 关注前 K 个结果覆盖了多少人工标注的正确证据，MRR 关注第一条正确证据出现得多靠前。我的项目里跨文档题可能需要多条来源，所以只看 MRR 会忽略证据是否找全；只看 Recall 又看不出正确证据是否长期排在后面。Day 11 把 Top-1、Top-3、Top-5 从同一份 pgvector 排序结果中切出来，同时计算两类指标。

#### 继续追问：跨文档题怎样计算 Recall？

对每道可回答题，我用“Top-K 中命中的预期证据条数 / 该题预期证据总条数”。证据用冻结文件名、页码和原文锚点匹配，不写死动态 Chunk ID。例如三条预期证据只找回两条，该题 Recall 就是 `2/3`；MRR 仍取最早命中证据的倒数排名。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `expected_evidence`
- `scripts/run_evaluation.py` 的 `source_matches_evidence()` 与 `calculate_retrieval_metrics()`
- 报告的 `summary.retrieval` 和逐题 `retrieval_by_top_k`

### 问题 2：为什么不能只把 threshold 调高来提高拒答正确率？

#### 30 秒参考答案

阈值提高会让更多无答案题正确拒答，但也可能让本来有答案的问题被错误拒答。我的报告同时给出可回答题接受率、无答案题拒答率和两者的平衡平均值，再结合 Recall 选参数，不允许只靠把所有问题都拒绝来得到好看的无答案指标。

#### 继续追问：参数选择规则怎样保证可复现？

候选值由 Day 10 在实验前固定为 Top-K 1/3/5、threshold 0.45/0.55/0.65。脚本按明确排序依次最大化平衡拒答准确率、Recall@K 和总体拒答正确率；仍相同时优先接近当前参考阈值，再选更小 K。规则和实际理由一起写入报告，所以不是运行后凭感觉挑结果。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `evaluation`
- `app/services/database_rag_service.py` 的 `MIN_RELEVANCE_SCORE` 与 `score >= threshold`
- 报告的 `summary.parameter_grid` 与 `summary.selected_parameters`

### 问题 3：为什么评测脚本直接调用 RetrievalService，而不是调用完整 RAG API？

#### 30 秒参考答案

Day 11 要隔离检索、阈值和延迟变量。完整 RAG API 会加入 HTTP、LLM 配置、生成延迟和回答随机性，而且当前 API 只暴露 Top-K、不暴露候选 threshold。脚本直接复用生产的 `SessionLocal → RetrievalService → ChunkRepository`，仍然走真实 Query Embedding、知识库过滤、ready 状态过滤和 pgvector 排序，但不会把 LLM 波动混进检索指标。

#### 继续追问：这样会不会绕过太多生产逻辑？

它绕过的是本日不评估的网络和生成层，没有重写检索 SQL。`RetrievalService` 和 `ChunkRepository` 正是生产数据库版 RAG 使用的组件，来源字段、分数语义和过滤规则保持一致。Day 12 会再用 pytest 覆盖接口和服务边界，Day 13 会做完整重启后的端到端验收。

#### 回答时要引用的项目依据

- `app/main.py` 的 `query_knowledge_base()`
- `app/services/retrieval_service.py`
- `app/repositories/chunk_repository.py` 的 knowledge base 与 ready 过滤
- `scripts/run_evaluation.py` 的导入和 `evaluate_case()`

### 问题 4：检索延迟为什么要报告 P95，计时口径是什么？

#### 30 秒参考答案

平均延迟容易掩盖少量慢请求，P95 更能反映尾部体验。当前项目在模型加载并用第一题预热后，对 18 道题各运行两次，计时范围是 Query Embedding 加 pgvector Top-K 查询，输出平均、P50、P95 和最大值；它不包含模型初始化、HTTP 和 LLM，因此我把它称为小样本检索基线，而不是生产端到端 SLA。

#### 继续追问：两次重复足够做性能结论吗？

不足以做生产性能结论，但足以在 60 分钟学习任务中发现明显不稳定，并形成可重复的初始基线。报告明确保存样本数和口径；如果要做容量规划，应增加预热轮数、并发、样本量、硬件记录和独立压测工具，而不是扩大今天的范围。

#### 回答时要引用的项目依据

- `scripts/run_evaluation.py` 的预热、`time.perf_counter()` 和 `summarize_latency()`
- 报告的 `experiment.latency_scope`
- 报告的 `summary.retrieval_latency_ms` 与 `reproducibility`

### 问题 5：怎样避免评测数据泄漏和“只展示最好结果”？

#### 30 秒参考答案

我在调参前先固定 4 份 PDF 的 SHA-256、18 道问题、答案标签、证据锚点和候选参数；Day 11 只读取这些输入。脚本把全部 9 个参数组合、逐题来源、失败类型、部分召回、错误接受、错误拒答和排序不稳定都写进报告，异常题不会从指标分母中消失，因此不能靠删题或只保存最佳组合美化结果。

#### 继续追问：如果发现 Ground truth 本身有错怎么办？

先把它记录为数据集缺陷，单独修改并提升数据集版本，再对所有候选参数重新运行；不能只为某个失败组合静默改证据。这样新旧报告仍可按 `dataset_version` 和 `corpus_version` 区分。

#### 回答时要引用的项目依据

- `data/demo_policies/manifest.json`
- `scripts/validate_enterprise_questions.py`
- `data/evaluation/enterprise_questions.json` 的版本与候选参数
- 报告的 `failure_cases`、`cases` 和 `parameter_grid`

## 十三、今天的完整数据流

### 正常路径

```text
Day 9 冻结 PDF + Day 10 固定 Ground truth
→ validate_enterprise_questions.py 校验哈希、页码、锚点和标签
→ 指定只含 4 份 ready 文档的 KnowledgeBase
→ SessionLocal 创建只读评测 Session
→ EmbeddingService 生成 Query Embedding
→ RetrievalService 校验知识库和 512 维向量
→ ChunkRepository 在指定知识库中过滤 ready Document
→ pgvector 余弦距离排序并返回 Top-5
→ 同一排序切出 Top-1 / Top-3 / Top-5
→ 文件名 + 页码 + 原文锚点匹配 expected_evidence
→ 计算 Recall@K 与 MRR@K
→ 各 K 下用 0.45 / 0.55 / 0.65 过滤候选
→ 计算可回答接受率、无答案拒答率和平衡拒答准确率
→ 聚合 mean / P50 / P95 / max 延迟
→ 按固定规则选参并保存全部失败案例
→ enterprise_evaluation_report.json
```

### 失败路径

```text
无效 knowledge_base_id / 固定数据损坏 / ready 文档不一致
→ 预检明确指出输入边界
→ 不进入逐题实验
→ 不写伪造报告
→ 数据库不变
→ 进程退出码 1

单题 Embedding 或 pgvector 检索异常
→ 记录 error_type，不写秘密和内部连接串
→ rollback 恢复 Session
→ 该题按未命中参与指标，不从分母删除
→ 继续保存其余逐题结果与 failure_cases
→ 报告落盘但最终退出码 1
→ 修复已知运行故障后重新执行
```

## 十四、完成标准

```text
[ ] 能手算一个多证据案例的 Recall@1/3/5 与 MRR，并解释“找得全”和“排得前”的区别
[ ] 能解释 threshold 对错误回答和错误拒答的双向影响，以及为什么要看平衡拒答准确率
[ ] scripts/run_evaluation.py 已改为复用 SessionLocal、RetrievalService 和 pgvector，不再调用旧 FAISS API
[ ] 评测前会校验固定数据，并确认指定知识库恰好有 4 份一一对应的 ready 冻结文档
[ ] 同一排序结果可以自动计算 Recall@1/3/5、MRR@1/3/5 和 9 个 Top-K × threshold 组合
[ ] 报告包含平均、P50、P95、最大检索延迟，并明确不含模型初始化、HTTP 和 LLM
[ ] 报告保存全部逐题来源、重复稳定性、失败案例、最终参数和可复述的选择理由
[ ] 已提供正常路径命令与稳定预期结构；实际动态指标必须来自脚本，不能手填或伪造
[ ] 已提供无效知识库和无答案题边界命令；失败不会改数据库、生成伪造报告或泄露秘密
[ ] 能不看代码复述“冻结输入 → pgvector 检索 → 证据匹配 → 指标聚合 → 选参报告”的完整数据流
[ ] git diff 和暂存区只包含评测脚本、真实生成的企业评测报告和 Day11 手册
[ ] 核心脚本与报告完成、failed_case_count=0 后可执行边界清晰的 Day 11 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
