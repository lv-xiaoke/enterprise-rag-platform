# Day 16：录制三分钟演示并编写独立简历条目

今天将直接完成一套可重复执行的三分钟企业 RAG 演示流程和一条独立简历项目经历，使当前项目获得可展示、可核对的求职材料，并为面试中的项目介绍、工程取舍和量化结果追问提供真实依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：三分钟演示视频及与视频、README、评测报告事实一致的独立简历项目条目  
> 当前真实状态：未开始  
> 对应总体安排：Day 16

## 一、今天完成后的项目变化

### 升级前

```text
README、架构图和评测报告已经说明项目
→ 但没有一条固定、计时、可重复的现场演示路径
→ 创建知识库、上传 4 份 PDF、跨文档问答、拒答和重启恢复仍需临场拼命令
→ 没有独立的最终简历条目及逐项证据映射
→ 面试时容易超时、漏讲来源或把离线指标说成生产结论
```

### 升级后

```text
固定 PowerShell 演示脚本
→ 创建唯一知识库并上传 4 份虚构 PDF
→ 展示 4 个 ready 文档
→ 展示跨两份制度的回答与来源
→ 展示无答案拒答和空来源
→ 重启 API 后复用同一知识库和 Document ID
→ 最后展示固定评测指标与限制
→ 形成约三分钟视频和独立、可追溯的简历项目条目
```

### 今天在完整项目中的位置

- 所属阶段：求职输出。
- 所属链路：把已经完成的项目实现和 Day 15 的可信说明转化为可观看演示与可投递表达。
- 今天的输入：当前 Docker Compose 环境、4 份虚构制度 PDF、企业知识库 API、Day 13 重启持久化能力、Day 15 的 README/架构图/评测报告及结构化源报告。
- 今天的输出：`scripts/run_enterprise_rag_demo.ps1`、`docs/demo-script.md`、`docs/resume-project-entry.md` 和本地 `artifacts/demo/enterprise-rag-demo.mp4`。
- 下一天为什么需要它：Day 17 将围绕固定演示流程和简历表述连续复现两次，并用同一证据回答模拟面试追问。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` Day 1～Day 15 的核心产物、用户完成标记和匹配提交均存在；最新提交是 `f5e3d2a Day15`。
- `[当前事实]` 生成本计划前 `git status --short` 无文件输出，只有 Git 无法访问用户级 ignore 文件的环境警告；没有识别到未提交工作区修改。
- `[当前事实]` 根目录 `README.md` 已给出项目定位、架构、Compose 启动、多文档操作、测试、评测和限制。
- `[当前事实]` `docs/architecture.md` 已提供 API、Service、Repository、SQLAlchemy 与 PostgreSQL/pgvector 的分层图，以及入库和问答两条时序。
- `[当前事实]` 当前数据库版 API 可以创建知识库、上传 PDF、列出文档、按知识库问答并返回来源；`top_k` 的合法范围是 `1..10`。
- `[当前事实]` 4 份演示 PDF 都是两页虚构资料，覆盖考勤、差旅报销、采购资产和访客会议室场景，不含真实企业数据。
- `[当前事实]` `cross-procurement-payment-01` 在已提交报告的 Top-3 中同时返回《差旅与费用报销制度》和《采购与办公资产管理制度》，该题 Recall 为 `1.0`，适合作为跨文档演示题。
- `[当前事实]` 无答案题“公司的股票期权归属周期和行权条件是什么？”应在当前阈值下返回固定拒答、`refused=true` 和空来源。
- `[当前事实]` 固定评测包含 12 道可回答题、6 道无答案题；Top-3 Recall 为 `0.972222`、MRR 为 `0.958333`，36 个预热检索样本 P95 为 `15.2546 ms`。
- `[当前事实]` 离线实验推荐 `Top-K=3、threshold=0.65`，但当前生产代码仍使用阈值 `0.55`；演示和简历必须清楚区分二者。
- `[当前事实]` 当前测试代码收集为 7 个 pytest case，覆盖输入边界、来源、拒答、知识库隔离、文档状态、Top-K 和排序。
- `[当前事实]` Git remote 是 `https://github.com/lv-xiaoke/enterprise-rag-platform.git`，可以作为简历项目链接。

### 仍然缺少

- `[当前事实]` 当前没有 `scripts/run_enterprise_rag_demo.ps1`，演示操作尚未固化为带断言的分步命令。
- `[当前事实]` 当前没有 `docs/demo-script.md`，没有精确到时间段、画面、操作、口述和剪辑边界的三分钟脚本。
- `[当前事实]` 当前没有 `docs/resume-project-entry.md`，Day 15 的技术事实尚未压缩为独立简历条目和证据映射。
- `[当前事实]` `.gitignore` 尚未忽略 `artifacts/demo/`，直接把录屏保存到仓库可能误暂存 MP4 和本地状态文件。
- `[当前事实]` 当前不存在可核对的 Day 16 演示视频；不得提前声称已经录制或已经上传公开链接。

### 待实测

- `[待实测]` 本机 Compose 环境、Embedding 缓存和 LLM 配置能否在录制前一次跑完整个演示脚本。
- `[待实测]` 创建新知识库并上传 4 份 PDF 的实际耗时；等待片段可剪掉，但不能替换或伪造输出。
- `[待实测]` 当前 LLM 对跨文档题的具体措辞；验收比较 `refused`、来源文件和稳定 ID，不要求逐字一致。
- `[待实测]` API 容器重启后的实际恢复时间；模型加载期间健康检查可能需要数分钟。
- `[待实测]` 最终视频时长、声音、字号和秘密遮挡是否符合三分钟演示要求。

### 需要保护的用户修改

- 当前工作区没有已识别的未提交修改；只操作今天文件清单，不读取或修改被生成器明确禁止的 `docs/简历.md`，不处理 Day 15 提交中其他历史文件，也不覆盖用户现有求职材料。

## 三、今天必须理解的核心知识

### 1. 演示要形成“操作—结果—证据”闭环

- 一句话解释：每个画面都应回答正在证明什么，而不是只展示终端滚动或朗读代码。
- 在当前项目中的职责：创建与上传证明入库，跨文档来源证明检索范围和追溯，拒答证明边界，重启后复用相同 ID 证明持久化，报告证明效果有量化基线。
- 与其他组件的关系：演示脚本调用现有 HTTP API；README 和架构图解释设计；评测报告说明结果范围。
- 容易混淆的点：HTTP 200 只能证明请求成功，不能单独证明来源正确、没有跨库或数据已经跨重启保留。
- 面试一句话：我的三分钟演示不是功能列表，而是按入库、检索、拒答、持久化和评测依次给出可观察证据。

### 2. 稳定断言与动态输出必须分开

