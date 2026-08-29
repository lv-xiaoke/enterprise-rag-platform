# Day 30：完成 Mini RAG 项目模拟面试与最终介绍

Day 29 已经完成 RAG、Agent 与 Function Calling 的面试回答，当前项目代码、评估结果和前 29 天记录均已提交。按照月计划，今天不再学习新框架，而是把过去一个月的代码和数据组织成一场完整的项目面试：先验证演示链路，再准备 3～5 分钟项目介绍、常见追问和简历表述，最后把 README 的学习进度更新到 Day 30。今天的结果不是继续增加功能，而是能够诚实、具体、有数据地讲清自己做过的项目。

面试介绍始终围绕这条顺序：

```text
为什么做
→ 解决什么问题
→ 系统怎样工作
→ 为什么这样设计
→ 怎样验证效果
→ 遇到什么问题
→ 还有哪些限制
→ 下一步怎样优化
```

---

# 一、先整理项目中可以确认的事实

打开项目并检查状态：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
git status --short
git log -3 --oneline
```

当前工作区应该干净，最近一次提交应为 Day 29。

再用 README 和源码确认面试中可以讲的事实：

```powershell
Select-String `
    -Path README.md,app\main.py,app\services\embedding_service.py,app\services\vector_store.py `
    -Pattern 'BAAI/bge-small-zh-v1.5|IndexFlatIP|CHUNK_SIZE|CHUNK_OVERLAP|TOP_K|@app\.(get|post)|Top-1|Top-3'
```

当前项目可以明确讲出：

```text
后端框架：FastAPI + Pydantic
LLM 调用：httpx.AsyncClient + DeepSeek API
PDF 解析：pypdf，只处理带文字层的 PDF
切块：chunk_size=200、overlap=40
Embedding：BAAI/bge-small-zh-v1.5，512 维归一化向量
向量检索：FAISS IndexFlatIP，固定 Top-3
普通聊天记录：SQLite
容器化：Dockerfile
接口数量：7 个，其中核心 RAG 接口是 /upload 和 /rag/chat
评估：12 道固定问题，另做 Top-1 与 Top-3 检索对照
```

面试时不要加入当前没有实现的能力。下面这些只能作为后续方向，不能说成已完成：

```text
OCR、图片和表格解析
多文档管理与用户隔离
向量索引持久化
BM25、Hybrid Search 和 Reranker
Agent 或 LangGraph
身份认证、限流和正式生产部署
```

---

# 二、用两个终端完成一次真实演示

正式模拟前先确认项目仍能跑通。今天不重新安装依赖，也不批量运行 12 道评估题，只验证最关键的上传和问答链路。

## 终端一：启动 FastAPI

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

应用启动时会加载本地 Embedding 模型，可能比普通 FastAPI 服务慢。看到类似下面的输出后再使用终端二：

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

如果启动失败，先检查当前是否在项目根目录、虚拟环境是否激活，以及依赖是否已经安装。不要在今天临时升级依赖。

## 终端二：检查健康状态

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get
```

预期至少看到：

```text
status         : ok
llm_configured : True
```

如果 `llm_configured` 是 `False`，只确认本地配置是否完整，不要在终端打印 `.env` 内容。

## 上传测试 PDF

当前本地已经存在：

```text
data/documents/sample.pdf
```

执行：

```powershell
curl.exe `
    -X POST `
    -F "file=@data/documents/sample.pdf;type=application/pdf" `
    "http://127.0.0.1:8000/upload"
```

预期返回：

```json
{
  "filename": "sample.pdf",
  "page_count": 3,
  "chunk_count": 10
}
```

`chunk_count` 取决于当前 PDF 内容和切块参数。如果与示例略有不同，先根据实际文件判断，不要为了匹配数字修改代码。

## 发送一个 RAG 问题

```powershell
$body = @{
    question = "什么是 RAG，基础流程包括哪些步骤？"
} | ConvertTo-Json

$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

$result = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/rag/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body $bodyBytes

