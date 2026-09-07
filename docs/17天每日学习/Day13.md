# Day 13：完成多文档与重启持久化验收

今天将直接完成四份企业制度 PDF 在 API 重启和 PostgreSQL 重启前后的端到端一致性验收，使项目获得“无需重新上传即可继续问答”的可核对持久化证据，并为面试中的状态生命周期、Docker Volume 和系统验收问题提供真实项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一条可重复执行的多文档持久化验收链路，证明同一知识库、Document、Chunk、向量和 RAG 来源在 API 与 PostgreSQL 重启后保持可用  
> 当前真实状态：已完成  
> 对应总体安排：Day 13

## 一、今天完成后的项目变化

### 升级前

```text
Day 9～Day 12 已经具备 4 份固定演示 PDF、固定评测集、评测报告和 pytest
→ 当前数据库也真实存在包含 4 份 ready 文档、27 个 Chunk 的知识库
→ 但尚无本日针对“API 重启 + PostgreSQL 重启”的连续端到端验收
→ 不能只凭表结构、单次查询或历史评测报告证明当前系统可重启恢复
```

### 升级后

```text
固定同一个知识库 ID 和四份 Document ID
→ 记录重启前的数据库指纹、文档列表、跨文档来源和拒答结果
→ 只重启受控的 FastAPI 进程，不重新上传
→ 使用同一知识库 ID 再次查询并比较稳定字段
→ 重启 PostgreSQL Compose 服务但保留 postgres_data Volume，不重新上传
→ 等数据库 healthy 后再次比较数据库指纹、来源和拒答结果
→ 证明数据权威来源是 PostgreSQL + pgvector，而不是进程内 FAISS
```

### 今天在完整项目中的位置

- 所属阶段：质量验收。
- 所属链路：同时验收“PDF → Document/Chunk/Vector 持久化”入库链路和“Question → pgvector → Answer + Sources”问答链路。
- 今天的输入：Day 9 冻结的 4 份演示 PDF、当前数据库中已有的 4 份 `ready` Document、Day 11 固定问题，以及 Day 12 的 7 个 pytest 回归测试。
- 今天的输出：重启前、API 重启后、PostgreSQL 重启后三组可比较的数据库与 HTTP 稳定字段；实际输出记录为可选。
- 下一天为什么需要它：Day 14 要把已经在本机成立的启动、迁移和运行顺序整理成干净环境可复现流程，不能用未经重启验证的步骤写公开说明。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 12 均存在与核心产物匹配的提交和用户完成标记；当前 `HEAD` 为 `d114184 Day12`。 
- `[当前事实]` 生成本计划时 `git status --short` 无输出，工作区干净。
- `[当前事实]` `docker compose ps postgres` 显示 `pgvector/pgvector:pg16` 服务正在运行且为 `healthy`，数据库通过命名 Volume `postgres_data` 挂载 `/var/lib/postgresql/data`。
- `[当前事实]` 当前数据库知识库 ID `20` 包含 4 份 `ready` 文档，Document ID 为 `20`～`23`，合计 27 个 Chunk；每份文档页码范围均为 1～2，`vector_dims(embedding)` 均为 512。
- `[当前事实]` `POST /knowledge-bases/{knowledge_base_id}/query` 从 PostgreSQL/pgvector 检索，返回 `answer`、`refused` 和包含 Chunk、Document、文件名、页码、原文、分数的 `sources`。
- `[当前事实]` `ChunkRepository.search_similar()` 在 SQL 查询中同时限制知识库 ID 和 `Document.status == "ready"`，按余弦距离升序并以 Chunk ID 作为稳定的第二排序键。
- `[当前事实]` `app/db.py` 只有一个应用级 Engine，启用了 `pool_pre_ping=True`；每个请求通过 `get_db_session()` 获得独立 Session。
- `[当前事实]` Day 11 报告中跨文档问题 `cross-trip-01` 能检索到《员工请假与考勤制度》和《差旅与费用报销制度》，无答案问题 `unknown-equity-01` 的候选分数低于当前代码阈值 `0.55`。

### 仍然缺少

- `[当前事实]` 尚无 `docs/17天每日学习/Day13.md` 以及与当前代码、数据和 Compose 状态对应的重启验收手册。
- `[当前事实]` 尚未形成“重启前 → API 重启后 → PostgreSQL 重启后”的同一知识库稳定字段对比。
- `[当前事实]` 当前 API 不在 `docker-compose.yml` 中，必须用一个可追踪 PID 的本地 Uvicorn 进程完成受控重启。
- `[当前事实]` `README.md` 仍主要描述旧 `/upload` + 内存 FAISS 链路，不能作为数据库版 RAG 已通过持久化验收的证据；README 更新属于 Day 15。

### 待实测

- `[待实测]` 本地 `.env` 是否配置了可调用的 LLM；只能通过 `/health` 的 `llm_configured` 布尔值判断，不读取或输出秘密。
- `[待实测]` 当前机器启动 `BAAI/bge-small-zh-v1.5` 的耗时；首次下载或模型加载不计入核心 60 分钟。
- `[待实测]` 受控 API 进程在端口 `8013` 上能否启动并连续完成三轮查询。
- `[待实测]` API 重启后，同一知识库的 Document ID、状态、Chunk 来源和页码是否保持不变。
- `[待实测]` PostgreSQL 重启并保留 Volume 后，数据库指纹是否完全一致，已有 API 能否依靠 `pool_pre_ping` 恢复连接。
- `[待实测]` 三轮无答案请求是否都返回固定拒答、空来源且不泄露内部信息。

### 需要保护的用户修改

- 生成计划时工作区干净；执行时仍只按当天文件清单操作，不覆盖、还原或暂存其他修改。
- 不删除任何知识库、Document、Chunk、数据库文件或 Docker Volume；今天复用现有数据并只执行读取、查询和受控服务重启。
- 不修改或输出 `.env`、API Key、数据库密码和完整数据库 URL。

## 三、今天必须理解的核心知识

### 1. 进程状态、数据库状态和 Volume 是三种不同生命周期

- 一句话解释：FastAPI 进程内对象随进程退出而消失，PostgreSQL 表数据随数据库进程重启仍可恢复，而 Docker Volume 负责让容器生命周期之外的数据文件继续存在。
- 在当前项目中的职责：新接口从 `knowledge_bases`、`documents`、`chunks` 和 pgvector 字段读取权威数据，不依赖旧路由的全局 `rag_service`。
- 与其他组件的关系：API 重启验证“业务状态不在 Python 内存”；PostgreSQL 重启验证“数据库服务可恢复”；Volume 保证数据库容器使用同一数据目录。
- 容易混淆的点：`docker compose restart postgres` 会重启服务但保留 Volume；删除或替换 Volume 是另一种破坏性操作，不能用来验证持久化。
- 面试一句话：我分别重启应用进程和 PostgreSQL 服务，并始终复用同一知识库 ID 与 Document ID，证明数据权威来源是挂载持久化 Volume 的 PostgreSQL/pgvector，而不是内存 FAISS。

### 2. 持久化验收必须比较稳定字段，不能比较 LLM 措辞

