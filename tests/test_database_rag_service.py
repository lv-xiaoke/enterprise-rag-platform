import asyncio

from app.repositories.chunk_repository import ChunkSearchResult
from app.services.database_rag_service import (
    DatabaseRAGService,
    REFUSAL_ANSWER,
)


class FakeRetrievalService:
    def __init__(self, results: list[ChunkSearchResult]) -> None:
        self._results = results
        self.calls: list[tuple[int, str, int]] = []

    def search(
        self,
        knowledge_base_id: int,
        question: str,
        top_k: int,
    ) -> list[ChunkSearchResult]:
        self.calls.append((knowledge_base_id, question, top_k))
        return list(self._results)


class FakeLLMService:
    def __init__(self, answer: str = "员工需要先提交申请。") -> None:
        self._answer = answer
        self.messages: list[str] = []

    async def chat(self, message: str) -> str:
        self.messages.append(message)
        return self._answer


def build_source(score: float) -> ChunkSearchResult:
    return ChunkSearchResult(
        chunk_id=101,
        document_id=21,
        knowledge_base_id=7,
        filename="员工请假与考勤制度.pdf",
        page_number=2,
        chunk_index=4,
        content="员工请假应提前提交申请并等待审批。",
        score=score,
    )


def test_answer_maps_source_and_builds_traceable_context() -> None:
    source = build_source(score=0.9)
    retrieval_service = FakeRetrievalService([source])
    llm_service = FakeLLMService()
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
        min_relevance_score=0.55,
    )

    result = asyncio.run(
        service.answer(
            knowledge_base_id=7,
            question="  员工如何请假？  ",
            top_k=3,
        )
    )

    assert result.refused is False
    assert result.answer == "员工需要先提交申请。"
    assert result.sources == [source]
    assert retrieval_service.calls == [(7, "员工如何请假？", 3)]
    assert len(llm_service.messages) == 1

    prompt = llm_service.messages[0]
    assert "员工如何请假？" in prompt
    assert "员工请假与考勤制度.pdf" in prompt
    assert "页码：2" in prompt
    assert "Chunk ID：101" in prompt
    assert "员工请假应提前提交申请并等待审批。" in prompt


def test_answer_refuses_low_score_without_calling_llm() -> None:
    retrieval_service = FakeRetrievalService(
        [build_source(score=0.54)]
    )
    llm_service = FakeLLMService()
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
        min_relevance_score=0.55,
    )

    result = asyncio.run(
        service.answer(
            knowledge_base_id=7,
            question="知识库里没有答案的问题",
            top_k=3,
        )
    )

    assert result.answer == REFUSAL_ANSWER
    assert result.refused is True
    assert result.sources == []
    assert llm_service.messages == []