$result.answer
$result.sources | Format-Table page, score, text -Wrap
```

重点不是模型回答必须逐字一致，而是确认：

```text
answer 有内容
sources 返回 3 条或不超过当前 Chunk 数量的结果
每条来源包含 text、page 和 score
来源中能找到与 RAG 流程相关的原文
```

这次调用会真实请求 LLM API。验证一次即可，不要为了得到相同措辞反复调用。

测试完成后回到终端一，按 `Ctrl+C` 停止服务。

---

# 三、创建项目模拟面试稿

创建今天的回答文件：

```powershell
$interviewFile = "docs\appendix\Day30-项目模拟面试稿.md"

if (-not (Test-Path -LiteralPath $interviewFile)) {
    New-Item -Path $interviewFile -ItemType File
}

code $interviewFile
```

先写入下面的结构：

```markdown
# Day 30：Mini RAG 项目模拟面试稿

## 一、30 秒项目概括
## 二、3～5 分钟项目介绍
### 1. 项目动机与问题
### 2. 整体架构
### 3. PDF 上传阶段
### 4. RAG 提问阶段
### 5. 关键设计选择
### 6. 评估结果
### 7. 遇到的问题
### 8. 已知限制与后续优化

## 三、常见追问与回答
## 四、简历项目表述
## 五、模拟记录
```

这份稿子不是逐字背诵材料，而是帮助你固定叙述顺序。完成后应当可以只看小标题就讲下去。

---

# 四、先写一个 30 秒项目概括

30 秒版本只回答“做了什么、用了什么、结果怎样”，不要展开所有技术细节。可以先写成：

> 我用 FastAPI、DeepSeek API、BGE Embedding 和 FAISS 做了一个纯文本科研 PDF RAG 后端。系统支持上传 PDF，按页解析和切块后建立内存向量索引，用户提问时检索 Top-3 相关片段，再让大模型根据资料回答，并返回来源文本、页码和相似度。我还设计了 12 道固定问题评估检索与回答效果，并通过 Top-1 和 Top-3 对照分析参数选择。目前项目已经完成本地运行、Dockerfile、README 和基础评估，但仍只支持单个文本型 PDF，索引也没有持久化。

把这段改成你平时说话的方式，避免一口气堆很多英文名词。面试官如果感兴趣，会继续追问架构、参数和评估。

---

# 五、准备 3～5 分钟完整项目介绍

下面给出一份基于当前代码的参考稿。先理解每段承担什么作用，再在模拟面试稿中改写，不要机械背诵。

## 第一部分：为什么做这个项目

可以这样讲：

> 我本身是数学硕士，之前更熟悉深度学习和图像处理，但希望补齐 AI 应用开发中的后端工程能力，所以选择做一个科研 PDF RAG 后端。这个项目解决的问题是：大模型本身不知道用户刚上传的论文内容，直接把整篇长文档放入 Prompt 又不够精确，因此需要先处理文档、检索相关片段，再让模型根据资料回答。

这里既说明了项目价值，也自然连接你的个人背景。不要说“为了学 RAG 随便做了一个项目”，要说明它解决的是外部文档问答与来源追溯问题。

## 第二部分：整体架构

可以这样讲：

> 后端使用 FastAPI 提供接口，并把职责拆成 PDF 解析、Chunk、Embedding、向量检索、RAG 编排和 LLM 调用几个服务。系统分成上传和提问两条链路：上传时把 PDF 解析、切块、向量化并写入 FAISS；提问时把问题向量化，检索 Top-3，拼接 RAG Prompt，再调用 LLM。接口最后同时返回回答和来源，便于核对幻觉。

说到这里时，可以指向 README 中的 Mermaid 架构图，不需要逐个朗读所有文件名。

## 第三部分：PDF 上传阶段

可以这样讲：

> 用户通过 `/upload` 上传带文字层的 PDF。项目使用 pypdf 按页提取文本，再按 200 个字符切块，相邻块保留 40 个字符 overlap，并为每个 Chunk 保存物理页码。之后用 `BAAI/bge-small-zh-v1.5` 生成 512 维归一化向量，再写入 FAISS `IndexFlatIP`。FAISS 保存向量，Python 中的元数据列表保存文本和页码，两者依靠相同顺序对应。

这一段体现你不只是“调用了一个 RAG 库”，而是理解各步骤的数据结构和元数据怎样保留。

## 第四部分：RAG 提问阶段

可以这样讲：

> 用户通过 `/rag/chat` 提问后，系统先用同一个 BGE 模型生成问题向量，再从 FAISS 检索 Top-3 Chunk。因为文档向量和问题向量都做了 L2 归一化，所以 `IndexFlatIP` 的内积可以作为余弦相似度排序。检索文本会和问题一起组成 Prompt，并明确要求资料没有答案时说明不知道。LLM 返回回答后，接口还会返回每个来源的文本、页码和相似度。

注意不要把 `score` 说成正确概率。它只用于同一个问题下的相似度排序。

## 第五部分：工程设计

可以这样讲：

> 接口层主要负责请求校验和异常转换，具体逻辑放在 services 中。Pydantic 用于校验请求和响应，httpx 的异步客户端用于调用 LLM API，普通聊天记录写入 SQLite。上传时只有 PDF 解析、切块、Embedding 和 FAISS 写入全部成功，才替换全局 RAG 服务，避免一次失败上传破坏上一份可用索引。项目还提供 Dockerfile，并通过 `.dockerignore` 排除 `.env` 和本地数据。

这里不要声称所有操作都已经异步化。Embedding、FAISS 和当前 SQLite 调用仍然是同步操作。

## 第六部分：怎样评估

可以这样讲：

> 我针对三页测试 PDF 设计了 12 道固定问题，包括事实题、总结题、对比题和无答案题，并分别记录检索命中和最终回答是否正确。基线使用 `chunk_size=200`、`overlap=40`、`top_k=3`，10 道可回答题的检索都命中，12 道最终回答都通过人工检查。我还固定切块参数，单独比较 Top-1 和 Top-3：Top-1 命中 9/10，Top-3 命中 10/10，其中综合题 `summary-02` 需要额外 Chunk 才覆盖完整信息，所以当前保留 Top-3。

紧接着主动补一句限制：

> 这些数据只来自一个三页 PDF 和人工问题集，不能当作通用准确率；它主要证明评估流程和参数分析已经跑通。

这种表达比只报“100% 正确率”更可信。

## 第七部分：遇到的问题

选择一个有实际代码证据的问题讲清楚，不要罗列很多小错误。推荐使用“来源元数据怎样贯穿检索链路”：

> 最初向量检索只需要返回文本，但为了让接口展示页码和相似度，我需要保证 Chunk 元数据不会在 Embedding 和 FAISS 检索过程中丢失。后来我定义了 `DocumentChunk` 保存文本和页码，定义 `SearchResult` 保存文本、页码和分数，并让 FAISS 向量编号与元数据列表保持相同写入顺序。这样检索命中向量编号后，就能找回完整来源，再通过 Pydantic 的 `RAGSource` 返回给客户端。这个过程让我更清楚地理解了向量索引和业务元数据是两套数据，但必须建立稳定映射。

面试官如果追问“为什么不用数据库保存元数据”，可以诚实回答：当前是单文档、内存型学习项目，用列表能保持实现最小；多文档与持久化版本会使用文档 ID、Chunk ID 和持久化存储建立映射。

## 第八部分：限制和下一步

可以这样结束：

> 当前项目只支持带文字层的 PDF，只维护最近一次上传的内存索引，重启后需要重新上传，也还没有多用户隔离、认证和完整自动化测试。下一步我会优先做索引持久化和多文档管理，再用更长的真实论文扩大评估集，继续比较 Chunk、overlap 和 Top-k。之后才会根据数据决定是否增加 BM25、Reranker 或其他组件，而不是先堆框架。

结束时保持范围克制，不要一次承诺多模态、Agent、Kubernetes 等所有功能。

---

# 六、准备九个核心追问

在模拟面试稿的“常见追问与回答”下面，用自己的话回答月计划中的九个问题。

## 1. 为什么做这个项目

回答个人动机与真实问题：补齐 AI 应用后端工程能力，并解决科研 PDF 外部知识问答与来源追溯。

## 2. 项目解决什么问题

回答模型不知道新上传文档、长文档不能全部直接放进 Prompt，以及回答需要来源核对。

## 3. 整体架构是什么

先讲上传链路，再讲提问链路，最后说明 FastAPI 是 HTTP 边界，services 负责具体能力。

## 4. PDF 怎样处理

回答 pypdf 按页提取、字符切块、overlap、页码元数据，以及只支持带文字层 PDF 的限制。

## 5. 怎样进行向量检索

回答 BGE Embedding、L2 归一化、FAISS `IndexFlatIP`、Top-3，以及内积相似度不是正确概率。

## 6. 怎样减少幻觉

回答外部资料、Top-3、无答案约束、返回来源和固定问题评估，同时说明 RAG 不能彻底消除幻觉。

## 7. 怎样评估效果

回答 12 道问题的类别、检索与生成分开评分、Top-1/Top-3 对照及小样本限制。

## 8. 遇到了什么问题

优先回答来源元数据映射，也可以补充 Top-k 不能凭感觉选择，而是通过 `summary-02` 的对照结果确定。

## 9. 下一步怎样优化

按优先级回答：索引持久化与多文档管理、真实论文评估、自动化测试与认证，再根据评估考虑检索增强组件。

每道回答先说结论，再用一处代码或数据作为证据，最后补充限制。不要把答案扩展成新的十分钟演讲。

---

# 七、准备简历中的项目表述

在模拟面试稿中先保留一个简洁版本：

> 基于 FastAPI、LLM API、BGE Embedding 和 FAISS 构建科研 PDF RAG 问答后端，实现文档解析、重叠切块、向量检索、来源页码返回及 Docker 容器化；设计 12 道固定问题评估检索与生成效果，并通过 Top-1/Top-3 对照分析检索参数。

如果简历允许写两条，可以拆成：

```text
• 基于 FastAPI、DeepSeek API、BGE Embedding 和 FAISS 实现科研 PDF RAG 后端，完成按页解析、字符切块、Top-3 向量检索及带页码和相似度的来源返回。

