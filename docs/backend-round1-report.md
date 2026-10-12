# 后端第一轮实施与验证报告

日期：2026-10-12。范围：升级计划 Task 1、Task 2。未创建提交、未推送、未删除文件或目录。

## 实现文件

- `app/main.py`：`create_app(*, session_factory=None, embedding_service=None, pdf_service=None, llm_service=None, settings=None)`；同源/Origin/Sec-Fetch-Site 校验、请求体大小限制、安全数据库/参数错误、数据库感知 `/health`。旧 `/history`、`/chat`、`/upload`、`/rag/chat`、无 `/api` 的知识库入口移除。
- `app/auth.py`：PBKDF2-HMAC-SHA256（600000 次、随机盐）、凭据长度限制、不透明随机 cookie、服务器仅存 SHA-256 令牌摘要、过期/退出/登录轮换、知识库归属校验。cookie 名为 `rag_session`，HttpOnly、SameSite=Lax、Path=/，Secure 随 `AUTH_COOKIE_SECURE` 开启。
- `app/api.py`：认证后的知识库创建/列表/读取、PDF 上传/文档状态、非流式查询。独立 Session 在同步工作线程内创建和关闭。同步 PDF/Embedding/检索操作不直接阻塞 async 事件循环。
- `app/conversations.py`：持久化对话和 user/assistant 消息、来源 JSON 快照、`meta/sources/delta/done/error` SSE、有限历史、上下文追问检索、拒答不调 LLM、并发上限、同对话互斥、超时/失败/中断状态。明确追问（如“那/这个/刚才/继续”）才补充上一问；独立问题单独检索，避免旧话题污染。
- `app/orm_models.py`：User、AuthSession、Conversation、ConversationMessage；知识库 nullable owner_id；每用户名称唯一；数据库 partial unique index 限制同对话同时只有一个 generating 消息。
- `app/config.py`：AppSettings；环境变量使用 `AUTH_COOKIE_SECURE`、`AUTH_SESSION_HOURS`、`MAX_UPLOAD_BYTES`、`RAG_MIN_RELEVANCE_SCORE`、`APP_ORIGIN`，不改检索默认 top_k=3 和阈值 0.55。
- `app/services/embedding_service.py`：首次真正执行 Embedding 时才加载 SentenceTransformer；导入应用和认证请求不会加载或下载模型。
- `app/services/llm_service.py`：真实 HTTPX `client.stream` + `aiter_lines`；逐 SSE 事件产出模型增量，保留原 `chat()` 接口。验证 JSON/字段、空内容、上游错误和缺失 `[DONE]` 的截断流。
- `migrations/versions/f120a438bd91_auth_conversations.py`：在旧 head 上添加上述表与约束；旧知识库 owner_id 保留 NULL，不分配给新用户，不删除旧记录。名称存在跨用户重复时明确拒绝安全回退，避免静默修改数据。
- `tests/test_fullstack_api.py`、`tests/test_streaming_llm.py`：真实路由/ORM/认证/pgvector 行为；只替换 PDF、Embedding、LLM 外部边界。

## 实际验证

连接主 Agent 建立的独立测试 PostgreSQL：127.0.0.1:55432 / rag_round1_test。认证/API fixture 使用外部事务与 Session savepoint，结束后回滚；未 truncate、drop 或清空开发数据库。

1. RED：`pytest tests/test_streaming_llm.py -q`，5 failed，原因是缺少 `LLMService.stream_chat`。
2. GREEN：实现 HTTPX 流后，5 passed。
3. RED：认证/API 测试首次运行因缺少 `create_app` 失败。
4. 执行 `.venv/Scripts/python.exe -m alembic upgrade head`，成功从空测试库迁移至 f120a438bd91。
5. 初始认证/上传/权限/会话/HTTPX 测试：10 passed。
6. RED→GREEN：追问检索缺少前文、独立新话题被旧话题污染、超长回答仍保存全部内容三个回归均先重现失败后修复。
7. `.venv/Scripts/python.exe -m alembic check`：`No new upgrade operations detected.`
8. 最终完整 `.venv/Scripts/python.exe -m pytest -q`：**31 passed，1 warning，4.93s**，退出码 0。包含项目原有 RAG Service、模型和 pgvector Repository 测试，以及主 Agent 的旧知识库归属测试。

