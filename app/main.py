from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from app.database import get_messages, init_database, save_message
from app.models import (
    ChatRequest,
    ChatResponse,
    Message,
    RAGChatRequest,
    RAGChatResponse,
    UploadResponse,
    RAGSource,
)

from app.services.llm_service import LLMService
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
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