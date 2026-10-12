# AI 全栈第一轮升级计划

> 日期：2026-10-12。用户已确认按此前建议的第一轮范围直接实现。本文同时保存设计、实施顺序、接口契约和验收记录，供 Agent 实施与本人面试复习。
> For agentic workers: use writing-plans、subagent-driven-development、test-driven-development、verification-before-completion。禁止批量删除；禁止提交密钥；不自动推送或公开发布。

**Goal:** 将现有企业制度与 SOP RAG 后端升级为可登录、可管理知识库、可连续对话、可流式生成且可部署的 Web 应用。

**Architecture:** React/TypeScript 浏览器通过同源 `/api` 请求 FastAPI；FastAPI 负责认证、资源授权、会话编排及模型事件转发。PostgreSQL 保存用户、登录会话、知识库、文档、Chunk、对话和消息；沿用已有解析、Embedding 与 pgvector 检索服务。Nginx 提供前端静态资源并代理 API，Compose 编排数据库、迁移、API、Web。

**Tech Stack:** React、TypeScript、Vite、Ant Design；Python/FastAPI、SQLAlchemy、Alembic、PostgreSQL/pgvector；pytest、Vitest、Playwright、GitHub Actions、Docker Compose。

**Spec:** 本文件“产品边界”和“接口契约”即本轮设计依据；不新增第二份重复规格。

## 产品边界与全局约束

- 第一轮实现：Web 前端、用户权限、持久化会话、真实流式回答、完整部署和验收文档。
- 第二轮暂缓：Redis/任务队列、Agent 工具调用、OCR、reranker、微调、微服务、计费。
- 保留现有 RAG Service/Repository 与固定评测基线；检索参数不静默替换为离线推荐值。
- 前端四类页面：登录/注册、知识库列表、文档管理、聊天工作台（含会话列表和来源抽屉）。中文界面；有加载、空数据、失败、拒答和中断提示。
- 用户仅访问自己的知识库、文档、对话、消息与来源。不存在和无权访问统一返回 404；未认证返回 401。旧的无鉴权学习入口不继续暴露；不得留下绕过 `/api` 的路径。
- 认证使用随机不透明会话令牌，数据库只保存令牌摘要；HttpOnly、SameSite=Lax cookie，生产 HTTPS 开启 Secure；密码使用标准库 scrypt 或 PBKDF2 安全哈希。限制凭据长度、登录有效期、上传大小。
- 旧知识库迁移后 owner_id 为空，保留数据库记录，不自动归给任何新用户；提供显式、按 ID 分配归属的本地维护入口。
- RAG 会话绑定知识库，持久化 user/assistant 消息，assistant 状态为 generating/completed/failed/interrupted；限制并发生成和历史上下文预算，刷新可恢复已保存消息。
- 真实 LLM 流通过 HTTPX 转发；不得用已生成答案的逐字动画模拟流式。来源先展示 Chunk 原文、文档名、页码；不承诺原 PDF 预览。
- 断开连接保存中断状态与已收到文本；服务重启遗留 generating 消息在启动时收敛为 interrupted。
- 本轮保留同步入库，但将同步 CPU/SQL 操作放入合适的线程执行边界，避免在 async handler 内直接阻塞事件循环；数据库 Session 不在并行任务间共享。
- 不覆盖用户既有改动，不批量删除文件或目录；保留实施记录。代码先留在本地功能分支，不自动提交/推送/部署到外部服务。

## 接口契约（前后端共同遵循）

所有业务 URL 前缀 `/api`，前端请求携带同源 cookie。错误 JSON 为 `{"detail":"中文可理解错误"}`；流一旦开启，错误改为 SSE error 事件。

| 方法和路径 | 请求 | 响应 |
| --- | --- | --- |
| POST /auth/register | `{username,password}` | 201 User，并设置登录 cookie |
| POST /auth/login | `{username,password}` | 200 User，并设置登录 cookie |
| GET /auth/me | 无 | User `{id,username}` |
| POST /auth/logout | 无 | 204，撤销服务器会话并清除 cookie |
| GET /knowledge-bases | 无 | 当前用户的 KnowledgeBase[] |
| POST /knowledge-bases | `{name,description?}` | 201 KnowledgeBase |
| GET /knowledge-bases/{kb_id} | 无 | KnowledgeBase |
| GET /knowledge-bases/{kb_id}/documents | 无 | Document[] |
| POST /knowledge-bases/{kb_id}/documents | multipart 字段 file | 201 `{document,page_count,chunk_count}` |
| GET /knowledge-bases/{kb_id}/documents/{id} | 无 | Document |
| POST /knowledge-bases/{kb_id}/query | `{question,top_k?}` | 保留原 Answer + refused + sources 非流式结构 |
| GET /knowledge-bases/{kb_id}/conversations | 无 | Conversation[] |
| POST /knowledge-bases/{kb_id}/conversations | `{title?}` | 201 Conversation |
| GET /conversations/{id}/messages | 无 | Message[]，按时间/ID 升序 |
| POST /conversations/{id}/messages/stream | `{content}` | `text/event-stream` |

