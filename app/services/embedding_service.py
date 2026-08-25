from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class EmbeddingService:
    """负责把查询和文档文本转换成向量。"""

    def __init__(self) -> None:
        self.model = SentenceTransformer(MODEL_NAME)

    def embed_query(self, query: str) -> list[float]:
        """把一个短查询转换成归一化向量。"""
        text = f"{QUERY_INSTRUCTION}{query}"
        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )
        return vector.tolist()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """把多段文档文本转换成归一化向量。"""
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )
        return vectors.tolist()