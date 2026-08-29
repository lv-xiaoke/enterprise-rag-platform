# 第二月 Day 2：搭建可持久的 PostgreSQL + pgvector 开发环境

> 来源计划：`docs/第二月每日实施参考.md` Day 2
> 预计用时：2～3 小时
> 今日状态：已完成
> 唯一产物：`docker-compose.yml`


Day 1 已用运行证据确认：当前 RAG 的 FAISS 索引只存在内存中，服务重启便无法继续检索。今天只在**数据层的运行环境**建立 PostgreSQL + pgvector、健康检查和命名卷验证；不接入 FastAPI、不安装 SQLAlchemy/Alembic、不创建业务表，也不替换 FAISS。今天得到的可重复数据库环境会成为 Day 3 接入 ORM、迁移和数据库会话的输入。

## 先记住 4 件事

- **PostgreSQL** 是保存结构化业务数据的数据库。当前 SQLite 只保存普通聊天，而 FAISS 向量与 PDF 元数据不能跨重启保留；以后 PostgreSQL 会保存组织、知识库、文档、版本和 Chunk 等长期数据。今天只让数据库容器稳定运行，不让应用访问它。
- **pgvector** 是安装在 PostgreSQL 里的扩展，为日后的向量列和相似度查询提供能力。它不会在今天自动把 FAISS 数据迁过去；证明自己理解的方式是能解释：`vector` 扩展可用，不等于 RAG 检索已经切换完成。[[pgvector]]
- **Docker Compose** 是把容器、端口、健康检查和存储卷写成一份可复现配置的工具。**命名卷**是 Docker 管理的持久磁盘空间；删掉并重建容器后数据仍在，才能证明不是“容器还没关所以看起来没丢”。它改变的是数据层运行环境，不改变接口层、检索层或生成层。[[Docker Compose]]
- 仓库 README 记录的是上一轮 30 天 Mini RAG 学习已完成；第二月主计划则明确要求从 Day 2 开始建立新环境。当前仓库也确实没有 Compose 文件、`.env.example`、PostgreSQL 驱动或数据库 URL 配置。以第二月主计划为本日依据，保留 README 和所有未提交改动，今天不要把“旧项目已完成”误当成“第二月环境已完成”。最常见的错误是执行 `docker compose down -v` 做“重启”；`-v` 会删除命名卷，恰好破坏今天要验证的持久化。

## 步骤 1：确认 Docker 与仓库起点

先确认本机有可用的 Docker Compose，并再次确认今天不会覆盖已有配置。这里不启动服务、不读取 `.env`；完成后应能判断是继续搭建环境，还是先解决 Docker Desktop 前置条件。

### [你来完成] 只读检查

在项目根目录执行：

```powershell
git status --short
Get-Command docker -ErrorAction SilentlyContinue
docker compose version
Test-Path .\docker-compose.yml
Test-Path .\compose.yaml
Test-Path .\.env.example
Get-Content .\app\config.py
Get-Content .\requirements.txt
```

预期：`docker compose version` 能输出版本；三个 `Test-Path` 目前都应为 `False`；`app/config.py` 只有 LLM 配置；依赖中还没有 PostgreSQL/SQLAlchemy/Alembic。`git status --short` 中已有的 docs 改动是你的工作区内容，只记录，不恢复或清理。

如果 `docker` 或 `docker compose` 不可用，先安装并启动 Docker Desktop，再重新执行本步骤；不要用手工安装 PostgreSQL 来绕过 Compose，因为 Day 2 要练的是可复现的容器环境。若三个目标文件中有任意一个已存在，先打开并理解它的用途，再把今天改为“验证已有配置、找缺口并做最小改进”，不要另建第二套数据库。

## 步骤 2：写出数据库容器与公开配置示例

现在把数据库运行方式写入仓库，而不是只在本机界面里点几下。它会新增 `docker-compose.yml` 这一唯一核心产物，并配套新增可公开提交的 `.env.example`；本机实际 `.env` 只保存你自己的开发密码，绝不贴到聊天或提交到 Git。

### [你来完成] 创建最小 Compose 配置

在 `docker-compose.yml` 中只定义一个 `postgres` 服务和一个命名卷 `postgres_data`。