- 一句话解释：知识库 ID、Document ID、Chunk ID、LLM 措辞和运行时间会变化，但状态、来源文件集合、拒答标记和评测口径可以稳定核对。
- 在当前项目中的职责：脚本把本次动态 ID 保存到本地状态文件，重启前后复用它；跨文档题断言两个目标文件都出现；拒答断言来源为空。
- 与其他组件的关系：数据库负责稳定持久化 ID，LLM 只负责基于 Context 生成措辞，评测 JSON 固定历史实验结果。
- 容易混淆的点：不能把某次视频里的具体 Chunk ID 写成系统固定值，也不能因 LLM 改写句子就误判持久化失败。
- 面试一句话：我对稳定业务字段做自动断言，对 LLM 文本只核对是否基于正确来源，不把非确定性输出当成数据库指纹。

### 3. 简历指标必须说明测量对象

- 一句话解释：简历上的百分比和延迟只有绑定数据规模、指标名称和计时范围才可信。
- 在当前项目中的职责：可以写 4 份 PDF、18 道题、Top-3 Recall 97.22%、MRR 95.83% 和预热检索 P95 15.25 ms，但不能写“系统准确率 97.22%”或“接口 P95 15.25 ms”。
- 与其他组件的关系：指标来自 `data/evaluation/enterprise_evaluation_report.json`，摘要解释位于 `docs/evaluation-report.md`，并且评测不调用 LLM。
- 容易混淆的点：离线推荐阈值 `0.65` 不是当前生产阈值，检索延迟也不包含 HTTP 和 LLM 生成。
- 面试一句话：我报告的是固定 4 文档、18 题上的证据检索指标和预热检索延迟，不把它外推为生产答案准确率或 SLA。

### 4. 视频与 Git 的安全边界

- 一句话解释：演示视频、状态文件和真实环境配置属于本地产物，脚本与说明文档才适合进入仓库。
- 在当前项目中的职责：`artifacts/demo/` 被忽略，录屏中只显示 `/health` 的配置布尔值，不打开 `.env`，不展示 API Key、数据库密码、完整连接串或真实企业资料。
- 与其他组件的关系：`.env.example` 公开变量名和示例，Compose 使用本地 `.env`，演示资料来自仓库内虚构 PDF。
- 容易混淆的点：`.gitignore` 能降低误提交风险，但不能替代录屏前的窗口清理、通知关闭和最终逐帧复核。
- 面试一句话：我把可复用脚本和文档提交到 Git，把包含本机画面的 MP4 与运行状态留在忽略目录，并在录制前后做秘密检查。

## 四、升级涉及的文件

| 文件                                       | 操作          | 作用                                |
| ---------------------------------------- | ----------- | --------------------------------- |
| `.gitignore`                             | 末尾追加明确目录    | 忽略本地视频、录屏状态和临时演示产物                |
| `scripts/run_enterprise_rag_demo.ps1`    | 新建          | 固化准备、跨文档问答、拒答和重启后核对四个阶段，并对稳定结果做断言 |
| `docs/demo-script.md`                    | 新建          | 固定约三分钟的画面、操作、口述、时间和安全检查           |
| `docs/resume-project-entry.md`           | 新建          | 提供可直接放入简历的独立项目条目及逐项证据映射           |
| `docs/17天每日学习/Day16.md`                  | 保留并按需更新执行记录 | 今天的完整升级手册、验证、排错、提交边界和面试答案         |
| `artifacts/demo/enterprise-rag-demo.mp4` | 本地生成，不提交    | 最终三分钟演示视频；文件名固定，实际录制内容动态          |

### 今日不做

- 不修改数据库表、迁移、API、Service、Repository、Embedding、LLM 或检索阈值；这不是录制日的功能开发任务。
- 不把离线推荐阈值 `0.65` 写成当前已部署配置。
- 不读取、修改或复用 `docs/简历.md`；独立条目写入新文件，用户之后自行合并到真实简历。
- 不在仓库提交 MP4、真实 `.env`、演示状态 JSON 或录屏软件工程文件。
- 不录制长篇代码教学，也不提前执行 Day 17 的两轮模拟面试复盘。

## 五、按顺序完成项目升级

### 步骤 1：隔离本地录屏产物（建议 3 分钟）

**目标**

避免把 MP4、本次动态数据库 ID 或录屏软件临时文件误提交到仓库。

**修改位置**

- 文件：`.gitignore`
- 定位：文件末尾的 `data/*.db-*` 与 `data/documents/` 之后
- 操作：在末尾追加下面完整配置段

**复制下面的完整配置**

```gitignore

# Day 16 本地演示视频与运行状态
artifacts/demo/
```

**这段配置怎样工作**

- 输入：本地 `artifacts/demo/` 下的视频、状态 JSON 和录屏临时产物。
- 输出：Git 默认不跟踪该目录内容。
- 调用谁：Git ignore 规则。
- 被谁调用：后续 `git status`、`git add` 和录屏保存过程。
- 正常路径：脚本可以创建状态文件，录屏软件可以保存 MP4，但 `git status --short` 不显示它们。
- 失败路径：如果文件此前已被 Git 跟踪，ignore 不会自动取消跟踪；今天不要使用破坏性命令，应先停止并核对历史。

**完成本步骤后的预期状态**

`.gitignore` 只新增一个明确的本地演示目录规则，没有扩大到整个 `artifacts/` 或所有视频文件。

### 步骤 2：新建可断言的演示脚本（建议 15 分钟）

**目标**

把现场演示拆成 `prepare`、`answerable`、`refusal` 和 `verify-after-restart` 四个可单独运行的阶段，减少临场输入错误。

**修改位置**

- 文件：`scripts/run_enterprise_rag_demo.ps1`
- 定位：新文件
- 操作：复制下面的完整文件内容

**复制下面的完整代码**

```powershell
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "prepare",
        "answerable",
        "refusal",
        "verify-after-restart"
    )]
    [string]$Mode,

    [string]$BaseUrl = "http://127.0.0.1:8000",

    [string]$StatePath = "artifacts\demo\state.json"
)

$ErrorActionPreference = "Stop"
$expectedDocumentNames = @(
    "员工请假与考勤制度.pdf",
    "差旅与费用报销制度.pdf",
    "采购与办公资产管理制度.pdf",
    "访客与会议室管理办法.pdf"
)

function ConvertTo-Utf8JsonBytes {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 8
    return [System.Text.Encoding]::UTF8.GetBytes($json)
}

function Get-DemoState {
    if (-not (Test-Path -LiteralPath $StatePath)) {
        throw "演示状态文件不存在，请先运行 -Mode prepare：$StatePath"
    }

    return Get-Content -LiteralPath $StatePath -Raw |
        ConvertFrom-Json
}

function Wait-ForHealthyApi {
    param(
        [int]$TimeoutSeconds = 300
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod `
                -Uri "$BaseUrl/health" `
                -Method Get `
                -TimeoutSec 10

            if (
                $health.status -eq "ok" -and
                $health.database_connected -eq $true
            ) {
                return $health
            }
        }
        catch {
            Write-Host "等待 API 与 Embedding 模型就绪……"
        }

        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    throw "API 未在 $TimeoutSeconds 秒内恢复健康"
}

