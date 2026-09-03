from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_messages, init_database, save_message
from app.db import get_db_session
from app.models import (
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    KnowledgeBaseQuerySource,
    KnowledgeBaseResponse,
    Message,
    RAGChatRequest,
    RAGChatResponse,
    RAGSource,
    UploadResponse,
)
from app.orm_models import (
    Document as DocumentModel,
    KnowledgeBase as KnowledgeBaseModel,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.services.chunk_service import split_text

from app.services.database_rag_service import (
    DatabaseRAGService,
    RAGConfigurationError,
)

from app.services.document_ingestion_service import (
    DocumentIngestionService,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService

from app.services.retrieval_service import RetrievalService

from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
)


DatabaseSession = Annotated[Session, Depends(get_db_session)]


def to_knowledge_base_response(
    knowledge_base: KnowledgeBaseModel,
) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=knowledge_base.id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        created_at=knowledge_base.created_at,
    )


def to_document_response(
    document: DocumentModel,
) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        filename=document.filename,
        status=document.status,
        failure_reason=document.failure_reason,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )

app = FastAPI(
    title="Mini RAG Backend",
    description="一个用于学习 RAG 和 AI 应用开发的后端项目",
    version="0.1.0",
)

# print("开始创建 LLMService")
llm_service = LLMService()
pdf_service = PDFService()
embedding_service = EmbeddingService()
rag_service: RAGService | None = None

CHUNK_SIZE = 200
CHUNK_OVERLAP = 40
TOP_K = 3

# print("开始初始化数据库")
init_database()  # 启动时初始化数据库

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Mini RAG Backend is running"
    }


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "llm_configured": llm_service.is_configured(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, response: Response) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    response.headers["Content-Type"] = "application/json; charset=utf-8"

    save_message(role="user", content=message)

    try:
        reply = await llm_service.chat(message)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    save_message(role="assistant", content=reply)

    return ChatResponse(reply=reply)

@app.get("/history", response_model=list[Message])
async def history(response: Response) -> list[Message]:
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return get_messages()


@app.get("/request-info")
async def request_info(
    x_client_name: str | None = Header(default=None),
) -> dict[str, str]:
    return {
        "client_name": x_client_name or "unknown"
    }


@app.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=201,
)
def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    session: DatabaseSession,
) -> KnowledgeBaseResponse:
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=400,
            detail="知识库名称不能只包含空格",
        )

    description = (
        request.description.strip()
        if request.description is not None
        else None
    )
    if description == "":
        description = None

    try:
        knowledge_base = KnowledgeBaseRepository(session).create(
            name=name,
            description=description,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="知识库名称已存在",
        ) from exc

    return to_knowledge_base_response(knowledge_base)


@app.get(
    "/knowledge-bases",
    response_model=list[KnowledgeBaseResponse],
)
def list_knowledge_bases(
    session: DatabaseSession,
) -> list[KnowledgeBaseResponse]:
    knowledge_bases = KnowledgeBaseRepository(session).list_all()
    return [
        to_knowledge_base_response(knowledge_base)
        for knowledge_base in knowledge_bases
    ]


@app.get(
    "/knowledge-bases/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
def get_knowledge_base(
    knowledge_base_id: int,
    session: DatabaseSession,
) -> KnowledgeBaseResponse:
    knowledge_base = KnowledgeBaseRepository(session).get(
        knowledge_base_id
    )
    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        )
    return to_knowledge_base_response(knowledge_base)


@app.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
async def upload_knowledge_base_document(
    knowledge_base_id: int,
    file: UploadFile,
    session: DatabaseSession,
) -> DocumentUploadResponse:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="只支持上传 PDF 文件",
        )

    pdf_bytes = await file.read()
    service = DocumentIngestionService(
        session=session,
        pdf_service=pdf_service,
        embedding_service=embedding_service,
    )

    try:
        result = service.ingest_pdf(
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            pdf_bytes=pdf_bytes,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="文档处理失败",
        ) from exc

    document = DocumentRepository(session).get(result.document_id)
    if document is None:
        raise HTTPException(
            status_code=500,
            detail="文档处理完成但无法读取结果",
        )

    return DocumentUploadResponse(
        document=to_document_response(document),
        page_count=result.page_count,
        chunk_count=result.chunk_count,
    )


