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