KnowledgeBase、Document 沿用已有响应字段。Conversation 为 `{id,knowledge_base_id,title,created_at,updated_at}`。Message 为 `{id,conversation_id,role,content,status,sources,created_at}`，user 状态为 completed。sources 沿用 `chunk_id,document_id,filename,page_number,chunk_index,content,score`。来源保存在消息 JSON 中，避免刷新后消失。

SSE 采用 `event: NAME\ndata: JSON\n\n`；前端必须处理网络分片、UTF-8 字符被分割、多个事件同批到达，不能假设一次 read 就是一个事件。

- `meta`: `{conversation_id,user_message_id,assistant_message_id}`。
- `sources`: `{sources:[...],refused:false}`；无证据则 refused=true。
- `delta`: `{text:"增量文本"}`。
- `done`: `{message:Message}`（最终数据库消息，含完整文本与来源）。
- `error`: `{detail:"安全错误",message_id?:number}`；前端查询历史恢复持久化状态。

## Review Focus

1. 改 URL 中的知识库/会话 ID、直接访问旧路径，不能绕过权限。
2. 网络中断、模型超时/无效流格式、同会话重复提交、进程重启，不能残留假完成消息。
3. 切换知识库/会话或退出登录时，不能把旧异步请求的结果显示给新的页面或用户。
4. 空文件、超限上传、扫描 PDF、模型配置缺失，应给出可操作错误并保持失败安全。
5. SSE 分片与中文跨字节、拒答无需调用模型、历史刷新与追问上下文，必须有可重复验证。

## Task 1：认证、数据迁移与资源授权

**Files:** 新增认证模块、API router、新迁移和 `tests/test_fullstack_api.py`；修改 `app/main.py`、`app/orm_models.py`、`app/config.py`。原 RAG 服务可复用。
**Interfaces:** 生产上述 auth、knowledge-bases、documents、query 接口；消费旧 Repository/Service；为 Task 2 提供用户依赖与独立 Session 工厂。

- [x] 先写失败测试：注册/登录/退出、密码不明文、用户 A/B 隔离、未登录与旧接口、文件大小上限。
- [x] 运行失败测试并记录缺失能力；实现安全密码哈希、不透明 cookie 会话与资源授权。
- [x] Alembic 增加用户、认证会话、知识库 owner、对话、消息表；旧数据保持不变且不对新用户开放。
- [x] 重跑测试，确认 401/404/409 等边界和迁移可执行。

## Task 2：持久化会话与真实流式生成

**Files:** 新增对话 service/router，修改 `app/services/llm_service.py` 和 RAG prompt/编排；新增流式/会话测试。
**Interfaces:** 消费 Task 1 用户依赖、Session；生产上述 conversation/messages/SSE 契约；历史上下文为 messages，检索仍限定当前知识库 ready 文档。

- [x] 先写失败测试：消息持久化、来源保存、历史影响追问、无证据拒答不调用上游、流中错误/取消、重复生成互斥。
- [x] 实现 HTTPX 上游流解析、下游 SSE、有限历史、消息状态与来源快照。
- [x] 同步数据库/Embedding 使用独立执行边界；不在生成期间长时间持有无用数据库连接。
- [x] 重跑测试，覆盖连接断开与遗留 generating 恢复。

## Task 3：React 前端

**Files:** `frontend/`；独立 package.json、lock、Vite/TS 配置、API 客户端、SSE 解析、页面和组件测试。
**Interfaces:** 仅消费上述 `/api`，禁止客户端包含 LLM key；Vite 开发代理 `/api` 至 `127.0.0.1:8000`。

- [x] 先写 SSE 解析失败测试与用户流程测试，涵盖中文分片、error、缺少 done。
- [x] 实现登录/注册/退出、知识库创建/列表、PDF 上传/状态、会话创建/选择、聊天、停止生成与来源抽屉。
- [x] 请求取消与上下文绑定，切换会话不显示旧流；刷新加载历史；错误可重试但不自动重复模型调用。
- [x] 执行 `npm test`、`npm run build`，提供键盘可操作与窄屏布局。

