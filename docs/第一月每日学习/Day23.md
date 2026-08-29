# Day 23：用 Top-1 与 Top-3 对照实验分析检索质量

昨天已经运行完 12 道题的 RAG 基线评估。根据当前的 `baseline_results.json`，10 道可回答题的 top-3 检索都命中了所需资料，12 道题的最终回答也都判断为正确。这说明当前系统在这份小型测试 PDF 上没有明显失败案例，但还不能直接得出“检索已经不需要优化”的结论。

首先，两道无答案题目前被误填成了 `retrieval_hit=true`。无答案题在 PDF 中本来就不存在正确资料块，所以这个指标应该是 `null`，只需要判断模型是否正确拒答。其次，当前的二元命中率只表示“正确资料有没有出现”，看不出 top-3 中额外两个 Chunk 是否有用，也看不出是否带来了重复内容、无关内容或从句子中间切开的片段。

今天只研究一个变量：保持 `chunk_size=200`、`overlap=40`、测试 PDF、问题集和 Embedding 模型不变，比较 `top_k=1` 与 `top_k=3` 的检索结果。实验不调用 LLM，也不需要启动 FastAPI，这样观察到的差异只来自检索数量，而不是模型回答的随机性。

今天约 1 小时的安排是：

```text
0～5 分钟：纠正无答案题的评分口径
5～15 分钟：理解单变量对照实验
15～30 分钟：编写 top-k 检索对比脚本
30～40 分钟：运行脚本并验证结果结构
40～55 分钟：人工检查 10 道可回答题
55～60 分钟：统计结论并提交 Git
```

---

# 一、先纠正昨天的无答案题评分

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

打开基线结果：

```powershell
code data\evaluation\baseline_results.json
```

找到：

```text
unknown-01
unknown-02
```

只把这两道题的：

```json
"retrieval_hit": true
```

改为：

```json
"retrieval_hit": null
```

不要改动它们的 `answer_correct=true`。这两个字段回答的是不同问题：

```text
retrieval_hit
→ 检索结果是否包含回答所需的文档依据

answer_correct
→ 模型最终回答是否符合标准
```

无答案题没有“应该检索到的正确答案”，所以 `retrieval_hit` 不适用；如果模型明确说明文档没有提供信息，它的 `answer_correct` 仍然可以是 `true`。

修改后运行验证：

```powershell
@'
import json
from pathlib import Path


path = Path(
    "data/evaluation/baseline_results.json"
)
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

answerable_cases = [
    case for case in cases if case["answerable"]
]
unanswerable_cases = [
    case for case in cases if not case["answerable"]
]

assert all(
    case["retrieval_hit"] is not None
    for case in answerable_cases
)
assert all(
    case["retrieval_hit"] is None
    for case in unanswerable_cases
)

retrieval_hits = sum(
    case["retrieval_hit"] is True
    for case in answerable_cases
)
answer_hits = sum(
    case["answer_correct"] is True
    for case in cases
)

print(
    "可回答题检索命中：",
    f"{retrieval_hits}/{len(answerable_cases)}",
)
print(
    "全部问题回答正确：",
    f"{answer_hits}/{len(cases)}",
)
'@ | .\.venv\Scripts\python.exe -
```

根据当前已经完成的人工评分，应该得到：

```text
可回答题检索命中： 10/10
全部问题回答正确： 12/12
```

以后计算检索命中率时，分母应明确使用 `answerable=true` 的题目，而不是依赖所有非空的 `retrieval_hit`。这样即使人工误填了无答案题，也不容易污染检索指标。

---

# 二、理解今天为什么只改变 top-k

如果一次同时修改：

```text
chunk_size
overlap
top_k
```

即使结果变好了，也无法判断是哪一个参数产生了作用。今天采用单变量对照：

```text
共同条件：sample.pdf、10 道可回答题、chunk_size=200、overlap=40

方案 A：top_k=1
方案 B：top_k=3
```

`top_k=1` 只返回相似度最高的一个 Chunk。它的优点是上下文更短、噪声更少，缺点是一个 Chunk 可能无法覆盖总结题或比较题需要的多个要点。

`top_k=3` 返回前三个 Chunk。它更可能找全资料，但额外结果也可能重复、无关，最终还会增加发送给 LLM 的上下文长度。

同一个索引中，top-3 的第一名应该与 top-1 完全相同。因此今天关注的是：

```text
top-1 已经足够回答哪些问题
哪些问题必须依赖第 2 或第 3 个 Chunk 才能命中
额外 Chunk 是否只是重复或无关内容
字符切块是否产生了明显的半句、断词现象
```

