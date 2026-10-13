# 本地环境排障与请求追踪

本文收录环境配置、历史演示环境和日志定位细节。项目介绍与通用启动方式见 [README](../README.md)，开发与测试见 [本地开发与测试](local-development.md)。

## Windows 下镜像认证连接超时

2026-10-12 本机验收记录：直接访问 `auth.docker.io` 超时，使用正在运行的本地 HTTP 代理 `127.0.0.1:7877` 可以访问认证服务。还出现过 `docker pull` 成功而 Compose/BuildKit 认证超时的差异；在执行构建的同一个 PowerShell 中设置客户端代理后，三个基础镜像认证和拉取均通过。

```powershell
# 端口必须与自己的 HTTP/Mixed 代理一致；7877 是本机已验证的端口
$env:HTTP_PROXY='http://127.0.0.1:7877'
$env:HTTPS_PROXY='http://127.0.0.1:7877'
$env:NO_PROXY='localhost,127.0.0.1,::1'
docker buildx imagetools inspect node:22-alpine
docker compose build --build-arg HTTP_PROXY=http://host.docker.internal:7877 --build-arg HTTPS_PROXY=http://host.docker.internal:7877 --build-arg NO_PROXY=localhost,127.0.0.1,::1 api web
docker compose up -d
docker compose ps --all
```

这些变量仅在当前终端及其子进程生效；新开终端需重新设置，并保持代理程序运行。HTTPS_PROXY 的值仍可使用 `http://`，因为这里指 HTTP 代理地址。客户端运行在 Windows，使用 `127.0.0.1`；构建容器中的 `127.0.0.1` 是容器自己，因此 RUN 阶段用 `host.docker.internal` 访问宿主机代理。本机已实际验证该地址可访问 PyPI，避免后端依赖直连下载缓慢。Docker CLI 的代理环境变量、Docker Desktop 的代理设置和 Dockerfile RUN 阶段的代理是不同作用范围；详情见 [Docker CLI 官方说明](https://docs.docker.com/reference/cli/docker/#environment-variables)、[构建代理参数](https://docs.docker.com/build/building/variables/#proxy-arguments) 和 [Desktop 代理设置](https://docs.docker.com/desktop/settings-and-maintenance/settings/#proxies)。镜像认证超时恢复不等于依赖安装或整个部署已完成，最终状态见验收记录。

## PDF 上传成功，但问答提示“大模型服务未配置”

上传使用 PDF 解析、本地 Embedding 和数据库；生成回答还需要后端同时配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。因此上传成功并不代表 LLM 已配置。健康检查中的 `llm_configured` 可检查三项是否齐全，但凭据是否有效仍需实际问答验证。

Compose 使用 `--env-file` 指定文件时，应修改该文件中的模型配置。宿主机 `.env` 中已有密钥，不代表使用 `.env.example` 启动的容器能够读取它。修改后用相同项目名、环境文件和覆盖文件执行 `up -d --no-build api`，让 Compose 重建 API 容器；仅执行 `restart` 不会更新容器环境变量。无需重新上传 PDF。

2026-10-12 的本机 `8082` 隔离验收环境使用本地忽略文件 `.env.rag-round1`，已从现有 `.env` 接入上述三项模型配置，保留原数据库、文档和端口。后续启动该演示环境时沿用以下命令（覆盖文件为本机验收产物，依赖已有模型缓存）：

```powershell
docker compose -p rag-round1-check --env-file .env.rag-round1 -f docker-compose.yml -f artifacts/fullstack/container-override.json up -d --no-build
Invoke-RestMethod http://127.0.0.1:8012/health
```

`.env.rag-round1` 包含真实凭据，不得提交到 Git；`.env.example` 保持公开空值示例。该环境已通过 Edge 网页、Nginx、真实 BGE 和 DeepSeek 问答验证，记录见 [真实模型验收记录](真实模型验收记录.md)。

## 请求追踪与故障定位

每次 HTTP 请求由后端生成 `X-Request-ID`，SSE 的 `meta/error` 事件携带同一个 `request_id`。上传或问答失败时，页面展示可复制的请求 ID；网络未收到响应时不会编造 ID。请求 ID 不写入业务表，刷新后保留原来的回答和状态，当前实现不保存错误提示中的 ID。

应用 logger `rag.app` 将一行一个 JSON 的日志输出到标准输出，记录权限检查、PDF 解析、向量生成、文档事务、检索、模型生成和终态保存。字段包括 `request_id`、`event`、`stage`、`outcome`、`duration_ms` 及安全的 `error_code`；不记录原文、文件名、Prompt、回答、密码或令牌。Uvicorn 的访问日志仍使用原有格式。

本地运行时直接查看后端终端；Compose 使用实际启动时相同的项目、环境文件和覆盖参数执行 `logs api`。默认项目示例：

```powershell
docker compose logs --since 10m api | Select-String -SimpleMatch '从页面复制的请求ID'
```

例如：问答失败时先找到同 ID 的 `retrieval`，再看 `llm` 和 `generation_finished`。`llm_timeout` 表示上游模型超时，`llm_unconfigured` 表示配置不完整，`persisted=true` 才表示终态已保存。SSE 失败时 HTTP 仍可能为 200，须结合业务 `outcome` 判断；用户停止生成应为 `interrupted`。没有终态保存成功的记录时，不能假设数据库已经更新。

`llm_first_delta.duration_ms` 从开始调用流到收到首个非空内容增量；`llm` 阶段总耗时包含消费模型流及增量保存/转发，不能视为纯上游推理耗时。`request_finished.duration_ms` 到流与清理结束，不能当作首字延迟。当前尚未实现模型用量统计、监控平台或后台入库队列。

实现范围与验收步骤见 [请求追踪实施计划](superpowers/plans/2026-10-13-request-tracing.md)。容器需要重建镜像才能包含这些代码；宿主机回归通过不代表已有运行容器已更新。