@app.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=list[DocumentResponse],
)
def list_knowledge_base_documents(
    knowledge_base_id: int,
    session: DatabaseSession,
) -> list[DocumentResponse]:
    knowledge_base = KnowledgeBaseRepository(session).get(
        knowledge_base_id
    )
    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        )

    documents = DocumentRepository(
        session
    ).list_by_knowledge_base(knowledge_base.id)
    return [
        to_document_response(document)
        for document in documents
    ]


@app.get(
    "/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_knowledge_base_document(
    knowledge_base_id: int,
    document_id: int,
    session: DatabaseSession,
) -> DocumentResponse:
    document = DocumentRepository(session).get(document_id)
    if (
        document is None
        or document.knowledge_base_id != knowledge_base_id
    ):
        raise HTTPException(
            status_code=404,
            detail="文档不存在",
        )
    return to_document_response(document)


@app.post(
    "/knowledge-bases/{knowledge_base_id}/query",
    response_model=KnowledgeBaseQueryResponse,
)
async def query_knowledge_base(
    knowledge_base_id: int,
    request: KnowledgeBaseQueryRequest,
    session: DatabaseSession,
) -> KnowledgeBaseQueryResponse:
    retrieval_service = RetrievalService(
        session=session,
        embedding_service=embedding_service,
    )
    service = DatabaseRAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
    )

    try:
        result = await service.answer(
            knowledge_base_id=knowledge_base_id,
            question=request.question,
            top_k=request.top_k,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="知识库不存在",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RAGConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="大模型服务未配置",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="问答上游服务暂时不可用",
        ) from exc

    return KnowledgeBaseQueryResponse(
        answer=result.answer,
        refused=result.refused,
        sources=[
            KnowledgeBaseQuerySource(
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                filename=source.filename,
                page_number=source.page_number,
                chunk_index=source.chunk_index,
                content=source.content,
                score=round(source.score, 6),
            )
            for source in result.sources
        ],
    )



@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile) -> UploadResponse:
    global rag_service

    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="只支持上传 PDF 文件",
        )

    pdf_bytes = await file.read()

    try:
        pages = pdf_service.extract_pages_from_bytes(pdf_bytes)

        chunks: list[DocumentChunk] = []

        for page_number, page_text in enumerate(
            pages,
            start=1,
        ):
            page_chunks = split_text(
                page_text,
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP,
            )
            chunks.extend(
                DocumentChunk(
                    text=chunk_text,
                    page=page_number,
                )
                for chunk_text in page_chunks
            )

        if not chunks:
            raise ValueError("PDF 没有生成任何 Chunk")

        document_vectors = (
            embedding_service.embed_documents(
                [chunk.text for chunk in chunks]
            )
        )

        vector_store = FAISSVectorStore(
            dimension=len(document_vectors[0])
        )
        vector_store.add(chunks, document_vectors)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    rag_service = RAGService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_service=llm_service,
    )
    # 只有 PDF 解析、切块、Embedding 和 FAISS 写入全部成功后，才执行：

    return UploadResponse(
        filename=filename,
        page_count=len(pages),
        chunk_count=len(chunks),
    )


@app.post("/rag/chat", response_model=RAGChatResponse)
async def rag_chat(
    request: RAGChatRequest,
    response: Response,
) -> RAGChatResponse:
    
    response.headers["Content-Type"] = (
        "application/json; charset=utf-8"
    )

    if rag_service is None:
        raise HTTPException(
            status_code=400,
            detail="请先上传 PDF",
        )

    try:
        answer, search_results = await rag_service.answer(
            question=request.question,
            top_k=TOP_K,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return RAGChatResponse(
            answer=answer,
            sources=[
                RAGSource(
                    text=result.text,
                    page=result.page,
                    score=round(result.score, 6),
                )
                for result in search_results
            ],
        )