import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import engine


class FakeEmbedding:
    def embed_query(self, text):
        return [1.0] + [0.0] * 511

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


class FakePDF:
    def extract_pages_from_bytes(self, content):
        if content == b'empty':
            return ['']
        return ['申请报销须在三十天内提交审批。']


class FakeLLM:
    def __init__(self):
        self.messages = []
        self.fail = False
        self.configured = True

    def is_configured(self):
        return self.configured

    async def chat(self, message):
        return '三十天内提交。'

    async def stream_chat(self, messages):
        self.messages.append(messages)
        yield '三十天'
        if self.fail:
            raise RuntimeError('secret upstream failure')
        yield '内提交。'


@pytest.fixture
def api():
    from app.main import create_app
    from app.config import AppSettings
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint')
    llm = FakeLLM()
    application = create_app(session_factory=factory, embedding_service=FakeEmbedding(), pdf_service=FakePDF(), llm_service=llm, settings=AppSettings(max_upload_bytes=32))
    try:
        with TestClient(application) as client:
            yield client, factory, llm, application
    finally:
        transaction.rollback()
        connection.close()


def register(client, name=None):
    name = name or 'user_' + uuid4().hex[:12]
    response = client.post('/api/auth/register', json={'username': name, 'password': 'secure-password-123'})
    assert response.status_code == 201, response.text
    return response.json()


def make_kb(client):
    response = client.post('/api/knowledge-bases', json={'name': '制度'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def make_conversation(client, kb):
    response = client.post(f'/api/knowledge-bases/{kb}/conversations', json={})
    assert response.status_code == 201
    return response.json()['id']


def events(response):
    assert response.status_code == 200, response.text
    result = []
    for block in response.text.strip().split('\n\n'):
        lines = block.splitlines()
        result.append((lines[0].split(': ', 1)[1], json.loads(lines[1].split(': ', 1)[1])))
    return result


def trace_records(caplog, request_id):
    return [record.trace_fields for record in caplog.records
            if record.name == 'rag.app' and record.trace_fields.get('request_id') == request_id]


def test_upload_trace_covers_stages_and_private_values_are_absent(api, caplog):
    client, _, _, _ = api
    register(client)
    kb = make_kb(client)
    with caplog.at_level('INFO',logger='rag.app'):
        response = client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('private-policy.pdf',b'pdf')})
    assert response.status_code == 201
    records = trace_records(caplog,response.headers['X-Request-ID'])
    stages = {record.get('stage') for record in records}
    assert {'authorization','pdf_parse','embedding','document_persist'} <= stages
    terminal = [record for record in records if record['event']=='document_finished']
    assert len(terminal)==1 and terminal[0]['outcome']=='completed'
    assert 'private-policy.pdf' not in str(records) and '三十天' not in str(records)


@pytest.mark.parametrize('fault,stage,code', [('pdf','pdf_parse','pdf_invalid'),('embedding','embedding','embedding_error')])
def test_upload_failure_trace_and_rollback(api, caplog, fault, stage, code):
    from app.orm_models import Chunk, Document
    client, factory, _, application = api
    register(client)
    kb = make_kb(client)
    if fault=='embedding':
        class BrokenEmbedding(FakeEmbedding):
            def embed_documents(self,texts):
                raise RuntimeError('secret-embedding-content')
        application.state.embedding_service = BrokenEmbedding()
    with caplog.at_level('INFO',logger='rag.app'):
        response = client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('private.pdf',b'empty' if fault=='pdf' else b'pdf')})
    assert response.status_code in (400,502)
    records = trace_records(caplog,response.headers['X-Request-ID'])
    assert any(r.get('stage')==stage and r.get('error_code')==code and r['outcome']=='failed' for r in records)
    assert len([r for r in records if r['event']=='document_finished'])==1
    with factory() as session:
        doc = session.scalar(select(Document).where(Document.knowledge_base_id==kb))
        assert doc.status=='failed'
        assert list(session.scalars(select(Chunk).where(Chunk.document_id==doc.id)))==[]
    assert 'secret-embedding-content' not in str(records)


