# Day 29：结合 Mini RAG 项目讲清 RAG、Agent 与 Function Calling

Day 28 已经完成 Transformer 与 LLM 原理学习，并整理了可以口述的面试回答。按照月计划，今天回到当前项目最核心的 RAG：先沿着真实代码解释检索增强生成，再讲清 Embedding、Chunk、Top-k、BM25、Reranker、幻觉与评估，最后区分 Agent、Workflow 和 Function Calling。今天不增加检索算法，也不实现 Agent；最终要得到一份基于 Mini RAG 项目证据、能够直接用于面试的回答笔记。

今天始终围绕这条主线：

```text
RAG 解决“回答时从哪里取得外部知识”
Agent 解决“模型怎样决定下一步做什么”
Function Calling 解决“模型怎样用结构化方式请求程序调用工具”
```

三者可以组合，但不是同一个概念。

---

# 一、先从项目代码复述完整 RAG 链路

打开项目并检查状态：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
git status --short
git log -2 --oneline
```

当前工作区应该干净，最近一次提交应为 Day 28。

先搜索当前 RAG 的关键证据：

```powershell
Select-String `
    -Path app\main.py,app\services\embedding_service.py,app\services\vector_store.py,app\services\rag_service.py `
    -Pattern 'CHUNK_SIZE|CHUNK_OVERLAP|TOP_K|embed_documents|embed_query|IndexFlatIP|search\(|build_rag_prompt|llm_service.chat'
```

根据源码，把项目分成两条数据流。

上传阶段：

```text
PDF bytes
→ 按页提取文本
→ chunk_size=200、overlap=40 切块
→ BGE 生成文档向量
→ FAISS 保存向量和 Chunk 元数据
```

提问阶段：

```text
用户问题
→ BGE 生成问题向量
→ FAISS 检索 Top-3
→ 拼接 Context 和 RAG Prompt
→ 调用 LLM API
→ 返回回答、来源文本、页码和相似度
```

尝试不看上面的文字，打开以下文件自己复述一次：

```powershell
code app\services\rag_service.py
```

面试时不要只说“项目用了 RAG”。至少说出检索前的文档处理、查询时的向量检索，以及检索结果怎样进入 LLM Prompt。

---

# 二、问题一：为什么需要 RAG

大模型的参数知识有几个现实限制：

```text
训练数据有时间边界
不知道企业内部或个人私有文档
参数中的知识不容易立即更新
回答依据不容易直接追溯
```

RAG 是 Retrieval-Augmented Generation，中文常译为“检索增强生成”。它在回答问题时先从外部知识库检索相关资料，再把资料作为 Context 交给生成模型。

当前项目中的价值可以具体说成：

```text
LLM 原本不知道刚上传的 PDF 内容
→ 项目把 PDF 切块并建立向量索引
→ 用户提问时检索相关 Chunk
→ LLM 根据这些 Chunk 生成回答
→ 接口同时返回来源，方便人工核对
```

RAG 不会保证回答一定正确。检索可能找错，正确资料可能没有进入 Top-k，Prompt 可能组织得不好，LLM 也可能忽略资料或错误概括。因此 RAG 是给模型提供更可靠的外部依据，不是彻底消除幻觉的开关。

可以准备这样的一分钟回答：

> RAG 用于解决大模型参数知识不够新、不包含私有文档以及回答依据难追溯的问题。它在推理时先检索外部资料，再把相关内容作为 Context 交给大模型。我的项目会把 PDF 切块并写入 FAISS，提问时检索 Top-3，再让 LLM 根据资料回答，同时返回文本、页码和相似度。RAG 不会自动保证正确，效果仍取决于文档质量、切块、检索和生成约束。

---

# 三、问题二：RAG 和微调有什么区别

最重要的区别是知识进入模型的方式：

```text
RAG
→ 推理时从外部知识库取资料
→ 不修改 LLM 参数

