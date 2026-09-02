from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories import (
    ChunkCreate,
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService


DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 40
EMBEDDING_DIMENSION = 512

# 表示一次 PDF 入库成功之后返回的结果。
@dataclass(frozen=True)
class DocumentIngestionResult:
    document_id: int
    knowledge_base_id: int
    filename: str
    page_count: int
    chunk_count: int
    status: str

# 表示已经切好的文本块，但还没有生成 embedding，也还没有写数据库。
# 为什么名字前面有：下划线？表示它是 DocumentIngestionService 的内部类，外部不应该直接使用它。
@dataclass(frozen=True)
class _PreparedChunk:
    page_number: int
    chunk_index: int
    content: str


class DocumentIngestionService:
    """把 PDF 处理结果持久化为 Document 和 Chunk 记录。"""

    def __init__(
        self,
        session: Session,
        pdf_service: PDFService,
        embedding_service: EmbeddingService,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

        self._session = session
        self._pdf_service = pdf_service
        self._embedding_service = embedding_service
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._knowledge_bases = KnowledgeBaseRepository(session)
        self._documents = DocumentRepository(session)
        self._chunks = ChunkRepository(session)

    # 接收一个 PDF，把它解析、切块、向量化并保存进数据库。
    def ingest_pdf(
        self,
        knowledge_base_id: int,
        filename: str,
        pdf_bytes: bytes,
    ) -> DocumentIngestionResult:
        cleaned_filename = filename.strip()
        if not cleaned_filename:
            raise ValueError("filename 不能为空")

        knowledge_base = self._knowledge_bases.get(knowledge_base_id)
        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        # PDF 真正处理之前，先往数据库建立一条 Document 记录。
        document = self._documents.create(
            knowledge_base_id=knowledge_base.id,
            filename=cleaned_filename,
            status="processing",
        )

        self._session.commit() # 先把文档保存下来
        document_id = document.id

        try:
            # 从 PDF 二进制内容中提取每一页的文本。
            pages = self._pdf_service.extract_pages_from_bytes(
                pdf_bytes
            )
            
            prepared_chunks = self._prepare_chunks(pages)

            if not prepared_chunks:
                raise ValueError("PDF 没有生成任何 Chunk")

            embeddings = self._embedding_service.embed_documents(
                [chunk.content for chunk in prepared_chunks]
            )
            self._validate_embeddings(
                embeddings=embeddings,
                expected_count=len(prepared_chunks),
            )

            chunk_inputs = [
                ChunkCreate(
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=embedding,
                )
                for chunk, embedding in zip(
                    prepared_chunks,
                    embeddings,
                )
            ]
            stored_chunks = self._chunks.bulk_create(
                document_id=document_id,
                chunks=chunk_inputs,
            )

            ready_document = self._documents.update_status(
                document_id=document_id,
                status="ready",
            )
            if ready_document is None:
                raise RuntimeError("Document 状态更新失败")

            self._session.commit()

            return DocumentIngestionResult(
                document_id=document_id,
                knowledge_base_id=knowledge_base.id,
                filename=cleaned_filename,
                page_count=len(pages),
                chunk_count=len(stored_chunks),
                status="ready",
            )
        except Exception as exc:
            self._session.rollback()
            try:
                self._mark_document_failed(
                    document_id=document_id,
                    error=exc,
                )
            except Exception as status_error:
                self._session.rollback()
                raise RuntimeError(
                    "文档处理失败，且无法保存 failed 状态"
                ) from status_error
            raise

    def _prepare_chunks(
        self,
        pages: list[str],
    ) -> list[_PreparedChunk]:
        prepared_chunks: list[_PreparedChunk] = []

        for page_number, page_text in enumerate(pages, start=1):
            page_chunks = split_text(
                page_text,
                chunk_size=self._chunk_size,
                overlap=self._chunk_overlap,
            )
            for content in page_chunks:
                prepared_chunks.append(
                    _PreparedChunk(
                        page_number=page_number,
                        chunk_index=len(prepared_chunks),
                        content=content,
                    )
                )

        return prepared_chunks

    @staticmethod
    def _validate_embeddings(
        embeddings: list[list[float]],
        expected_count: int,
    ) -> None:
        if len(embeddings) != expected_count:
            raise RuntimeError(
                "Chunk 与 Embedding 数量不一致: "
                f"chunks={expected_count}, embeddings={len(embeddings)}"
            )

        for index, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSION:
                raise RuntimeError(
                    f"第 {index} 个 Embedding 维度应为 "
                    f"{EMBEDDING_DIMENSION}，实际为 {len(embedding)}"
                )

    def _mark_document_failed(
        self,
        document_id: int,
        error: Exception,
    ) -> None:
        failed_document = self._documents.update_status(
            document_id=document_id,
            status="failed",
            failure_reason=self._safe_failure_reason(error),
        )
        if failed_document is None:
            raise RuntimeError("找不到需要标记失败的 Document")
        self._session.commit()

    @staticmethod
    def _safe_failure_reason(error: Exception) -> str:
        if isinstance(error, ValueError):
            message = str(error).strip()
            if message:
                return message[:500]
        return "文档处理失败"