@pytest.mark.parametrize('fault,code', [('unconfigured','llm_unconfigured'),('timeout','llm_timeout'),('midstream','llm_error')])
def test_stream_failure_trace_matches_http_and_database(api, caplog, fault, code):
    import httpx
    client, _, llm, application = api
    register(client)
    kb = make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation = make_conversation(client,kb)
    if fault=='unconfigured':
        llm.configured=False
    elif fault=='midstream':
        llm.fail=True
    else:
        class TimeoutLLM(FakeLLM):
            async def stream_chat(self,messages):
                yield '部分回答'
                raise httpx.ReadTimeout('secret upstream URL and token')
        application.state.llm_service=TimeoutLLM()
    with caplog.at_level('INFO',logger='rag.app'):
        response = client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'})
    request_id = response.headers['X-Request-ID']
    data = events(response)
    assert data[0][1]['request_id']==request_id
    assert data[-1][0]=='error' and data[-1][1]['request_id']==request_id
    records = trace_records(caplog,request_id)
    final = [r for r in records if r['event']=='generation_finished']
    assert len(final)==1 and final[0]['outcome']=='failed' and final[0]['error_code']==code
    assert final[0]['persisted'] is True
    assert any(r.get('stage')=='retrieval' for r in records)
    assert len([r for r in records if r['event']=='llm_first_delta']) == (0 if fault=='unconfigured' else 1)
    message = client.get(f'/api/conversations/{conversation}/messages').json()[-1]
    assert message['status']=='failed'
    assert message['content'] == ('' if fault=='unconfigured' else '三十天' if fault=='midstream' else '部分回答')
    assert 'secret upstream' not in str(records)


def test_success_and_refusal_traces_are_distinct(api, caplog):
    client, _, _, _ = api
    register(client)
    kb = make_kb(client)
    conversation=make_conversation(client,kb)
    with caplog.at_level('INFO',logger='rag.app'):
        refusal=client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'制度'})
    refusal_records=trace_records(caplog,refusal.headers['X-Request-ID'])
    assert [r['outcome'] for r in refusal_records if r['event']=='generation_finished']==['refused']
    assert not any(r['event']=='llm_first_delta' for r in refusal_records)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    with caplog.at_level('INFO',logger='rag.app'):
        response=client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'})
    records=trace_records(caplog,response.headers['X-Request-ID'])
    assert [r['outcome'] for r in records if r['event']=='generation_finished']==['completed']
    first=[r for r in records if r['event']=='llm_first_delta']
    total=[r for r in records if r.get('stage')=='llm' and r['event']=='stage_finished']
    assert len(first)==len(total)==1 and 0<=first[0]['duration_ms']<=total[0]['duration_ms']
    retrieval=[r for r in records if r.get('stage')=='retrieval']
    assert len(retrieval)==1 and retrieval[0]['source_count']==1 and retrieval[0]['duration_ms']>=0


def test_terminal_persistence_outage_is_not_reported_as_saved(api, caplog, monkeypatch):
    from sqlalchemy.exc import OperationalError
    import app.conversations as conversations
    client, _, _, _ = api
    register(client)
    kb=make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation=make_conversation(client,kb)
    original=conversations.save_progress
    def unavailable(factory,message_id,content,status='generating',sources=None):
        if status!='generating':
            raise OperationalError('secret-sql',None,Exception('secret-db-password'))
        return original(factory,message_id,content,status,sources)
    monkeypatch.setattr(conversations,'save_progress',unavailable)
    with caplog.at_level('INFO',logger='rag.app'):
        response=client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'})
    assert events(response)[-1][0]=='error'
    records=trace_records(caplog,response.headers['X-Request-ID'])
    final=[r for r in records if r['event']=='generation_finished']
    assert len(final)==1 and final[0]['persisted'] is False and final[0]['error_code']=='database_error'
    assert 'secret-sql' not in str(records) and 'secret-db-password' not in str(records)
    assert client.get(f'/api/conversations/{conversation}/messages').json()[-1]['status']=='generating'


