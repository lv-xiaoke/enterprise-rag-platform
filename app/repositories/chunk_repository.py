from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Chunk


@dataclass(frozen=True)
class ChunkCreate:
    page_number: int
    chunk_index: int
    content: str
    embedding: list[float]


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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

    def list_by_document(self, document_id: int) -> list[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return list(self._session.scalars(statement))