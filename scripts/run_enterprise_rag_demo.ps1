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
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)

    return ,$bytes
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

        $documents = Invoke-RestMethod `
            -Uri "$BaseUrl/knowledge-bases/$($knowledgeBase.id)/documents" `
            -Method Get `
            -TimeoutSec 30

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
        $documents = Invoke-RestMethod `
            -Uri (
                "$BaseUrl/knowledge-bases/" +
                "$($state.knowledge_base_id)/documents"
            ) `
            -Method Get `
            -TimeoutSec 30

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