def test_registration_sessions_hashes_logout_and_legacy_disabled(api):
    client, factory, _, _ = api
    name = 'user_' + uuid4().hex[:12]
    user = register(client, name)
    cookie = client.cookies.get('rag_session')
    assert cookie and len(cookie) >= 40
    assert 'httponly' in client.post('/api/auth/login', json={'username':name, 'password':'secure-password-123'}).headers['set-cookie'].lower()
    from app.orm_models import User, AuthSession
    with factory() as session:
        stored = session.get(User, user['id'])
        assert stored.password_hash != 'secure-password-123'
        assert cookie not in [row.token_digest for row in session.scalars(select(AuthSession))]
    assert client.get('/api/auth/me').json() == user
    assert client.post('/api/auth/register', json={'username':name, 'password':'secure-password-123'}).status_code == 409
    assert client.post('/api/auth/login', json={'username':name, 'password':'wrong-password'}).status_code == 401
    assert client.post('/api/auth/logout').status_code == 204
    assert client.get('/api/auth/me').status_code == 401
    assert client.get('/api/knowledge-bases').status_code == 401
    for route in ['/knowledge-bases', '/history', '/upload', '/chat', '/rag/chat']:
        response = client.get(route) if route in ['/history','/knowledge-bases'] else client.post(route)
        assert response.status_code == 404


def test_user_isolation_documents_and_csrf(api):
    client, _, _, _ = api
    register(client)
    kb = make_kb(client)
    conversation = make_conversation(client, kb)
    uploaded = client.post(f'/api/knowledge-bases/{kb}/documents', files={'file':('policy.pdf',b'pdf','application/pdf')})
    assert uploaded.status_code == 201
    doc = uploaded.json()['document']['id']
    assert client.post('/api/knowledge-bases', json={'name':'bad'}, headers={'Origin':'https://attacker.invalid'}).status_code == 403
    assert client.post('/api/auth/logout', headers={'Sec-Fetch-Site':'cross-site'}).status_code == 403
    client.post('/api/auth/logout')
    register(client)
    assert client.get('/api/knowledge-bases').json() == []
    assert client.post('/api/knowledge-bases', json={'name':'制度'}).status_code == 201
    for route in [f'/api/knowledge-bases/{kb}', f'/api/knowledge-bases/{kb}/documents', f'/api/knowledge-bases/{kb}/documents/{doc}', f'/api/knowledge-bases/{kb}/conversations', f'/api/conversations/{conversation}/messages']:
        assert client.get(route).status_code == 404
    assert client.post(f'/api/knowledge-bases/{kb}/query', json={'question':'报销期限'}).status_code == 404
    assert client.post(f'/api/conversations/{conversation}/messages/stream', json={'content':'问'}).status_code == 404


def test_upload_limits_and_empty_pdf(api):
    client, _, _, _ = api
    register(client)
    kb = make_kb(client)
    assert client.post(f'/api/knowledge-bases/{kb}/documents', files={'file':('x.pdf',b'a'*33)}).status_code == 413
    assert client.post(f'/api/knowledge-bases/{kb}/documents', files={'file':('x.pdf',b'')}).status_code == 400
    assert client.post(f'/api/knowledge-bases/{kb}/documents', files={'file':('x.pdf',b'empty')}).status_code == 400
    documents = client.get(f'/api/knowledge-bases/{kb}/documents').json()
    assert documents[0]['status'] == 'failed'


def test_refusal_persists_without_upstream(api):
    client, _, llm, _ = api
    register(client)
    kb = make_kb(client)
    conversation = make_conversation(client, kb)
    result = events(client.post(f'/api/conversations/{conversation}/messages/stream', json={'content':'没有证据'}))
    assert [event for event, _ in result] == ['meta','sources','delta','done']
    assert result[1][1] == {'sources':[], 'refused':True}
    history = client.get(f'/api/conversations/{conversation}/messages').json()
    assert [message['status'] for message in history] == ['completed','completed']
    assert history[1] == result[-1][1]['message']
    assert llm.messages == []


def test_stream_sources_multiturn_failure_and_restart_recovery(api):
    client, factory, llm, application = api
    register(client)
    kb = make_kb(client)
    assert client.post(f'/api/knowledge-bases/{kb}/documents', files={'file':('policy.pdf',b'pdf')}).status_code == 201
    conversation = make_conversation(client, kb)
    path = f'/api/conversations/{conversation}/messages/stream'
    result = events(client.post(path, json={'content':'报销期限？'}))
    assert [event for event, _ in result] == ['meta','sources','delta','delta','done']
    message = result[-1][1]['message']
    assert message['content'] == '三十天内提交。'
    assert message['sources'][0]['filename'] == 'policy.pdf'
    events(client.post(path, json={'content':'刚才说几天？'}))
    assert any(item['role']=='assistant' and item['content']=='三十天内提交。' for item in llm.messages[-1])
    llm.fail = True
    failed = events(client.post(path,json={'content':'模型失败'}))
    assert failed[-1][0] == 'error'
    assert 'secret' not in failed[-1][1]['detail']
    history = client.get(f'/api/conversations/{conversation}/messages').json()
    assert history[-1]['status'] == 'failed'
    assert history[-1]['content'] == '三十天'
    from app.orm_models import ConversationMessage
    with factory() as session:
        session.add(ConversationMessage(conversation_id=conversation, role='assistant',content='遗留',status='generating',sources=[]))
        session.commit()
    conflict = client.post(path,json={'content':'重叠请求'})
    assert conflict.status_code == 409
    from app.conversations import recover_generating
    recover_generating(factory)
    history = client.get(f'/api/conversations/{conversation}/messages').json()
    assert history[-1]['status'] == 'interrupted'