## Task 4：交付、CI、演示和复习材料

**Files:** `frontend/Dockerfile`、Nginx 配置、Compose、`.github/workflows/ci.yml`、`.env.example`、README、E2E 测试、复习文档。
**Interfaces:** Web 同源反代 `/api`；生产禁用模型 fake；CI 中明确使用测试替身，验证真实应用路由/数据库/前端，不能伪造真实模型验收。

- [x] 提供前端 Docker 多阶段构建、数据库感知 API health 与迁移先于启动的编排。新镜像/完整 Compose 运行受仓库网络限制，见最终记录。
- [x] CI 启动 pgvector，迁移到 head，执行后端测试、前端测试/构建、浏览器流程。
- [x] E2E 覆盖注册、创建知识库、上传文本 PDF、对话、引用、刷新、第二用户隔离；上游 LLM 与 Embedding 使用独立测试替身保证可重复。
- [x] 更新本地运行、Compose、HTTPS cookie 配置、旧数据归属、真实 LLM 验收说明。
- [x] 编写核心请求路径、文件索引、设计取舍、故障定位与可亲手练习的小需求。
- [x] 最终运行测试/构建/迁移/Compose 配置检查；独立审查发现的终态竞态已修复，并发测试和整体验收已重跑。实际输出与环境限制见下表。

## 实施记录

- 基线 commit：`9b90318`；工作分支：`codex/ai-fullstack-round1`。
- 开始时工作区干净；Docker Desktop 引擎未启动，不能把 Compose 静态检查描述成容器验收。
- 用户明确要求写计划并直接实现，因此不再插入重复审批环节。
- 后端与前端在接口固定后分工实现；部署、集成与复核由主 Agent 负责。
- 禁止批量删除优先于技能中清理临时工作区的指令；本轮保留记录，不执行递归删除。

## 最终验收记录

验收日期：2026-10-12。由主 Agent 独立运行，数据库为本轮专用 `rag_round1_test`，未改动开发数据库。只有已运行成功的项目可以打勾；不把静态代码或 Agent 自述当作通过证据。

| 验证 | 实际结果 |
| --- | --- |
| 后端 `python -m pytest -q` | 最终 37 passed，4.99s；含 6 组真实 PostgreSQL 并发终态回归；1 条 Starlette TestClient 上游弃用提示 |
| 前端 `npm test` | 3 个测试文件，16 passed |
| 前端 `npm run build` | TypeScript + Vite exit 0；主 JS 727.20 kB，gzip 238.08 kB，存在后续拆包提示 |
| Playwright + 本地 Edge + 真实 pgvector | 最终 1 个端到端场景 passed，8.7s；含桌面和 390px 窄屏 |
| `alembic current` / `alembic check` | head 为 `f120a438bd91`；No new upgrade operations detected |
| 已有数据迁移 | 额外新建 `rag_migration_round1`，旧 head 写入虚构知识库、PDF 记录与 512 维 Chunk 后升级；内容、向量维度、ready 状态全部保留，owner 为 NULL |
| `docker compose --env-file .env.example config --quiet` | exit 0 |
| Linux API 容器兼容性 | 使用已有 API 运行镜像只读挂载新代码，连接独立测试库；health 数据库连接正常，注册与 cookie me 验证通过；验收容器已停止 |
| 全新 API / Web 镜像构建 | 后续代理修复后均构建成功，exit 0；API 新镜像 `3e7e5da0de09`，Web 新镜像 `7638a8e4caa9` |
| 完整 Compose / Nginx | 独立项目 `rag-round1-check` 启动通过；migrate Exited(0)，PostgreSQL/API/Web 均 healthy，Nginx 配置检查通过 |
| 容器 API 集成与实际 Edge 网页 | 认证、建库、真实 PDF ready/7 Chunk、SSE拒答与历史、模型缺配置的来源/失败状态、A/B隔离、旧接口404、退出均通过；Edge经Nginx注册/建库/上传/退出通过 |
| 真实 BGE + DeepSeek + PDF 问答 | 用户授权后执行通过；PDF ready / 7 个 Chunk，3 条来源，149 个 delta + done，completed 持久化；逐条核对回答有原文支持 |
| `git diff --check` | exit 0；仅 Windows 换行转换提示 |