function Invoke-KnowledgeBaseQuery {
    param(
        [Parameter(Mandatory = $true)]
        [int]$KnowledgeBaseId,

        [Parameter(Mandatory = $true)]
        [string]$Question
    )

    $body = ConvertTo-Utf8JsonBytes -Value @{
        question = $Question
        top_k = 3
    }

    return Invoke-RestMethod `
        -Uri "$BaseUrl/knowledge-bases/$KnowledgeBaseId/query" `
        -Method Post `
        -ContentType "application/json; charset=utf-8" `
        -Body $body `
        -TimeoutSec 120
}

switch ($Mode) {
    "prepare" {
        $health = Wait-ForHealthyApi
        if ($health.llm_configured -ne $true) {
            throw (
                "LLM 未配置。只在本地补充自己的三个 LLM 配置，" +
                "不要打开、打印或提交 .env。"
            )
        }

        $runTag = Get-Date -Format "yyyyMMdd-HHmmss"
        $createBody = ConvertTo-Utf8JsonBytes -Value @{
            name = "三分钟演示制度库-$runTag"
            description = "仓库内 4 份公开虚构制度 PDF"
        }

        $knowledgeBase = Invoke-RestMethod `
            -Uri "$BaseUrl/knowledge-bases" `
            -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body $createBody `
            -TimeoutSec 30

        Write-Host "已创建知识库 ID=$($knowledgeBase.id)"

        $pdfFiles = @(
            Get-ChildItem `
                -LiteralPath "data\demo_policies\pdfs" `
                -Filter "*.pdf"
        )
        if ($pdfFiles.Count -ne 4) {
            throw "演示目录必须恰好包含 4 份 PDF，当前为 $($pdfFiles.Count)"
        }

        foreach ($pdfFile in $pdfFiles) {
            Write-Host "上传：$($pdfFile.Name)"
            $uploadOutput = & curl.exe `
                --fail-with-body `
                --silent `
                --show-error `
                -X POST `
                -F "file=@$($pdfFile.FullName);type=application/pdf" `
                "$BaseUrl/knowledge-bases/$($knowledgeBase.id)/documents"

            if ($LASTEXITCODE -ne 0) {
                throw "上传失败：$($pdfFile.Name)"
            }
            if ([string]::IsNullOrWhiteSpace($uploadOutput)) {
                throw "上传接口没有返回响应：$($pdfFile.Name)"
            }
        }

        $documents = @(
            Invoke-RestMethod `
                -Uri "$BaseUrl/knowledge-bases/$($knowledgeBase.id)/documents" `
                -Method Get `
                -TimeoutSec 30
        )

        if ($documents.Count -ne 4) {
            throw "预期 4 个 Document，实际为 $($documents.Count)"
        }
        if (@($documents | Where-Object status -ne "ready").Count -ne 0) {
            throw "存在非 ready 文档，不能开始录制"
        }

        $actualNames = @($documents.filename | Sort-Object)
        $expectedNames = @($expectedDocumentNames | Sort-Object)
        if (
            (Compare-Object $expectedNames $actualNames).Count -ne 0
        ) {
            throw "数据库中的文件名与固定演示语料不一致"
        }

        $stateDirectory = Split-Path -Parent $StatePath
        if (
            -not [string]::IsNullOrWhiteSpace($stateDirectory) -and
            -not (Test-Path -LiteralPath $stateDirectory)
        ) {
            New-Item `
                -ItemType Directory `
                -Path $stateDirectory `
                -Force | Out-Null
        }

        $state = [ordered]@{
            base_url = $BaseUrl
            knowledge_base_id = [int]$knowledgeBase.id
            knowledge_base_name = $knowledgeBase.name
            created_at = (Get-Date).ToString("o")
            documents = @(
                $documents |
                    Sort-Object id |
                    Select-Object id, filename, status
            )
        }
        $state |
            ConvertTo-Json -Depth 8 |
            Set-Content -LiteralPath $StatePath -Encoding UTF8

        [ordered]@{
            demo_ready = $true
            knowledge_base_id = $knowledgeBase.id
            document_count = $documents.Count
            ready_count = @(
                $documents | Where-Object status -eq "ready"
            ).Count
            state_path = $StatePath
        } | Format-List
    }

    "answerable" {
        $state = Get-DemoState
        $result = Invoke-KnowledgeBaseQuery `
            -KnowledgeBaseId $state.knowledge_base_id `
            -Question (
                "办公设备到货后，要完成资产登记并进入财务付款，" +
                "需要经过哪些关键动作和凭证？"
            )

        if ($result.refused -ne $false) {
            throw "跨文档可回答题被错误拒答"
        }

        $sourceNames = @($result.sources.filename | Sort-Object -Unique)
        $requiredSourceNames = @(
            "差旅与费用报销制度.pdf",
            "采购与办公资产管理制度.pdf"
        )
        foreach ($requiredName in $requiredSourceNames) {
            if ($requiredName -notin $sourceNames) {
                throw "跨文档来源缺失：$requiredName"
            }
        }

        [ordered]@{
            question = (
                "办公设备到货后，要完成资产登记并进入财务付款，" +
                "需要经过哪些关键动作和凭证？"
            )
            refused = $result.refused
            answer = $result.answer
            sources = @(
                $result.sources |
                    Select-Object `
                        filename,
                        page_number,
                        chunk_id,
                        score
            )
        } | ConvertTo-Json -Depth 8
    }

    "refusal" {
        $state = Get-DemoState
        $result = Invoke-KnowledgeBaseQuery `
            -KnowledgeBaseId $state.knowledge_base_id `
            -Question "公司的股票期权归属周期和行权条件是什么？"

        if ($result.refused -ne $true) {
            throw "无答案问题没有拒答"
        }
        if (@($result.sources).Count -ne 0) {
            throw "拒答响应不应包含来源"
        }
        if ($result.answer -ne "当前知识库中没有找到足够的信息。") {
            throw "拒答文本与当前服务约定不一致"
        }

        [ordered]@{
            question = "公司的股票期权归属周期和行权条件是什么？"
            refused = $result.refused
            answer = $result.answer
            source_count = @($result.sources).Count
        } | ConvertTo-Json -Depth 5
    }

    "verify-after-restart" {
        $health = Wait-ForHealthyApi
        $state = Get-DemoState
        $documents = @(
            Invoke-RestMethod `
                -Uri (
                    "$BaseUrl/knowledge-bases/" +
                    "$($state.knowledge_base_id)/documents"
                ) `
                -Method Get `
                -TimeoutSec 30
        )

        $beforeIds = @($state.documents.id | ForEach-Object { [int]$_ })
        $afterIds = @($documents.id | ForEach-Object { [int]$_ })
        if ((Compare-Object $beforeIds $afterIds).Count -ne 0) {
            throw "API 重启后 Document ID 发生变化"
        }
        if (@($documents | Where-Object status -ne "ready").Count -ne 0) {
            throw "API 重启后存在非 ready 文档"
        }

        $result = Invoke-KnowledgeBaseQuery `
            -KnowledgeBaseId $state.knowledge_base_id `
            -Question (
                "办公设备到货后，要完成资产登记并进入财务付款，" +
                "需要经过哪些关键动作和凭证？"
            )
        if ($result.refused -ne $false) {
            throw "API 重启后可回答题被错误拒答"
        }

        $sourceNames = @($result.sources.filename | Sort-Object -Unique)
        foreach ($requiredName in @(
            "差旅与费用报销制度.pdf",
            "采购与办公资产管理制度.pdf"
        )) {
            if ($requiredName -notin $sourceNames) {
                throw "API 重启后跨文档来源缺失：$requiredName"
            }
        }

        [ordered]@{
            api_healthy = $true
            same_knowledge_base_id = [int]$state.knowledge_base_id
            document_ids_unchanged = $true
            ready_document_count = $documents.Count
            query_refused = $result.refused
            source_documents = $sourceNames
        } | ConvertTo-Json -Depth 6
    }
}
```

**这段代码怎样工作**

- 输入：现有 API、4 份固定 PDF、本地 LLM 配置和 `-Mode` 参数。
- 输出：本地状态 JSON、四文档 ready 摘要、跨文档答案及来源、拒答摘要或重启后指纹摘要。
- 调用谁：`/health`、知识库创建、文档上传、文档列表和知识库问答 API，以及 `curl.exe`。
- 被谁调用：预演、正式录屏和 Day 17 的重复演示。
- 正常路径：每个阶段只展示稳定字段并在不满足预期时抛错，动态 ID 从状态文件复用。
- 失败路径：API 不健康、LLM 未配置、PDF 数量错误、非 ready 文档、跨文档来源缺失、拒答错误或重启后 ID 变化都会立即中止，不继续录制伪成功结果。

**完成本步骤后的预期状态**

脚本可以被 PowerShell 解析，且本地状态只写入被 Git 忽略的 `artifacts/demo/state.json`；它不读取或打印 `.env`。

### 步骤 3：新建三分钟录制脚本（建议 10 分钟）

**目标**

把每个时间段的画面、命令、口述重点和剪辑规则固定下来，使视频围绕证据而不是围绕代码滚动。

**修改位置**

- 文件：`docs/demo-script.md`
- 定位：新文件
- 操作：复制下面的完整文件内容

**复制下面的完整内容**

````markdown
# Enterprise RAG Platform 三分钟演示脚本

> 目标时长：2 分 40 秒～3 分 10 秒  
> 演示语料：仓库内 4 份公开虚构制度 PDF  
> 演示主线：架构 → 多文档入库 → 跨文档来源 → 无答案拒答 → API 重启恢复 → 评测结论

## 录制前准备

1. 关闭通知、邮箱、聊天软件、密码管理器和无关终端。
2. 不打开 `.env`，不显示 API Key、数据库密码、完整连接串或真实企业资料。
3. 把终端字号调到观众能看清，预先打开 README 架构图和 `docs/evaluation-report.md`。
4. 确认 Compose 服务就绪：

```powershell
docker compose up --build -d
docker compose ps --all
```

5. 在正式录制前完整预演一次；预演产生的知识库可以保留，不删除数据库数据或 Volume。
6. 正式录制时重新执行 `prepare`，让视频真实展示创建知识库和上传 4 份 PDF。

## 0:00～0:25：业务目标与架构

**画面**：根目录 README 的标题、核心能力和架构图。

**口述**：

> 这是我独立实现的企业制度与 SOP RAG 后端。它支持多知识库、多 PDF 入库，把页码、原文和 512 维向量持久化到 PostgreSQL + pgvector，并在指定知识库的 ready 文档内检索。系统分为 FastAPI、Service、Repository 和数据库四层；今天我用一条真实流程展示入库、跨文档来源、拒答和重启恢复。

## 0:25～1:10：创建知识库并上传四份 PDF

**画面**：PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode prepare
```