微调
→ 使用训练数据更新部分或全部模型参数
→ 改变模型的行为或任务能力
```

RAG 更适合：

```text
知识经常更新
使用企业或个人私有文档
需要展示来源
希望快速增加或删除资料
```

微调更适合：

```text
希望模型稳定遵循特定格式
学习某类任务的表达或判断模式
适应特定风格、术语或行为
```

当前项目上传 PDF 后，只生成 Embedding 并建立 FAISS 索引，LLM 参数完全没有变化，所以这是 RAG，不是微调。删除或替换索引后，外部知识也会随之改变；如果是微调，知识或行为已经进入参数，更新和回退的成本更高。

不要回答成“RAG 和微调只能二选一”。真实系统可以先微调模型的行为，再让它通过 RAG 获取最新知识，两者可以组合。

---

# 四、问题三：Embedding 是什么

Embedding 是把文本映射成一组稠密数值向量，使语义相近的文本在向量空间中通常更接近。它不是给每个词手工设置标签，也不是把原文无损压缩到向量里。

当前项目使用：

```text
BAAI/bge-small-zh-v1.5
```

文档和问题的处理略有区别：

```python
def embed_query(self, query: str) -> list[float]:
    text = f"{QUERY_INSTRUCTION}{query}"
    ...

def embed_documents(self, texts: list[str]) -> list[list[float]]:
    ...
```

问题使用查询指令，是因为当前 BGE 模型希望用特定提示区分“查询”和“候选文档”。项目还对向量进行 L2 归一化，并使用 FAISS 的 `IndexFlatIP` 计算内积；归一化向量的内积可以作为余弦相似度使用。

相似度高只表示模型认为两段文本的语义方向接近，不等于答案必然正确，也不是概率。Embedding 负责把文本变成可比较的向量，FAISS 才负责在大量向量中执行相似搜索。

---

# 五、问题四：Chunk 大小怎样选择

长文档不能简单当成一个整体处理。一个向量如果混合太多主题，查询时很难精确匹配某个局部事实；但 Chunk 过小又会丢失上下文。

常见取舍是：

```text
Chunk 太大
→ 一个块包含多个主题
→ 检索不够精确
→ 进入 Prompt 的无关内容和 Token 增加

Chunk 太小
→ 句子或段落被切断
→ 单个块信息不完整
→ 回答可能需要的上下文分散到多个块
```

Overlap 会让相邻 Chunk 保留一部分重复内容，降低重要信息恰好被切在边界上的风险。代价是文档块数量、Embedding 成本和重复检索结果都会增加。

当前项目采用：

```text
chunk_size = 200 个字符
overlap = 40 个字符
```

这不是通用最优值，只是针对当前三页测试 PDF 的学习基线。真实论文还需要根据语言、段落结构、表述密度、Embedding 模型和问题类型，通过固定问题集进行对照评估。面试时不要只给一个数字，要先说清选择标准和验证方法。

---

# 六、问题五：Top-k 怎样选择

Top-k 表示一次检索返回最相似的前多少个 Chunk。

```text
k 太小
→ 可能漏掉答案需要的资料

k 太大
→ 无关或重复内容增加
→ Prompt 更长，成本和干扰也增加
```

读取当前项目的真实对照结论：

```powershell
$comparison = Get-Content `
    data\evaluation\top_k_comparison.json `
    -Raw | ConvertFrom-Json

