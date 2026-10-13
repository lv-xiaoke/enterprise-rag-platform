# 请求追踪与故障定位实施计划

> 执行 Agent：用户要求按本文实施时，按 `executing-plans` 工作方式逐项完成实现与验证；不自动分派子智能体，不扩展到下一轮功能。

**Goal：** 用户遇到上传或问答错误时，能用页面上的请求 ID 找到后端失败阶段，并确认数据状态正确。

**Architecture：** 后端使用纯 ASGI 中间件生成请求 ID，通过 ContextVar 贯穿异步调用和线程池，以标准 logging 输出 JSON 日志。前端从 HTTP 响应头及 SSE 事件读取 ID，在上传和聊天错误提示中展示并支持复制。

**Tech Stack：** 沿用 FastAPI、Starlette、Python logging/contextvars、React/TypeScript、pytest、Vitest 和 Playwright，不新增运行依赖。

**Spec：** 本文件第 1—3 节为本轮需求与接口约定；遵循 [双项目核心目标](../../双项目升级取舍与智能体约束.md)。

## 1. 范围与约束

- 本轮只做请求追踪、阶段日志、前端错误定位和故障验证。
- 不做 Agent、任务队列、云部署、监控大屏、数据库迁移或日志平台。
- 保留认证授权、上传事务、真实 SSE、取消处理及原子终态更新，不顺带重构业务架构。
- 禁止批量删除文件、目录，禁止清空数据库或删除数据卷；沿用仓库 AGENTS.md。
- 不输出密钥、Cookie、密码、请求体、文档原文、文件名、Prompt、回答或未经处理的异常文本。应用日志使用字段白名单，不直接 `logger.exception` 输出可能含敏感数据的异常链。
- 测试使用独立数据库和模型替身。生产入口不得加入故障开关或测试模型；本轮无需调用外部真实模型。
- 用户只要求生成本文时，不开始实现；收到按本文执行的指令后，在授权范围内连续完成。

## 2. 接口与日志约定

### 请求 ID

- 每个 HTTP 请求由服务端生成一个新的 `uuid4().hex`，忽略客户端传入的同名头，避免伪造和串线。
- 响应头统一为 `X-Request-ID`，覆盖正常请求、鉴权/校验/上传限额错误和安全的 500 响应。
- SSE 的 `meta` 与 `error` 数据增加 `request_id`，必须与响应头一致；不改变已有事件名和业务字段。
- ID 保持到流结束及清理完成，再重置 ContextVar；线程池工作读取同一个 ID，并发请求不能串线。
- 不将请求 ID 写入业务表。本轮保证当次错误可定位，刷新后仍保留原有历史内容和状态，不承诺刷新后恢复错误提示里的 ID。

```text
HTTP: X-Request-ID: 32位服务端生成ID
SSE error: {"detail":"回答生成失败，请稍后重试","message_id":123,"request_id":"同一ID"}
页面: 回答生成失败，请稍后重试。请求 ID：…… [复制请求 ID]
```

### 结构化日志

应用 logger 命名为 `rag.app`，每条日志输出一行 JSON，字段如下；Uvicorn 原有访问日志不必改造。

| 字段 | 约定 |
| --- | --- |
| `timestamp` / `level` | UTC 时间与日志级别 |
| `request_id` / `event` | 请求关联 ID；受控事件名 |
| `stage` / `outcome` | 阶段；`completed`、`failed`、`interrupted` 或 `refused` |
| `duration_ms` | 使用 `perf_counter` 计算，不使用墙上时钟相减 |
| `error_code` | 安全分类，如 `llm_timeout`、`llm_unconfigured`、`database_error`、`pdf_invalid`、`client_disconnected`、`internal_error` |
| 可选字段 | `method`、路由模板 `route`、HTTP `status_code`、内部数字资源 ID、`source_count`、`chunk_count` |

只记录已知路由模板，不记录原始 URL、查询参数或任意请求头；未知路径用固定值 `unmatched`。错误分类依据异常类型、受控调用位置及已知异常原因链，不靠匹配原始异常字符串猜测。

阶段至少覆盖：`authorization`、`pdf_parse`、`embedding`、`document_persist`、`retrieval`、`llm`、`generation_finalize`。记录请求结束、关键阶段结束以及最终业务结果；不为每个 token 或每次增量数据库写入打日志。

模型首增量耗时：从开始调用 `stream_chat` 到收到第一个非空内容增量；未收到时不填数值。模型阶段总耗时从同一起点到该阶段结束。请求总耗时到响应流与清理结束，不能在发送响应头时提前结束。

## 3. 必须守住的边界