浏览器场景实际覆盖：注册 → 创建知识库 → 解析仓库虚构制度 PDF → 流式回答 → 来源抽屉 → 刷新恢复 → 第二账号访问返回 404 / 列表为空 → 拒答 → 网络取消后保存 interrupted → 退出后 401。外部模型使用测试专用替身，回答明确带“测试模型”字样；真实 PDF、应用路由、数据库和网页均参与运行。

浏览器额外发现并修复窄屏长用户名挤出退出按钮的问题；新增 390px 全页宽度断言后复验通过。另修复独立新问题检索混入上一主题、旧账户迟到 401 影响新登录、同批 SSE 增量更新等边界。详细 RED→GREEN 记录见 [后端报告](backend-round1-report.md)、[前端报告](frontend-round1-report.md)。

独立审查发现一个必须修复的问题：超时/中断的终态可能被迟到线程覆盖。`save_progress` 改为数据库 `UPDATE ... WHERE status='generating' RETURNING ...` 原子更新；正文与来源也受同一条件保护，返回实际数据库状态。新增 3 种终态 × 2 种迟到写入共 6 组真实 PostgreSQL 双连接/线程回归，先重现失败，再全部通过；主 Agent 独立复跑完整 37 项后端测试和浏览器场景。修复复核见 [独立审查报告](fullstack-round1-review.md)。

### 尚未通过的环境验收

- **云端 GitHub Actions：待首次实际运行。** 已编写 workflow，本轮未提交或推送，不能声称线上 CI 已通过。

真实模型验收先前因数据发送授权被拦截，用户随后明确回复“可以，继续执行”，现已在独立测试库完成。详情与实际回答见 [真实模型验收记录](真实模型验收记录.md)。本次经真实 API 调用核验，不把单题结果泛化为准确率，也不把脚本总耗时当作生产 SLA。Docker 早期同日重试失败，后续按下述代理方案已解决。

### Docker 网络修复及最终运行条件

本机直连 `auth.docker.io` 超时，而本地 HTTP 代理 `127.0.0.1:7877` 返回认证 200。Docker pull 可以使用现有 Desktop/系统代理，但当前未设置环境变量的 BuildKit 客户端仍复现认证超时。在执行构建的同一 PowerShell 设置 HTTP_PROXY、HTTPS_PROXY 后，python/node/nginx 基础镜像认证和拉取全部通过。

还需区分构建客户端与容器 RUN 阶段：客户端代理为 `http://127.0.0.1:7877`，RUN 阶段通过 build-arg 指定 `http://host.docker.internal:7877`。已用真实容器验证后者访问 PyPI 为 200，随后依赖安装、新镜像导出和 Compose 启动全部完成。可复制命令见 [README 的 Windows 超时处理](../README.md#windows-下镜像认证连接超时)。未修改系统 DNS、Docker 全局代理、永久环境变量或用户的代理监听配置。

完整容器验收使用独立项目、数据库与端口：Web `http://localhost:8082`，API `127.0.0.1:8012`，PostgreSQL `127.0.0.1:55433`。环境来自 `.env.example`；测试覆盖文件只读挂载已有 Hugging Face 缓存并设置离线模式，避免额外下载模型。运行服务保留，数据在本项目独立命名卷中；没有操作其他现有数据库。

本次容器配置未放入真实 LLM key：验证真实 BGE/PDF、SSE拒答，以及有证据但模型缺配置时安全保存 failed/来源；外部 DeepSeek 真实生成使用前述独立真实模型验收结果。Nginx SSE 的 meta 在约0.015秒收到、最终拒答在约3.359秒完成，验证本次状态流未被全量缓冲；这是单次本地观察，不是 SLA。原始结果/截图保存在本地忽略目录 `artifacts/fullstack/`。

### 使用与复习

- 运行入口与配置：[README](../README.md)。
- 两条实际调用链、设计取舍、故障定位与练习：[运行与面试指南](AI全栈第一轮-运行与面试指南.md)。
- 当前改动保留在本地分支 `codex/ai-fullstack-round1`，没有提交、推送或公开发布。
- Docker 测试容器与迁移测试库保留验收记录，未执行批量删除。完整回归需连接独立已迁移测试库。

## 投递后继续升级的顺序

第一轮可先用于展示全栈闭环；讲解时如实说明以上未完成的环境验收。下一轮优先依据实际失败样例扩充检索/拒答评测，加入最终回答的引用一致性评价，再比较混合检索与 reranker。之后针对同步入库的等待问题引入任务队列、真实任务状态与重试，补充限流、日志与观测。Agent 工具调用应围绕明确业务动作设计，并补权限、确认与工具失败测试；不为了简历同时堆入全部组件。