$comparison.experiment
$comparison.manual_summary
```

当前结果是：

```text
固定 chunk_size=200、overlap=40
10 道可回答题
Top-1 命中 9 道
Top-3 命中 10 道
summary-02 因需要跨 Chunk 整合信息而受到 Top-3 帮助
```

因此当前接口保留 `TOP_K = 3`。但这只代表一个三页测试 PDF 和 10 道可回答题，不应说成“Top-3 永远最好”。更可靠的做法是用代表性问题集比较检索命中、回答正确率、上下文长度和延迟，再确定适合业务的 k。

---

# 七、问题六：BM25 和向量检索有什么区别

BM25 是基于词项匹配和词频统计的稀疏检索方法，擅长精确关键词、专有名词、编号和代码等字面匹配。向量检索先用 Embedding 把文本变成稠密向量，更擅长找到表达不同但语义相近的内容。

例如查询：

```text
怎样保存模型的历史键和值？
```

文档写的是：

```text
KV Cache 缓存历史 Token 的 Key 和 Value
```

向量检索可能通过语义联系找到它；如果用户直接搜索准确的 `KV Cache`、Sample ID 或错误码，BM25 的字面匹配可能更稳定。

二者都不是任何情况下都更好：

```text
BM25 依赖词面重合，可能漏掉同义表达
向量检索可能找到语义相关但不能回答问题的文本
```

当前项目只有 BGE + FAISS 向量检索，没有实现 BM25 或 Hybrid Search。今天只需要能比较原理和适用场景，不要修改项目加入新检索器。

---

# 八、问题七：Reranker 有什么作用

初次检索通常追求速度，会从大量 Chunk 中快速召回一批候选。Reranker 再使用更强但更慢的模型，同时查看“问题和候选 Chunk”，对候选重新打分和排序。

可以理解成两阶段：

```text
第一阶段 Retriever
→ 快速从全部 Chunk 中召回较多候选

第二阶段 Reranker
→ 精细比较问题与每个候选
→ 把更可能真正回答问题的 Chunk 排到前面
```

Embedding 检索通常先独立编码问题和文档，速度快且向量可预先保存；Cross-Encoder 类 Reranker 会联合处理问题和文档，交互更充分，但每次查询的计算成本更高。

当前项目没有 Reranker，FAISS 的相似度顺序直接作为最终 Top-3。加入 Reranker 可能提高排序质量，但也会增加模型依赖、延迟和评估工作，因此不能只说“加上一定更好”，仍要通过测试数据验证。

---

# 九、问题八：怎样减少幻觉

幻觉是模型生成看似合理、但没有可靠依据或与事实不符的内容。RAG 可以减少一部分知识型幻觉，但需要同时控制检索和生成两侧。

当前项目已经使用的做法有：

```text
使用外部 PDF 作为知识依据
检索 Top-3 相关 Chunk
Prompt 要求资料中没有答案时明确说明不知道
返回来源文本、页码和相似度供人工核对
使用固定问题集检查回答
```

还可以从思路上说明：

```text
提高文档质量和解析质量
优化 Chunk、Embedding 和 Top-k
过滤明显低相关候选
让 Prompt 明确只能依据资料
要求回答引用来源
对关键结论做规则或人工校验
```

不要只修改 Temperature 就声称消除了幻觉。较低随机性可能让输出更稳定，但如果检索到错误资料，模型仍然可能稳定地给出错误答案。

当前项目的相似度也没有被当成正确概率，并且还没有设置统一的拒答阈值。面试时如实说明现状和限制，比声称“项目已经解决幻觉”更可信。

---

# 十、问题九：怎样评估 RAG

RAG 至少包含检索和生成两个阶段，因此不能只看最终答案。

```text
检索评估
→ 正确资料是否进入 Top-k
→ 排名是否靠前

生成评估
→ 回答是否覆盖标准答案要点
→ 是否忠实于检索资料
→ 无答案时是否正确拒答
```

当前项目建立了 12 道固定问题：

```text
6 道直接事实题
2 道总结题
2 道对比题
2 道无答案题
```

基线结果为：

```text
chunk_size=200
overlap=40
top_k=3
10 道可回答题的检索全部命中
12 道最终回答均通过人工检查
```

Top-k 对照又把检索单独拿出来比较，并且没有调用 LLM，避免把生成随机性混入检索实验。这个设计帮助区分：

```text
正确 Chunk 没进入 Top-k
→ 主要是检索问题

正确 Chunk 已进入 Top-k，但回答仍错误
→ 主要检查 Prompt 或生成阶段
```

这些结果的样本很小，不能称为通用准确率。进一步评估可以增加真实论文、更多问题、不同切块参数、延迟和成本指标，并让人工评分标准更一致。

---

# 十一、问题十：Agent 和 Workflow 有什么区别

Workflow 是预先规定好的执行流程，步骤和分支主要由程序决定。Agent 则让 LLM 根据目标和当前状态，动态决定下一步要调用什么工具、是否继续以及何时结束。

当前项目属于固定 Workflow：

```text
上传 PDF
→ 解析
→ 切块
→ Embedding
→ FAISS 建库