def test_followup_retrieval_uses_previous_question(api):
    client, _, _, application = api
    class ContextEmbedding(FakeEmbedding):
        def embed_query(self, text):
            return ([0.0,1.0]+[0.0]*510) if text == '那期限？' else [1.0]+[0.0]*511
    register(client)
    kb = make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    application.state.embedding_service = ContextEmbedding()
    conversation = make_conversation(client,kb)
    events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销制度'}))
    followup = events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'那期限？'}))
    assert followup[1][1]['refused'] is False
    assert followup[1][1]['sources'][0]['filename'] == 'policy.pdf'


def test_disconnect_and_cancel_preserve_partial_and_release_conversation(api):
    import asyncio
    from types import SimpleNamespace
    from app.conversations import MessageCreate, stream_message
    client,factory,llm,application = api
    user = register(client)
    kb = make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation = make_conversation(client,kb)
    class DirectRequest:
        app = application
        async def is_disconnected(self):
            return False
    request = DirectRequest()
    async def run():
        response = await stream_message(conversation,MessageCreate(content='报销'),request,user['id'])
        stream = response.body_iterator
        assert 'event: meta' in await anext(stream)
        assert 'event: sources' in await anext(stream)
        assert '三十天' in await anext(stream)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await stream_message(conversation,MessageCreate(content='重叠'),request,user['id'])
        assert exc.value.status_code == 409
        await stream.aclose()
        # Re-enter the same conversation after cancellation to prove the lock is released.
        class WaitingLLM(FakeLLM):
            async def stream_chat(self,messages):
                yield '已收到'
                await asyncio.Event().wait()
        application.state.llm_service = WaitingLLM()
        response = await stream_message(conversation,MessageCreate(content='再次报销'),request,user['id'])
        iterator = response.body_iterator
        await anext(iterator)
        await anext(iterator)
        await anext(iterator)
        task = asyncio.create_task(anext(iterator))
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    history = client.get(f'/api/conversations/{conversation}/messages').json()
    assert [(item['content'],item['status']) for item in history if item['role']=='assistant'] == [('三十天','interrupted'),('已收到','interrupted')]


def test_expired_session_and_legacy_owner_null_are_inaccessible(api):
    from datetime import datetime,timedelta,timezone
    from app.orm_models import AuthSession,KnowledgeBase
    client,factory,_,_ = api
    register(client)
    with factory() as session:
        legacy = KnowledgeBase(name='legacy_' + uuid4().hex)
        session.add(legacy)
        session.commit()
        legacy_id=legacy.id
    assert client.get(f'/api/knowledge-bases/{legacy_id}').status_code == 404
    assert client.get('/api/knowledge-bases').json() == []
    with factory() as session:
        from app.auth import token_digest
        auth = session.scalar(select(AuthSession).where(AuthSession.token_digest == token_digest(client.cookies.get('rag_session'))))
        auth.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        session.commit()
    assert client.get('/api/auth/me').status_code == 401


def test_unconfigured_model_stream_fails_safely_and_query_refuses_without_evidence(api):
    client,_,llm,_=api
    register(client)
    kb=make_kb(client)
    llm.configured=False
    response=client.post(f'/api/knowledge-bases/{kb}/query',json={'question':'问题'})
    assert response.status_code == 200 and response.json()['refused']
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation=make_conversation(client,kb)
    result=events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'}))
    assert result[-1][0] == 'error'
    assert client.get(f'/api/conversations/{conversation}/messages').json()[-1]['status'] == 'failed'