- 一句话解释：数据库主键、文件名、状态、Chunk ID、页码和检索来源在相同数据与参数下应稳定，LLM 自然语言回答可能存在合理波动。
- 在当前项目中的职责：验收指纹比较 4 个 Document 的 `id|filename|status` 和跨文档响应的 `chunk_id|document_id|filename|page_number|chunk_index`。
- 与其他组件的关系：HTTP 响应证明 API/Service/Repository 全链路可用，数据库只读查询证明底层记录和 512 维向量没有丢失。
- 容易混淆的点：不应因为回答标点或措辞变化判定持久化失败，也不能只比较 HTTP 200 而忽略来源是否还是原 Document/Chunk。
- 面试一句话：我的重启验收比较可重复的数据库和来源标识，不把非确定性的 LLM 文本当作持久化指纹。

### 3. 重启、重建和迁移不是同一件事

- 一句话解释：重启只改变进程生命周期，重建可能替换容器，迁移改变数据库 Schema；Day 13 只验证重启恢复，不改变 Schema。
- 在当前项目中的职责：今天执行 `docker compose restart postgres`，不生成 Alembic revision，也不执行 downgrade。
- 与其他组件的关系：`migrations/versions/e780fe92751b_create_core_rag_tables.py` 已经建立三张表；Day 13 的数据必须留在这些表中接受重启验证。
- 容易混淆的点：用迁移回滚或空数据库重建来“验证”会破坏今天要比较的已有数据；干净环境迁移属于 Day 14。
- 面试一句话：Day 13 验证已有数据在服务重启后的连续性，Day 14 才验证新环境能否从公开配置迁移到 head。

### 4. 端到端验收与 pytest 回归测试互补

- 一句话解释：pytest 固定规则并快速定位回归，端到端验收覆盖真实进程、HTTP、模型、连接池、PostgreSQL 和 Volume 的组合行为。
- 在当前项目中的职责：先运行 Day 12 的 7 个测试保护过滤、来源和拒答规则，再用真实四文档知识库完成三轮 HTTP 查询。
- 与其他组件的关系：单元测试使用可控假 LLM，集成测试使用真实 pgvector，Day 13 再加入真实 Uvicorn 和外部 LLM 边界。
- 容易混淆的点：全套 pytest 通过不能证明服务重启后仍能读取历史数据；一次 Swagger 成功也不能替代可重复的自动回归。
- 面试一句话：我用 pytest 保护业务规则，用重启前后的端到端指纹验证部署运行时和持久化边界。

## 四、升级涉及的文件

| 文件                                          | 操作             | 作用                                               |
| ------------------------------------------- | -------------- | ------------------------------------------------ |
| `docs/17天每日学习/Day13.md`                     | 新建；执行后可选补充实际记录 | 保存今天完整的多文档与重启持久化验收手册、预期结果、排错和面试答案                |
| `app/main.py`                               | 只读复核           | 确认知识库、文档和数据库版 RAG 的真实 HTTP 路径与响应模型               |
| `app/db.py`                                 | 只读复核           | 确认 Engine、`pool_pre_ping` 和请求 Session 生命周期       |
| `app/repositories/chunk_repository.py`      | 只读复核           | 确认知识库范围、`ready` 状态、Top-K 排序和来源字段                 |
| `docker-compose.yml`                        | 只读复核           | 确认 `postgres` 服务、健康检查和 `postgres_data` 命名 Volume |
| `data/demo_policies/manifest.json`          | 只读输入           | 固定四份 PDF 的文件名、页数和 SHA-256                        |
| `data/evaluation/enterprise_questions.json` | 只读输入           | 提供跨文档问题、无答案问题和固定预期证据                             |

运行时的 Uvicorn 标准输出和错误日志写到系统临时目录，不进入仓库，也不放入 Git 提交。

### 今日不做

- 不修改应用代码、ORM、Repository、Service、API、迁移或测试；发现真实缺陷时先保存失败现象，再单独决定修复范围。
- 不创建新迁移、不执行 downgrade、不重建空数据库；干净环境迁移属于 Day 14。
- 不把 API 加进 Compose、不调整 Dockerfile 或公开配置；这属于 Day 14。
- 不更新旧 FAISS README、架构图或求职材料；这属于 Day 15。
- 不调整 `MIN_RELEVANCE_SCORE=0.55` 或默认 Top-K；Day 13 只验证当前实现，不把 Day 11 的选参结论偷偷改进生产代码。
- 不删除数据库 Volume、知识库或历史测试数据，也不通过重新上传掩盖重启后数据丢失。

## 五、按顺序完成项目升级

### 步骤 1：建立可重复的验收断言（建议 8 分钟）

**目标**

在同一个 PowerShell 窗口定义启动/停止受控 API、执行数据库版 RAG 请求、检查四份文档、检查跨文档来源、检查拒答和生成稳定指纹的函数；后续三轮验收必须复用同一组函数。

**修改位置**

- 文件：不修改应用文件；函数只存在于当前 PowerShell 会话。
- 定位：在项目根目录新开的 Day 13 验收窗口中执行。
- 操作：完整复制下面的函数定义，不要使用 `--reload`，否则父子进程会让 PID 重启边界不清楚。

**复制下面的完整代码**

