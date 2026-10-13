"""Safe application diagnostics; never serialize request or exception contents."""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import math
import sys
from time import perf_counter
from uuid import uuid4

import httpx
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse
from starlette.requests import ClientDisconnect

_request_id = ContextVar('rag_request_id', default=None)
_business_result = ContextVar('rag_business_result', default=None)
LOGGER = logging.getLogger('rag.app')
EVENTS = {'request_finished', 'stage_finished', 'llm_first_delta', 'generation_finished', 'document_finished'}
STAGES = {'authorization', 'pdf_parse', 'embedding', 'document_persist', 'retrieval', 'llm', 'generation_finalize'}
OUTCOMES = {'completed', 'failed', 'interrupted', 'refused'}
ERROR_CODES = {'llm_timeout', 'llm_unconfigured', 'llm_error', 'generation_timeout', 'database_error',
               'pdf_invalid', 'embedding_error', 'client_disconnected', 'request_rejected', 'internal_error',
               'answer_limit', 'llm_invalid_stream'}
NUMERIC_FIELDS = {'duration_ms', 'status_code', 'user_id', 'knowledge_base_id', 'document_id',
                  'conversation_id', 'message_id', 'source_count', 'chunk_count'}


def get_request_id() -> str | None:
    return _request_id.get()


def error_code(error: BaseException, default: str = 'internal_error') -> str:
    """Classify known types/causes, without reading error messages or URLs."""
    current, seen = error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, SQLAlchemyError):
            return 'database_error'
        if isinstance(current, httpx.TimeoutException):
            return 'llm_timeout'
        if isinstance(current, TimeoutError):
            return 'generation_timeout'
        code = getattr(current, 'error_code', None)
        if code in ERROR_CODES:
            return code
        current = current.__cause__
    return default if default in ERROR_CODES else 'internal_error'


class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': record.levelname}
        payload.update(record.trace_fields)
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)


class SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record):
        # logging's default fallback can print exception internals to stderr.
        pass


def configure_logging():
    if not any(getattr(handler, '_rag_handler', False) for handler in LOGGER.handlers):
        handler = SafeStreamHandler(sys.stdout)
        handler._rag_handler = True
        handler.setFormatter(JSONFormatter())
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


def log_event(event: str, **fields) -> None:
    """Allowlisted metadata only; sink failure must not alter business behavior."""
    try:
        if event not in EVENTS:
            return
        payload = {'request_id': get_request_id(), 'event': event}
        for key, value in fields.items():
            if key in NUMERIC_FIELDS and type(value) in (int, float) and math.isfinite(value) and value >= 0:
                payload[key] = value
            elif key == 'stage' and value in STAGES:
                payload[key] = value
            elif key == 'outcome' and value in OUTCOMES:
                payload[key] = value
            elif key == 'error_code' and value in ERROR_CODES:
                payload[key] = value
            elif key == 'method' and value in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'}:
                payload[key] = value
            elif key == 'route' and isinstance(value,str):
                payload[key] = value
            elif key == 'persisted' and type(value) is bool:
                payload[key] = value
        result = _business_result.get()
        if result is not None and event in {'generation_finished','document_finished'}:
            # Each request owns this dictionary; child ASGI tasks share only
            # their parent's result, unlike ContextVar reassignment in a child.
            result.update({key:payload[key] for key in ('outcome','error_code') if key in payload})
        LOGGER.info(event, extra={'trace_fields': payload})
    except Exception:
        pass


@contextmanager
def trace_stage(stage: str, *, failure_code: str = 'internal_error', **fields):
    started = perf_counter()
    try:
        yield fields
    except BaseException as exc:
        interrupted = isinstance(exc, (asyncio.CancelledError, GeneratorExit))
        log_event('stage_finished',stage=stage,outcome='interrupted' if interrupted else 'failed',
                  error_code='client_disconnected' if interrupted else error_code(exc,failure_code),
                  duration_ms=(perf_counter()-started)*1000,**fields)
        raise
    else:
        log_event('stage_finished',stage=stage,outcome='completed',duration_ms=(perf_counter()-started)*1000,**fields)


class RequestTraceMiddleware:
    """Pure ASGI: context survives streaming and its cancellation-safe cleanup."""
    def __init__(self, app):
        self.app = app
        configure_logging()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope,receive,send)
        request_id = uuid4().hex
        token = _request_id.set(request_id)
        result = {}
        result_token = _business_result.set(result)
        scope.setdefault('state',{})['request_id'] = request_id
        started, status, response_started = perf_counter(), 500, False
        outcome, failure = None, None

        async def traced_send(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                message = dict(message)
                status = message['status']
                message['headers'] = [(k,v) for k,v in message.get('headers',[]) if k.lower()!=b'x-request-id']
                message['headers'].append((b'x-request-id',request_id.encode('ascii')))
                response_started = True
            await send(message)

        try:
            await self.app(scope,receive,traced_send)
        except asyncio.CancelledError:
            outcome, failure = 'interrupted', 'client_disconnected'
            raise
        except ClientDisconnect:
            outcome, failure = 'interrupted', 'client_disconnected'
            raise
        except Exception as exc:
            outcome, failure = 'failed', error_code(exc)
            if response_started:
                raise
            await JSONResponse({'detail':'服务暂时不可用，请稍后重试'},status_code=500)(scope,receive,traced_send)
        finally:
            try:
                route = getattr(scope.get('route'),'path','unmatched')
                log_event('request_finished',method=scope.get('method'),route=route,status_code=status,
                          outcome=outcome or result.get('outcome') or ('failed' if status>=400 else 'completed'),
                          error_code=failure or result.get('error_code'),duration_ms=(perf_counter()-started)*1000)
            finally:
                _business_result.reset(result_token)
                _request_id.reset(token)