1. SSE 中途失败时 HTTP 可能仍为 200，业务失败必须由流事件、日志和数据库终态共同说明。
2. 用户停止或客户端断连为 `interrupted`，不能因日志改造变成 `failed`；生成槽位仍须释放。
3. 普通 500 在响应未开始时安全返回并附 ID；响应开始后不得再发第二个 HTTP 响应，异常和取消仍按原流式清理规则处理。
4. 日志配置只作用于应用 logger，重复调用 `create_app()` 不重复添加 handler，不改测试框架的 root logger；日志写入失败不能覆盖原业务异常或阻断清理。
5. 浏览器没有收到响应时显示网络提示，不编造服务端 ID；复制失败时提示手动复制。复制按钮保留可选中的原始 ID 文本。

## 4. 实施任务

### Task 1：请求 ID 与日志基础

**Files：** 新建 `app/observability.py`、`tests/test_observability.py`；修改 `app/main.py`。

**Interfaces：** 提供 `RequestTraceMiddleware(app)`、`configure_logging()`、`get_request_id() -> str | None`、`log_event(event: str, **fields) -> None`。日志字段白名单在模块内部执行，模块不得依赖业务数据库。

- [x] 先编写下列测试及正常/403/422/500、并发请求、线程池 ID、一行 JSON、敏感字段过滤测试，运行确认失败。

```python
def test_server_generates_request_id():
    import re
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.observability import RequestTraceMiddleware
    application = FastAPI()
    application.add_middleware(RequestTraceMiddleware)
    response = TestClient(application).get('/missing', headers={'X-Request-ID': 'forged'})
    assert response.status_code == 404
    assert re.fullmatch(r'[0-9a-f]{32}', response.headers['X-Request-ID'])
```

- [x] 实现纯 ASGI 请求上下文及包装 `send`，在响应开始事件中附 ID；计时和上下文释放在整个调用结束后执行。中间件位于 `BrowserRequestGuard` 外层，使其直接返回的 403/413 也带 ID。
- [x] 使用 `ContextVar` 的 set/reset token，结合 UUID 和白名单 JSON formatter 实现上述接口；添加受控的未知异常处理，遵守第 3 节。
- [x] 运行 `python -m pytest tests/test_observability.py -q`，检查错误响应、隔离和日志脱敏结果。

### Task 2：上传与问答阶段日志

**Files：** 修改 `app/auth.py`、`app/api.py`、`app/conversations.py`、`app/services/document_ingestion_service.py`；必要时在 `app/services/llm_service.py` 增加可分类的异常类型，保持 `RuntimeError` 兼容；扩展 `tests/test_fullstack_api.py` 和 `tests/test_streaming_llm.py`。

**Interfaces：** 消费 Task 1 的日志接口；不改变现有 HTTP 业务返回结构，SSE 仅增加可选的 `request_id` 字段。

- [x] 先扩展现有 `api` fixture 下的测试：上传解析失败、向量失败、模型未配置、模型中途异常、超时和断连；捕获日志，检查 ID 与真实业务状态。

```python
def test_stream_meta_carries_http_request_id(api):
    client, _, _, _ = api
    register(client)
    kb = make_kb(client)
    conversation = make_conversation(client, kb)
    response = client.post(f'/api/conversations/{conversation}/messages/stream', json={'content': '制度有哪些？'})
    assert events(response)[0][1]['request_id'] == response.headers['X-Request-ID']
```

- [x] 在实际权限检查、解析、向量生成、文档事务和检索边界计时并记录结果，不打印输入内容。解析/向量失败仍按现有事务规则回滚并保留 failed 状态。
- [x] 在生成器开始前捕获请求 ID，加入 `meta/error`；计量模型首增量和总耗时。记录已确认的最终数据库状态，不把“准备保存 completed”写成“已完成”。
- [x] 终态日志在完成、失败或 cleanup 路径中去重，保留条件 UPDATE、屏蔽取消的清理和槽位释放。数据库无法保存终态时明确记录失败，不假称已持久化。
- [x] 运行 `python -m pytest tests/test_fullstack_api.py tests/test_streaming_llm.py tests/test_conversation_concurrency.py -q`，确认旧边界和新增日志断言通过。

### Task 3：前端可复制的错误请求 ID

**Files：** 修改 `frontend/src/api.ts`、`sse.ts`、`components.tsx`、`Documents.tsx`、`Chat.tsx`；扩展对应 `api.test.ts`、`sse.test.ts`、`App.test.tsx`。

**Interfaces：** `ApiError` 增加可选 `requestId`；SSE 错误也携带可选 `requestId`。`ErrorNotice` 接收可选 `requestId` 并保留原有错误文本和重试行为。

- [x] 先写 HTTP 错误读取响应头、SSE error 读取 ID、缺 ID 向后兼容，以及上传/聊天提示复制 ID 的测试。

```typescript
it('preserves the request ID on HTTP errors', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(
    '{"detail":"文档处理失败"}',
    { status: 502, headers: { 'X-Request-ID': 'a'.repeat(32) } },
  )));
  await expect(request('/knowledge-bases/1/documents')).rejects.toMatchObject({
    status: 502, requestId: 'a'.repeat(32),
  });
});
```