```powershell
$day13ExpectedFilenames = @(
    '员工请假与考勤制度.pdf',
    '差旅与费用报销制度.pdf',
    '采购与办公资产管理制度.pdf',
    '访客与会议室管理办法.pdf'
)

function Stop-Day13Api {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -Timeout 15 -ErrorAction SilentlyContinue
    }
}

function Start-Day13Api {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExecutable,

        [Parameter(Mandatory = $true)]
        [int]$Port,

        [Parameter(Mandatory = $true)]
        [string]$StdoutPath,

        [Parameter(Mandatory = $true)]
        [string]$StderrPath
    )

    $startedProcess = Start-Process `
        -FilePath $PythonExecutable `
        -ArgumentList @(
            '-m',
            'uvicorn',
            'app.main:app',
            '--host',
            '127.0.0.1',
            '--port',
            [string]$Port
        ) `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath `
        -PassThru `
        -WindowStyle Hidden

    $healthResponse = $null
    for ($attempt = 1; $attempt -le 120; $attempt++) {
        if ($startedProcess.HasExited) {
            break
        }

        try {
            $healthResponse = Invoke-RestMethod `
                -Method Get `
                -Uri "http://127.0.0.1:$Port/health" `
                -TimeoutSec 2
            break
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($null -eq $healthResponse) {
        if (Test-Path -LiteralPath $StderrPath) {
            Get-Content -LiteralPath $StderrPath -Tail 80
        }
        throw "Day 13 API 未在 120 秒内就绪，日志：$StderrPath"
    }

    return $startedProcess
}

function Invoke-Day13Query {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,

        [Parameter(Mandatory = $true)]
        [int]$KnowledgeBaseId,

        [Parameter(Mandatory = $true)]
        [string]$Question,

        [int]$TopK = 3
    )

    $requestJson = @{
        question = $Question
        top_k = $TopK
    } | ConvertTo-Json

    return Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/knowledge-bases/$KnowledgeBaseId/query" `
        -ContentType 'application/json; charset=utf-8' `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($requestJson))
}

function Assert-Day13Documents {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Documents,

        [Parameter(Mandatory = $true)]
        [string[]]$ExpectedFilenames
    )

    $documentList = @($Documents)
    if ($documentList.Count -ne 4) {
        throw "预期正好 4 份文档，实际为 $($documentList.Count)"
    }

    foreach ($expectedFilename in $ExpectedFilenames) {
        $matchingDocuments = @(
            $documentList |
                Where-Object { $_.filename -eq $expectedFilename }
        )
        if ($matchingDocuments.Count -ne 1) {
            throw "文档数量不符合预期：$expectedFilename"
        }
        if ($matchingDocuments[0].status -ne 'ready') {
            throw "文档不是 ready：$expectedFilename"
        }
        if ([int]$matchingDocuments[0].id -le 0) {
            throw "文档 ID 非法：$expectedFilename"
        }
    }
}

function Assert-Day13CrossDocumentResponse {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Response
    )

    if ($Response.refused -ne $false) {
        throw '跨文档问题不应被拒答'
    }

    $sources = @($Response.sources)
    if ($sources.Count -lt 2) {
        throw '跨文档问题至少应返回两条可核对来源'
    }

    $sourceFilenames = @(
        $sources |
            Select-Object -ExpandProperty filename -Unique
    )
    foreach ($expectedFilename in @(
        '员工请假与考勤制度.pdf',
        '差旅与费用报销制度.pdf'
    )) {
        if ($expectedFilename -notin $sourceFilenames) {
            throw "跨文档来源缺少：$expectedFilename"
        }
    }

    foreach ($source in $sources) {
        if (
            [int]$source.chunk_id -le 0 -or
            [int]$source.document_id -le 0 -or
            [int]$source.page_number -le 0 -or
            [string]::IsNullOrWhiteSpace([string]$source.content)
        ) {
            throw '来源字段不完整'
        }
    }
}

function Assert-Day13RefusalResponse {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Response
    )

    if ($Response.refused -ne $true) {
        throw '无答案问题必须拒答'
    }
    if ([string]$Response.answer -ne '当前知识库中没有找到足够的信息。') {
        throw '无答案问题没有返回固定拒答文案'
    }
    if (@($Response.sources).Count -ne 0) {
        throw '无答案问题不得返回伪造来源'
    }
}

function Get-Day13StableFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [int]$KnowledgeBaseId,

        [Parameter(Mandatory = $true)]
        [object[]]$Documents,

        [Parameter(Mandatory = $true)]
        [object]$CrossDocumentResponse,

        [Parameter(Mandatory = $true)]
        [object]$RefusalResponse
    )

    $documentKeys = @(
        $Documents |
            Sort-Object id |
            ForEach-Object {
                '{0}|{1}|{2}' -f $_.id, $_.filename, $_.status
            }
    )
    $sourceKeys = @(
        $CrossDocumentResponse.sources |
            ForEach-Object {
                '{0}|{1}|{2}|{3}|{4}' -f `
                    $_.chunk_id,
                    $_.document_id,
                    $_.filename,
                    $_.page_number,
                    $_.chunk_index
            }
    )

    return [pscustomobject]@{
        knowledge_base_id = $KnowledgeBaseId
        document_keys = $documentKeys
        cross_document_source_keys = $sourceKeys
        refusal = [pscustomobject]@{
            refused = [bool]$RefusalResponse.refused
            answer = [string]$RefusalResponse.answer
            source_count = @($RefusalResponse.sources).Count
        }
    } | ConvertTo-Json -Depth 5 -Compress
}
```

**这段代码怎样工作**

- 输入：Python 路径、受控端口、动态知识库 ID、HTTP 文档列表和两类问答响应。
- 输出：明确的 PowerShell 异常或一个只包含稳定字段的压缩 JSON 指纹。
- 调用谁：`Start-Process` 启动当前仓库的 Uvicorn；`Invoke-RestMethod` 调用当前 FastAPI；断言函数只检查公开响应。
- 被谁调用：后面的重启前、API 重启后和 PostgreSQL 重启后三轮验收命令。
- 正常路径：三轮指纹完全一致，LLM 的具体自然语言措辞不参与比较。
- 失败路径：文档数量、状态、来源文件、ID、页码、拒答文案或来源数量任何一项变化都会立即抛出明确错误。

**完成本步骤后的预期状态**

当前 PowerShell 会话已经具备可重复的验收函数，但尚未启动、停止或修改任何服务和数据。

### 步骤 2：锁定同一个已有四文档知识库（建议 7 分钟）

**目标**

从真实数据库动态选择“正好包含四份固定 `ready` PDF”的最新知识库，不把报告中的 ID `20` 永久写死；当前数据库执行时预期仍选中 ID `20`。

**修改位置**

- 文件：不修改文件和数据库记录。
- 定位：`knowledge_bases`、`documents`、`chunks` 三张表。
- 操作：只读查询容器内公开的数据库用户名和库名，不读取密码；再把目标知识库 ID 保存到 `$day13KnowledgeBaseId`。

**复制下面的完整代码**

```powershell
$day13DbUser = (
    docker compose exec -T postgres printenv POSTGRES_USER
).Trim()
$day13DbName = (
    docker compose exec -T postgres printenv POSTGRES_DB
).Trim()

if (
    [string]::IsNullOrWhiteSpace($day13DbUser) -or
    [string]::IsNullOrWhiteSpace($day13DbName)
) {
    throw '无法从 postgres 容器读取公开的数据库用户名或库名'
}

$day13FindKnowledgeBaseSql = @"
SELECT kb.id
FROM knowledge_bases AS kb
JOIN documents AS d
  ON d.knowledge_base_id = kb.id
WHERE d.status = 'ready'
GROUP BY kb.id
HAVING COUNT(DISTINCT d.id) = 4
   AND COUNT(DISTINCT d.filename) FILTER (
       WHERE d.filename IN (
           '员工请假与考勤制度.pdf',
           '差旅与费用报销制度.pdf',
           '采购与办公资产管理制度.pdf',
           '访客与会议室管理办法.pdf'
       )
   ) = 4
ORDER BY kb.id DESC
LIMIT 1;
"@

$day13KnowledgeBaseIdText = (
    docker compose exec -T postgres `
        psql `
        -v ON_ERROR_STOP=1 `
        -At `
        -U $day13DbUser `
        -d $day13DbName `
        -c $day13FindKnowledgeBaseSql
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw '定位 Day 13 知识库的只读 SQL 执行失败'
}
if ($day13KnowledgeBaseIdText -notmatch '^\d+$') {
    throw '没有找到正好包含四份固定 ready PDF 的知识库；先按排错表补建一次，不要删除旧数据'
}

