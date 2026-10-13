"""Application factory. No model download or database write occurs at import."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api import router as knowledge_router
from app.auth import router as auth_router
from app.config import AppSettings
from app.conversations import recover_generating, router as conversation_router
from app.db import SessionLocal
from app.observability import RequestTraceMiddleware
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService


class BrowserRequestGuard:
    def __init__(self,app,settings):
        self.app,self.settings=app,settings

    async def __call__(self,scope,receive,send):
        if scope['type'] != 'http' or scope['method'] in ('GET','HEAD','OPTIONS'):
            return await self.app(scope,receive,send)
        headers = {key.decode('latin1'):value.decode('latin1') for key,value in scope['headers']}
        host_origin = f"{scope.get('scheme','http')}://{headers.get('host','')}"
        allowed = {host_origin.rstrip('/'),self.settings.app_origin.rstrip('/')}
        origin = headers.get('origin')
        if headers.get('sec-fetch-site') == 'cross-site' or (origin is not None and origin.rstrip('/') not in allowed):
            return await JSONResponse({'detail':'请求来源不受信任，请从本站重新操作'},status_code=403)(scope,receive,send)
        # Limit the transport body as well as file bytes, before multipart can
        # spool an arbitrarily large upload to disk. Allow multipart headers.
        limit = self.settings.max_upload_bytes + 65536 if '/documents' in scope['path'] else 65536
        try:
            length = int(headers.get('content-length','0'))
        except ValueError:
            return await JSONResponse({'detail':'请求长度无效'},status_code=400)(scope,receive,send)
        if length > limit:
            return await JSONResponse({'detail':'请求内容过大'},status_code=413)(scope,receive,send)
        consumed=0
        async def bounded_receive():
            nonlocal consumed
            event=await receive()
            consumed += len(event.get('body',b''))
            if consumed > limit:
                raise HTTPException(413,'请求内容过大')
            return event
        await self.app(scope,bounded_receive,send)


def create_app(*,session_factory=None,embedding_service=None,pdf_service=None,llm_service=None,settings=None):
    settings = settings or AppSettings()
    factory = session_factory or SessionLocal

    @asynccontextmanager
    async def lifespan(application):
        application.state.generation_slots = asyncio.Semaphore(settings.max_generations)
        await run_in_threadpool(recover_generating,factory)
        yield

    application = FastAPI(title='企业知识库助手',version='1.0.0',lifespan=lifespan)
    application.state.session_factory=factory
    application.state.settings=settings
    application.state.embedding_service=embedding_service or EmbeddingService()
    application.state.pdf_service=pdf_service or PDFService()
    application.state.llm_service=llm_service or LLMService()
    application.state.generation_slots=asyncio.Semaphore(settings.max_generations)
    application.add_middleware(BrowserRequestGuard,settings=settings)
    application.add_middleware(RequestTraceMiddleware)
    application.include_router(auth_router)
    application.include_router(knowledge_router)
    application.include_router(conversation_router)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(_request,_exc):
        return JSONResponse(status_code=503,content={'detail':'数据库服务暂时不可用，请稍后重试'})

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request,_exc):
        return JSONResponse(status_code=422,content={'detail':'输入格式不正确，请检查字段内容与长度'})

    @application.get('/health')
    def health(response:Response):
        connected=False
        try:
            with factory() as session:
                connected=session.scalar(text('SELECT 1')) == 1
        except SQLAlchemyError:
            pass
        if not connected:
            response.status_code=503
        return {'status':'ok' if connected else 'error','database_connected':connected,'llm_configured':application.state.llm_service.is_configured()}

    @application.get('/')
    def root():
        return {'message':'企业知识库助手 API'}

    return application


app=create_app()