今天不调用 `/rag/chat`，因为一旦加入 LLM，回答差异可能来自模型生成，而不是检索。先把检索层单独看清楚，再讨论最终回答。

---

# 三、创建 top-k 对比脚本

新建：

```text
scripts/compare_top_k.py
```

写入：

```python
import json
from pathlib import Path

from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.vector_store import FAISSVectorStore


QUESTIONS_PATH = Path(
    "data/evaluation/questions.json"
)
RESULTS_PATH = Path(
    "data/evaluation/top_k_comparison.json"
)
TOP_K_VALUES = (1, 3)


def format_sources(
    results: list[tuple[str, float]],
) -> list[dict]:
    """为人工检查保留排名、相似度和原文。"""
    return [
        {
            "rank": rank,
            "score": round(score, 6),
            "text": text,
        }
        for rank, (text, score) in enumerate(
            results,
            start=1,
        )
    ]


def main() -> None:
    data = json.loads(
        QUESTIONS_PATH.read_text(
            encoding="utf-8-sig"
        )
    )
    baseline = data["baseline"]
    document_path = Path(data["document"])

    pages = PDFService().extract_pages(
        document_path
    )
    chunks: list[str] = []

    for page_text in pages:
        chunks.extend(
            split_text(
                page_text,
                chunk_size=baseline["chunk_size"],
                overlap=baseline["overlap"],
            )
        )

    if not chunks:
        raise ValueError("测试 PDF 没有生成 Chunk")

    print("加载 Embedding 模型……")
    embedding_service = EmbeddingService()
    document_vectors = (
        embedding_service.embed_documents(chunks)
    )

    vector_store = FAISSVectorStore(
        dimension=len(document_vectors[0])
    )
    vector_store.add(chunks, document_vectors)

    answerable_cases = [
        case
        for case in data["cases"]
        if case["answerable"]
    ]
    comparison_cases: list[dict] = []

    for position, case in enumerate(
        answerable_cases,
        start=1,
    ):
        print(
            f"[{position}/{len(answerable_cases)}] "
            f"{case['id']}"
        )
        query_vector = (
            embedding_service.embed_query(
                case["question"]
            )
        )

        comparison_case = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_answer": (
                case["expected_answer"]
            ),
            "expected_points": (
                case["expected_points"]
            ),
            "comparison_notes": "",
        }

        for top_k in TOP_K_VALUES:
            results = vector_store.search(
                query_vector,
                top_k=top_k,
            )
            comparison_case[f"top_{top_k}"] = {
                "retrieved_sources": (
                    format_sources(results)
                ),
                "retrieval_hit": None,
            }

        comparison_cases.append(
            comparison_case
        )

    output = {
        "document": str(document_path),
        "experiment": {
            "fixed_chunk_size": (
                baseline["chunk_size"]
            ),
            "fixed_overlap": baseline["overlap"],
            "top_k_values": list(TOP_K_VALUES),
            "question_count": len(
                comparison_cases
            ),
            "calls_llm": False,
        },
        "manual_summary": {
            "top_1_hits": None,
            "top_3_hits": None,
            "cases_helped_by_top_3": [],
            "conclusion": "",
        },
        "cases": comparison_cases,
    }

    RESULTS_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Chunk 数量：", len(chunks))
    print("结果已保存到：", RESULTS_PATH)


if __name__ == "__main__":
    main()
```

这个脚本复用了项目当前真正使用的四个组件：

```text
PDFService
→ 提取 sample.pdf 的文本

split_text
→ 按基线参数 200/40 切块

EmbeddingService
→ 为文档块和问题生成向量

FAISSVectorStore
→ 对同一个问题分别搜索 top-1 和 top-3
```

脚本只处理 10 道 `answerable=true` 的题。两道无答案题适合检查模型是否拒答，却不适合比较“正确资料是否进入 top-k”，所以不进入今天的检索命中率分母。

`score` 是当前归一化向量经过 FAISS 内积检索得到的相似度。今天可以用它观察同一道题内部的排名差距，但不要根据这 10 道题立即制定一个通用阈值。

---

# 四、先检查语法，再运行检索实验

检查脚本语法：

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\compare_top_k.py
```

然后从项目根目录以模块方式运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_top_k
```

这里使用：

```text
-m scripts.compare_top_k
```

是为了让项目根目录正确进入 Python 的模块搜索路径，使脚本能够导入 `app.services`。今天不需要启动 Uvicorn，也不会调用 LLM API；本地 Embedding 模型第一次加载时可能需要稍等片刻。

