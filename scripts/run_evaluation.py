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