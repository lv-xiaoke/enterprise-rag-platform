"""Request lifecycle probes run without a database or external model."""
import asyncio
import io
import json
import logging
import re

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from starlette.concurrency import run_in_threadpool


def traced_app():
    from app.observability import RequestTraceMiddleware, get_request_id
    application = FastAPI()

    @application.get('/context')
    async def context():
        before = get_request_id()
        await asyncio.sleep(0.005)
        threaded = await run_in_threadpool(get_request_id)
        return {'before': before, 'threaded': threaded, 'after': get_request_id()}

    @application.get('/reject/{status}')
    def reject(status: int):
        raise HTTPException(status, 'safe error')

    @application.get('/crash')
    def crash():
        raise RuntimeError('secret credential must never escape')

    application.add_middleware(RequestTraceMiddleware)
    return application


@pytest.mark.parametrize('path,status', [('/missing',404),('/reject/403',403),('/reject/413',413),('/reject/not-int',422),('/crash',500)])
def test_error_responses_have_server_generated_id(path, status):
    with TestClient(traced_app(), raise_server_exceptions=False) as client:
        response = client.get(path, headers={'X-Request-ID': 'forged'})
    assert response.status_code == status
    assert re.fullmatch(r'[0-9a-f]{32}', response.headers['X-Request-ID'])
    assert 'secret credential' not in response.text


def test_concurrent_requests_and_threadpool_keep_separate_contexts():
    from app.observability import get_request_id
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=traced_app()),base_url='http://test') as client:
            responses = await asyncio.gather(*(client.get('/context') for _ in range(8)))
        ids = []
        for response in responses:
            request_id = response.headers['X-Request-ID']
            assert set(response.json().values()) == {request_id}
            ids.append(request_id)
        assert len(set(ids)) == len(ids)
        assert get_request_id() is None
    asyncio.run(run())


def test_json_logging_filters_sensitive_values_and_is_idempotent():
    from app.observability import configure_logging, log_event
    root_handlers = list(logging.getLogger().handlers)
    configure_logging()
    logger = logging.getLogger('rag.app')
    handlers = list(logger.handlers)
    configure_logging()
    assert logger.handlers == handlers
    assert logging.getLogger().handlers == root_handlers
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(handlers[0].formatter)
    logger.addHandler(handler)
    try:
        log_event('stage_finished', stage='pdf_parse', outcome='failed', error_code='pdf_invalid', duration_ms=1.5,
                  filename='private.pdf', password='secret-password', content='secret-document',
                  request_id='forged', unknown='secret-unknown')
    finally:
        logger.removeHandler(handler)
    line = stream.getvalue()
    record = json.loads(line)
    assert record['stage'] == 'pdf_parse' and record['duration_ms'] == 1.5
    assert record['request_id'] is None
    assert all(secret not in line for secret in ['private.pdf','secret-password','secret-document','secret-unknown','forged'])
    assert len(line.splitlines()) == 1


def test_broken_logging_does_not_break_requests(monkeypatch):
    from app.observability import configure_logging
    configure_logging()
    def broken(*args, **kwargs):
        raise OSError('log sink failed')
    monkeypatch.setattr(logging.getLogger('rag.app'), 'info', broken)
    with TestClient(traced_app()) as client:
        response = client.get('/context')
    assert response.status_code == 200


def test_stream_context_lasts_until_cleanup_and_no_second_response(caplog):
    from app.observability import RequestTraceMiddleware, get_request_id
    seen = []
    async def stream(scope, receive, send):
        request_id = get_request_id()
        await send({'type':'http.response.start','status':200,'headers':[]})
        await send({'type':'http.response.body','body':b'partial','more_body':True})
        seen.append(get_request_id())
        raise RuntimeError('secret stream error')
    async def run():
        sent = []
        async def send(event):
            sent.append(event)
        async def receive():
            return {'type':'http.request','body':b''}
        with pytest.raises(RuntimeError):
            await RequestTraceMiddleware(stream)({'type':'http','method':'GET','path':'/stream'},receive,send)
        assert len([item for item in sent if item['type']=='http.response.start']) == 1
        assert get_request_id() is None
        assert seen == [dict(sent[0]['headers'])[b'x-request-id'].decode()]
    with caplog.at_level(logging.INFO, logger='rag.app'):
        asyncio.run(run())
    records = [r.trace_fields for r in caplog.records if r.name=='rag.app']
    assert records[-1]['event']=='request_finished' and records[-1]['outcome']=='failed'
    assert 'secret stream error' not in caplog.text


def test_raw_unknown_url_is_not_logged(caplog):
    with caplog.at_level(logging.INFO, logger='rag.app'):
        with TestClient(traced_app()) as client:
            response = client.get('/private-token-value?password=secret-value')
    assert response.status_code == 404
    assert 'private-token-value' not in str([getattr(r,'trace_fields',{}) for r in caplog.records])


def test_http_200_keeps_failed_business_outcome_from_stream_subtask(caplog):
    from app.observability import RequestTraceMiddleware, log_event
    async def app(scope, receive, send):
        await send({'type':'http.response.start','status':200,'headers':[]})
        async def stream_task():
            log_event('generation_finished',outcome='failed',error_code='llm_timeout',persisted=True)
        await asyncio.create_task(stream_task())
        await send({'type':'http.response.body','body':b'event: error\n\n'})
    async def run():
        async def send(message):
            pass
        async def receive():
            return {'type':'http.request','body':b''}
        await RequestTraceMiddleware(app)({'type':'http','method':'POST','path':'/stream'},receive,send)
    with caplog.at_level(logging.INFO,logger='rag.app'):
        asyncio.run(run())
    final=[r.trace_fields for r in caplog.records if r.name=='rag.app' and r.trace_fields['event']=='request_finished'][-1]
    assert final['status_code']==200 and final['outcome']=='failed' and final['error_code']=='llm_timeout'