$day13KnowledgeBaseId = [int]$day13KnowledgeBaseIdText
$day13KnowledgeBaseId
```

**这段代码怎样工作**

- 输入：当前 Compose `postgres` 容器公开环境中的用户名、库名和三张业务表。
- 输出：动态 `$day13KnowledgeBaseId`；按生成计划时的真实数据库状态预期为 `20`。
- 调用谁：容器内 `psql`，SQL 全程只有 `SELECT`。
- 被谁调用：文档列表、数据库指纹和三轮 RAG 请求。
- 正常路径：只选中同时满足 4 个固定文件名、4 个 Document、全部 `ready` 的最新知识库。
- 失败路径：数据库不可用、表不存在或没有符合条件的数据时抛错，不自动删除、覆盖或重复上传。

**完成本步骤后的预期状态**

验收对象被固定为同一个动态知识库 ID；后面所有请求都必须复用此变量，不能在重启后重新创建知识库或重新上传 PDF。

### 步骤 3：建立数据库与 HTTP 双重基线（建议 12 分钟）

**目标**

在任何重启前，保存四份 Document 的数据库指纹，并通过 API 获得文档列表、跨文档回答和无答案拒答的稳定字段。

**修改位置**

- 文件：不修改应用文件；可选把实际摘要填写到本文件“十五、可选执行记录”。
- 定位：当前 PowerShell 窗口中的 `$day13KnowledgeBaseId` 和 `$day13BaseUrl`。
- 操作：先查询数据库，再发起 HTTP 请求；指纹只保存在内存变量中。

**复制下面的完整代码**

```powershell
$day13DatabaseFingerprintSql = @"
SELECT
    d.id::text || '|' ||
    d.filename || '|' ||
    d.status || '|' ||
    COUNT(c.id)::text || '|' ||
    COALESCE(MIN(c.page_number)::text, '') || '|' ||
    COALESCE(MAX(c.page_number)::text, '') || '|' ||
    COALESCE(MIN(vector_dims(c.embedding))::text, '') || '|' ||
    COALESCE(MAX(vector_dims(c.embedding))::text, '')
FROM documents AS d
LEFT JOIN chunks AS c
  ON c.document_id = d.id
WHERE d.knowledge_base_id = $day13KnowledgeBaseId
GROUP BY d.id, d.filename, d.status
ORDER BY d.id;
"@

$day13DatabaseFingerprintBefore = @(
    docker compose exec -T postgres `
        psql `
        -v ON_ERROR_STOP=1 `
        -At `
        -U $day13DbUser `
        -d $day13DbName `
        -c $day13DatabaseFingerprintSql
) -join "`n"

if ($LASTEXITCODE -ne 0) {
    throw '重启前数据库指纹查询失败'
}

$day13DocumentsBefore = @(
    Invoke-RestMethod `
        -Method Get `
        -Uri "$day13BaseUrl/knowledge-bases/$day13KnowledgeBaseId/documents"
)
Assert-Day13Documents `
    -Documents $day13DocumentsBefore `
    -ExpectedFilenames $day13ExpectedFilenames

$day13CrossQuestion = '员工因公出差时，从出发前到返程后，为了考勤和报销需要完成哪些关键步骤？'
$day13RefusalQuestion = '公司的股票期权归属周期和行权条件是什么？'

$day13CrossBefore = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13CrossQuestion `
    -TopK 3
Assert-Day13CrossDocumentResponse -Response $day13CrossBefore

$day13RefusalBefore = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13RefusalQuestion `
    -TopK 3
Assert-Day13RefusalResponse -Response $day13RefusalBefore

$day13HttpFingerprintBefore = Get-Day13StableFingerprint `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Documents $day13DocumentsBefore `
    -CrossDocumentResponse $day13CrossBefore `
    -RefusalResponse $day13RefusalBefore

$day13DocumentsBefore |
    Select-Object id, filename, status, failure_reason |
    Format-Table
$day13CrossBefore.sources |
    Select-Object document_id, filename, page_number, chunk_id, chunk_index, score |
    Format-Table
$day13RefusalBefore | ConvertTo-Json -Depth 4
```

**这段代码怎样工作**

- 输入：同一个知识库 ID、四份固定 PDF、一个跨文档问题和一个无答案问题。
- 输出：数据库指纹 `$day13DatabaseFingerprintBefore`、HTTP 指纹 `$day13HttpFingerprintBefore` 和便于人工核对的表格。
- 调用谁：PostgreSQL、FastAPI、Embedding、pgvector、LLM 和响应模型。
- 被谁调用：后面的两次重启对比以这两份基线指纹为唯一参照。
- 正常路径：4 份文档均为 `ready`；跨文档来源同时包含人事与差旅 PDF；无答案请求固定拒答。
- 失败路径：任何稳定字段不符合约定都会在建立基线时停止，避免拿错误基线继续比较。

**完成本步骤后的预期状态**

已经获得重启前基线，但尚不能声称持久化验收完成；必须继续完成 API 和 PostgreSQL 两类重启。

### 步骤 4：依次重启 API 与 PostgreSQL并比较同一指纹（建议 18 分钟）

**目标**

停止并重新启动唯一受控的 Day 13 Uvicorn PID，再重启 PostgreSQL 服务；两次都不调用上传接口，并在服务恢复后比较稳定字段。

**修改位置**

- 文件：不修改代码、数据库或 Volume。
- 定位：`$day13ApiProcess`、Compose `postgres` 服务、两份重启前指纹。
- 操作：先 API 重启并验收，再 PostgreSQL 重启并验收，不能交换或并行执行。

**复制下面的完整代码**

```powershell
Stop-Day13Api -Process $day13ApiProcess

$day13ApiProcess = Start-Day13Api `
    -PythonExecutable $day13PythonExecutable `
    -Port $day13Port `
    -StdoutPath (Join-Path $day13LogDirectory 'api-restart.stdout.log') `
    -StderrPath (Join-Path $day13LogDirectory 'api-restart.stderr.log')

$day13DocumentsAfterApiRestart = @(
    Invoke-RestMethod `
        -Method Get `
        -Uri "$day13BaseUrl/knowledge-bases/$day13KnowledgeBaseId/documents"
)
Assert-Day13Documents `
    -Documents $day13DocumentsAfterApiRestart `
    -ExpectedFilenames $day13ExpectedFilenames

$day13CrossAfterApiRestart = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13CrossQuestion `
    -TopK 3
Assert-Day13CrossDocumentResponse `
    -Response $day13CrossAfterApiRestart

$day13RefusalAfterApiRestart = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13RefusalQuestion `
    -TopK 3
Assert-Day13RefusalResponse `
    -Response $day13RefusalAfterApiRestart

$day13HttpFingerprintAfterApiRestart = Get-Day13StableFingerprint `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Documents $day13DocumentsAfterApiRestart `
    -CrossDocumentResponse $day13CrossAfterApiRestart `
    -RefusalResponse $day13RefusalAfterApiRestart

if (
    $day13HttpFingerprintAfterApiRestart -cne
    $day13HttpFingerprintBefore
) {
    throw 'API 重启后的 Document/Chunk 稳定字段与重启前不一致'
}

docker compose restart postgres
if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL 重启命令失败'
}

$day13DatabaseReady = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    docker compose exec -T postgres `
        pg_isready `
        -U $day13DbUser `
        -d $day13DbName *> $null
    if ($LASTEXITCODE -eq 0) {
        $day13DatabaseReady = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $day13DatabaseReady) {
    throw 'PostgreSQL 重启后 60 秒内未恢复 ready'
}

$day13DatabaseFingerprintAfterPostgresRestart = @(
    docker compose exec -T postgres `
        psql `
        -v ON_ERROR_STOP=1 `
        -At `
        -U $day13DbUser `
        -d $day13DbName `
        -c $day13DatabaseFingerprintSql
) -join "`n"

if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL 重启后的数据库指纹查询失败'
}
if (
    $day13DatabaseFingerprintAfterPostgresRestart -cne
    $day13DatabaseFingerprintBefore
) {
    throw 'PostgreSQL 重启后的 Document/Chunk/向量维度指纹发生变化'
}