新增覆盖注册/登录/退出、哈希与摘要、过期、凭据限额、Secure cookie、A/B 隔离、NULL-owner 隐藏、旧路由不可用、CSRF、上传大小/空文件/无文本失败、来源与历史刷新、拒答不调用上游、多轮上下文/预算、重复生成409、超时/超长回答failed、取消/关闭生成器/ASGI socket发送失败interrupted、遗留generating恢复。HTTPX 测试把中文 UTF-8 字节拆开，并让上游等待消费者收到第一段后才发送剩余内容，验证答案未全量缓冲后模拟输出。

## 接入约定与限制

- 工厂注入 PDF `extract_pages_from_bytes`；Embedding `embed_query`/`embed_documents`；LLM `is_configured`、`chat` 和 async `stream_chat(messages)`（逐段 yield str）。测试替身只由调用方显式注入，生产启动无 fake 环境开关。
- 独立数据库 Session 不跨并行任务共享。消息每段更新持久化，模型生成期间不长时间占用数据库连接。SSE 响应在取消或 socket 发送失败后关闭生成器并释放并发槽。
- 本轮部署必须使用单个 API worker。启动时将全部遗留 generating 收敛为 interrupted；多 worker 或多实例滚动启动需要后续引入进程租约/心跳后再扩展，不能直接增加 workers。
- 历史预算以字符数限制（12000），回答上限32000字符，总生成超时180秒；同进程最多8个生成。简单追问指代规则不等于完整语义重写。
- 数据库不可用时无法保证继续保存新收到内容或最终状态；恢复后启动收敛可处理仍为 generating 的记录。进程强杀最多保留最后成功提交的文本。
- 未进行真实远程模型/真实 Embedding 模型验收；该部分须使用实际模型配置验证。本报告不把外部替身当作真实模型通过。
- 测试唯一 warning 是 Starlette TestClient 对 httpx 的上游弃用提示；未为消除警告新增依赖。
- 本机 sandbox 阻止 Python asyncio 的 loopback socketpair，最初测试挂在事件循环创建；获自动审批后在 sandbox 外运行测试成功。未把挂起调用当作功能失败或通过。

主 Agent 另负责 React、浏览器 E2E、Compose、CI、旧知识库按 ID 维护入口与交付文档。后端代码等待独立审查，审查若提出实际缺陷再补修复与验证记录。

补充验收：用户于同日明确授权后，主 Agent 已完成真实 BGE + DeepSeek + 仓库虚构 PDF 的 API 链路验收：7 个 Chunk、3 条来源、149 个真实增量事件和 done，消息 completed 并可从历史读取。回答与来源核对及 Docker 重试限制见 [真实模型验收记录](真实模型验收记录.md)。前述“未进行真实模型验收”描述的是本报告初次交付时的状态。

## 独立审查修复：消息终态竞态

独立审查发现 `save_progress` 原先的 SELECT → Python 判断 → ORM UPDATE 不构成原子操作。`asyncio.timeout` 取消等待不会终止工作线程；迟到线程可能覆盖另一 Session 已提交的 failed/interrupted 状态，或在状态未回退时覆盖正文和来源。

- 新增 `tests/test_conversation_concurrency.py`：使用两个独立真实 PostgreSQL Session/连接和线程 Event，在迟到写入执行 UPDATE 前暂停，先让另一个 Session 提交终态，再放行迟到写入。覆盖 failed/interrupted/completed 三种终态 × generating/completed 两种迟到写入，共六组。断言最终状态、正文、来源以及迟到调用返回的当前数据库结果。
- RED：原实现六组全部失败；实际观察到 failed/interrupted 变成 completed，以及终态保留但正文/来源遭覆盖。
- 修复：`app/conversations.py::save_progress` 使用单条条件 `UPDATE conversation_messages ... WHERE id=:id AND status='generating' RETURNING conversation_id`；只有确实更新到消息时才触碰对话更新时间。提交后以新 Session 的当前数据库记录返回消息，不返回原先缓存的生成状态。
- GREEN：focused concurrency suite **6 passed，0.84s**；完整 `.venv/Scripts/python.exe -m pytest -q` **37 passed，1 warning，5.08s**，退出码0。
- 并发测试只创建 UUID 命名的测试记录，结束时按测试创建的四个明确主键逐条删除；没有 truncate、drop、宽泛删除条件或修改其他记录。其余 API 测试仍通过事务/savepoint 回滚。

以上为审查修复后的最新后端验收结果；31项是修复前的阶段记录。主 Agent 继续执行独立复核与浏览器集成验收。