用户提问
→ 问题 Embedding
→ Top-3 检索
→ 构造 Prompt
→ LLM 生成
```

每一步都由 Python 代码预先写好，LLM 不能自行跳过检索、改变 Top-k、重新上传文档或选择其他工具，所以它不是 Agent。

如果做成 Agent，可能变为：

```text
接收目标
→ LLM 判断是否需要搜索文档
→ 选择并调用检索工具
→ 检查结果是否足够
→ 必要时修改查询再次检索
→ 最终回答
```

Agent 更灵活，但执行路径更难预测，通常会增加延迟、Token 成本、权限风险和评估难度。能用固定 Workflow 稳定解决的问题，不一定需要 Agent。今天只学概念，不引入 LangGraph 或 Multi-Agent。

---

# 十二、问题十一：Function Calling 是什么

Function Calling 是让模型根据工具的名称、参数说明和 JSON Schema，返回一个结构化的工具调用请求。模型负责“建议调用哪个工具以及传什么参数”，真正执行函数的是应用程序。

例如为当前项目假设一个工具：

```json
{
  "name": "search_document",
  "description": "从已上传的 PDF 中检索相关文本",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "top_k": {"type": "integer", "minimum": 1, "maximum": 5}
    },
    "required": ["query"]
  }
}
```

模型可能返回类似：

```json
{
  "name": "search_document",
  "arguments": {
    "query": "RAG 的基础流程",
    "top_k": 3
  }
}
```

接下来应由后端完成：

```text
校验工具名和参数
→ 检查权限与调用范围
→ 执行真实检索函数
→ 把结果返回给模型
→ 模型根据工具结果继续回答
```

模型不会因为输出了函数名就自动执行本地代码，也不能绕过程序权限。Function Calling 是构建 Agent 的常用基础能力，但一次函数调用本身不等于完整 Agent；完整 Agent 通常还包含循环、状态、停止条件和错误处理。

---

# 十三、整理 RAG 与 Agent 面试回答

[[Day29-RAG与Agent面试回答]]

今天创建回答笔记：

```powershell
$answerFile = "docs\appendix\Day29-RAG与Agent面试回答.md"

if (-not (Test-Path -LiteralPath $answerFile)) {
    New-Item -Path $answerFile -ItemType File
}

code $answerFile
```

先写入下面的标题：

```markdown
# Day 29：RAG 与 Agent 面试回答

## 1. 为什么需要 RAG？
## 2. RAG 和微调有什么区别？
## 3. Embedding 是什么？
## 4. Chunk 大小怎样选择？
## 5. Top-k 怎样选择？
## 6. BM25 和向量检索有什么区别？
## 7. Reranker 有什么作用？
## 8. 怎样减少 RAG 幻觉？
## 9. 怎样评估 RAG？
## 10. Agent 和 Workflow 有什么区别？
## 11. Function Calling 是什么？
```

每道题写 4～6 句，使用这个顺序：

```text
先解释它是什么
再说明核心取舍
接着联系 Mini RAG 的真实实现或数据
最后补一个限制或常见误解
```

回答中至少写入这些真实证据：

```text
Embedding 模型：BAAI/bge-small-zh-v1.5
向量库：FAISS IndexFlatIP
chunk_size=200、overlap=40、top_k=3
Top-1 命中 9/10，Top-3 命中 10/10
当前只有向量检索，没有 BM25 和 Reranker
当前 RAG 是固定 Workflow，不是 Agent
```

不要把今天的长篇解释整段复制过去。回答笔记的目标是让你脱离 Day29 计划后，也能在一分钟左右讲清每个问题。

---

# 十四、进行一轮项目追问模拟

关闭计划文件，随机打乱问题：

```powershell
$questions = @(
    "为什么需要 RAG？"
    "RAG 和微调有什么区别？"
    "Embedding 是什么？"
    "Chunk 大小怎样选择？"
    "Top-k 怎样选择？"
    "BM25 和向量检索有什么区别？"
    "Reranker 有什么作用？"
    "怎样减少 RAG 幻觉？"
    "怎样评估 RAG？"
    "Agent 和 Workflow 有什么区别？"
    "Function Calling 是什么？"
)