$day13DocumentsAfterPostgresRestart = @(
    Invoke-RestMethod `
        -Method Get `
        -Uri "$day13BaseUrl/knowledge-bases/$day13KnowledgeBaseId/documents"
)
Assert-Day13Documents `
    -Documents $day13DocumentsAfterPostgresRestart `
    -ExpectedFilenames $day13ExpectedFilenames

$day13CrossAfterPostgresRestart = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13CrossQuestion `
    -TopK 3
Assert-Day13CrossDocumentResponse `
    -Response $day13CrossAfterPostgresRestart

$day13RefusalAfterPostgresRestart = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question $day13RefusalQuestion `
    -TopK 3
Assert-Day13RefusalResponse `
    -Response $day13RefusalAfterPostgresRestart

$day13HttpFingerprintAfterPostgresRestart = Get-Day13StableFingerprint `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Documents $day13DocumentsAfterPostgresRestart `
    -CrossDocumentResponse $day13CrossAfterPostgresRestart `
    -RefusalResponse $day13RefusalAfterPostgresRestart

if (
    $day13HttpFingerprintAfterPostgresRestart -cne
    $day13HttpFingerprintBefore
) {
    throw 'PostgreSQL 重启后的 HTTP 稳定字段与重启前不一致'
}

[pscustomobject]@{
    knowledge_base_id = $day13KnowledgeBaseId
    document_count = @($day13DocumentsAfterPostgresRestart).Count
    database_fingerprint_unchanged = $true
    api_restart_fingerprint_unchanged = $true
    postgres_restart_fingerprint_unchanged = $true
    cross_document_refused = $day13CrossAfterPostgresRestart.refused
    refusal_question_refused = $day13RefusalAfterPostgresRestart.refused
} | Format-List
```

**这段代码怎样工作**

- 输入：重启前数据库/HTTP 指纹和受控 API PID。
- 输出：两次精确比较结果；全部通过时最后显示 4 个 Document、三项一致性为 `True`、跨文档问题 `refused=False`、无答案问题 `refused=True`。
- 调用谁：精确 PID 的 `Stop-Process`、Uvicorn、Compose `restart postgres`、`pg_isready`、PostgreSQL、FastAPI 和当前 RAG 链路。
- 被谁调用：这是 Day 13 唯一核心验收闭环。
- 正常路径：没有任何上传请求；相同知识库和 Document/Chunk 在两类重启后继续可用。
- 失败路径：数据库没有恢复、Volume 指向错误、API 使用内存状态、来源变化或拒答失效都会终止并指出阶段。

**完成本步骤后的预期状态**

如果全部命令没有抛错，则依据当前实现应得到一条完整的重启持久化证据链；实际输出是否保存和回填由用户选择，不影响本计划提供完整验收能力。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成 revision、不执行 upgrade/downgrade；当前数据库必须已经位于 `e780fe92751b (head)`。今天只检查现有迁移、启动缺失服务并运行 Day 12 回归测试。

### 1. 检查当前状态

执行目录：项目根目录。目的：确认输入文件、当前 Git 边界、数据库服务、迁移 head 和测试基线。按顺序执行：

```powershell
Get-Location
git status --short
python --version
python scripts/generate_demo_pdfs.py --verify-only
python scripts/validate_enterprise_questions.py
docker compose ps postgres
python -m alembic current
python -m pytest -q
```

预期结果：

- `git status --short` 在首次执行时只应显示新生成的 `docs/17天每日学习/Day13.md`；若还有其他文件，记录并保持不动。
- 两个固定数据校验命令退出码应为 0；它们只验证 4 个 PDF、清单、18 道题及哈希一致，不代表今天的重启已经通过。
- PostgreSQL 预期为 `running/healthy`。
- Alembic 当前版本预期显示 `e780fe92751b (head)`。
- 当前测试套件预期为 7 个测试通过、退出码 0；实际执行结果可选记录，不能提前写成真实成功。

失败时检查：

- Python 或 pytest 不一致：运行 `python -c "import sys; print(sys.executable)"`，确保使用安装了 `requirements.txt` 与 `requirements-test.txt` 的同一个虚拟环境。
- 固定数据校验失败：先核对报错文件名、SHA-256 或 case ID，不要通过改题、改 PDF 或删数据制造通过。
- 数据库不是 healthy：查看 `docker compose ps postgres` 和 `docker compose logs --tail 80 postgres`，日志不得复制真实密码。
- Alembic 不在 head：停止 Day 13，先恢复 Day 1～Day 2 的迁移基线；今天不通过迁移回滚处理。
- pytest 失败：先修复已知回归再做系统验收，不能用手工 HTTP 成功掩盖自动测试失败。

### 2. 执行升级

今天没有代码或 Schema 升级。仅当 `postgres` 当前未运行时，在项目根目录执行下面的环境恢复；已经 healthy 时不要重复启动：

```powershell
$day13RunningServices = @(
    docker compose ps --status running --services
)

if ('postgres' -notin $day13RunningServices) {
    docker compose up -d postgres
}

docker compose ps postgres
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

然后准备受控 API。继续使用定义过验收函数的同一个 PowerShell 窗口：

```powershell
$day13Port = 8013
$day13BaseUrl = "http://127.0.0.1:$day13Port"

$day13ExistingListener = Get-NetTCPConnection `
    -LocalPort $day13Port `
    -State Listen `
    -ErrorAction SilentlyContinue
if ($null -ne $day13ExistingListener) {
    throw "端口 $day13Port 已被其他进程占用；不要停止未知进程"
}

if (Test-Path -LiteralPath '.\.venv\Scripts\python.exe') {
    $day13PythonExecutable = (
        Resolve-Path '.\.venv\Scripts\python.exe'
    ).Path
}
else {
    $day13PythonExecutable = (Get-Command python).Source
}

$day13RunTag = Get-Date -Format 'yyyyMMdd-HHmmss'
$day13LogDirectory = Join-Path `
    ([System.IO.Path]::GetTempPath()) `
    "enterprise-rag-day13-$day13RunTag"
New-Item `
    -ItemType Directory `
    -Path $day13LogDirectory `
    -Force | Out-Null

$day13ApiProcess = Start-Day13Api `
    -PythonExecutable $day13PythonExecutable `
    -Port $day13Port `
    -StdoutPath (Join-Path $day13LogDirectory 'api-before.stdout.log') `
    -StderrPath (Join-Path $day13LogDirectory 'api-before.stderr.log')

$day13Health = Invoke-RestMethod `
    -Method Get `
    -Uri "$day13BaseUrl/health"
$day13Health

if ($day13Health.status -ne 'ok') {
    throw 'API 健康检查没有返回 status=ok'
}
if ($day13Health.llm_configured -ne $true) {
    throw 'LLM 未配置；只在本地补充自己的配置，不输出或提交秘密，然后重启受控 API'
}
```

预期结果：连接探针输出 `1`；`/health` 返回 `status="ok"` 且 `llm_configured=true`。首次加载 Embedding 模型可能明显超过普通 API 启动时间，这段外部等待不计入核心时间。

### 3. 回滚并恢复

今天没有迁移，因此不执行数据库 downgrade；对 `e780fe92751b` 回滚会删除三张业务表，不属于 Day 13 的安全验证。

如果执行过程中中断，只做服务级恢复：

```powershell
docker compose ps postgres

if ($null -ne $day13ApiProcess) {
    Stop-Day13Api -Process $day13ApiProcess
}