**口述**：

> 脚本先检查数据库和 LLM 是否就绪，然后创建一个本次演示专用知识库，上传考勤、差旅报销、采购资产和访客会议室四份虚构 PDF。每份 PDF 都经过按页解析、200/40 重叠切块和 BGE 512 维向量化。只有四个 Document 全部进入 ready 状态，脚本才会继续。

**屏幕上必须看见**：

- 动态知识库 ID。
- `document_count = 4`。
- `ready_count = 4`。
- 不出现 `.env` 内容和任何秘密。

## 1:10～1:45：跨文档问答与来源追溯

**画面**：同一 PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode answerable
```

**口述**：

> 这个问题同时需要采购验收、资产登记和财务付款凭证。查询向量在 SQL 层限定当前知识库和 ready 状态，按余弦相似度取 Top-3。回答之外，我返回文档名、页码、Chunk ID 和分数；脚本还会断言来源同时覆盖《采购与办公资产管理制度》和《差旅与费用报销制度》。分数表示语义相似度，不是答案正确概率。

**屏幕上必须看见**：

- `refused = false`。
- 两个目标 PDF 文件名。
- 页码、Chunk ID 和 score。

## 1:45～2:05：无答案拒答

**画面**：同一 PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode refusal
```

**口述**：

> 知识库没有股票期权制度。最高候选证据不足时，系统会在调用 LLM 前拒答，返回固定文本和空来源，避免模型利用不相关资料编造归属周期。

**屏幕上必须看见**：

- `refused = true`。
- `source_count = 0`。
- 固定拒答文本。

## 2:05～2:35：API 重启后复用同一数据

**画面**：PowerShell 终端。

```powershell
docker compose restart api
.\scripts\run_enterprise_rag_demo.ps1 -Mode verify-after-restart
```

**口述**：

> 现在只重启 API，不重新上传。脚本读取本次演示保存的动态知识库 ID，等待健康检查恢复，再比较重启前后的 Document ID，并重新执行跨文档查询。相同 ID、四个 ready 文档和相同来源类型说明权威数据来自 PostgreSQL + pgvector，而不是 FastAPI 进程内存。数据库进程与 Volume 的重启持久化已经在独立验收中验证。

**屏幕上必须看见**：

- `document_ids_unchanged = true`。
- `ready_document_count = 4`。
- `query_refused = false`。
- 两个目标来源文件名。

## 2:35～3:00：评测与边界

**画面**：`docs/evaluation-report.md` 的结论摘要和失败案例。

**口述**：

> 我用四份两页虚构制度和十八道固定问题评测检索，其中十二道可回答、六道无答案。Top-3 Recall 是 97.22%，MRR 是 95.83%；三十六个预热后的 Query Embedding 加 pgvector 检索样本 P95 是 15.25 毫秒。离线实验推荐阈值 0.65，但生产代码仍是 0.55，我没有把建议包装成已上线配置。当前限制包括只支持文本型 PDF、同步入库、无认证、没有 ANN 索引，也没有把检索延迟说成端到端 SLA。

## 剪辑边界