正常情况下会看到：

```text
加载 Embedding 模型……
[1/10] fact-01
……
[10/10] compare-02
Chunk 数量：……
结果已保存到： data\evaluation\top_k_comparison.json
```

运行后验证结果结构：

```powershell
@'
import json
from pathlib import Path


path = Path(
    "data/evaluation/top_k_comparison.json"
)
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

assert len(cases) == 10

for case in cases:
    top_1 = case["top_1"][
        "retrieved_sources"
    ]
    top_3 = case["top_3"][
        "retrieved_sources"
    ]

    assert len(top_1) == 1
    assert len(top_3) == 3
    assert top_1[0]["text"] == top_3[0]["text"]
    assert top_1[0]["score"] == top_3[0]["score"]
    assert case["top_1"]["retrieval_hit"] is None
    assert case["top_3"]["retrieval_hit"] is None

print("问题数量：", len(cases))
print("top-1/top-3 结果结构验证通过")
'@ | .\.venv\Scripts\python.exe -
```

如果第一名不一致，先不要继续评分。检查两次检索是否确实使用了同一个 `query_vector` 和同一个 `vector_store`。

---

# 五、逐题比较 top-1 与 top-3

打开实验结果：

```powershell
code data\evaluation\top_k_comparison.json
```

每道题先阅读：

```text
question
expected_answer
expected_points
```

然后按以下顺序评分。

## 1. 判断 top-1

只看：

```json
"top_1": {
  "retrieved_sources": [
    {
      "rank": 1,
      "score": 0.0,
      "text": "……"
    }
  ],
  "retrieval_hit": null
}
```

如果这一个 Chunk 已经包含回答问题所需的资料，把它改成：

```json
"retrieval_hit": true
```

如果缺少关键资料，改成：

```json
"retrieval_hit": false
```

## 2. 判断 top-3

把三个 `text` 合起来阅读。如果三者合起来包含回答所需的资料，就填写：

```json
"retrieval_hit": true
```

否则填写：

```json
"retrieval_hit": false
```

评分时按题型使用一致标准：

```text
direct_fact
→ 来源中出现回答该事实所需的明确依据

summary
→ 多个来源合起来覆盖 expected_points 中的主要步骤

comparison
→ 来源同时包含被比较双方的关键依据
```

不要要求 PDF 原文与 `expected_answer` 逐字一致，但也不能因为主题相近就算命中。例如问题询问测试地址，只检索到“使用 curl 测试”而没有地址，仍然不能算命中。

## 3. 记录额外 Chunk 的实际作用

在每道题的：

```json
"comparison_notes": ""
```

中写一句简短结论，例如：

```json
"comparison_notes": "top-1 已包含完整事实，后两个来源没有增加必要信息"
```

或者：

```json
"comparison_notes": "top-1 只有定义，第 2 个来源补全了流程步骤"
```

还要留意两类质量问题：

```text
噪声
→ 后两个 Chunk 与问题无关或只是重复第一名

边界
→ Chunk 从词语、英文单词或句子中间开始，阅读不完整
```

即使 top-3 包含无关内容，只要其中已经有正确资料，`retrieval_hit` 仍然是 `true`。噪声不能用这个二元指标表达，所以要写进 `comparison_notes`。这正是“命中率 100%”仍然需要人工分析来源质量的原因。

---

# 六、统计两个方案的命中结果

10 道题全部评分后运行：

```powershell
@'
import json
from pathlib import Path


path = Path(
    "data/evaluation/top_k_comparison.json"
)
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

for key in ("top_1", "top_3"):
    pending = [
        case["id"]
        for case in cases
        if case[key]["retrieval_hit"] is None
    ]
    if pending:
        raise ValueError(
            f"{key} 尚未评分：{pending}"
        )

top_1_hits = sum(
    case["top_1"]["retrieval_hit"] is True
    for case in cases
)
top_3_hits = sum(
    case["top_3"]["retrieval_hit"] is True
    for case in cases
)
helped_by_top_3 = [
    case["id"]
    for case in cases
    if not case["top_1"]["retrieval_hit"]
    and case["top_3"]["retrieval_hit"]
]
inconsistent = [
    case["id"]
    for case in cases
    if case["top_1"]["retrieval_hit"]
    and not case["top_3"]["retrieval_hit"]
]

assert not inconsistent, (
    "top-3 包含 top-1，出现命中下降时应检查评分："
    f"{inconsistent}"
)

print("top-1 命中：", f"{top_1_hits}/10")
print("top-3 命中：", f"{top_3_hits}/10")
print("top-3 新增帮助：", helped_by_top_3)
'@ | .\.venv\Scripts\python.exe -
```

