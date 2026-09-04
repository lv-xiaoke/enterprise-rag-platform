from sqlalchemy.orm import Session

from app.repositories.chunk_repository import (
    ChunkRepository,
    ChunkSearchResult,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.embedding_service import EmbeddingService


DEFAULT_TOP_K = 3
MAX_TOP_K = 10
EMBEDDING_DIMENSION = 512


class RetrievalService:
    """生成 Query Embedding 并执行限定范围的 pgvector 检索。"""

    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService,
    ) -> None:
        self._embedding_service = embedding_service
        self._knowledge_bases = KnowledgeBaseRepository(session)
        self._chunks = ChunkRepository(session)

    def search(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[ChunkSearchResult]:
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError("question 不能为空")
        if top_k <= 0 or top_k > MAX_TOP_K:
            raise ValueError(
                f"top_k 必须在 1 到 {MAX_TOP_K} 之间"
            )

        knowledge_base = self._knowledge_bases.get(
            knowledge_base_id
        )
        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        try:
            query_embedding = self._embedding_service.embed_query(
                cleaned_question
            )
        except Exception as exc:
            raise RuntimeError("问题向量生成失败") from exc

        self._validate_query_embedding(query_embedding)

        return self._chunks.search_similar(
            knowledge_base_id=knowledge_base.id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

    @staticmethod
    def _validate_query_embedding(
        query_embedding: list[float],
    ) -> None:
        actual_dimension = len(query_embedding)
        if actual_dimension != EMBEDDING_DIMENSION:
            raise RuntimeError(
                "Query Embedding 维度应为 "
                f"{EMBEDDING_DIMENSION}，实际为 "
                f"{actual_dimension}"
            )