from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "evaluation" / "enterprise_questions.json"
)
ALLOWED_CATEGORIES = {
    "direct_fact",
    "comprehensive",
    "cross_document",
    "isolation",
    "unanswerable",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="校验 Day 10 企业制度固定评测集。"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="评测集 JSON 路径。",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 JSON 文件：{path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return payload


def require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} 必须是对象")
    return value


def require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} 必须是数组")
    return value


def require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")
    return value.strip()


def resolve_project_path(value: Any, field_name: str) -> Path:
    relative_path = Path(require_non_empty_string(value, field_name))
    if relative_path.is_absolute():
        raise ValueError(f"{field_name} 必须是项目内相对路径")
    resolved_path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT != resolved_path and PROJECT_ROOT not in resolved_path.parents:
        raise ValueError(f"{field_name} 不能指向项目目录之外")
    return resolved_path


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_candidates(evaluation: dict[str, Any]) -> None:
    top_k_candidates = require_list(
        evaluation.get("top_k_candidates"),
        "evaluation.top_k_candidates",
    )
    if (
        not top_k_candidates
        or any(type(value) is not int for value in top_k_candidates)
        or any(value < 1 or value > 10 for value in top_k_candidates)
        or top_k_candidates != sorted(set(top_k_candidates))
    ):
        raise ValueError(
            "evaluation.top_k_candidates 必须是 1 到 10 内的升序唯一整数"
        )

    default_top_k = evaluation.get("default_top_k")
    if default_top_k not in top_k_candidates:
        raise ValueError("evaluation.default_top_k 必须属于 top_k_candidates")

    threshold_candidates = require_list(
        evaluation.get("threshold_candidates"),
        "evaluation.threshold_candidates",
    )
    if not threshold_candidates:
        raise ValueError("evaluation.threshold_candidates 不能为空")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in threshold_candidates
    ):
        raise ValueError("threshold_candidates 只能包含数字")
    normalized_thresholds = [float(value) for value in threshold_candidates]
    if (
        any(value < -1.0 or value > 1.0 for value in normalized_thresholds)
        or normalized_thresholds != sorted(set(normalized_thresholds))
    ):
        raise ValueError("threshold_candidates 必须是 -1 到 1 内的升序唯一数字")

    reference_threshold = evaluation.get("current_reference_threshold")
    if (
        isinstance(reference_threshold, bool)
        or not isinstance(reference_threshold, (int, float))
        or float(reference_threshold) not in normalized_thresholds
    ):
        raise ValueError(
            "current_reference_threshold 必须属于 threshold_candidates"
        )

    if evaluation.get("score_semantics") != "cosine_similarity_higher_is_better":
        raise ValueError("score_semantics 与当前 pgvector 检索实现不一致")


def validate_corpus(
    dataset: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], Path]:
    corpus = require_mapping(dataset.get("corpus"), "corpus")
    manifest_path = resolve_project_path(
        corpus.get("manifest_path"),
        "corpus.manifest_path",
    )
    pdf_directory = resolve_project_path(
        corpus.get("pdf_directory"),
        "corpus.pdf_directory",
    )
    manifest = read_json(manifest_path)

    corpus_version = require_non_empty_string(
        corpus.get("corpus_version"),
        "corpus.corpus_version",
    )
    if corpus_version != manifest.get("corpus_version"):
        raise ValueError("评测集 corpus_version 与 manifest 不一致")

    manifest_documents = require_list(
        manifest.get("documents"),
        "manifest.documents",
    )
    manifest_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(manifest_documents, start=1):
        document = require_mapping(item, f"manifest.documents[{index}]")
        filename = require_non_empty_string(
            document.get("filename"),
            f"manifest.documents[{index}].filename",
        )
        if filename in manifest_by_name:
            raise ValueError(f"manifest PDF 文件名重复：{filename}")
        manifest_by_name[filename] = document

    frozen_documents = require_list(
        corpus.get("documents"),
        "corpus.documents",
    )
    frozen_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(frozen_documents, start=1):
        document = require_mapping(item, f"corpus.documents[{index}]")
        filename = require_non_empty_string(
            document.get("filename"),
            f"corpus.documents[{index}].filename",
        )
        sha256 = require_non_empty_string(
            document.get("sha256"),
            f"corpus.documents[{index}].sha256",
        )
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"{filename} 的 sha256 格式错误")
        if filename in frozen_by_name:
            raise ValueError(f"评测集 PDF 文件名重复：{filename}")
        frozen_by_name[filename] = document

    expected_document_count = corpus.get("document_count")
    if type(expected_document_count) is not int:
        raise ValueError("corpus.document_count 必须是整数")
    if expected_document_count != len(frozen_by_name):
        raise ValueError("corpus.document_count 与 documents 数量不一致")
    if set(frozen_by_name) != set(manifest_by_name):
        raise ValueError("评测集冻结的 PDF 清单与 manifest 不一致")

    for filename, frozen_document in frozen_by_name.items():
        manifest_document = manifest_by_name[filename]
        frozen_hash = frozen_document["sha256"]
        if frozen_hash != manifest_document.get("sha256"):
            raise ValueError(f"{filename} 的冻结哈希与 manifest 不一致")
        pdf_path = pdf_directory / filename
        if not pdf_path.is_file():
            raise FileNotFoundError(f"缺少冻结 PDF：{pdf_path}")
        if sha256_file(pdf_path) != frozen_hash:
            raise ValueError(f"{filename} 的实际 SHA-256 已变化")

    if manifest.get("document_count") != len(manifest_by_name):
        raise ValueError("manifest.document_count 与 documents 数量不一致")

    return manifest, manifest_by_name, pdf_directory