最关键的更正：你当前项目的 [app/config.py](D:\\my_develop\\A_work_program\\AI-study-2609\\enterprise-rag-platform\\app\\config.py) 已经从 `.env` 读取 LLM 配置。**不要把 `.env.example` 整体复制覆盖 `.env`**，否则可能丢掉已有的模型配置。

在项目根目录 `D:\my_develop\A_work_program\AI-study-2609\enterprise-rag-platform` 按下面做。

1. 新建 `docker-compose.yml`，写入：

[[docker-compose.yml讲解]]

```
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

2. 新建 `.env.example`，它是可提交的说明文件。保留 LLM 键名，但不填真实值：

```
# LLM：示例文件中不放真实值
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=

# PostgreSQL：仅本地开发示例
POSTGRES_DB=enterprise_rag
POSTGRES_USER=rag_app
POSTGRES_PASSWORD=change-me-local-only
POSTGRES_PORT=5432
```

3. 打开你本机已有的 `.env`，只在文件末尾追加下面四项；保留其中原有的 `LLM_*` 配置，也不要把 `.env` 内容发给我：

```
POSTGRES_DB=enterprise_rag
POSTGRES_USER=rag_app
POSTGRES_PASSWORD=你自己设置的本机开发密码
POSTGRES_PORT=5432
```

这里 Compose 会读取 `.env` 中的数据库变量；当前 FastAPI 虽然暂时不用它们，但不会受影响。Day 3 才会让应用真正连接 PostgreSQL。

4. 在 PowerShell 验证并启动：

```powershell
docker compose config --quiet 
# 检查你的 `docker-compose.yml` 是否能够被 Docker Compose 正确解析。

docker compose up -d postgres
# 根据 Compose 配置，创建并启动 `postgres` 服务。-d 是 detached mode，后台运行

docker compose ps
# 查看当前 Compose 项目中的容器状态。ps：process status 表示 现在这些容器怎么样了？

```

看到 `postgres` 变为 `healthy` 后，验证 pgvector：

```powershell
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
# 在 `postgres` 容器里，使用 `rag_app` 用户连接 `enterprise_rag` 数据库，然后执行一条 SQL，让 PostgreSQL 启用 pgvector。

docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
# 查询 PostgreSQL 当前已经安装的扩展，看看 `vector` 在不在。pg_extension可以理解成：“PostgreSQL 当前安装了哪些扩展”的登记表。

```

[[docker-安装并检查vector拓展的命令]]

第二条应返回 `vector`。

这几个字段的作用很简单：

- `image`：带 pgvector 的 PostgreSQL 镜像。
- `environment`：首次初始化数据库名、用户和密码。
- `ports`：只允许本机通过 `127.0.0.1:5432` 访问。
- `postgres_data`：保存数据库数据；容器重建后数据仍保留。
- `healthcheck`：让 Docker 判断数据库是否已接受连接。
- `$$POSTGRES_USER`：双美元符让变量在容器里展开，而不是被 Compose 提前替换。

不要执行 `docker compose down -v`；它会删除 `postgres_data`，等于清掉数据库。

### [AI 辅助] 请求一次配置审查

完成草稿后可提问：

> 请只审查我贴出的 `docker-compose.yml` 和 `.env.example`：检查 pgvector 镜像、命名卷、健康检查、端口绑定和变量转义是否合理。不要读取或索要 `.env`，不要替我运行 Docker、迁移或修改任何文件；请把问题按“会阻塞启动 / 可改进”分类说明。

## 步骤 3：启动服务并确认健康与扩展

这一步把配置从“写过”变成可观察的数据库实例。终端 A 负责启动和查看容器日志；终端 B 负责检查健康状态与 SQL 结果。除本步骤外不要启动 FastAPI。

### [你来完成] 运行正常路径

终端 A：

```powershell
docker compose config --quiet
docker compose up -d postgres
docker compose ps
```

`docker compose config --quiet` 只校验配置而不打印可能包含本机密码的展开结果。预期 `postgres` 最终显示为 `healthy`；如果仍是 `starting`，等待一个健康检查周期后再看一次。

终端 B：

```powershell
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -v ON_ERROR_STOP=1 -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