• 设计 12 道固定问题区分检索命中与回答正确，并在固定切块参数下完成 Top-1/Top-3 对照，检索命中由 9/10 提升至 10/10。
```

不要写下面这些未经项目证明的表述：

```text
达到生产级高并发
支持任意复杂 PDF
彻底解决大模型幻觉
准确率达到 100%
完成大规模部署
```

简历的目标是让每一句都能在代码、README 或评估 JSON 中找到证据。

---

# 八、进行一轮计时模拟面试

先关闭 Day30 计划，只保留模拟面试稿的小标题。使用 PowerShell 计时：

```powershell
Read-Host "准备好后按 Enter 开始项目介绍" | Out-Null
$start = Get-Date

Read-Host "口述结束后按 Enter" | Out-Null
$elapsed = (Get-Date) - $start

"本次项目介绍用时：{0:N1} 分钟" -f $elapsed.TotalMinutes
```

第一轮允许看小标题，目标是把结构讲完整。第二轮不看长稿，只保留这八个关键词：

```text
动机
架构
上传
提问
设计
评估
问题
优化
```

项目介绍结束后，从下面问题中随机抽取至少 5 道：

```powershell
$followUps = @(
    "为什么用 FastAPI？"
    "为什么选择 BGE-small-zh？"
    "为什么归一化后使用 IndexFlatIP？"
    "Chunk 为什么是 200，overlap 为什么是 40？"
    "为什么选 Top-3，不选 Top-1 或 Top-10？"
    "如何区分检索错误和生成错误？"
    "score 为什么不是正确概率？"
    "RAG 能彻底解决幻觉吗？"
    "为什么你的项目不是 Agent？"
    "多个用户同时上传 PDF 会怎样？"
    "服务重启后索引还在吗？"
    "如果用于真实长论文，下一步先改什么？"
)

