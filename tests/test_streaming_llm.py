import asyncio
import json

import httpx
import pytest

from app.services.llm_service import LLMService


@pytest.mark.parametrize('fault,code',[('timeout','llm_timeout'),('status','llm_error'),('format','llm_invalid_stream')])
def test_real_httpx_failure_wrappers_keep_safe_error_codes(fault, code):
    from app.services.llm_service import LLMServiceError
    def upstream(request):
        if fault=='timeout':
            raise httpx.ReadTimeout('secret-upstream-token')
        if fault=='status':
            return httpx.Response(503,text='secret-upstream-token')
        return httpx.Response(200,text='data: invalid-json\n\n')
    async def run():
        service=LLMService()
        service.api_key,service.base_url,service.model='test','http://upstream','model'
        service.transport=httpx.MockTransport(upstream)
        return [chunk async for chunk in service.stream_chat([{'role':'user','content':'问'}])]
    with pytest.raises(LLMServiceError) as caught:
        asyncio.run(run())
    assert caught.value.error_code==code
    assert 'secret-upstream-token' not in str(caught.value)


def test_llm_forwards_actual_stream_and_multiturn_messages():
    seen = []

    def upstream(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"中文"}}]}\n\ndata: {"choices":[{"delta":{"content":"回答"}}]}\n\ndata: [DONE]\n\n')

    async def run():
        service = LLMService()
        service.api_key, service.base_url, service.model = "test", "http://upstream/v1", "model"
        service.transport = httpx.MockTransport(upstream)
        return [text async for text in service.stream_chat([
            {"role": "user", "content": "第一个问题"},
            {"role": "assistant", "content": "之前回答"},
            {"role": "user", "content": "追问"},
        ])]

    assert asyncio.run(run()) == ["中文", "回答"]
    assert seen[0]["stream"] is True
    assert seen[0]["messages"][1]["content"] == "之前回答"


@pytest.mark.parametrize("body", [
    'data: {bad json}\n\n',
    'data: {"choices":[{"delta":{"content":"部分"}}]}\n\n',
    'data: [DONE]\n\n',
    'data: {"error":{"message":"secret"}}\n\n',
])
def test_llm_rejects_malformed_truncated_and_empty_streams(body):
    async def run():
        service = LLMService()
        service.api_key, service.base_url, service.model = "test", "http://upstream", "model"
        service.transport = httpx.MockTransport(lambda request: httpx.Response(200, text=body))
        return [text async for text in service.stream_chat([{"role":"user","content":"问"}])]
    with pytest.raises(RuntimeError):
        asyncio.run(run())


def test_first_delta_arrives_before_upstream_finishes_with_split_utf8():
    async def run():
        delivered=asyncio.Event()
        class Upstream(httpx.AsyncByteStream):
            async def __aiter__(self):
                first='data: {"choices":[{"delta":{"content":"中文"}}]}\n\n'.encode()
                offset=first.index('中'.encode())+1
                yield first[:offset]
                yield first[offset:]
                # A buffering implementation deadlocks here: upstream waits for
                # the caller to receive the first delta before sending the rest.
                await asyncio.wait_for(delivered.wait(),timeout=1)
                yield b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n'
        service=LLMService()
        service.api_key,service.base_url,service.model='test','http://upstream','model'
        service.transport=httpx.MockTransport(lambda request:httpx.Response(200,stream=Upstream()))
        chunks=[]
        async for chunk in service.stream_chat([{'role':'user','content':'问题'}]):
            chunks.append(chunk)
            delivered.set()
        return chunks
    assert asyncio.run(run()) == ['中文','ok']