-v 表示：设置 psql 的一个变量。
这里设置的是：
ON_ERROR_STOP = 1
ON_ERROR_STOP=1
意思是：
遇到 SQL 错误就立即停止。

预期第二条命令返回一行 `vector` 扩展及版本号。这里的 `CREATE EXTENSION IF NOT EXISTS` 可重复执行，且只为这个空的开发数据库启用能力；Day 3 才会用迁移文件管理应用业务结构。

如果你把 `.env` 中的数据库名或用户名改成了示例以外的值，把两条命令中的 `rag_app`、`enterprise_rag` 同步换成你的值；不要把密码写进命令行。

## 步骤 4：证明重启后仍保留数据，并检查失败路径

健康状态只能说明数据库活着，不能说明数据在容器重建后还在。用一张专门的探针表写入一行数据、移除容器再启动并读取它，才能证明命名卷生效；随后删除这张仅用于测试的表，避免干扰 Day 3 的正式迁移。

### [你来完成] 验证命名卷持久化

终端 B 先创建探针数据：

```powershell
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -v ON_ERROR_STOP=1 -c "CREATE TABLE IF NOT EXISTS day2_persistence_probe (marker text PRIMARY KEY); INSERT INTO day2_persistence_probe (marker) VALUES ('survives-container-recreate') ON CONFLICT DO NOTHING; SELECT marker FROM day2_persistence_probe;"
```

[[docker-创建探针数据的命令]]

预期能看到 `survives-container-recreate`。接着在终端 A 执行（注意命令中**没有** `-v`）：

```powershell
docker compose down
docker compose up -d postgres
docker compose ps
```

[[docker-删除容器再重新创建新容器并检查状态]]

确认健康后，终端 B 执行：

```powershell
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -v ON_ERROR_STOP=1 -c "SELECT extname FROM pg_extension WHERE extname = 'vector'; SELECT marker FROM day2_persistence_probe;"
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -v ON_ERROR_STOP=1 -c "DROP TABLE day2_persistence_probe;"

# 第一条：验证 pgvector 和数据还在不在
# 第二条：删除之前专门用于测试的表
```


预期第一条同时返回 `vector` 和探针值，第二条只移除你刚创建的测试表。记录这两段输出和 `docker compose ps` 的健康状态，作为今日真实证据。

### [你来完成] 观察一个安全的失败路径

不修改配置、不停止服务，执行一次指向不存在数据库的连接：

```powershell
docker compose exec -T postgres psql -U rag_app -d day2_database_should_not_exist -c "SELECT 1;"
```

预期为非零退出并出现“数据库不存在”一类错误。这证明错误配置不会悄悄连到业务数据库。随后再次运行 `docker compose ps`，预期原来的 `postgres` 服务仍为 `healthy`。如果扩展创建失败，先检查镜像是否确为 pgvector 镜像，再查看 `docker compose logs --tail=100 postgres`；日志中不要粘贴或提交密码。

## 步骤 5：记录边界与为 Day 3 留下明确输入

今天的结论应同时说明“已经验证的运行环境”与“尚未接入的应用能力”。不要为了让 README 看起来完整而提前添加 SQLAlchemy、`psycopg`、Alembic、业务表、FastAPI 数据库连接或任何迁移；它们属于 Day 3。

### [你来完成] 更新本日学习记录

在本文件底部的记录区填写实际的 Docker/Compose 版本、健康检查结果、`vector` 查询输出、重启前后探针查询结果，以及失败路径的真实报错摘要。再用自己的话回答：为什么 `docker compose down` 后数据仍在，而 `docker compose down -v` 后不会在？

在最终验收前检查 `git diff -- docker-compose.yml .env.example .gitignore`：应能看到 Compose 和公开示例，不应看到 `.env` 或真实密码。当前 README 与第一月资料保持不动；如果你发现已有文件与今天的方案冲突，在“与原计划的偏差”中写出事实和最小处理方式。

## 常见问题