def validate_cases(
    dataset: dict[str, Any],
    evaluation: dict[str, Any],
    manifest: dict[str, Any],
    manifest_by_name: dict[str, dict[str, Any]],
    pdf_directory: Path,
) -> Counter[str]:
    cases = require_list(dataset.get("cases"), "cases")
    if not cases:
        raise ValueError("cases 不能为空")

    readers: dict[str, PdfReader] = {}
    seen_ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    answerable_count = 0
    unanswerable_count = 0
    answerable_categories: set[str] = set()
    reserved_absent_topics = set(
        require_list(
            manifest.get("reserved_absent_topics"),
            "manifest.reserved_absent_topics",
        )
    )

    for position, item in enumerate(cases, start=1):
        case = require_mapping(item, f"cases[{position}]")
        case_id = require_non_empty_string(
            case.get("id"),
            f"cases[{position}].id",
        )
        if case_id in seen_ids:
            raise ValueError(f"case id 重复：{case_id}")
        seen_ids.add(case_id)

        category = require_non_empty_string(
            case.get("category"),
            f"{case_id}.category",
        )
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"{case_id} 使用未知 category：{category}")
        category_counts[category] += 1

        require_non_empty_string(case.get("question"), f"{case_id}.question")
        require_non_empty_string(
            case.get("expected_answer"),
            f"{case_id}.expected_answer",
        )
        expected_points = require_list(
            case.get("expected_points"),
            f"{case_id}.expected_points",
        )
        if not expected_points:
            raise ValueError(f"{case_id}.expected_points 不能为空")
        for point_index, point in enumerate(expected_points, start=1):
            require_non_empty_string(
                point,
                f"{case_id}.expected_points[{point_index}]",
            )

        answerable = case.get("answerable")
        expected_refusal = case.get("expected_refusal")
        if type(answerable) is not bool:
            raise ValueError(f"{case_id}.answerable 必须是布尔值")
        if type(expected_refusal) is not bool:
            raise ValueError(f"{case_id}.expected_refusal 必须是布尔值")
        evidence_items = require_list(
            case.get("expected_evidence"),
            f"{case_id}.expected_evidence",
        )

        if answerable:
            answerable_count += 1
            answerable_categories.add(category)
            if category == "unanswerable":
                raise ValueError(f"{case_id} 可回答但 category 是 unanswerable")
            if expected_refusal:
                raise ValueError(f"{case_id} 可回答但 expected_refusal=true")
            if not evidence_items:
                raise ValueError(f"{case_id} 可回答但没有 expected_evidence")

            evidence_filenames: set[str] = set()
            for evidence_index, evidence_item in enumerate(
                evidence_items,
                start=1,
            ):
                evidence = require_mapping(
                    evidence_item,
                    f"{case_id}.expected_evidence[{evidence_index}]",
                )
                filename = require_non_empty_string(
                    evidence.get("filename"),
                    f"{case_id}.expected_evidence[{evidence_index}].filename",
                )
                if filename not in manifest_by_name:
                    raise ValueError(f"{case_id} 引用了未知 PDF：{filename}")
                evidence_filenames.add(filename)

                page_number = evidence.get("page_number")
                page_count = manifest_by_name[filename].get("page_count")
                if (
                    type(page_number) is not int
                    or type(page_count) is not int
                    or not 1 <= page_number <= page_count
                ):
                    raise ValueError(
                        f"{case_id} 的 {filename} 页码超出冻结范围"
                    )

                evidence_contains = require_non_empty_string(
                    evidence.get("evidence_contains"),
                    f"{case_id}.expected_evidence[{evidence_index}].evidence_contains",
                )
                if filename not in readers:
                    readers[filename] = PdfReader(pdf_directory / filename)
                extracted_text = (
                    readers[filename].pages[page_number - 1].extract_text()
                    or ""
                )
                if normalize_text(evidence_contains) not in normalize_text(
                    extracted_text
                ):
                    raise ValueError(
                        f"{case_id} 的证据原文不在 {filename} 第 {page_number} 页"
                    )

            if category == "cross_document" and len(evidence_filenames) < 2:
                raise ValueError(f"{case_id} 是跨文档题但证据不足两个 PDF")
        else:
            unanswerable_count += 1
            if category != "unanswerable":
                raise ValueError(f"{case_id} 不可回答但 category 不是 unanswerable")
            if not expected_refusal:
                raise ValueError(f"{case_id} 不可回答但 expected_refusal=false")
            if evidence_items:
                raise ValueError(f"{case_id} 不可回答但仍标注了证据")
            absent_topic = require_non_empty_string(
                case.get("absent_topic"),
                f"{case_id}.absent_topic",
            )
            if absent_topic not in reserved_absent_topics:
                raise ValueError(
                    f"{case_id}.absent_topic 不在 manifest 的保留缺失主题中"
                )

    answerable_minimum = evaluation.get("answerable_minimum")
    unanswerable_minimum = evaluation.get("unanswerable_minimum")
    if type(answerable_minimum) is not int or answerable_minimum < 12:
        raise ValueError("answerable_minimum 必须至少为 12")
    if type(unanswerable_minimum) is not int or unanswerable_minimum < 6:
        raise ValueError("unanswerable_minimum 必须至少为 6")
    if answerable_count < answerable_minimum:
        raise ValueError(
            f"可回答题不足：需要 {answerable_minimum}，实际 {answerable_count}"
        )
    if unanswerable_count < unanswerable_minimum:
        raise ValueError(
            f"无答案题不足：需要 {unanswerable_minimum}，实际 {unanswerable_count}"
        )

    required_categories = set(
        require_list(
            evaluation.get("required_answerable_categories"),
            "evaluation.required_answerable_categories",
        )
    )
    missing_categories = required_categories - answerable_categories
    if missing_categories:
        raise ValueError(
            "可回答题缺少类别：" + ", ".join(sorted(missing_categories))
        )

    return category_counts