def test_failed_socket_send_closes_generator_and_persists_interrupted(api):
    import asyncio
    from app.conversations import MessageCreate,stream_message
    client,_,_,application=api
    user=register(client)
    kb=make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation=make_conversation(client,kb)
    class DirectRequest:
        app=application
        async def is_disconnected(self):
            return False
    async def run():
        response=await stream_message(conversation,MessageCreate(content='报销'),DirectRequest(),user['id'])
        async def send(event):
            if event.get('body',b'').startswith(b'event: delta'):
                raise OSError('socket disconnected')
        async def receive():
            return {'type':'http.disconnect'}
        from starlette.requests import ClientDisconnect
        with pytest.raises(ClientDisconnect):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    asyncio.run(run())
    message=client.get(f'/api/conversations/{conversation}/messages').json()[-1]
    assert message['status'] == 'interrupted'
    assert message['content'] == '三十天'


def test_answer_limit_and_generation_timeout_persist_failure(api):
    from dataclasses import replace
    import asyncio
    client,_,_,application=api
    register(client)
    kb=make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation=make_conversation(client,kb)
    application.state.settings=replace(application.state.settings,max_answer_chars=3)
    result=events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'}))
    assert result[-1][0] == 'error'
    message=client.get(f'/api/conversations/{conversation}/messages').json()[-1]
    assert message['status'] == 'failed'
    assert len(message['content']) <= 3
    class StalledLLM(FakeLLM):
        async def stream_chat(self,messages):
            yield '已收到'
            await asyncio.Event().wait()
    application.state.llm_service=StalledLLM()
    application.state.settings=replace(application.state.settings,max_answer_chars=100,generation_timeout_seconds=0.05)
    result=events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销'}))
    assert result[-1][0] == 'error'
    message=client.get(f'/api/conversations/{conversation}/messages').json()[-1]
    assert message['status'] == 'failed'
    assert message['content'] == '已收到'


def test_independent_question_does_not_inherit_previous_topic(api):
    client,_,_,application=api
    class TopicEmbedding(FakeEmbedding):
        def embed_query(self,text):
            return [0.0,1.0]+[0.0]*510 if '宇宙' in text else [1.0]+[0.0]*511
    register(client)
    kb=make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    application.state.embedding_service=TopicEmbedding()
    conversation=make_conversation(client,kb)
    path=f'/api/conversations/{conversation}/messages/stream'
    first=events(client.post(path,json={'content':'宇宙的奥秘？'}))
    assert first[1][1]['refused'] is True
    second=events(client.post(path,json={'content':'报销期限？'}))
    assert second[1][1]['refused'] is False


def test_history_budget_excludes_failed_turns_and_oversized_completed_turns(api):
    from dataclasses import replace
    from app.orm_models import ConversationMessage
    client,factory,llm,application=api
    register(client)
    kb=make_kb(client)
    client.post(f'/api/knowledge-bases/{kb}/documents',files={'file':('policy.pdf',b'pdf')})
    conversation=make_conversation(client,kb)
    with factory() as session:
        for role,content,status in [('user','错误问题','completed'),('assistant','失败的回答','failed'),('user','长问题','completed'),('assistant','长'*100,'completed')]:
            session.add(ConversationMessage(conversation_id=conversation,role=role,content=content,status=status,sources=[]))
            session.flush()
        session.commit()
    application.state.settings=replace(application.state.settings,history_budget=10)
    events(client.post(f'/api/conversations/{conversation}/messages/stream',json={'content':'报销期限？'}))
    assert [item['role'] for item in llm.messages[-1]] == ['system','user']
    assert '失败的回答' not in str(llm.messages[-1])


def test_secure_cookie_flags_and_credential_lengths(api):
    from dataclasses import replace
    client,_,_,application=api
    application.state.settings=replace(application.state.settings,cookie_secure=True)
    response=client.post('/api/auth/register',json={'username':'secure_'+uuid4().hex[:12],'password':'secure-password-123'})
    assert response.status_code == 201
    cookie=response.headers['set-cookie'].lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=lax' in cookie and 'path=/' in cookie
    assert client.post('/api/auth/register',json={'username':'name','password':'a'*129}).status_code == 422
    assert client.post('/api/auth/login',json={'username':'a'*65,'password':'abcdefgh'}).status_code == 422