- 可以剪掉模型加载、四个文件依次处理和 API 重启健康等待中的静默时间。
- 不得替换请求结果、拼接其他知识库输出、修改来源或隐藏失败后假装一次成功。
- 如果断言失败，停止录制，按错误修复后从头重新录；不要只剪掉报错。
- 最终视频保存为 `artifacts/demo/enterprise-rag-demo.mp4`，不要加入 Git。

## 录制后检查

```text
[ ] 视频时长在 2:40～3:10
[ ] 能听清业务目标、两条链路和关键取舍
[ ] 展示 4 个 ready 文档
[ ] 跨文档题包含两个真实来源文件名和页码
[ ] 无答案题为 refused=true 且 sources 为空
[ ] API 重启后使用同一知识库 ID，未重新上传
[ ] 指标口径明确，不把 0.65 说成已部署
[ ] 没有 .env、API Key、数据库密码、完整 URL 凭据、通知或个人隐私
```
````

**这段内容怎样工作**

- 输入：步骤 2 的四个脚本阶段、README 架构图和评测报告。
- 输出：一条约三分钟、每段都有画面与证据要求的录制路线。
- 调用谁：PowerShell 脚本、Docker Compose、README 和评测报告。
- 被谁调用：录屏者和 Day 17 模拟演示。
- 正常路径：按时间推进并展示稳定断言结果。
- 失败路径：任何断言失败都停止并重录，剪辑只能去掉等待，不能制造成功。

**完成本步骤后的预期状态**

用户无需临场组织语言或挑选问题；脚本在三分钟内覆盖总体安排要求的架构、创建、上传、跨文档问答、来源、拒答、重启和评测。

### 步骤 4：新建独立简历项目条目（建议 7 分钟）

**目标**

把当前项目压缩为一个与企业办公 Agent 项目边界清楚、数字可追溯、能够展开追问的简历条目。

**修改位置**

- 文件：`docs/resume-project-entry.md`
- 定位：新文件
- 操作：复制下面的完整文件内容；不要自动合并到任何现有简历

**复制下面的完整内容**

````markdown
# 企业 RAG 项目简历条目

## 可直接使用版本

### 2026.08–2026.09｜企业制度与 SOP 智能知识库 RAG 后端｜独立开发

**技术栈**：Python、FastAPI、PostgreSQL、pgvector、SQLAlchemy、Alembic、BGE Embedding、pytest、Docker Compose  
**项目地址**：<https://github.com/lv-xiaoke/enterprise-rag-platform>

- 基于 FastAPI、BGE 和 PostgreSQL/pgvector 打通多知识库、多 PDF 的解析、`200/40` 重叠切分、512 维向量持久化、知识库范围 Top-K 检索和 LLM 问答，返回文档名、页码、Chunk 原文与相似度来源。
- 设计 `KnowledgeBase → Document → Chunk` 数据模型和 `processing/ready/failed` 状态边界，以 SQL 层知识库/状态过滤、事务回滚和阈值前置拒答避免跨库结果及不可检索半成品；使用 Alembic 与 Docker Compose 固化迁移和重启恢复流程。
- 建立 4 份两页虚构制度、18 道固定问题的离线评测：Top-3 Recall@3 为 `97.22%`、MRR@3 为 `95.83%`，36 个预热后 Query Embedding + pgvector 检索样本 P95 为 `15.25 ms`；编写 7 个 pytest case 覆盖输入边界、来源、拒答、知识库隔离、文档状态、Top-K 与排序。

## 面试时必须主动说明的指标口径

- `97.22%` 是固定小数据集上的证据 Recall@3，不是最终 LLM 答案准确率。
- `15.25 ms` 只包括预热后的 Query Embedding + pgvector 查询，不包括模型初始化、HTTP 和 LLM 生成，不是生产 SLA。
- 离线实验推荐 `Top-K=3、threshold=0.65`；当前生产代码仍使用阈值 `0.55`，不能说 `0.65` 已上线。
- 语料全部为公开虚构资料；系统当前只支持文本型 PDF，并且没有认证、异步任务、ANN 索引或大规模并发验证。

## 与企业办公 Agent 项目的边界

```text
本项目重点：数据模型、持久化、范围过滤、来源追溯、拒答、评测、测试和复现
Agent 项目重点：意图路由、工具选择、多步骤任务、结构化业务数据调用和交互
```

不要在两个项目中重复声称相同的 RAG、切分和 Top-K 成果；本条目回答的是“企业知识怎样可靠入库、检索、评测并跨重启保留”。

## 逐项证据映射

| 简历表述 | 仓库依据 |
| --- | --- |
| 多知识库、多文档 API | `app/main.py`、`app/models.py` |
| 三层数据模型与 `vector(512)` | `app/orm_models.py`、`migrations/versions/` |
| 入库事务和失败状态 | `app/services/document_ingestion_service.py` |
| 知识库与 ready 状态过滤 | `app/repositories/chunk_repository.py` |
| 来源与阈值前置拒答 | `app/services/database_rag_service.py` |
| 4 份两页虚构制度和 18 道题 | `data/demo_policies/`、`data/evaluation/enterprise_questions.json` |
| Recall、MRR 和 P95 | `data/evaluation/enterprise_evaluation_report.json`、`docs/evaluation-report.md` |
| 7 个 pytest case | `tests/test_models.py`、`tests/test_database_rag_service.py`、`tests/test_chunk_repository_integration.py` |
| Compose 迁移和持久化 | `docker-compose.yml`、`Dockerfile`、`docs/17天每日学习/Day13.md` |

## 视频完成后再做

只有在视频真实生成并逐帧检查后，才把实际上传后的公开链接加入投递版简历；未上传时保留 GitHub 项目链接即可，不填写虚假或占位视频地址。
````

**这段内容怎样工作**

- 输入：当前代码、README、测试收集数和已提交结构化评测报告。
- 输出：三条结果导向的独立项目描述，以及面试口径、项目边界和证据映射。
- 调用谁：不调用程序；每条事实链接到仓库证据。
- 被谁调用：用户之后手工合并到真实投递简历，Day 17 用于模拟追问。
- 正常路径：招聘者可以从功能、设计和结果三条快速理解项目。
- 失败路径：如果后续代码、数据集或报告变化，先更新证据和数字，再更新简历；不能只改简历数字。

**完成本步骤后的预期状态**

项目条目与 Agent 项目职责不同，不读取或覆盖现有简历，并且所有技术和数字都能在当前仓库中找到依据。

### 步骤 5：预演、录制并逐帧复核（建议 25 分钟，不含模型等待）

**目标**

真实生成约三分钟视频，并确保视频内容、脚本断言、简历和评测报告一致。

**修改位置**

- 文件：`artifacts/demo/enterprise-rag-demo.mp4`
- 定位：本地忽略目录
- 操作：按 `docs/demo-script.md` 预演一次，再正式录制；可以使用 Windows 自带录屏或用户熟悉的录屏工具

**执行顺序**

1. 完整预演四个阶段，确认没有断言失败。
2. 清理屏幕上所有秘密与个人通知。
3. 正式录制时重新创建演示知识库并上传 4 份 PDF。
4. 依次展示跨文档答案、拒答、API 重启恢复和评测摘要。
5. 只剪掉等待，不修改真实输出。
6. 把最终文件保存为明确路径并播放一遍检查。

