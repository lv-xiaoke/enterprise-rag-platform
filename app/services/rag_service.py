from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store import (
    FAISSVectorStore,
    SearchResult,
)


def build_rag_prompt(
    question: str,
    contexts: list[str],
) -> str:
    """把参考资料和用户问题组合成 RAG Prompt。"""
    cleaned_question = question.strip()
    cleaned_contexts = [
        context.strip()
        for context in contexts
        if context.strip()
    ]

    if not cleaned_question:
        raise ValueError("question 不能为空")
    if not cleaned_contexts:
        raise ValueError("contexts 不能为空")

    context_text = "\n\n".join(
        f"[参考资料 {index}]\n{context}"
        for index, context in enumerate(
            cleaned_contexts,
            start=1,
        )
    )

    return (
        "请根据下面的参考资料回答问题。\n\n"
        f"参考资料：\n{context_text}\n\n"
        f"用户问题：\n{cleaned_question}\n\n"
        "如果参考资料中没有答案，请明确说明不知道。"
    )


class RAGService:
    """负责组织检索和大模型生成流程。"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: FAISSVectorStore,
        llm_service: LLMService,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.llm_service = llm_service

    async def answer(
        self,
        question: str,
        top_k: int = 3,
) -> tuple[str, list[SearchResult]]:
        """检索相关文本，并让大模型根据文本回答。"""
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError("question 不能为空")

        query_vector = self.embedding_service.embed_query(
            cleaned_question
        )
        search_results = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
        )

        if not search_results:
            raise ValueError("没有检索到可用的参考资料")

        contexts = [
            result.text
            for result in search_results
        ]
        prompt = build_rag_prompt(
            question=cleaned_question,
            contexts=contexts,
        )

        answer = await self.llm_service.chat(prompt)

        return answer, search_results