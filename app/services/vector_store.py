from dataclasses import dataclass

import faiss
import numpy as np


@dataclass(frozen=True)  # `@dataclass` 适合这种主要用于保存数据的普通 Python 类。`frozen=True` 表示对象创建后不能随意修改字段
class DocumentChunk:
    """一个等待写入向量库的文档块。"""

    text: str
    page: int


@dataclass(frozen=True)
class SearchResult:
    """一次向量检索得到的来源信息。"""

    text: str
    page: int
    score: float


class FAISSVectorStore:
    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[DocumentChunk] = []

    @property
    def count(self) -> int:
        return self.index.ntotal

    def add(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if not chunks:
            raise ValueError("chunks 不能为空")
        if len(chunks) != len(vectors):
            raise ValueError(
                "chunks 和 vectors 的数量必须一致"
            )
        if any(not chunk.text.strip() for chunk in chunks):
            raise ValueError("Chunk 文本不能为空")
        if any(chunk.page <= 0 for chunk in chunks):
            raise ValueError("Chunk 页码必须大于 0")

        matrix = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if matrix.ndim != 2:
            raise ValueError("vectors 必须是二维数组")
        if matrix.shape[1] != self.dimension:
            raise ValueError(
                f"向量维度应为 {self.dimension}，"
                f"实际为 {matrix.shape[1]}"
            )

        matrix = np.ascontiguousarray(matrix)
        faiss.normalize_L2(matrix)

        self.index.add(matrix)
        self.chunks.extend(chunks)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 3,
    ) -> list[SearchResult]:
        if not query_vector:
            raise ValueError("query_vector 不能为空")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        if self.count == 0:
            return []

        query_matrix = np.asarray(
            [query_vector],
            dtype=np.float32,
        )

        if (
            query_matrix.ndim != 2
            or query_matrix.shape[1] != self.dimension
        ):
            actual_dimension = (
                query_matrix.shape[1]
                if query_matrix.ndim == 2
                else "未知"
            )
            raise ValueError(
                f"查询向量维度应为 {self.dimension}，"
                f"实际为 {actual_dimension}"
            )

        query_matrix = np.ascontiguousarray(
            query_matrix
        )
        faiss.normalize_L2(query_matrix)

        k = min(top_k, self.count)
        scores, indices = self.index.search(
            query_matrix,
            k,
        )

        results: list[SearchResult] = []

        for index, score in zip(
            indices[0],  # 这里因为是只问了一个问题，所以只取第一行，indices[0] 是一个长度为 k 的数组，表示最相似的 k 个向量的索引
            scores[0],   # scores[0] 是一个长度为 k 的数组，表示对应的相似度分数
        ):
            if index < 0:
                continue

            chunk = self.chunks[int(index)]
            results.append(
                SearchResult(
                    text=chunk.text,
                    page=chunk.page,
                    score=float(score),
                )
            )

        return results