**这一步怎样工作**

- 输入：可用 Compose 服务、本地 LLM 配置、步骤 2～4 的文件。
- 输出：`enterprise-rag-demo.mp4`。
- 调用谁：现有 API、PostgreSQL/pgvector、LLM、Docker Compose 和录屏软件。
- 被谁调用：求职投递、项目仓库外部展示和 Day 17 最终复现。
- 正常路径：视频真实覆盖核心链路，时长约三分钟，不暴露秘密。
- 失败路径：出现断言失败、来源缺失、LLM 配置错误、超时或秘密画面时停止，不提交、不发布，修复后重新完整录制。

**完成本步骤后的预期状态**

本地视频真实存在并可播放；Git 只看见今天的脚本、说明、简历条目、计划和 `.gitignore`，不看见 MP4 或状态 JSON。

## 六、运行数据库迁移或环境命令

今天不涉及数据库结构变更，不生成 Alembic revision，不执行 downgrade，也不写入非演示用途的数据；正式演示会创建一个新的明确知识库并上传仓库内 4 份虚构 PDF。

### 1. 检查当前状态

在项目根目录执行，先确认工作区边界、Compose 配置和 API 健康状态：

```powershell
git status --short

docker compose config --quiet
docker compose ps --all

$health = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get

$health | ConvertTo-Json
```

预期结果：Compose 配置退出码为 0；`/health` 返回 `status=ok`、`database_connected=true`，执行回答题前还必须是 `llm_configured=true`。

失败时检查：若服务未启动，执行下一节的 Compose 命令；若只缺 LLM，打开本地编辑器填写自己的三个 `LLM_*` 值并重建 API，但不要读取、打印或提交 `.env`。

### 2. 执行升级

先启动当前环境，再检查新脚本的 PowerShell 语法；这里只给出可复制命令，生成计划时未执行：

```powershell
docker compose up --build -d
docker compose ps --all

$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path "scripts\run_enterprise_rag_demo.ps1"),
    [ref]$tokens,
    [ref]$errors
) | Out-Null

if ($errors.Count -gt 0) {
    $errors | Format-List
    throw "演示脚本存在 PowerShell 语法错误"
}

"OK：演示脚本语法检查通过"
```

随后按照第五节和 `docs/demo-script.md` 预演及录制。

### 3. 回滚并恢复

今天没有 Schema 回滚。预演和录制创建的知识库属于明确的本地演示数据，可以保留给 Day 17；不要删除数据库 Volume，也不要使用批量删除或破坏性 Git 命令。

如果录屏文件不满意，只针对明确文件 `artifacts\demo\enterprise-rag-demo.mp4` 在文件管理器中覆盖或由用户手工删除后重录；计划不生成批量删除命令。

### 预期结果

- 没有新增迁移、没有改变表结构、没有修改生产阈值。
- 4 份虚构 PDF 形成一个新的演示知识库，4 个 Document 均为 `ready`。
- 脚本语法检查退出码为 0。
- 本地 MP4 和状态 JSON 不出现在 Git 状态中。

## 七、验证正常路径

### 启动或准备服务

在项目根目录启动现有 Compose 环境。首次加载 Embedding 或重建 API 可能超出核心 60 分钟，不计入录制内容：

```powershell
docker compose up --build -d
docker compose ps --all
```

### 执行正常请求或测试

在正式录制前完整执行一次：

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode prepare
.\scripts\run_enterprise_rag_demo.ps1 -Mode answerable
.\scripts\run_enterprise_rag_demo.ps1 -Mode refusal

docker compose restart api

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode verify-after-restart

Test-Path -LiteralPath `
    "artifacts\demo\enterprise-rag-demo.mp4"

git check-ignore -v `
    "artifacts\demo\enterprise-rag-demo.mp4"
```

可选再运行现有测试和数据校验，确认录制日没有改变核心规则：

```powershell
.\.venv\Scripts\python.exe `
    scripts\validate_enterprise_questions.py

.\.venv\Scripts\python.exe -m pytest -q
```

### 预期状态码或输出结构

动态 ID、回答措辞、来源分数和耗时以本次运行结果为准；稳定结构应满足：

```json
{
  "prepare": {
    "demo_ready": true,
    "knowledge_base_id": "动态正整数",
    "document_count": 4,
    "ready_count": 4
  },
  "answerable": {
    "refused": false,
    "required_source_documents": [
      "差旅与费用报销制度.pdf",
      "采购与办公资产管理制度.pdf"
    ]
  },
  "refusal": {
    "refused": true,
    "answer": "当前知识库中没有找到足够的信息。",
    "source_count": 0
  },
  "after_restart": {
    "document_ids_unchanged": true,
    "ready_document_count": 4,
    "query_refused": false
  },
  "video_exists": true,
  "video_is_ignored": true,
  "pytest": "预期 7 passed，实际执行可选"
}
```

### 为什么它能证明今天已经完成

`prepare` 证明视频使用真实新知识库和 4 份 PDF；跨文档断言证明回答来源覆盖两个制度；拒答断言证明无答案时不伪造来源；重启后 ID 比较证明没有靠 FastAPI 内存或重新上传恢复；视频存在和 Git ignore 检查证明产物已生成但没有污染仓库；简历证据映射保证投递表述能回到代码和报告。

## 八、验证失败和边界路径

### 场景：没有先准备演示状态就执行重启后验证，脚本必须安全失败

这个测试使用一个明确不存在的状态文件路径，只验证脚本的前置条件，不读取 `.env`、不调用上传接口、不修改数据库：

```powershell
$missingStatePath = `
    "artifacts\demo\intentionally-missing-state.json"

if (Test-Path -LiteralPath $missingStatePath) {
    throw "边界测试路径意外存在，请换一个明确的新文件名"
}

.\scripts\run_enterprise_rag_demo.ps1 `
    -Mode verify-after-restart `
    -StatePath $missingStatePath
