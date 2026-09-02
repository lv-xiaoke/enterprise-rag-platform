from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Chunk, Document, KnowledgeBase

# ChunkCreate 描述“准备创建的 Chunk 数据”
@dataclass(frozen=True)
class ChunkCreate:
    page_number: int
    chunk_index: int
    content: str
    embedding: list[float]

@dataclass(frozen=True)
class ChunkSearchResult:
    chunk_id: int
    document_id: int
    knowledge_base_id: int
    filename: str
    page_number: int
    chunk_index: int
    content: str
    score: float

# ChunkRepository 封装对 Chunk 表的数据库操作
class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # bulk_create 批量插入 Chunk
    def bulk_create(
        self,
        document_id: int,
        chunks: Sequence[ChunkCreate],
    ) -> list[Chunk]:
        chunk_models = [
            Chunk(
                document_id=document_id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
            )
            for chunk in chunks
        ]

        if not chunk_models:
            return []

        self._session.add_all(chunk_models)
        self._session.flush()
        return chunk_models

    # 查询某个文档的所有 Chunk
    def list_by_document(self, document_id: int) -> list[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return list(self._session.scalars(statement))

    def search_similar(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[ChunkSearchResult]:
        query_vector = list(query_embedding)
        distance_expression = Chunk.embedding.cosine_distance(
            query_vector
        )

        statement = (
            select(
                Chunk.id,
                Chunk.document_id,
                Document.knowledge_base_id,
                Document.filename,
                Chunk.page_number,
                Chunk.chunk_index,
                Chunk.content,
                distance_expression.label("distance"),
            )
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .join(
                KnowledgeBase,
                Document.knowledge_base_id == KnowledgeBase.id,
            )
            .where(
                KnowledgeBase.id == knowledge_base_id,
                Document.status == "ready",
            )
            .order_by(
                distance_expression.asc(),
                Chunk.id.asc(),
            )
            .limit(top_k)
        )

        rows = self._session.execute(statement)
        results: list[ChunkSearchResult] = []

        for (
            chunk_id,
            document_id,
            result_knowledge_base_id,
            filename,
            page_number,
            chunk_index,
            content,
            distance,
        ) in rows:
            results.append(
                ChunkSearchResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    knowledge_base_id=result_knowledge_base_id,
                    filename=filename,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    content=content,
                    score=1.0 - float(distance),
                )
            )

        return results