- [x] 普通错误从响应头读取 ID；`consumeSSE` 的 error 和意外 EOF 保留响应头 ID，SSE 事件 ID 作为兼容补充；冲突时以响应头为准。不将停止生成转成普通失败。
- [x] 上传和聊天页面分别保存本次请求 ID，开始新操作时清空，切换会话或账号不沿用旧 ID；缺少 ID 时正常显示原提示。
- [x] `ErrorNotice` 显示可选中的 ID 和“复制请求 ID”按钮。Clipboard API 不可用或拒绝时提示手动复制，不影响重试。
- [x] 运行 `npm.cmd test` 和 `npm.cmd run build`（工作目录 `frontend`），确认中文分片、done/error、停止和旧请求竞态测试仍通过。

### Task 4：完整验收与简短运行说明

**Files：** 扩展 `frontend/e2e/app.spec.ts`；必要的模型故障替身只放 `tests/e2e_app.py`；更新根目录 `README.md`。

- [x] 使用隔离测试数据库及现有 E2E 应用，验证正常上传/问答不受影响；故障场景检查页面 ID、响应 ID、应用日志 ID 一致。
- [x] 覆盖验收表，特别用真实连接中断或现有 socket-send 探针验证 interrupted；不能用 TestClient 缓冲响应冒充浏览器断连验收。
- [x] 执行后端完整 `python -m pytest -q`，前端测试/构建以及 `npx.cmd playwright test`。Windows 已有 Edge 时可设置 `E2E_BROWSER_CHANNEL=msedge`。使用已迁移的独立 PostgreSQL；没有条件时如实报告阻塞，不改用业务库。
- [x] README 只补日志查找、请求 ID 使用及一个故障排查例子。若验证容器，须重建包含新代码的镜像并沿用该项目环境文件和数据卷；不把旧镜像的健康检查当新功能验收。
- [x] 交付修改摘要、实际命令与结果、未通过项和一段调用链解释；不自动提交、推送或部署。

## 5. 最终验收表

| 场景 | 应看到的结果 |
| --- | --- |
| 正常上传 | 同一 ID 串起解析、向量与事务阶段；文档 ready，无原文日志 |
| PDF/向量失败 | 前端可复制 ID；日志指出失败阶段；文档失败且没有有效半成品 Chunk |
| 正常问答 | 来源、增量和历史仍正常；首增量/模型总耗时可区分 |
| 模型未配置/超时/中途异常 | SSE error 带 ID；日志分类正确；failed 和已生成内容按原规则保存 |
| 停止/断连 | interrupted、部分内容保留、槽位释放，日志不误记 completed |
| 403/413/422/500 | 保持正确 HTTP 状态及安全提示，响应含 ID；开始响应后不重复发送 |
| 并发、脱敏与复制失败 | ID 不串线；敏感值不进入应用日志；复制失败可手动复制 |

**完成标准：** 人为制造一次问答失败，仅凭页面请求 ID 能找到失败阶段，并核对数据库终态。只有实际运行通过的项目才能标为完成。


## 6. 本轮实际验收记录

验收日期：2026-10-13。源码升级完成，当前 8080 Docker 服务未重建，不能将原有容器的运行状态当作新版本验收。

| 检查 | 实际结果 |
| --- | --- |
| 后端完整 pytest | 59 passed，7.20 秒；含真实 PostgreSQL/pgvector、并发终态、请求隔离和持久化故障 |
| 前端 Vitest | 27 passed，9.23 秒；本机使用 threads / 单 worker 参数 |
| TypeScript 与 Vite 构建 | exit 0；保留原有大 chunk 提示 |
| Playwright + Edge | 1 个完整场景 passed，10.3 秒；测试模型，真实 PDF、应用路由和独立 pgvector |
| 故障闭环 | PDF 解析失败与模型超时的页面 ID、响应 ID、JSON 日志一致；failed 内容和来源可恢复 |
| 取消与写入故障 | 真实浏览器停止后 interrupted；模拟终态写入不可用时 persisted=false，不宣称已保存 |

专用测试数据库位于本轮新建容器 `rag-trace-test-20261013` 的 55434 端口，未使用现有业务数据库。未调用外部真实模型，未提交、推送或部署。复核采用主 Agent 自审，未分派独立审查 Agent。新增的 `persisted` 字段用于区分终态是否真正保存；检索耗时和来源数合并为单条阶段日志。

本地验收日志、请求 ID 样例、截图和执行记录保留在 Git 忽略的 `artifacts/fullstack/`。README 已补充按请求 ID 查日志的方法。已有 Starlette TestClient 弃用提示和前端 chunk 体积提示不影响本轮通过，未扩大范围处理。