$followUps | Sort-Object { Get-Random } | Select-Object -First 5
```

遇到项目没有实现的能力，使用这个回答方式：

```text
先说明当前真实状态
→ 再解释为什么当前这样设计
→ 最后给出合理的下一步方案
```

例如“多个用户同时上传会怎样”：

> 当前只有一个进程内的全局 RAG 服务，后一次成功上传会覆盖前一次索引，所以还不支持用户隔离。这是学习版项目为了先跑通单文档链路做的范围控制。下一步会给文档分配 ID，将索引和元数据持久化，并让查询明确指定文档或知识库。

在模拟面试稿末尾记录：

```text
项目介绍用时：
讲得最清楚的部分：
最容易卡住的追问：
出现但项目没有实现的表述：
下一轮要缩短或补充的内容：
```

---

# 九、把 README 更新到最终进度

当前 README 仍写着：

```text
当前进度：Day 26/30
```

完成模拟面试后，打开 README：

```powershell
code README.md
```

把进度更新为：

```markdown
**当前进度：Day 30/30**

**当前状态：30 天 Mini RAG 学习主线已完成，项目已进入演示、复盘与持续优化阶段。**
```

再把项目结构中的：

```text
Day1.md ～ Day26.md
```

改成：

```text
Day1.md ～ Day30.md
```

最后检查 README 没有把未实现功能写成已完成，也不要加入真实 `.env`、API Key 或本地隐私数据。

用下面的命令核对三处最终状态：

```powershell
Select-String `
    -Path README.md `
    -Pattern 'Day 30/30|30 天 Mini RAG|Day1.md ～ Day30.md'