- `docker` 找不到：先确认 Docker Desktop 已安装且正在运行，再重新打开 PowerShell；不要改用手工安装数据库。
- `docker compose up` 后一直 `starting` 或 `unhealthy`：先执行 `docker compose logs --tail=100 postgres`，再检查 `.env` 的数据库名、用户名、密码是否非空。
- 5432 端口被占用：先确认是否已有 PostgreSQL 或容器监听该端口；将本机 `.env` 的 `POSTGRES_PORT` 改为未占用端口，再重新启动，容器内端口仍是 5432。
- `CREATE EXTENSION vector` 失败：先检查 Compose 使用的是 pgvector 镜像而非普通 PostgreSQL 镜像，再确认容器已健康。
- 重启后探针表消失：先确认重启命令没有带 `-v`，再检查 `volumes` 是否把 `postgres_data` 挂载到 `/var/lib/postgresql/data`。
- 配置检查泄露了密码：不要运行会打印完整展开配置的命令或分享终端截图；只用 `docker compose config --quiet` 校验，并保持 `.env` 不进入 Git。

## 验收清单

- [ ] 我能用自己的话解释 PostgreSQL、pgvector、Docker Compose 与命名卷各自解决什么问题，以及它们今天只影响数据层环境。
- [ ] 已创建唯一核心产物 `docker-compose.yml`，其中只有 PostgreSQL + pgvector 服务、健康检查和 `postgres_data` 命名卷。
- [ ] 已创建 `.env.example`，本机 `.env` 未提交、未展示、未写入任何真实密码。
- [ ] `docker compose ps` 显示 PostgreSQL 服务为 `healthy`，并已记录实际输出。
- [ ] 已实际执行并记录 `vector` 扩展创建与查询结果。
- [ ] 已验证探针数据在 `docker compose down`（不带 `-v`）和再次启动后仍存在。
- [ ] 已运行不存在数据库的失败路径，确认原服务仍健康。
- [ ] 我明确记录了尚未接入 FastAPI、ORM、迁移和 FAISS 替换，它们会作为 Day 3 及后续任务继续完成。

## 今日学习记录

```text
实际完成：
- 创建 docker-compose.yml 和 .env.example；仅在本机 .env 追加 PostgreSQL 配置，未展示或提交密码。
- docker compose 版本： v5.4.0
- postgres 服务状态：healthy。
- 已启用并查询 pgvector 扩展。
- 已验证命名卷：docker compose down（未带 -v）后重建容器，探针数据仍存在。
- 已执行不存在数据库的失败连接，服务仍为 healthy。

我今天真正理解了：
PostgreSQL 是长期保存业务数据的数据库；pgvector 是 PostgreSQL 的向量扩展；Docker Compose 用配置复现运行环境；命名卷保存容器之外的数据。
docker compose down 只删除容器和网络，postgres_data 命名卷仍保留；docker compose down -v 会同时删除命名卷，所以数据会丢失。
vector 扩展可用，不代表当前 RAG 已切换到 PostgreSQL 或不再使用 FAISS。

仍然不理解：
暂无

遇到的报错：
无阻塞报错。

测试/验证结果：
- docker compose ps：[postgres 为 healthy]
- vector 查询：[vector |  0.8.6]
- 重启前探针查询：[survives-container-recreate]
- 重启后探针查询：[vector；survives-container-recreate]
- 失败路径：连接 day2_database_should_not_exist 失败，提示数据库不存在；随后 postgres 仍为 healthy。

AI 代办内容及我的复核结果：
- AI 协助解释 Compose、健康检查、命名卷和验证命令。
- 我自行执行并确认了健康状态、vector 扩展、重启持久化及失败路径。
- 未让 AI 读取 .env，未提供任何真实密码。

与原计划的偏差：
[无]
今天未接入 FastAPI、SQLAlchemy、Alembic、业务表，也未替换 FAISS；这些留给 Day 3。

明天开始前要解决：
[无]

Git commits：
[已提交]
```

Day 3 会读取今天的 `docker-compose.yml`、`.env.example`、健康检查和 `vector` 扩展证据，在不改变已验证数据库环境的前提下接入 SQLAlchemy 2、PostgreSQL 驱动与 Alembic，并做第一条可升级、可回滚的迁移。若今天未通过健康、扩展或重启持久化验证，Day 3 的数据库连接与迁移都应暂停，先修复本日环境。