def validate_dataset(dataset_path: Path) -> None:
    dataset = read_json(dataset_path.resolve())
    if dataset.get("schema_version") != 1:
        raise ValueError("schema_version 必须为 1")
    dataset_version = require_non_empty_string(
        dataset.get("dataset_version"),
        "dataset_version",
    )
    evaluation = require_mapping(dataset.get("evaluation"), "evaluation")
    validate_candidates(evaluation)
    manifest, manifest_by_name, pdf_directory = validate_corpus(dataset)
    category_counts = validate_cases(
        dataset=dataset,
        evaluation=evaluation,
        manifest=manifest,
        manifest_by_name=manifest_by_name,
        pdf_directory=pdf_directory,
    )

    total = sum(category_counts.values())
    answerable = total - category_counts["unanswerable"]
    print(f"OK：评测集版本 {dataset_version}")
    print(
        "OK：语料版本 "
        f"{manifest['corpus_version']}，{len(manifest_by_name)} 个 PDF 哈希一致"
    )
    print(
        f"OK：共 {total} 题（可回答 {answerable}，"
        f"无答案 {category_counts['unanswerable']}）"
    )
    print(
        "OK：题型 "
        + "，".join(
            f"{category}={category_counts[category]}"
            for category in sorted(category_counts)
        )
    )
    print("OK：JSON 结构、证据页、原文锚点和拒答标签通过校验")


def main() -> None:
    args = parse_args()
    validate_dataset(args.dataset)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError, PdfReadError) as exc:
        print(f"ERROR：{exc}", file=sys.stderr)
        raise SystemExit(1) from None