```

预期找到 3 行。

---

# 十、检查并提交本月最后一次学习记录

确认今天的模拟面试稿存在：

```powershell
Get-Item "docs\appendix\Day30-项目模拟面试稿.md"
```

确认其中包含核心部分：

```powershell
Select-String `
    -Path "docs\appendix\Day30-项目模拟面试稿.md" `
    -Pattern '30 秒项目概括|3～5 分钟项目介绍|常见追问与回答|简历项目表述|模拟记录'
```

查看全部修改：

```powershell
git status --short
git diff --check
git diff --stat
```

今天正常应包含：

```text
README.md
docs/Day30.md
docs/appendix/Day30-项目模拟面试稿.md
```

今天不需要修改：

```text
app 中的业务代码
requirements.txt
Dockerfile
评估 JSON
.env
```

确认演示成功、README 内容准确、模拟稿没有夸大项目能力后暂存：

```powershell
git add `
    README.md `
    docs/Day30.md `
    "docs/appendix/Day30-项目模拟面试稿.md"

git diff --cached --stat
git status
```

确认暂存文件正确后提交：

```powershell
git commit -m "docs: complete 30-day Mini RAG learning plan"
```

最后检查：

```powershell
git log -1 --oneline
git status --short
```

---

# Day 30 完成标准

- [ ] 已使用两个终端验证 `/health`、`/upload` 和 `/rag/chat`
- [ ] `/rag/chat` 返回回答以及带 `text`、`page`、`score` 的来源
- [ ] 能在 30 秒内概括项目做了什么、使用什么技术和取得什么结果
- [ ] 能在 3～5 分钟内按固定结构完整介绍项目
- [ ] 能讲清上传阶段和提问阶段的两条数据流
- [ ] 能解释 pypdf、Chunk、BGE Embedding、FAISS 和 LLM 各自的作用
- [ ] 能解释 L2 归一化、`IndexFlatIP` 和相似度分数的关系
- [ ] 能用 Top-1 9/10、Top-3 10/10 说明当前选择 Top-3 的依据
- [ ] 能主动说明当前评估只是小型基线，不是通用准确率
- [ ] 能从检索和生成两侧解释怎样减少幻觉
- [ ] 能讲清来源元数据如何与 FAISS 向量编号建立对应
- [ ] 能如实说明单文档内存索引、无 OCR、无认证和评估规模小等限制
- [ ] 能按优先级说明索引持久化、多文档管理和真实论文评估等后续方向
- [ ] 已完成 `docs/appendix/Day30-项目模拟面试稿.md`
- [ ] 已完成至少两轮项目介绍和一轮随机追问
- [ ] 已形成一条或两条可以放入简历、且有项目证据支持的表述
- [ ] README 已更新为 Day 30/30，并同步更新当前状态和 Day 文件范围
- [ ] 已确认没有夸大为生产级、高并发、任意 PDF 或 100% 准确率
- [ ] 已确认没有修改业务代码、依赖、Dockerfile、评估数据或 `.env`
- [ ] 检查成功后完成 Git 提交，并确认工作区干净

实际完成：

遇到的卡点：

Git commit：