为什么理论上不应出现：

```text
top-1 命中
top-3 反而不命中
```

因为 top-3 本身包含 top-1 的结果。`retrieval_hit` 只判断正确资料是否存在，不因增加噪声而从 `true` 变成 `false`。如果真的出现这种情况，通常是人工评分标准前后不一致。

最后把统计值填写到文件顶部的：

```json
"manual_summary": {
  "top_1_hits": 0,
  "top_3_hits": 0,
  "cases_helped_by_top_3": [],
  "conclusion": ""
}
```

这里的数字要替换成实际结果，不要照抄示例中的 `0`。

---

# 七、根据数据写出结论，不急着改生产参数

如果结果是：

```text
top-1 = 10/10
top-3 = 10/10
```

可以得出的结论是：在当前 `sample.pdf` 和这 10 道可回答题上，额外两个 Chunk 没有提高检索命中率，并且可能增加上下文长度或噪声。

不能直接得出：

```text
所有文档都应该使用 top_k=1
```

因为当前 PDF 很短、问题数量很少，而且题目主要由你根据同一份文档编写，覆盖范围还不够大。

如果结果是：

```text
top-1 < top-3
```

就逐个查看 `cases_helped_by_top_3`。重点判断它们是否集中在 `summary` 或 `comparison` 类型；如果是，说明多要点问题确实需要多个来源，当前保留 `top_k=3` 更合理。

如果观察到来源经常从句子或单词中间开始，把它写入 `conclusion`。这提示后续可以单独比较 `chunk_size`、`overlap`，或者研究按段落、标题和句子边界切块。但今天不要同时修改切块逻辑，否则会破坏 top-k 单变量实验。

今天也不要修改：

```text
app/main.py 中的 TOP_K
RAGService 的生成 Prompt
Embedding 模型
questions.json 的问题与标准答案
```

今天的产物是检索证据和实验结论，而不是为了追求更高数字直接改业务参数。

---

# 八、检查改动并提交 Git

先查看工作区：

```powershell
git status --short
```

今天正常应看到：

```text
修改 data/evaluation/baseline_results.json
新增 scripts/compare_top_k.py
新增 data/evaluation/top_k_comparison.json
新增 docs/Day23.md
```

检查：

```text
baseline_results.json 只纠正了两道无答案题的 retrieval_hit
top_k_comparison.json 只包含 10 道可回答题
top-1 和 top-3 的人工评分已经全部完成
manual_summary 已填写真实统计值和结论
没有调用 LLM，也没有覆盖 questions.json
没有修改 app/main.py 或其他业务代码
结果文件不包含 API Key、.env 内容或其他秘密
```

暂存今天的文件：

```powershell
git add docs/Day23.md scripts/compare_top_k.py data/evaluation/baseline_results.json data/evaluation/top_k_comparison.json
git diff --cached --stat
git status
```

确认暂存区只有今天的实验文件，再提交：

```powershell
git commit -m "test: compare top-k retrieval quality"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看笔记说明：为什么无答案题不参与检索命中率，为什么今天不调用 LLM，为什么对照实验只能改变一个主要变量，以及为什么 top-3 命中率不低于 top-1 并不代表 top-3 的上下文质量一定更好。

---

# Day 23 完成标准

- [ ] 已把 `unknown-01` 和 `unknown-02` 的 `retrieval_hit` 纠正为 `null`
- [ ] 能区分检索命中与最终回答正确这两个指标
- [ ] 能解释为什么今天固定 `chunk_size=200` 和 `overlap=40`，只比较 top-k
- [ ] 已创建 `scripts/compare_top_k.py`
- [ ] 脚本只评估 10 道可回答题，不把无答案题放入检索命中率分母
- [ ] 脚本复用当前 PDF、切块、Embedding 和 FAISS 组件，没有调用 LLM
- [ ] 已生成 `data/evaluation/top_k_comparison.json`
- [ ] 已验证每道题的 top-1 与 top-3 第一名一致
- [ ] 已逐题填写 top-1 和 top-3 的 `retrieval_hit`
- [ ] 已在 `comparison_notes` 中记录额外 Chunk 的作用、噪声或边界问题
- [ ] 已计算 top-1、top-3 命中数以及受额外来源帮助的题目
- [ ] 已在 `manual_summary` 中填写真实数据和有范围限制的结论
- [ ] 已确认今天没有修改生产环境的 top-k、切块参数或 RAG Prompt
- [ ] 已检查暂存内容、完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
