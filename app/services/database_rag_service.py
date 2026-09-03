from dataclasses import dataclass

from app.repositories.chunk_repository import ChunkSearchResult
from app.services.llm_service import LLMService
from app.services.rag_service import build_rag_prompt
from app.services.retrieval_service import (
    DEFAULT_TOP_K,
    RetrievalService,
)


MIN_RELEVANCE_SCORE = 0.55
REFUSAL_ANSWER = "当前知识库中没有找到足够的信息。"


class RAGConfigurationError(RuntimeError):
    """RAG 生成所需的外部配置不完整。"""


@dataclass(frozen=True)
class DatabaseRAGResult:
    answer: str
    refused: bool
    sources: list[ChunkSearchResult]


class DatabaseRAGService:
    """编排指定知识库的检索、拒答和 LLM 生成。"""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        min_relevance_score: float = MIN_RELEVANCE_SCORE,
    ) -> None:
        if not -1.0 <= min_relevance_score <= 1.0:
            raise ValueError(
                "min_relevance_score 必须在 -1 到 1 之间"
            )

        self._retrieval_service = retrieval_service
        self._llm_service = llm_service
        self._min_relevance_score = min_relevance_score

    async def answer(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> DatabaseRAGResult:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("question 不能为空")

        search_results = self._retrieval_service.search(
            knowledge_base_id=knowledge_base_id,
            question=cleaned_question,
            top_k=top_k,
        )
        relevant_results = [
            result
            for result in search_results
            if result.score >= self._min_relevance_score
        ]

        if not relevant_results:
            return DatabaseRAGResult(
                answer=REFUSAL_ANSWER,
                refused=True,
                sources=[],
            )

        contexts = [
            self._build_context(result)
            for result in relevant_results
        ]
        prompt = build_rag_prompt(
            question=cleaned_question,
            contexts=contexts,
        )

        try:
            answer = await self._llm_service.chat(prompt)
        except ValueError as exc:
            raise RAGConfigurationError(
                "大模型服务配置不完整"
            ) from exc

        return DatabaseRAGResult(
            answer=answer.strip(),
            refused=False,
            sources=relevant_results,
        )

    @staticmethod
    def _build_context(result: ChunkSearchResult) -> str:
        return (
            f"文档：{result.filename}\n"
            f"页码：{result.page_number}\n"
            f"Chunk ID：{result.chunk_id}\n"
            f"原文：\n{result.content}"
        )