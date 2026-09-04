from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
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
MAX_FILENAME_LENGTH = 255


class DocumentInputError(ValueError):
    """客户端修改文件输入后可以解决的错误。"""


class DocumentProcessingError(RuntimeError):
    """不能向客户端公开底层细节的文档处理错误。"""


@dataclass(frozen=True)
class DocumentIngestionResult:
    document_id: int
    knowledge_base_id: int
    filename: str
    page_count: int
    chunk_count: int
    status: str


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

    def ingest_pdf(
        self,
        knowledge_base_id: int,
        filename: str,
        pdf_bytes: bytes,
    ) -> DocumentIngestionResult:
        cleaned_filename = self._validate_upload(
            filename=filename,
            pdf_bytes=pdf_bytes,
        )

        try:
            knowledge_base = self._knowledge_bases.get(
                knowledge_base_id
            )
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise DocumentProcessingError(
                "数据库服务暂时不可用"
            ) from exc

        if knowledge_base is None:
            raise LookupError(
                f"知识库不存在: {knowledge_base_id}"
            )

        try:
            document = self._documents.create(
                knowledge_base_id=knowledge_base.id,
                filename=cleaned_filename,
                status="processing",
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise DocumentProcessingError(
                "无法创建文档处理记录"
            ) from exc

        document_id = document.id

        try:
            pages = self._extract_pdf_pages(pdf_bytes)
            prepared_chunks = self._prepare_chunks(pages)

            if not prepared_chunks:
                raise DocumentInputError(
                    "PDF 没有生成任何 Chunk"
                )

            try:
                embeddings = (
                    self._embedding_service.embed_documents(
                        [
                            chunk.content
                            for chunk in prepared_chunks
                        ]
                    )
                )
            except Exception as exc:
                raise DocumentProcessingError(
                    "文档向量生成失败"
                ) from exc

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
                raise DocumentProcessingError(
                    "Document 状态更新失败"
                )

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
                raise DocumentProcessingError(
                    "文档处理失败，且无法保存 failed 状态"
                ) from status_error

            if isinstance(
                exc,
                (DocumentInputError, DocumentProcessingError),
            ):
                raise

            raise DocumentProcessingError(
                "文档处理失败"
            ) from exc

    @staticmethod
    def _validate_upload(
        filename: str,
        pdf_bytes: bytes,
    ) -> str:
        cleaned_filename = filename.strip()
        if not cleaned_filename:
            raise DocumentInputError("文件名不能为空")
        if len(cleaned_filename) > MAX_FILENAME_LENGTH:
            raise DocumentInputError(
                "文件名不能超过 255 个字符"
            )
        if not cleaned_filename.lower().endswith(".pdf"):
            raise DocumentInputError("只支持上传 PDF 文件")
        if not pdf_bytes:
            raise DocumentInputError("PDF 文件不能为空")
        return cleaned_filename

    def _extract_pdf_pages(
        self,
        pdf_bytes: bytes,
    ) -> list[str]:
        try:
            return self._pdf_service.extract_pages_from_bytes(
                pdf_bytes
            )
        except ValueError as exc:
            safe_message = str(exc).strip()
            if not safe_message:
                safe_message = "PDF 文件无法处理"
            raise DocumentInputError(
                safe_message[:500]
            ) from exc

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
            raise DocumentProcessingError(
                "Chunk 与 Embedding 数量不一致"
            )

        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIMENSION:
                raise DocumentProcessingError(
                    "Embedding 维度不符合入库约定"
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
            raise DocumentProcessingError(
                "找不到需要标记失败的 Document"
            )
        self._session.commit()

    @staticmethod
    def _safe_failure_reason(error: Exception) -> str:
        if isinstance(error, DocumentInputError):
            message = str(error).strip()
            if message:
                return message[:500]
        return "文档处理失败"