$questions | Sort-Object { Get-Random }
```

随机选择至少 6 道口述。每道题先给结论，再给当前项目证据，最后说明限制。

额外练习下面的连续追问：

```text
为什么当前选择 Top-3，而不是 Top-1？
→ 用 9/10 与 10/10，以及 summary-02 回答

为什么不直接增加到 Top-10？
→ 说明噪声、Prompt 长度、延迟和成本

你的项目用了 BM25 或 Reranker 吗？
→ 如实回答没有，并说明当前只有 BGE + FAISS

你的项目是 Agent 吗？
→ 如实回答是固定 RAG Workflow，再解释 Agent 的动态决策

RAG 能彻底解决幻觉吗？
→ 回答不能，并从检索错误和生成错误分别说明
```

在回答笔记末尾记录：

```text
最流畅的三题：
最容易卡住的三题：
最需要补充的项目证据：
```

---

# 十五、检查并提交 Git

确认回答笔记包含 11 个标题：

```powershell
Select-String `
    -Path "docs\appendix\Day29-RAG与Agent面试回答.md" `
    -Pattern '^## ([1-9]|1[01])\.'
```

预期找到 11 行。再人工确认每个标题下都有自己的回答，并且 Top-k 数据没有写错。

检查今天的修改：

```powershell
git status --short
git diff --check
```

今天正常应包含：

```text
docs/Day29.md
docs/appendix/Day29-RAG与Agent面试回答.md
```

今天不需要修改：

```text
app 中的业务代码
requirements.txt
README.md
评估 JSON
Dockerfile
.env
```

确认无误后暂存：

```powershell
git add `
    docs/Day29.md `
    "docs/appendix/Day29-RAG与Agent面试回答.md"

git diff --cached --stat
git status
```

确认暂存文件正确后提交：

```powershell
git commit -m "docs: prepare RAG and Agent interview answers"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

---

# Day 29 完成标准

- [ ] 能按照上传阶段和提问阶段完整讲清当前 RAG 数据流
- [ ] 能解释为什么需要 RAG，并说明它不能保证回答一定正确
- [ ] 能从是否修改模型参数、知识更新和来源追溯区分 RAG 与微调
- [ ] 能解释 Embedding、FAISS 和相似度各自负责什么
- [ ] 能结合 `chunk_size=200`、`overlap=40` 说明 Chunk 的取舍
- [ ] 能结合 Top-1 9/10、Top-3 10/10 解释当前为何选择 Top-3
- [ ] 能说明当前评估结果只适用于小型测试集，不是通用准确率
- [ ] 能比较 BM25 与向量检索的原理和适用场景
- [ ] 能解释 Retriever 与 Reranker 的两阶段关系及成本取舍
- [ ] 能从检索和生成两侧说明怎样减少幻觉
- [ ] 能区分检索命中与最终回答正确
- [ ] 能说明当前项目是固定 Workflow，而不是 Agent
- [ ] 能解释 Agent 的灵活性以及延迟、成本、权限和评估代价
- [ ] 能解释 Function Calling 中模型与应用程序各自负责什么
- [ ] 能说明 RAG、Agent 与 Function Calling 可以组合但不是同一概念
- [ ] 已完成 `docs/appendix/Day29-RAG与Agent面试回答.md`
- [ ] 已随机口述至少 6 道题，并完成连续追问练习
- [ ] 已确认没有实现 BM25、Reranker、Agent、LangGraph 或 Multi-Agent
- [ ] 已确认没有修改业务代码、依赖、README、评估数据或 `.env`
- [ ] 检查成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