docker compose up -d postgres
```

重新打开 PowerShell 后，从步骤 1 重新定义函数和变量，再重新建立基线；不要删除数据或 Volume。最后一轮验收结束后，可以精确停止本日启动的 API 进程：

```powershell
Stop-Day13Api -Process $day13ApiProcess
```

### 预期结果

- 今天的 Alembic revision 链和三张表结构完全不变。
- 仅受控 API PID 和 `postgres` 服务发生重启，`postgres_data` Volume 不被删除或替换。
- 系统临时目录中的日志只用于排错，不出现在 `git status --short`。

## 七、验证正常路径

### 启动或准备服务

先按“六、运行数据库迁移或环境命令”启动 PostgreSQL 和端口 `8013` 的受控 API，再按“步骤 2”动态获得 `$day13KnowledgeBaseId`。执行顺序不能省略：固定数据校验 → pytest → 数据库 healthy → API health → 锁定知识库。

当前真实数据库已有合格知识库，预期无需上传。只有步骤 2 明确报告没有合格知识库时，才允许新建一个隔离知识库并各上传一次四份固定 PDF；不得删除旧数据。补建命令如下，成功后继续使用返回的动态 ID：

```powershell
$day13BootstrapBody = @{
    name = "Day13持久化验收-$day13RunTag"
    description = '四份虚构企业制度的重启持久化验收数据'
} | ConvertTo-Json

$day13BootstrapKnowledgeBase = Invoke-RestMethod `
    -Method Post `
    -Uri "$day13BaseUrl/knowledge-bases" `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($day13BootstrapBody))
$day13KnowledgeBaseId = [int]$day13BootstrapKnowledgeBase.id

$day13PdfPaths = @(
    'data\demo_policies\pdfs\员工请假与考勤制度.pdf',
    'data\demo_policies\pdfs\差旅与费用报销制度.pdf',
    'data\demo_policies\pdfs\采购与办公资产管理制度.pdf',
    'data\demo_policies\pdfs\访客与会议室管理办法.pdf'
)

foreach ($day13PdfPath in $day13PdfPaths) {
    curl.exe --fail-with-body --silent --show-error `
        -X POST `
        "$day13BaseUrl/knowledge-bases/$day13KnowledgeBaseId/documents" `
        -F "file=@$day13PdfPath;type=application/pdf"
    if ($LASTEXITCODE -ne 0) {
        throw "上传失败：$day13PdfPath"
    }
}
```

### 执行正常请求或测试

在同一 PowerShell 窗口依次执行“步骤 3”和“步骤 4”的完整代码。关键顺序是：

```text
建立重启前数据库与 HTTP 指纹
→ API PID 重启
→ 不上传，比较 HTTP 稳定字段
→ PostgreSQL 服务重启并等待 ready
→ 不上传，比较数据库与 HTTP 稳定字段
```

### 预期状态码或输出结构

三轮文档列表均应返回 HTTP 200，稳定结构为 4 个 `ready` 文档，ID 是数据库动态值但在重启前后必须保持一致：

```json
[
  {
    "id": "动态正整数；三轮保持不变",
    "knowledge_base_id": "同一个动态正整数",
    "filename": "四份固定 PDF 之一",
    "status": "ready",
    "failure_reason": null,
    "created_at": "动态时间戳；三轮保持不变",
    "updated_at": "动态时间戳；三轮保持不变"
  }
]
```

三轮跨文档请求均应返回 HTTP 200，`answer` 的自然语言措辞可以变化，但 `refused` 必须为 `false`，来源至少同时覆盖两份指定 PDF：

```json
{
  "answer": "LLM 动态回答，不做逐字比较",
  "refused": false,
  "sources": [
    {
      "chunk_id": "动态正整数；三轮保持不变",
      "document_id": "动态正整数；三轮保持不变",
      "filename": "员工请假与考勤制度.pdf 或 差旅与费用报销制度.pdf",
      "page_number": 2,
      "chunk_index": "动态非负整数；三轮保持不变",
      "content": "可核对的原文",
      "score": "动态相似度；不是正确概率"
    }
  ]
}
```

最终 PowerShell 汇总的稳定结构应为：

```text
knowledge_base_id                    : 动态正整数
document_count                       : 4
database_fingerprint_unchanged       : True
api_restart_fingerprint_unchanged    : True
postgres_restart_fingerprint_unchanged : True
cross_document_refused               : False
refusal_question_refused             : True
```

### 为什么它能证明今天已经完成

同一知识库的 4 个 Document、27 个 Chunk、页码与 512 维向量首先由数据库只读指纹固定；API 重启后没有重新上传却能返回相同 Document/Chunk 来源，排除了 Python 进程内存作为权威存储；PostgreSQL 重启后指纹和 HTTP 来源仍一致，证明 Compose 命名 Volume 中的数据被重新加载，并且现有 Engine 通过 `pool_pre_ping` 能在数据库恢复后建立有效连接。

## 八、验证失败和边界路径

### 场景：重启后无答案问题仍必须拒答，不能因为 pgvector 总能返回候选而编造答案

完成 PostgreSQL 重启并确认 healthy 后，继续使用相同 `$day13KnowledgeBaseId`，不上传任何文件：

```powershell
$day13BoundaryResponse = Invoke-Day13Query `
    -BaseUrl $day13BaseUrl `
    -KnowledgeBaseId $day13KnowledgeBaseId `
    -Question '公司的股票期权归属周期和行权条件是什么？' `
    -TopK 3