```

### 预期结果

- HTTP 状态码或异常：脚本抛出“演示状态文件不存在，请先运行 `-Mode prepare`”，PowerShell 返回非零退出状态；即使 API 健康，也不会伪造旧 ID。
- 数据库应该保留：现有知识库、Document、Chunk、向量和 Alembic revision 全部保持原样。
- 数据库不应该存在：该失败路径不创建知识库、不上传 PDF、不更新文档状态。
- 响应不能泄露：不得出现 `.env` 内容、LLM API Key、数据库密码、完整数据库 URL、驱动堆栈或真实个人信息。

这个边界验证直接证明演示的重启恢复必须绑定 `prepare` 阶段保存的同一组动态 ID，不能随便挑一个已有知识库或重新上传后宣称持久化成功。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| PowerShell 报脚本禁止运行 | 当前 ExecutionPolicy 阻止本地脚本 | `Get-ExecutionPolicy -List` | 只对当前进程执行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`，关闭终端后自动恢复；不要修改整机策略 |
| `prepare` 提示 LLM 未配置 | 三个 LLM 配置项至少一个缺失，或 API 没有重建 | 只看 `/health` 的 `llm_configured` 布尔值，不打印 `.env` | 在本地编辑器填写自己的配置，执行 `docker compose up --build -d api` 后等待健康 |
| 上传某个 PDF 失败 | API 未就绪、文件数量/路径变化、解析或 Embedding 出错 | `docker compose logs --tail 100 api`；`Get-ChildItem data\demo_policies\pdfs -Filter *.pdf` | 先运行数据集校验；修复真实错误后新建一次演示知识库，不在失败库上伪造 ready |
| 跨文档题缺少一个来源 | 语料/切块/模型版本变化，或请求不是固定问题与 Top-3 | 对照 `data/evaluation/enterprise_questions.json` 和源报告的 `cross-procurement-payment-01` | 停止录制，确认 4 份 PDF 哈希、模型、`top_k=3` 和当前检索代码；不要编辑视频隐藏缺失 |
| 可回答题返回 HTTP 503 | LLM 配置缺失；检索已找到证据后才需要 LLM | `/health`、`app/services/database_rag_service.py` | 补齐本地配置并重启 API；拒答题能成功不代表 LLM 已配置 |
| API 重启后等待很久 | Embedding 模型重新加载或缓存未命中 | `docker compose ps api`；`docker compose logs --tail 100 api` | 保留 `huggingface_cache` Volume，等待健康；剪掉等待可以，但不能绕过最终断言 |
| 重启后 Document ID 不一致 | 状态文件被覆盖、换了 Compose 项目/数据库或重新运行了 prepare | 查看 `artifacts\demo\state.json` 的知识库 ID；对照文档列表 | 重新从 `prepare` 开始完整录制；不要手改状态 JSON 冒充同一数据 |
| 视频超过三分钟 | 口述太细、完整保留了模型和重启等待 | 对照 `docs/demo-script.md` 各段时间 | 只保留业务目标、稳定证据、指标口径和限制；剪掉静默等待，不删失败事实 |
| 视频出现秘密或个人通知 | 录制前没有清屏，打开了 `.env` 或桌面通知 | 逐帧检查成片，重点看终端历史、浏览器标签和通知区域 | 不发布该版本；关闭通知、清理窗口后重新录制，不依赖模糊遮挡补救 |
| MP4 出现在 `git status` | `.gitignore` 规则未追加、保存路径不同或文件曾被跟踪 | `git check-ignore -v artifacts\demo\enterprise-rag-demo.mp4` | 保存到约定目录并修正明确规则；如果此前已跟踪，停止并先核对历史，不使用批量删除 |
| 简历写成“准确率 97.22%” | 混淆 Recall 与答案正确率 | `docs/evaluation-report.md` 第 3～4 节 | 改为“固定 18 题上的 Top-3 证据 Recall@3 97.22%”，并保留数据规模与口径 |
| 简历写“0.65 已部署” | 把离线推荐参数误当生产配置 | `rg -n "MIN_RELEVANCE_SCORE" app\services\database_rag_service.py` | 明确生产仍为 0.55；今天不改代码，只在报告和面试中说明差异 |

## 十、检查最终代码差异

```powershell
git status --short

git diff -- `
    .gitignore `
    scripts\run_enterprise_rag_demo.ps1 `
    docs\demo-script.md `
    docs\resume-project-entry.md `
    docs\17天每日学习\Day16.md

git check-ignore -v `
    artifacts\demo\enterprise-rag-demo.mp4 `
    artifacts\demo\state.json
```

重点检查：

- diff 只包含今天五个可提交文本文件，不包含 `.env`、MP4、状态 JSON、应用代码、迁移、测试、PDF 或评测源报告。
- 演示脚本没有固定写死某次数据库 ID，没有打印 `.env`，也没有删除数据库或 Volume 的命令。
- 跨文档题固定使用已提交报告中 Top-3 完整命中的 `cross-procurement-payment-01`，并断言两个来源文件。
- 拒答题固定要求 `refused=true`、空来源和当前约定文本。
- 重启后核对复用同一状态文件和 Document ID，不重新上传。
- 简历只写 `97.22% Recall@3`、`95.83% MRR@3` 和明确范围的 `15.25 ms P95`，没有写成答案准确率或生产 SLA。
- 所有材料都区分当前生产阈值 `0.55` 和离线建议 `0.65`。
- 视频公开链接只有在实际上传后才添加，没有占位或虚假 URL。

## 十一、Git 提交

核心脚本、演示说明、简历条目和忽略规则完成并检查 Git diff 边界后即可执行；视频实际文件留在本地，不加入提交，验证输出也不要求回填：

```powershell
git status --short

git diff -- `
    .gitignore `
    scripts\run_enterprise_rag_demo.ps1 `
    docs\demo-script.md `
    docs\resume-project-entry.md `
    docs\17天每日学习\Day16.md

git add `
    .gitignore `
    scripts\run_enterprise_rag_demo.ps1 `
    docs\demo-script.md `
    docs\resume-project-entry.md `
    docs\17天每日学习\Day16.md

