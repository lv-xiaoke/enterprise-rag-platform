# Day 21：建立第一版 RAG 评估问题集

昨天已经完成了 `POST /upload` 和 `POST /rag/chat`，能够上传 PDF，再针对 PDF 返回回答与来源。现在项目已经“能运行”，但还不能客观说明效果好不好：随手问一两个问题得到正常回答，并不能证明检索稳定，也看不出错误究竟发生在检索还是生成阶段。今天不继续增加功能，而是根据 `sample.pdf` 的真实内容建立 12 个固定测试问题，为后面分析 Chunk、top-k 和模型回答准备一套可重复使用的基线。

---

# 一、先理解为什么需要固定问题集

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

如果每次测试都临时想一个新问题，就很难比较修改前后的效果。例如今天问“什么是 RAG”，明天修改 `chunk_size` 后却改问“Embedding 有什么作用”，即使结果不同，也无法判断是参数变化造成的，还是问题本身难度不同。

固定问题集的作用是：

```text
使用同一份 PDF
使用同一批问题
记录同一组参数
分别观察检索来源和模型回答
```

以后调整：

```text
chunk_size
overlap
top_k
```

仍然使用今天的 12 个问题，就能更公平地比较结果。

今天的评估不是训练模型，也不是追求复杂的自动评分。先建立一个人工可检查的小数据集，每个问题都有文档依据和预期答案，已经足够发现最明显的问题。

---

# 二、分清检索评估和回答评估

当前 `/rag/chat` 返回：

```json
{
  "answer": "大模型生成的回答",
  "sources": [
    "检索到的 Chunk 1",
    "检索到的 Chunk 2",
    "检索到的 Chunk 3"
  ]
}
```

因此评估时要把两个阶段分开看。

## 1. 检索是否成功

先不看 `answer`，只看 `sources`：

```text
能够支持标准答案的原文是否进入 top-3？
```

如果问题是“RAG 的英文全称是什么”，`sources` 中完全没有出现 `Retrieval-Augmented Generation`，那么首先是检索没有命中。此时模型即使碰巧凭自身知识答对，也不能说明 RAG 检索有效。

今天用字段记录：

```json
"retrieval_hit": null
```

以后测试时再填写：

```text
true：支持标准答案的资料进入了 sources
false：sources 中没有足够资料支持标准答案
null：还没有执行测试
```

## 2. 模型回答是否正确

在检索来源的基础上，再检查：

```text
answer 是否回答了问题
关键事实是否与文档一致
是否加入了 sources 中没有依据的重要信息
无答案题是否明确说明不知道
```

今天使用：

```json
"answer_correct": null
```

以后人工判断为 `true` 或 `false`。

可以出现下面四种组合：

```text
检索命中 + 回答正确：完整链路正常
检索命中 + 回答错误：生成阶段有问题
检索未命中 + 回答错误：首先检查检索
检索未命中 + 回答碰巧正确：模型用了自身知识，不能算有依据的 RAG 成功
```

这就是为什么评估文件要同时保存 `retrieved_sources` 和 `model_answer`，不能只记录最终回答。

---

# 三、设计四种问题类型

今天的 12 个问题不要全部写成“原文中某个词是什么”，而是分成四类。

## 1. 直接事实题

答案可以从文档中直接定位，例如：

```text
测试 PDF 共有多少页？
RAG 的英文全称是什么？
```

这类题主要检查检索能否找回包含明确事实的 Chunk。

## 2. 总结题

答案需要综合一段或多段资料，例如：

```text
这份测试 PDF 的主要用途是什么？
```

这类题会同时考察检索覆盖范围和模型组织答案的能力。

## 3. 对比题

需要把两个概念放在一起说明区别，例如：

```text
Chunk 和 Embedding 在 RAG 中分别负责什么？
```

如果相关信息落在不同 Chunk 中，top-3 是否能同时覆盖它们就很重要。

## 4. 文档中没有答案的问题

故意询问 PDF 没有提供的信息，例如：

```text
这份 PDF 使用了哪个 Embedding 模型？
```

项目代码虽然使用 `BAAI/bge-small-zh-v1.5`，但 `sample.pdf` 并没有写这个信息。RAG 应该根据上传文档回答，而不是把项目代码或模型自身知识混进来，所以理想回答是“参考资料中没有说明”。