Assert-Day13RefusalResponse -Response $day13BoundaryResponse
$day13BoundaryResponse | ConvertTo-Json -Depth 5
```

### 预期结果

- HTTP 状态码或异常：HTTP 200；这是业务拒答，不是系统异常。
- 稳定响应：`answer="当前知识库中没有找到足够的信息。"`、`refused=true`、`sources=[]`。
- 数据库应该保留：同一知识库、4 份 `ready` Document、27 个 Chunk、原主键、页码和 512 维向量全部不变。
- 数据库不应该存在：由无答案请求创建的新 KnowledgeBase、Document 或 Chunk；当前查询链路是只读的。
- 响应不能泄露：`.env` 内容、LLM API Key、数据库密码、完整数据库 URL、SQL、Python 堆栈、模型内部请求头或无关来源。

这个边界场景同时证明：服务重启不会绕过当前 `MIN_RELEVANCE_SCORE=0.55`，也不会把 PostgreSQL 中“最接近但仍不足”的 Chunk 当成可靠答案。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `docker compose ps postgres` 不是 healthy | Docker Desktop 未运行、数据库仍启动中或端口冲突 | `docker compose ps postgres`；`docker compose logs --tail 80 postgres` | 先启动 Docker Desktop；只在服务未运行时执行 `docker compose up -d postgres`，等待健康检查，不删除 Volume。 |
| 找不到包含四份固定 ready PDF 的知识库 | 当前数据库不是 Day 9～11 使用的数据库、数据未入库或连接到了不同 Compose 项目 | 运行步骤 2 的只读 SQL；核对 `docker compose ls` 和 `docker compose ps postgres` | 优先切回当前项目原有 Compose 数据库；确实没有时只执行“七、启动或准备服务”的一次性补建命令，不删除旧知识库。 |
| 端口 `8013` 已占用 | 另一个本地服务正在监听 | `Get-NetTCPConnection -LocalPort 8013 -State Listen` | 不停止未知进程；把 `$day13Port` 改成一个明确空闲端口，再重新计算 `$day13BaseUrl` 和日志路径。 |
| API 在 120 秒内未 ready | 首次下载/加载 Embedding 模型、解释器依赖不完整或导入失败 | `Get-Content -LiteralPath (Join-Path $day13LogDirectory 'api-before.stderr.log') -Tail 80` | 首次模型下载保持网络可用并等待；依赖缺失时用同一 Python 执行 `python -m pip install -r requirements.txt`，不要升级固定版本。 |
| `/health` 的 `llm_configured=false` | 三个 LLM 配置项至少一个缺失 | `app/config.py` 和 `/health` 布尔值；不要读取、输出 `.env` | 在本地秘密配置中填写自己的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，精确停止并重启本日 API PID，绝不提交秘密。 |
| API 查询返回 503 `数据库服务暂时不可用` | PostgreSQL 重启尚未 ready，或请求恰好落在停机窗口 | `docker compose ps postgres`；容器内 `pg_isready` | 等 `pg_isready` 成功后重试同一请求；现有 `pool_pre_ping` 应建立新连接，不需要重启 API或重新上传。 |
| API 查询返回 503 `大模型服务未配置` | 回答题检索到了证据，但 LLM 配置不完整 | `/health`；`app/services/database_rag_service.py` | 补齐本地 LLM 配置并重启受控 API；无答案题可能在调用 LLM 前拒答成功，但不能据此宣称完整问答通过。 |
| API 查询返回 502 `问答上游服务暂时不可用` | LLM 网络、限流或供应商错误 | 系统临时目录中的 API 错误日志；供应商控制台 | 保留数据库和来源证据，待上游恢复后重跑跨文档请求；不改 Prompt、阈值或演示文档制造成功。 |
| 跨文档响应只包含一份 PDF | 使用了错误知识库、固定语料被修改、Top-K/阈值或检索实现发生变化 | `data/evaluation/enterprise_questions.json` 的 `cross-trip-01`；Day 11 报告；响应 `sources` | 确认 `top_k=3`、目标知识库包含四份固定 PDF、哈希校验通过；若当前代码变化，先定位差异，不在 Day 13 悄悄改参数。 |
| API 重启后文档 ID 变化或列表为空 | 错用了旧 `/upload` + `/rag/chat` 内存链路，或重启后换了数据库 | 检查请求必须是 `/knowledge-bases/{id}/documents` 和 `/knowledge-bases/{id}/query`；比较数据库指纹 | 始终使用数据库版路由和同一 `$day13KnowledgeBaseId`；不要重新上传掩盖问题。 |
| PostgreSQL 重启后数据库指纹变化 | Compose 项目/Volume 发生切换，或重启期间有其他写入 | `docker compose ls`、`docker volume ls`、两份指纹文本 | 停止继续验收，确认当前项目仍挂载原 `postgres_data`；不要删除 Volume，也不要用空库补数据后宣称持久化成功。 |
| `git status --short` 出现 API 日志 | 日志路径被改到仓库目录 | 查看 `$day13LogDirectory` | 使用计划中的系统临时目录；不要暂存日志。对已出现的单个日志文件，先确认准确路径，再由用户自行决定处理。 |

## 十、检查最终代码差异

执行目录：项目根目录。今天不应出现任何应用代码、迁移、测试、数据库文件或秘密变更：

```powershell
git status --short
git diff -- docs/17天每日学习/Day13.md
git diff -- app/main.py app/db.py app/repositories/chunk_repository.py docker-compose.yml
git diff --check
```

重点检查：

- 只有 `docs/17天每日学习/Day13.md` 是今天允许的新文件；应用与 Compose 的 diff 应为空。
- 计划中没有真实 `.env` 值、API Key、数据库密码、完整连接串、真实内部资料或响应头。
- 没有把系统临时日志、数据库文件、模型缓存和 pytest 缓存纳入 Git。
- 没有删除知识库、Document、Chunk 或 Volume 的命令。
- 所有未执行结果都写成“预期结果”或“待实测”，没有把历史 Day 11 报告冒充为今天的重启证据。

## 十一、Git 提交

今天的核心产物是验收手册；检查 Git diff 边界后即可提交，不要求保存或提交实际响应和日志。如果执行中发现真实失败，先在可选记录中写明卡点，不把失败写成已通过：

```powershell
git status --short
git diff -- docs/17天每日学习/Day13.md
git add docs/17天每日学习/Day13.md
git diff --cached -- docs/17天每日学习/Day13.md
git commit -m "docs: add Day13 restart persistence validation"
```

不要暂存 `.env`、系统临时日志、数据库文件、模型缓存、无关文档或任何应用代码变化。

## 十二、面试高频问题与参考答案

### 问题 1：你怎样证明项目已经从内存 FAISS 升级为持久化 pgvector？

#### 30 秒参考答案

我选定同一个包含四份企业制度 PDF 的知识库，先记录数据库中 4 个 Document、27 个 Chunk、页码和 512 维向量指纹，再记录跨文档查询返回的 Document/Chunk 来源。随后分别重启 FastAPI 进程和 PostgreSQL Compose 服务，两次都不重新上传，仍用同一个知识库 ID 查询。重启后数据库指纹、Document ID 和来源 Chunk 保持一致，说明权威数据来自 PostgreSQL + pgvector 以及持久化 Volume，而不是 Python 全局对象或未保存的 FAISS 索引。

#### 继续追问：只重启 FastAPI 够不够？

不够。只重启 FastAPI 只能排除 Python 进程内状态，不能证明数据库进程重启后数据文件仍能恢复。因此我还重启 `postgres` 服务并保留命名 Volume，等待健康检查通过后，在不重启 API 的情况下再次查询；这也顺便验证 `pool_pre_ping` 能处理连接池中的失效连接。

#### 回答时要引用的项目依据

- `docker-compose.yml` 的 `postgres_data:/var/lib/postgresql/data`。
- `app/db.py` 的应用级 Engine、`pool_pre_ping=True` 和请求 Session。
- `app/main.py` 的 `/knowledge-bases/{id}/documents` 与 `/knowledge-bases/{id}/query`。
- Day 13 的重启前后数据库与 HTTP 指纹；实际执行结果为可选记录。

### 问题 2：为什么重启验收不逐字比较 LLM 的 answer？

#### 30 秒参考答案

LLM 生成文本可能因为采样、供应商实现或措辞产生合理变化，逐字比较会把生成波动误判成持久化失败。我比较的是知识库 ID、Document ID、状态、Chunk ID、文件名、页码和 Chunk 顺序这些稳定字段；同时只要求回答题 `refused=false` 且来源覆盖预期两份文档，无答案题则要求固定拒答和空来源。

#### 继续追问：那怎么防止答案内容完全错误？

持久化验收不单独承担全部质量评估。Day 10 固定了答案要点和证据，Day 11 用 Recall@K、MRR 和拒答指标做质量评测，Day 12 用 pytest 固定来源映射与拒答规则；Day 13 重点确认真实运行时在重启后仍能复用相同数据和来源。必要时可人工核对 answer 是否覆盖固定要点，但不把逐字一致作为指纹。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `cross-trip-01` 和 `unknown-equity-01`。
- `data/evaluation/enterprise_evaluation_report.json` 的逐题来源和指标。
- `tests/test_database_rag_service.py` 对来源 Context 与拒答的稳定断言。

### 问题 3：Docker Volume、容器和数据库之间是什么关系？

#### 30 秒参考答案

容器提供 PostgreSQL 进程和运行环境，数据库表由 PostgreSQL 管理，Volume 把 `/var/lib/postgresql/data` 映射到独立持久化存储。重启容器或服务会终止并重新启动数据库进程，但只要仍挂载同一个 Volume，表数据和向量应继续存在。Day 13 只重启服务并保留 Volume；删除 Volume 会销毁验收对象，既不安全也不能证明持久化。

#### 继续追问：为什么 Day 13 不直接重建一个空数据库？

因为今天要验证的是“已有数据是否跨重启保持”，空库重建会改变问题。干净环境从零执行迁移解决的是可复现性，属于 Day 14；持久化和可复现是两个不同验收维度。

#### 回答时要引用的项目依据

- `docker-compose.yml` 的 PostgreSQL 镜像、healthcheck 和命名 Volume。
- `migrations/versions/751357b5d274_enable_vector_extension.py` 与 `e780fe92751b_create_core_rag_tables.py`。
- Day 13 数据库指纹中的 Document、Chunk、页码和向量维度。

### 问题 4：PostgreSQL 重启后，为什么旧 FastAPI 进程还能恢复查询？

#### 30 秒参考答案

当前应用维护一个 SQLAlchemy Engine，但每个请求创建独立 Session。PostgreSQL 重启会让连接池里的旧连接失效，`pool_pre_ping=True` 会在借出连接前检查可用性并替换断开的连接。因此数据库 healthy 后，同一个 FastAPI 进程的新请求可以重新连库；请求级 Session 结束时会关闭并归还连接，异常时执行 rollback。

#### 继续追问：`pool_pre_ping` 能保证数据库重启期间的请求成功吗？

不能。数据库真正不可用时，请求仍应失败，当前全局 SQLAlchemy 异常处理会返回泛化的 503。`pool_pre_ping` 解决的是服务恢复后避免继续使用死连接，不是让停机窗口消失。验收脚本因此先等待 `pg_isready` 成功，再发下一轮请求。

#### 回答时要引用的项目依据

- `app/db.py` 的 `create_engine(..., pool_pre_ping=True)`、`SessionLocal` 和 `get_db_session()`。
- `app/main.py` 的 `SQLAlchemyError` 全局处理器，响应为 `数据库服务暂时不可用`。
- Day 13 中 PostgreSQL 重启后不重启 API 的第三轮查询。

### 问题 5：端到端验收和自动化测试各自发现什么问题？

#### 30 秒参考答案

自动化测试适合快速、可重复地固定业务规则。当前项目的真实 pgvector 集成测试覆盖知识库隔离、`ready` 状态过滤、Top-K 排序和事务回滚，假依赖单元测试覆盖来源构造与低分拒答。端到端验收则覆盖 Uvicorn、HTTP 编解码、真实 Embedding/LLM、连接池、PostgreSQL 进程和 Volume 组合后的行为，尤其能发现重启后数据或连接恢复问题。

#### 继续追问：为什么不把 Day 13 全部写成 pytest？

可以在后续自动化部分流程，但数据库服务重启涉及宿主机 Docker、端口和外部 LLM，直接放进普通测试套件会让测试慢、环境耦合强且不稳定。当前做法是先用 7 个快速测试守住代码规则，再用边界明确的 PowerShell 验收脚本做真实系统验证，职责更清楚。

#### 回答时要引用的项目依据

- `tests/conftest.py` 的外层事务和结束回滚。
- `tests/test_chunk_repository_integration.py` 的真实 pgvector 查询。
- `tests/test_database_rag_service.py` 和 `tests/test_models.py`。
- Day 13 的受控 Uvicorn PID、Compose 重启和三轮指纹比较。

## 十三、今天的完整数据流

### 正常路径

```text
Day 9 四份固定 PDF（只作为版本依据，不重复上传）
→ PostgreSQL 已有 KnowledgeBase + 4 个 ready Document + 27 个 Chunk + 512 维 Vector
→ 只读 SQL 选择同一个知识库 ID并生成数据库指纹
→ FastAPI GET 文档列表
→ POST 数据库版 query
→ RetrievalService 生成 Query Embedding
→ ChunkRepository 在同一知识库的 ready 文档中执行 pgvector Top-K
→ DatabaseRAGService 使用 0.55 阈值筛选来源
→ 跨文档题调用 LLM，返回 answer + 两份文档来源
→ 无答案题在 LLM 前拒答，返回空来源
→ 停止并重启受控 Uvicorn PID
→ 不上传，使用同一知识库 ID重复查询并比较 HTTP 稳定字段
→ docker compose restart postgres，postgres_data Volume 保留
→ pg_isready 成功
→ 原 FastAPI 进程通过 pool_pre_ping 获得有效连接
→ 不上传，再次比较数据库与 HTTP 稳定字段
→ 三轮一致，形成持久化验收闭环
```

### 失败路径

```text
PostgreSQL 正在重启或尚未 ready
→ SQLAlchemy 无法获得有效连接
→ FastAPI 返回泛化 503，不泄露连接串或密码
→ 不写入、不重新上传、不删除数据
→ 等待 pg_isready 成功
→ pool_pre_ping 替换失效连接
→ 使用同一知识库 ID重新执行只读查询