git commit -m "docs: add three-minute RAG demo and resume entry"
```

提交前若视频、状态 JSON或真实配置仍出现在 `git status`，先停止提交并修正路径/ignore；不要用 `git add .`，也不要为了清理状态执行破坏性 Git 命令。

## 十二、面试高频问题与参考答案

### 问题 1：为什么你的演示不是直接打开 Swagger 点几个接口？

#### 30 秒参考答案

Swagger 适合探索接口，但三分钟面试演示更需要稳定证据链。我把流程固化为四个 PowerShell 阶段：创建知识库并上传 4 份文档、跨文档问答、无答案拒答、API 重启后复用同一 ID。脚本不仅发请求，还断言 4 个 Document 全部 ready、来源覆盖两份目标制度、拒答来源为空、重启后 Document ID 不变，因此比只看 HTTP 200 更能证明系统边界。

#### 继续追问：为什么仍保留 Swagger？

Swagger 对人工查看请求模型、状态码和临时探索很方便，README 也保留入口；但重复演示和验收需要确定输入、自动断言和非零退出状态，所以使用脚本作为正式路径，两者职责不同。

#### 回答时要引用的项目依据

- `scripts/run_enterprise_rag_demo.ps1`
- `docs/demo-script.md`
- `app/main.py`
- `app/models.py`

### 问题 2：你怎样证明跨文档问答不是模型自己编出来的？

#### 30 秒参考答案

我选择采购设备到付款的固定问题，它需要同时引用采购资产制度和差旅报销制度。检索在 SQL 层限定知识库和 ready 状态，Top-3 的来源中必须同时出现这两个文件，响应还带页码、Chunk ID、原文和相似度。演示脚本会对文件集合做断言；已提交评测中该题 Top-3 找回全部 5 个预期证据，Recall 为 1.0。这样回答可以回查原 PDF，而不是只相信 LLM 文本。

#### 继续追问：相似度分数能表示答案正确概率吗？

不能。当前 score 是 `1 - cosine_distance`，表示查询和 Chunk 向量的语义接近程度。它用于排序和阈值判断，不是经过概率校准的答案置信度；最终仍要看来源是否覆盖所需证据，并通过固定评测分析失败案例。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `cross-procurement-payment-01`
- `data/evaluation/enterprise_evaluation_report.json`
- `app/repositories/chunk_repository.py`
- `app/services/database_rag_service.py`

### 问题 3：简历上的 97.22% 和 15.25 ms 分别代表什么？

#### 30 秒参考答案

97.22% 是 4 份两页虚构制度、12 道可回答题上的平均证据 Recall@3，衡量预期证据是否进入前三条；MRR@3 是 95.83%，衡量第一条正确证据的排序位置。15.25 ms 是 36 个预热后 Query Embedding 加 pgvector Top-K 查询样本的 P95，不包含模型初始化、HTTP 或 LLM 生成。因此我不会把前者叫答案准确率，也不会把后者叫生产接口 SLA。

#### 继续追问：为什么报告推荐 0.65，但代码仍是 0.55？

0.65 在候选参数中提高了无答案拒答率，但已经让一条可回答的酒店标准问题误拒答。Day 11 的职责是给出离线实验建议，不自动改生产代码；当前代码仍保留 0.55。要上线 0.65，我会扩大数据集、做独立配置变更并重跑 API、pytest 和评测回归。

#### 回答时要引用的项目依据

- `docs/evaluation-report.md`
- `data/evaluation/enterprise_evaluation_report.json`
- `app/services/database_rag_service.py` 的 `MIN_RELEVANCE_SCORE`

### 问题 4：只重启 API 能证明 PostgreSQL 持久化吗？

#### 30 秒参考答案

API 重启后不重新上传，仍使用同一知识库和 Document ID，并返回相同来源类型，能够排除 FastAPI 进程内存是权威存储。它是三分钟视频里最直观的证据。完整持久化验收还需要重启 PostgreSQL 进程并保留命名 Volume；这个项目在 Day 13 已单独比较数据库与 HTTP 指纹。视频受时长限制展示 API 重启，但我会明确完整证据所在，而不是夸大单一步骤。

#### 继续追问：为什么不在视频里删除 Volume 再启动？

删除 Volume 会销毁要验证的持久化数据，也不是“重启恢复”的正确测试。持久化测试应该保留同一个 Volume 重启进程；干净环境从空库执行迁移属于可复现性测试，是 Day 14 的另一条证据。

#### 回答时要引用的项目依据

- `scripts/run_enterprise_rag_demo.ps1` 的 `verify-after-restart`
- `docker-compose.yml` 的 `postgres_data`
- `docs/17天每日学习/Day13.md`
- `docs/17天每日学习/Day14.md`

### 问题 5：这个 RAG 项目与另一个办公 Agent 项目怎样避免重复？

#### 30 秒参考答案

这个项目回答的是企业知识怎样可靠地入库、按知识库隔离检索、追溯来源、拒答、评测并跨重启保留，重点是 FastAPI、PostgreSQL/pgvector、事务、测试和 Docker。办公 Agent 项目则应突出意图路由、工具选择、多步骤任务和结构化业务系统调用。我在简历中分别用数据可靠性和任务编排两条主线描述，不重复把切分、向量库和 Top-K 当作两个项目的核心成果。

#### 继续追问：为什么不把两者合成一个更大的项目？

合并会模糊问题边界，也难以判断每个能力是否真的完成。独立项目让 RAG 后端的检索质量、数据一致性和复现证据可以单独评测，让 Agent 的工具选择和任务成功率可以使用另一套指标；以后若集成，也应通过清晰 API 边界连接，而不是把两份经历写成一个无法核对的大系统。

#### 回答时要引用的项目依据

- `docs/resume-project-entry.md`
- `README.md` 的项目定位和已知限制
- `docs/AI应用开发岗位简历修改建议.md` 的两个项目分工

## 十三、今天的完整数据流

### 正常路径

```text
README、架构图、评测 JSON 和当前代码事实
→ 固化三分钟演示脚本和简历证据映射
→ Compose API 健康且 LLM 已配置
→ 创建本次唯一知识库
→ 上传 4 份虚构 PDF
→ 4 个 Document 全部 ready
→ 跨文档题返回两份制度来源
→ 无答案题在 LLM 前拒答且来源为空
→ 重启 API，不重新上传
→ 使用状态文件中的同一知识库和 Document ID 查询成功
→ 展示固定评测指标与限制
→ 保存本地 MP4并逐帧检查
→ Git 只提交脚本、文档和 ignore 规则
→ Day 17 使用同一路线连续复现与模拟面试
```

### 失败路径

```text
API/LLM 未就绪、PDF 数量错误、文档非 ready、来源缺失、拒答错误或重启后 ID 改变
→ PowerShell 脚本抛出明确错误并返回非零状态
→ 停止录制或停止发布
→ 保留数据库与已有文件，不删除 Volume、不伪造输出
→ 定位实际环境、数据或代码差异
→ 修复后从 prepare 开始完整重录
```

## 十四、完成标准

```text
[ ] 能解释为什么三分钟演示必须按“操作—结果—证据”推进，而不是只展示 HTTP 200
[ ] 能准确解释哪些字段是动态值，以及为什么重启验收比较 ID/来源而不逐字比较 LLM answer
[ ] .gitignore 已只忽略 artifacts/demo/，MP4 和状态 JSON 不进入 Git
[ ] scripts/run_enterprise_rag_demo.ps1 已完整实现 prepare、answerable、refusal 和 verify-after-restart 四个阶段及稳定断言
[ ] docs/demo-script.md 已固定架构、4 文档上传、跨文档来源、拒答、API 重启恢复、评测和安全画面
[ ] docs/resume-project-entry.md 已形成与 Agent 项目独立的三条项目描述，所有数字均有当前仓库证据
[ ] 已提供四阶段预演、视频存在、Git ignore、数据集校验和 pytest 的正常验证命令及预期结果，实际执行记录可选
[ ] 已提供缺失状态文件的失败验证，预期非零退出且数据库零写入、响应不泄露秘密
[ ] 本地 enterprise-rag-demo.mp4 真实存在、可播放、约三分钟并已逐帧检查；这是当天核心产物，不能只写脚本代替
[ ] 能不看代码复述“入库 → 跨文档来源 → 拒答 → API 重启恢复 → 评测 → 简历证据”的完整演示数据流
[ ] git diff 只包含今天五个文本文件，没有秘密、MP4、状态 JSON、应用代码、迁移或无关修改
[ ] 核心材料完成后可使用明确文件清单提交，不以回填可选验证输出为前提
```

## 十五、可选执行记录

- 实际完成：未执行
- 视频路径与时长：可选，不要求填写
- 四阶段预演结果：可选，不要求填写
- 验证结果：可选，不要求填写
- 用户完成标记：待用户自行填写
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：未提交