无答案题主要检查 Prompt 中这句约束是否生效：

```text
如果参考资料中没有答案，请明确说明不知道。
```

---

# 四、先完整查看测试 PDF 的真实内容

标准答案必须来自被评估的文档，不能凭印象编写。执行：

```powershell
$env:PYTHONIOENCODING = "utf-8"

@'
from app.services.pdf_service import PDFService


pages = PDFService().extract_pages(
    "data/documents/sample.pdf"
)

for page_number, text in enumerate(pages, start=1):
    print(f"\n===== 第 {page_number} 页 =====")
    print(text)
'@ | python -
```

阅读三页文字，确认今天问题集依据的主要事实：

```text
PDF 一共有 3 页
RAG 全称是 Retrieval-Augmented Generation
RAG 中文常译为“检索增强生成”
基础流程包括接收问题、检索文档、拼接上下文、调用大模型
Embedding 把文本转换成向量，用于计算语义相似度
FastAPI 可以快速构建 Python Web API
切分长文档能让系统更容易找到真正相关的片段
Sample ID 是 mini-rag-pdf-test-001
文档没有提供作者、发表年份和具体 Embedding 模型名称
```

如果终端中文乱码，先确认：

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
```

今天不要根据项目代码替 PDF 补充答案。评估对象是上传文档，标准答案必须以 PDF 内容为准。

---

# 五、创建评估问题文件

创建目录：

```powershell
New-Item -ItemType Directory -Force data\evaluation
```

新建：

```text
data/evaluation/questions.json
```

写入下面的内容：

```json
{
  "document": "data/documents/sample.pdf",
  "baseline": {
    "chunk_size": 200,
    "overlap": 40,
    "top_k": 3
  },
  "cases": [
    {
      "id": "fact-01",
      "category": "direct_fact",
      "question": "这份测试 PDF 一共有多少页？",
      "answerable": true,
      "expected_answer": "这份测试 PDF 一共有 3 页。",
      "expected_points": ["3 页"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "fact-02",
      "category": "direct_fact",
      "question": "RAG 的英文全称和中文常用译名分别是什么？",
      "answerable": true,
      "expected_answer": "RAG 的英文全称是 Retrieval-Augmented Generation，中文常译为检索增强生成。",
      "expected_points": [
        "Retrieval-Augmented Generation",
        "检索增强生成"
      ],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "fact-03",
      "category": "direct_fact",
      "question": "文档介绍的基础 RAG 流程包括哪些步骤？",
      "answerable": true,
      "expected_answer": "基础流程包括接收用户问题、检索相关文档、拼接上下文、调用大模型生成回答。",
      "expected_points": [
        "接收用户问题",
        "检索相关文档",
        "拼接上下文",
        "调用大模型生成回答"
      ],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "fact-04",
      "category": "direct_fact",
      "question": "Embedding 在文档中被描述为什么作用？",
      "answerable": true,
      "expected_answer": "Embedding 可以把文本转换成向量，用于计算语义相似度。",
      "expected_points": ["文本转换成向量", "语义相似度"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "fact-05",
      "category": "direct_fact",
      "question": "FastAPI 在文档中可以用来做什么？",
      "answerable": true,
      "expected_answer": "FastAPI 可以用来快速构建 Python Web API。",
      "expected_points": ["快速构建", "Python Web API"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "fact-06",
      "category": "direct_fact",
      "question": "这份测试 PDF 的 Sample ID 是什么？",
      "answerable": true,
      "expected_answer": "Sample ID 是 mini-rag-pdf-test-001。",
      "expected_points": ["mini-rag-pdf-test-001"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "summary-01",
      "category": "summary",
      "question": "这份 PDF 的主要用途是什么？",
      "answerable": true,
      "expected_answer": "它是一份用于本地开发和 PDF 文本提取验证的安全测试样例，正文可以选中复制。",
      "expected_points": [
        "本地开发测试",
        "PDF 文本提取",
        "文本可以选中或复制"
      ],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "summary-02",
      "category": "summary",
      "question": "根据文档，概括一个最基础的 RAG 如何从文档得到回答。",
      "answerable": true,
      "expected_answer": "先处理并切分文档，把文本转换成向量；用户提问后检索相关片段，拼接为上下文，再让大模型生成回答。",
      "expected_points": [
        "切分文档",
        "文本转换成向量",
        "检索相关片段",
        "上下文",
        "大模型生成回答"
      ],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "compare-01",
      "category": "comparison",
      "question": "把长文档整体向量化与先切成较小 Chunk 相比，有什么区别？",
      "answerable": true,
      "expected_answer": "长文档整体向量化通常会使检索不够精确；切成较小 Chunk 后，系统更容易找到与问题真正相关的片段。",
      "expected_points": ["整体向量化不够精确", "更容易找到相关片段"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "compare-02",
      "category": "comparison",
      "question": "Chunk 和 Embedding 在 RAG 中分别负责什么？",
      "answerable": true,
      "expected_answer": "Chunk 负责把文档切成较小文本片段，Embedding 负责把文本转换成向量表示。",
      "expected_points": ["文档切分后的文本片段", "文本转换为向量"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "unknown-01",
      "category": "unanswerable",
      "question": "这份 PDF 使用了哪个具体的 Embedding 模型？",
      "answerable": false,
      "expected_answer": "文档没有说明具体使用了哪个 Embedding 模型。",
      "expected_points": ["明确说明文档未提供该信息"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    },
    {
      "id": "unknown-02",
      "category": "unanswerable",
      "question": "这份 PDF 的作者是谁，发表于哪一年？",
      "answerable": false,
      "expected_answer": "文档没有提供作者和发表年份。",
      "expected_points": ["明确说明作者和年份均未提供"],
      "retrieved_sources": [],
      "model_answer": "",
      "retrieval_hit": null,
      "answer_correct": null,
      "notes": ""
    }
  ]
}
```

这里把当前接口参数写进 `baseline`：

```json
"chunk_size": 200,
"overlap": 40,
"top_k": 3
```

以后参数发生变化时，要另行记录测试使用的参数，不能让同一份结果失去实验条件。

`expected_points` 不是要求模型逐字复述，而是帮助人工检查回答有没有覆盖关键事实。例如回答可以换一种说法，只要含义正确、依据充分，就可以判断为正确。

---

# 六、验证 JSON 结构和问题分布

先检查 JSON 是否能被 Python 正常读取：

```powershell
python -m json.tool data\evaluation\questions.json > $null
```

如果没有输出也没有报错，表示 JSON 语法正确。如果提示类似：

```text
Expecting ',' delimiter
```

通常是上一行末尾漏了逗号，或者字符串的双引号没有配对。JSON 中不能写 `# 注释` 或 `// 注释`。

再运行结构检查：

```powershell
$env:PYTHONIOENCODING = "utf-8"

@'
import json
from collections import Counter
from pathlib import Path


path = Path("data/evaluation/questions.json")
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

ids = [case["id"] for case in cases]
categories = Counter(
    case["category"] for case in cases
)

assert 10 <= len(cases) <= 15
assert len(ids) == len(set(ids))
assert all(case["question"].strip() for case in cases)
assert all(case["expected_answer"].strip() for case in cases)
assert all(case["retrieval_hit"] is None for case in cases)
assert all(case["answer_correct"] is None for case in cases)
assert categories == {
    "direct_fact": 6,
    "summary": 2,
    "comparison": 2,
    "unanswerable": 2,
}

print("问题总数：", len(cases))
print("问题分布：", dict(categories))
print("评估问题集验证通过")
'@ | python -
```

预期输出：

```text
问题总数： 12
问题分布： {'direct_fact': 6, 'summary': 2, 'comparison': 2, 'unanswerable': 2}
评估问题集验证通过
```

这个检查只验证数据结构，不代表标准答案一定正确。标准答案仍要由你对照 PDF 人工核对。

---

# 七、人工检查标准答案是否公平

逐个阅读 12 个问题，重点检查：

```text
问题表述是否清楚，不依赖对话中的隐藏上下文
answerable=true 的答案是否真的能从 sample.pdf 找到依据
answerable=false 的信息是否确实没有出现在 PDF 中
expected_answer 是否没有混入项目代码中的额外知识
问题之间是否只是换词重复
```

特别注意：

```text
“使用哪个 Embedding 模型”是无答案题
```

虽然你知道项目代码使用：

```text
BAAI/bge-small-zh-v1.5
```

但上传文档没有写出这个名称，所以模型不应该根据项目背景补答。这里正好用来检查 RAG 是否遵守“只根据参考资料回答”的约束。

今天不要填写：

```json
"retrieved_sources"
"model_answer"
"retrieval_hit"
"answer_correct"
```

这些字段保持初始状态，表示评估尚未执行。下一次会使用同一份问题集运行基线，先检查哪些问题的正确资料进入 top-3，再分析模型回答。

下面的代码修改 target_id = "fact-02" 的编号即可调用不同的问题

```powershell

$env:PYTHONIOENCODING = "utf-8"

@'
import json
from pathlib import Path

import httpx


target_id = "unknown-01"

question_path = Path("data/evaluation/questions.json")
pdf_path = Path("data/documents/sample.pdf")

data = json.loads(
    question_path.read_text(encoding="utf-8-sig")
)

case = next(
    item
    for item in data["cases"]
    if item["id"] == target_id
)

with httpx.Client(
    base_url="http://127.0.0.1:8000",
    timeout=120.0,
) as client:
    # 先上传 PDF，建立内存索引
    with pdf_path.open("rb") as pdf_file:
        upload_response = client.post(
            "/upload",
            files={
                "file": (
                    pdf_path.name,
                    pdf_file,
                    "application/pdf",
                )
            },
        )
    upload_response.raise_for_status()

    # 只把 question 发给 RAG，不发送标准答案
    chat_response = client.post(
        "/rag/chat",
        json={"question": case["question"]},
    )
    chat_response.raise_for_status()
    result = chat_response.json()


print("问题 ID：", case["id"])
print("问题：", case["question"])

print("\n标准答案：")
print(case["expected_answer"])

print("\n关键得分点：")
for point in case["expected_points"]:
    print("-", point)

print("\n检索结果：")
for index, source in enumerate(
    result["sources"],
    start=1,
):
    print(f"\n[来源 {index}]")
    print(source)

print("\n模型回答：")
print(result["answer"])
'@ | .\.venv\Scripts\python.exe -

```



---

# 八、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- data/evaluation/questions.json docs/Day21.md
```

今天正常只应新增：

```text
data/evaluation/questions.json
docs/Day21.md
```

新文件可能不会显示在普通 `git diff` 中，可以执行：

```powershell
Get-Content data\evaluation\questions.json
```

确认：

```text
没有修改 app 目录中的业务代码
没有调整 CHUNK_SIZE、CHUNK_OVERLAP 或 TOP_K
没有批量调用 /rag/chat 和消耗模型额度
没有把模型回答伪装成尚未执行的评估结果
没有提交 sample.pdf、chat.db 或 .env
```

验证通过后执行：

```powershell
git add data/evaluation/questions.json docs/Day21.md
git status
```

确认暂存区只有今天的评估问题和学习记录，再提交：

```powershell
git commit -m "test: add RAG evaluation questions"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看笔记说明：为什么评估必须使用固定问题，直接事实题、总结题、对比题和无答案题分别检查什么，为什么要把检索命中和回答正确分开记录，以及为什么模型凭自身知识答对不能直接算 RAG 成功。

---

# Day 21 完成标准

- [ ] 能解释为什么固定问题集比临时提问更适合比较 RAG 效果
- [ ] 能区分检索命中与模型回答正确
- [ ] 能解释直接事实题、总结题、对比题和无答案题各自检查什么
- [ ] 已完整阅读 `sample.pdf` 的三页提取文本，并以文档内容为标准答案依据
- [ ] 已创建 `data/evaluation/questions.json`
- [ ] 问题集包含 12 个问题，覆盖四种问题类型
- [ ] 每个问题都有唯一 ID、标准答案、关键得分点和空白评估字段
- [ ] 已记录基线参数 `chunk_size=200`、`overlap=40`、`top_k=3`
- [ ] JSON 语法和问题分布检查均已通过
- [ ] 已人工确认两道无答案题的信息没有出现在 PDF 中
- [ ] 已确认今天没有修改业务代码、调整检索参数或批量调用大模型
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
