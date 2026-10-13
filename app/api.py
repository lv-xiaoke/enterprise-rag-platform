"""Owned knowledge base API; synchronous SQL/CPU work runs in worker threads."""
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.auth import current_user, require_knowledge_base
from app.models import DocumentResponse, DocumentUploadResponse, KnowledgeBaseCreateRequest, KnowledgeBaseQueryRequest, KnowledgeBaseQueryResponse, KnowledgeBaseResponse
from app.orm_models import Document, KnowledgeBase
from app.services.database_rag_service import DatabaseRAGService, REFUSAL_ANSWER
from app.services.document_ingestion_service import DocumentIngestionService, DocumentInputError, DocumentProcessingError
from app.services.rag_service import build_rag_prompt
from app.services.retrieval_service import RetrievalService
from app.observability import trace_stage

router = APIRouter(prefix='/api/knowledge-bases')


def kb_response(kb):
    return KnowledgeBaseResponse(id=kb.id,name=kb.name,description=kb.description,created_at=kb.created_at)


def document_response(document):
    return DocumentResponse(**{key:getattr(document,key) for key in DocumentResponse.model_fields})


@router.get('', response_model=list[KnowledgeBaseResponse])
def list_knowledge_bases(request: Request, user_id: int = Depends(current_user)):
    with request.app.state.session_factory() as session:
        return [kb_response(kb) for kb in session.scalars(select(KnowledgeBase).where(KnowledgeBase.owner_id == user_id).order_by(KnowledgeBase.id))]


@router.post('', status_code=201, response_model=KnowledgeBaseResponse)
def create_knowledge_base(body: KnowledgeBaseCreateRequest, request: Request, user_id: int = Depends(current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400,'知识库名称不能为空')
    with request.app.state.session_factory() as session:
        kb = KnowledgeBase(owner_id=user_id,name=name,description=(body.description or '').strip() or None)
        session.add(kb)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409,'知识库名称已存在') from None
        return kb_response(kb)


@router.get('/{kb_id}', response_model=KnowledgeBaseResponse)
def get_knowledge_base(kb_id: int, request: Request, user_id: int = Depends(current_user)):
    with request.app.state.session_factory() as session:
        return kb_response(require_knowledge_base(session,kb_id,user_id))


@router.get('/{kb_id}/documents', response_model=list[DocumentResponse])
def list_documents(kb_id: int, request: Request, user_id: int = Depends(current_user)):
    with request.app.state.session_factory() as session:
        require_knowledge_base(session,kb_id,user_id)
        return [document_response(doc) for doc in session.scalars(select(Document).where(Document.knowledge_base_id == kb_id).order_by(Document.id))]


@router.get('/{kb_id}/documents/{document_id}', response_model=DocumentResponse)
def get_document(kb_id: int, document_id: int, request: Request, user_id: int = Depends(current_user)):
    with request.app.state.session_factory() as session:
        require_knowledge_base(session,kb_id,user_id)
        doc = session.get(Document, document_id)
        if doc is None or doc.knowledge_base_id != kb_id:
            raise HTTPException(404,'文档不存在')
        return document_response(doc)


def ingest(request, kb_id, user_id, filename, content):
    with request.app.state.session_factory() as session:
        require_knowledge_base(session,kb_id,user_id)
        service = DocumentIngestionService(session, request.app.state.pdf_service, request.app.state.embedding_service)
        try:
            result = service.ingest_pdf(kb_id, filename, content)
        except DocumentInputError as exc:
            raise HTTPException(400,str(exc)) from None
        except DocumentProcessingError:
            raise HTTPException(502,'文档处理失败，请检查文件或稍后重试') from None
        return DocumentUploadResponse(document=document_response(session.get(Document,result.document_id)),page_count=result.page_count,chunk_count=result.chunk_count)


@router.post('/{kb_id}/documents', status_code=201, response_model=DocumentUploadResponse)
async def upload_document(kb_id: int, request: Request, file: UploadFile, user_id: int = Depends(current_user)):
    # Check ownership before reading or parsing the uploaded file.
    await run_in_threadpool(check_owned, request.app.state.session_factory,kb_id,user_id)
    content = bytearray()
    try:
        while part := await file.read(65536):
            content.extend(part)
            if len(content) > request.app.state.settings.max_upload_bytes:
                raise HTTPException(413,'文件过大，请压缩 PDF 后重试')
    finally:
        await file.close()
    return await run_in_threadpool(ingest,request,kb_id,user_id,file.filename or '',bytes(content))


def check_owned(factory,kb_id,user_id):
    with factory() as session:
        require_knowledge_base(session,kb_id,user_id)


def retrieve_sources(state, kb_id, user_id, question, top_k=3):
    with state.session_factory() as session:
        require_knowledge_base(session,kb_id,user_id)
        with trace_stage('retrieval',knowledge_base_id=kb_id,user_id=user_id) as metrics:
            results = RetrievalService(session,state.embedding_service).search(kb_id,question,top_k)
            filtered = [result for result in results if result.score >= state.settings.min_relevance_score]
            metrics['source_count'] = len(filtered)
            return filtered


def source_snapshot(results):
    return [{key:value for key,value in asdict(result).items() if key != 'knowledge_base_id'} for result in results]


def evidence_prompt(question, results):
    return build_rag_prompt(question,[DatabaseRAGService._build_context(result) for result in results])


@router.post('/{kb_id}/query',response_model=KnowledgeBaseQueryResponse)
async def query(kb_id: int, body: KnowledgeBaseQueryRequest, request: Request, user_id: int = Depends(current_user)):
    try:
        results = await run_in_threadpool(retrieve_sources,request.app.state,kb_id,user_id,body.question,body.top_k)
        if not results:
            return KnowledgeBaseQueryResponse(answer=REFUSAL_ANSWER,refused=True,sources=[])
        with trace_stage('llm',failure_code='llm_error',knowledge_base_id=kb_id):
            answer = await request.app.state.llm_service.chat(evidence_prompt(body.question,results))
        if not isinstance(answer,str) or not answer.strip():
            raise RuntimeError('empty answer')
        return KnowledgeBaseQueryResponse(answer=answer.strip(),refused=False,sources=source_snapshot(results))
    except ValueError:
        raise HTTPException(503,'大模型服务未配置，请联系管理员') from None
    except RuntimeError:
        raise HTTPException(502,'问答服务暂时不可用，请稍后重试') from None