无答案问题
→ pgvector 仍可能返回最接近的候选 Chunk
→ 候选分数低于 0.55
→ DatabaseRAGService 在调用 LLM 前拒答
→ HTTP 200 + refused=true + 固定拒答 + sources=[]
→ 数据库记录保持不变
```

## 十四、完成标准

```text
[ ] 能解释 FastAPI 进程、PostgreSQL 服务和 Docker Volume 的三种生命周期差异
[ ] 能说明为什么重启验收比较 Document/Chunk/来源稳定字段，而不逐字比较 LLM answer
[ ] 已确认 Day 12 全套 7 个 pytest 的可执行命令和预期退出码，实际运行与记录可选
[ ] 已提供动态定位同一个四文档 ready 知识库的只读 SQL；当前生成依据为知识库 ID 20、4 个 Document、27 个 Chunk 和 512 维向量
[ ] 已提供重启前数据库指纹、文档列表、跨文档来源和无答案拒答的完整验证命令与预期结果
[ ] 已提供精确 PID 的 API 重启命令；重启后不调用上传接口，并比较同一知识库的稳定字段
[ ] 已提供保留 postgres_data Volume 的 PostgreSQL 重启、健康等待、数据库指纹和 HTTP 恢复验证命令
[ ] 已提供重启后无答案问题的失败/边界验证，预期为固定拒答、空来源且数据库零写入
[ ] 能不看代码复述“已有 PDF 数据 → 重启前基线 → API 重启 → PostgreSQL 重启 → 同一来源恢复”的完整数据流
[ ] git diff 只包含 Day13.md，不包含秘密、日志、数据库文件或无关修改；核心手册完成后可执行边界清晰的 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 重启前知识库 ID / Document 数 / Chunk 数：可选，不要求填写
- API 重启后指纹对比：可选，不要求填写
- PostgreSQL 重启后指纹对比：可选，不要求填写
- 跨文档来源与拒答结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
