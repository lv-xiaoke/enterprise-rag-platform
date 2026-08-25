import json
from pathlib import Path

from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
    SearchResult,
)


QUESTIONS_PATH = Path(
    "data/evaluation/questions.json"
)
RESULTS_PATH = Path(
    "data/evaluation/top_k_comparison.json"
)
TOP_K_VALUES = (1, 3)


def format_sources(
    results: list[SearchResult],
) -> list[dict]:
    """为人工检查保留排名、页码、相似度和原文。"""
    return [
        {
            "rank": rank,
            "page": result.page,
            "score": round(result.score, 6),
            "text": result.text,
        }
        for rank, result in enumerate(
            results,
            start=1,
        )
    ]


def main() -> None:
    data = json.loads(
        QUESTIONS_PATH.read_text(
            encoding="utf-8-sig"
        )
    )
    baseline = data["baseline"]
    document_path = Path(data["document"])

    pages = PDFService().extract_pages(
        document_path
    )
    chunks: list[DocumentChunk] = []

    for page_number, page_text in enumerate(
        pages,
        start=1,
    ):
        page_chunks = split_text(
            page_text,
            chunk_size=baseline["chunk_size"],
            overlap=baseline["overlap"],
        )
        chunks.extend(
            DocumentChunk(
                text=chunk_text,
                page=page_number,
            )
            for chunk_text in page_chunks
        )

    if not chunks:
        raise ValueError("测试 PDF 没有生成 Chunk")

    print("加载 Embedding 模型……")
    embedding_service = EmbeddingService()
    document_vectors = (
        embedding_service.embed_documents(
            [chunk.text for chunk in chunks]
        )
    )
    vector_store = FAISSVectorStore(
        dimension=len(document_vectors[0])
    )
    vector_store.add(chunks, document_vectors)

    answerable_cases = [
        case
        for case in data["cases"]
        if case["answerable"]
    ]
    comparison_cases: list[dict] = []

    for position, case in enumerate(
        answerable_cases,
        start=1,
    ):
        print(
            f"[{position}/{len(answerable_cases)}] "
            f"{case['id']}"
        )
        query_vector = (
            embedding_service.embed_query(
                case["question"]
            )
        )

        comparison_case = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_answer": (
                case["expected_answer"]
            ),
            "expected_points": (
                case["expected_points"]
            ),
            "comparison_notes": "",
        }

        for top_k in TOP_K_VALUES:
            results = vector_store.search(
                query_vector,
                top_k=top_k,
            )
            comparison_case[f"top_{top_k}"] = {
                "retrieved_sources": (
                    format_sources(results)
                ),
                "retrieval_hit": None,
            }

        comparison_cases.append(
            comparison_case
        )

    output = {
        "document": str(document_path),
        "experiment": {
            "fixed_chunk_size": (
                baseline["chunk_size"]
            ),
            "fixed_overlap": baseline["overlap"],
            "top_k_values": list(TOP_K_VALUES),
            "question_count": len(
                comparison_cases
            ),
            "calls_llm": False,
        },
        "manual_summary": {
            "top_1_hits": None,
            "top_3_hits": None,
            "cases_helped_by_top_3": [],
            "conclusion": "",
        },
        "cases": comparison_cases,
    }

    RESULTS_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Chunk 数量：", len(chunks))
    print("结果已保存到：", RESULTS_PATH)


if __name__ == "__main__":
    main()
