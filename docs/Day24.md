# Day 24：让 RAG 接口返回页码和相似度

昨天完成了 Top-1 与 Top-3 的检索对照实验：在当前 10 道可回答题中，Top-1 命中 9 道，Top-3 命中 10 道，`summary-02` 需要额外 Chunk 才能覆盖完整信息。因此当前项目继续保留 `top_k=3` 是有实际依据的。

现在 `/rag/chat` 的 `sources` 仍然只是字符串列表。虽然 FAISS 搜索已经计算了相似度，但 `RAGService` 把分数丢掉了；上传 PDF 时也只保存了 Chunk 文本，没有保留它来自哪一页。今天要把这条元数据链路补完整，让接口的每条来源都返回文本、PDF 页码和相似度。这样既方便用户核对答案，也方便你以后判断检索结果为什么排在前面。

---

# 一、先看清当前信息丢在哪里

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

当前上传 PDF 时，`app/main.py` 使用的是：

```python
chunks: list[str] = []
for page_text in pages:
    chunks.extend(split_text(page_text, ...))
```

这里遍历了每一页，却没有记录 `page_text` 是第几页。切块完成后只剩文本，页码已经无法恢复。

当前 `FAISSVectorStore.search()` 实际返回：

```python
list[tuple[str, float]]
```

也就是：

```text
(Chunk 文本, 相似度分数)
```

但 `RAGService.answer()` 又执行：

```python
sources = [
    text
    for text, _score in search_results
]
```

变量名 `_score` 表示这个值暂时不用，所以最终接口只得到文本。

今天要把数据流改成：

```text
PDF 第几页
→ DocumentChunk(text, page)
→ 对 Chunk 文本生成向量
→ FAISS 返回向量位置和分数
→ 用位置找到原来的 DocumentChunk
→ SearchResult(text, page, score)
→ RAGSource(text, page, score)
→ JSON 响应
```

FAISS 本身主要负责保存和搜索向量，不会自动理解“页码”。我们的做法是让 Chunk 元数据列表与 FAISS 向量保持完全相同的顺序。FAISS 返回索引位置后，再使用这个位置取回对应的文本和页码。

---

# 二、让向量库同时保存 Chunk 元数据

打开：

```text
app/services/vector_store.py
```

将文件改为：

```python
from dataclasses import dataclass

import faiss
import numpy as np


@dataclass(frozen=True)
class DocumentChunk:
    """一个等待写入向量库的文档块。"""

    text: str
    page: int


@dataclass(frozen=True)
class SearchResult:
    """一次向量检索得到的来源信息。"""

    text: str
    page: int
    score: float


class FAISSVectorStore:
    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[DocumentChunk] = []

    @property
    def count(self) -> int:
        return self.index.ntotal

    def add(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if not chunks:
            raise ValueError("chunks 不能为空")
        if len(chunks) != len(vectors):
            raise ValueError(
                "chunks 和 vectors 的数量必须一致"
            )
        if any(not chunk.text.strip() for chunk in chunks):
            raise ValueError("Chunk 文本不能为空")
        if any(chunk.page <= 0 for chunk in chunks):
            raise ValueError("Chunk 页码必须大于 0")

        matrix = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if matrix.ndim != 2:
            raise ValueError("vectors 必须是二维数组")
        if matrix.shape[1] != self.dimension:
            raise ValueError(
                f"向量维度应为 {self.dimension}，"
                f"实际为 {matrix.shape[1]}"
            )

        matrix = np.ascontiguousarray(matrix)
        faiss.normalize_L2(matrix)

        self.index.add(matrix)
        self.chunks.extend(chunks)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 3,
    ) -> list[SearchResult]:
        if not query_vector:
            raise ValueError("query_vector 不能为空")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        if self.count == 0:
            return []

        query_matrix = np.asarray(
            [query_vector],
            dtype=np.float32,
        )

        if (
            query_matrix.ndim != 2
            or query_matrix.shape[1] != self.dimension
        ):
            actual_dimension = (
                query_matrix.shape[1]
                if query_matrix.ndim == 2
                else "未知"
            )
            raise ValueError(
                f"查询向量维度应为 {self.dimension}，"
                f"实际为 {actual_dimension}"
            )

        query_matrix = np.ascontiguousarray(
            query_matrix
        )
        faiss.normalize_L2(query_matrix)

        k = min(top_k, self.count)
        scores, indices = self.index.search(
            query_matrix,
            k,
        )

        results: list[SearchResult] = []

        for index, score in zip(
            indices[0],
            scores[0],
        ):
            if index < 0:
                continue

            chunk = self.chunks[int(index)]
            results.append(
                SearchResult(
                    text=chunk.text,
                    page=chunk.page,
                    score=float(score),
                )
            )

        return results
```

这里新增了两个内部数据类型：

```text
DocumentChunk
→ 写入向量库之前保存文本和页码

SearchResult
→ 搜索之后保存文本、页码和分数
```

`@dataclass` 适合这种主要用于保存数据的普通 Python 类。`frozen=True` 表示对象创建后不能随意修改字段，可以减少“向量已经写入，但对应页码后来被改掉”之类的问题。

最关键的对应关系是：

```python
self.index.add(matrix)
self.chunks.extend(chunks)
```

两者使用相同顺序保存。搜索得到 `index` 后：

```python
chunk = self.chunks[int(index)]
```

就能取回这个向量对应的原始文本和页码。

---

# 三、上传 PDF 时给每个 Chunk 标记页码

打开：

```text
app/main.py
```

把原来的导入：

```python
from app.services.vector_store import FAISSVectorStore
```

改成：

```python
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
)
```

然后找到 `upload_pdf()` 中创建 Chunk 的部分，将原来的字符串列表改成：

```python
chunks: list[DocumentChunk] = []

for page_number, page_text in enumerate(
    pages,
    start=1,
):
    page_chunks = split_text(
        page_text,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
    )
    chunks.extend(
        DocumentChunk(
            text=chunk_text,
            page=page_number,
        )
        for chunk_text in page_chunks
    )

if not chunks:
    raise ValueError("PDF 没有生成任何 Chunk")

document_vectors = (
    embedding_service.embed_documents(
        [chunk.text for chunk in chunks]
    )
)

vector_store = FAISSVectorStore(
    dimension=len(document_vectors[0])
)
vector_store.add(chunks, document_vectors)
```

注意：

```python
enumerate(pages, start=1)
```

让 Python 列表中的第一个页面记为 PDF 第 1 页，而不是第 0 页。这里的 `page` 指 PDF 文件中的物理页序号，不依赖页面正文是否恰好印着“第 1 页”。

Embedding 模型仍然只接收字符串，所以传入：

```python
[chunk.text for chunk in chunks]
```

页码不会参与向量计算，它只作为元数据与文本一起保存。

`UploadResponse` 不需要变化，下面的代码仍然有效：

```python
chunk_count=len(chunks)
```

因为 `len()` 只关心列表里有多少个元素，不关心元素是字符串还是 `DocumentChunk`。

---

# 四、定义接口要返回的来源结构

打开：

```text
app/models.py
```

在 `RAGChatResponse` 前面新增：

```python
class RAGSource(BaseModel):
    """一条可供用户核对的 RAG 来源。"""

    text: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float
```

再把原来的：

```python
class RAGChatResponse(BaseModel):
    """RAG 问答响应。"""

    answer: str
    sources: list[str]
```

改为：

```python
class RAGChatResponse(BaseModel):
    """RAG 问答响应。"""

    answer: str
    sources: list[RAGSource]
```

这里的 `RAGSource` 是 API 对外响应模型，Pydantic 会检查：

```text
text 不是空字符串
page 大于 0
score 是可以转换为浮点数的值
```

它与向量库内部的 `SearchResult` 内容相似，但职责不同：

```text
SearchResult
→ 服务内部传递检索结果

RAGSource
→ 约束接口最终返回的 JSON 结构
```

这样向量检索代码不需要依赖 FastAPI 的响应模型，模块职责仍然清楚。

---

# 五、让 RAGService 保留完整检索结果

打开：

```text
app/services/rag_service.py
```

把向量库的导入改为：

```python
from app.services.vector_store import (
    FAISSVectorStore,
    SearchResult,
)
```

把 `answer()` 的返回类型改为：

```python
) -> tuple[str, list[SearchResult]]:
```

然后将原来的：

```python
sources = [
    text
    for text, _score in search_results
]
prompt = build_rag_prompt(
    question=cleaned_question,
    contexts=sources,
)

answer = await self.llm_service.chat(prompt)

return answer, sources
```

改为：

```python
contexts = [
    result.text
    for result in search_results
]
prompt = build_rag_prompt(
    question=cleaned_question,
    contexts=contexts,
)

answer = await self.llm_service.chat(prompt)

return answer, search_results
```

大模型 Prompt 仍然只需要来源文本，所以使用 `contexts`。但是方法返回给接口层的是完整的 `search_results`，页码和分数不会再丢失。

---

# 六、在接口边界转换成 RAGSource

回到：

```text
app/main.py
```

在 `from app.models import (...)` 中加入：

```python
RAGSource,
```

然后把 `/rag/chat` 中的：

```python
answer, sources = await rag_service.answer(
    question=request.question,
    top_k=TOP_K,
)
```

改为：

```python
answer, search_results = await rag_service.answer(
    question=request.question,
    top_k=TOP_K,
)
```

最后把返回值改为：

```python
return RAGChatResponse(
    answer=answer,
    sources=[
        RAGSource(
            text=result.text,
            page=result.page,
            score=round(result.score, 6),
        )
        for result in search_results
    ],
)
```

`round(..., 6)` 只是让 JSON 更容易阅读，不改变 FAISS 的排序。来源数组原来的先后顺序也保留下来了：第一个对象就是相似度排名第 1 的来源。

接口预期从原来的：

```json
{
  "answer": "……",
  "sources": [
    "来源文本 1",
    "来源文本 2"
  ]
}
```

变成：

```json
{
  "answer": "……",
  "sources": [
    {
      "text": "来源文本 1",
      "page": 2,
      "score": 0.664656
    },
    {
      "text": "来源文本 2",
      "page": 2,
      "score": 0.656285
    }
  ]
}
```

---

# 七、同步更新 Day 23 的实验脚本

`scripts/compare_top_k.py` 也在直接调用 `FAISSVectorStore`。如果只改业务代码而不改脚本，它以后运行时会因为仍然传入字符串列表而报错。

打开：

```text
scripts/compare_top_k.py
```

把向量库导入改为：

```python
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
    SearchResult,
)
```

把 `format_sources()` 改为：

```python
def format_sources(
    results: list[SearchResult],
) -> list[dict]:
    """为人工检查保留排名、页码、相似度和原文。"""
    return [
        {
            "rank": rank,
            "page": result.page,
            "score": round(result.score, 6),
            "text": result.text,
        }
        for rank, result in enumerate(
            results,
            start=1,
        )
    ]
```

再把创建 Chunk 和文档向量的部分改为：

```python
chunks: list[DocumentChunk] = []

for page_number, page_text in enumerate(
    pages,
    start=1,
):
    page_chunks = split_text(
        page_text,
        chunk_size=baseline["chunk_size"],
        overlap=baseline["overlap"],
    )
    chunks.extend(
        DocumentChunk(
            text=chunk_text,
            page=page_number,
        )
        for chunk_text in page_chunks
    )

if not chunks:
    raise ValueError("测试 PDF 没有生成 Chunk")

print("加载 Embedding 模型……")
embedding_service = EmbeddingService()
document_vectors = (
    embedding_service.embed_documents(
        [chunk.text for chunk in chunks]
    )
)
```

后面的：

```python
vector_store.add(chunks, document_vectors)
```

可以保持不变。

今天只检查这个脚本能够通过语法检查，不要重新运行完整实验。因为它当前会重新生成 `top_k_comparison.json`，从而覆盖 Day 23 已经人工填写的 20 个评分和结论。已有 JSON 是昨天实验的历史结果，不要求补写页码。

`scripts/run_evaluation.py` 不需要修改。它只是把接口返回的 `result["sources"]` 原样保存到 JSON；将来重新运行时，自然会保存新的来源对象结构。

---

# 八、先做不调用模型的元数据测试

先检查今天涉及文件的语法：

```powershell
.\.venv\Scripts\python.exe -m py_compile app\models.py app\main.py app\services\vector_store.py app\services\rag_service.py scripts\compare_top_k.py
```

然后使用两个简单向量验证“向量位置、文本和页码”没有错位：

```powershell
@'
from app.services.vector_store import (
    DocumentChunk,
    FAISSVectorStore,
)


chunks = [
    DocumentChunk(
        text="第一页关于 RAG 的内容",
        page=1,
    ),
    DocumentChunk(
        text="第二页关于 FastAPI 的内容",
        page=2,
    ),
]
vectors = [
    [1.0, 0.0],
    [0.0, 1.0],
]

store = FAISSVectorStore(dimension=2)
store.add(chunks, vectors)

results = store.search(
    query_vector=[0.0, 1.0],
    top_k=2,
)

assert len(results) == 2
assert results[0].text == "第二页关于 FastAPI 的内容"
assert results[0].page == 2
assert abs(results[0].score - 1.0) < 0.000001

print("第一名文本：", results[0].text)
print("第一名页码：", results[0].page)
print("第一名分数：", results[0].score)
print("向量与来源元数据对应正确")
'@ | .\.venv\Scripts\python.exe -
```

预期输出包含：

```text
第一名文本： 第二页关于 FastAPI 的内容
第一名页码： 2
第一名分数： 1.0
向量与来源元数据对应正确
```

如果文本正确但页码错误，重点检查：

```text
self.index.add(matrix)
self.chunks.extend(chunks)
```

是否接收了相同顺序的数据。不要在生成向量后单独排序 `chunks`，否则 FAISS 索引位置与元数据位置会错开。

---

# 九、启动接口并检查真实响应

今天仍然使用两个终端。

## 终端 A：启动 FastAPI

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

等到终端出现：

```text
Application startup complete
```

如果启动时报：

```text
cannot unpack non-iterable SearchResult object
```

说明 `RAGService` 中还保留着：

```python
for text, _score in search_results
```

需要改为读取 `result.text`。

## 终端 B：重新上传 PDF

服务重启后，内存中的 `rag_service` 是空的，必须重新上传：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
curl.exe -X POST "http://127.0.0.1:8000/upload" -F "file=@data/documents/sample.pdf"
```

预期仍然返回文件名、页数和 Chunk 数量。上传响应不需要出现来源详情。

然后发送一个需要多个来源的问题：

```powershell
$body = @{
    question = "根据文档，概括一个最基础的 RAG 如何从文档得到回答。"
} | ConvertTo-Json

$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes(
    $body
)

$result = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/rag/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body $bodyBytes

$result | ConvertTo-Json -Depth 5
```

返回的每条来源都应该出现：

```text
text
page
score
```

再运行自动检查：

```powershell
if ($result.sources.Count -ne 3) {
    throw "来源数量不是 3"
}

if ($result.sources | Where-Object { $_.page -le 0 }) {
    throw "存在无效页码"
}

if ($result.sources | Where-Object { $null -eq $_.score }) {
    throw "存在缺失的相似度"
}

$result.sources |
    Select-Object page, score, text
```

还可以打开：

```text
http://127.0.0.1:8000/docs
```

展开 `RAGChatResponse`，确认 Swagger 中的 `sources` 已经显示为对象数组，而不是字符串数组。

如果接口出现响应校验错误，优先检查：

```text
RAGChatResponse.sources 是否已改为 list[RAGSource]
main.py 是否把 SearchResult 转换成了 RAGSource
页码是否从 1 开始
```

---

# 十、正确理解 similarity score

当前项目使用：

```python
faiss.IndexFlatIP
```

并且文档向量与查询向量都经过了 L2 归一化。因此这里的内积得分可以用作余弦相似度：方向越接近，分数通常越高，FAISS 就把它排得越靠前。

但 `score` 不是：

```text
模型回答正确的概率
来源一定相关的置信度
可以跨所有模型直接比较的统一分数
```

例如：

```json
"score": 0.66
```

不能解释为“这个来源有 66% 概率正确”。它首先用于同一个查询下的相对排序。是否真正命中问题，仍然需要结合来源文本和评估问题判断。

页码和分数分别解决两个不同问题：

```text
page
→ 用户可以回到 PDF 的对应页面核对原文

score
→ 开发者可以观察检索排序和相关性差距
```

今天先做到响应中附带来源对象，不要求让大模型在回答正文中生成 `[来源 1]` 这样的行内引用。修改生成 Prompt 属于另一个变量，避免与来源元数据改造混在一起。

---

# 十一、检查改动并提交 Git

停止服务后查看：

```powershell
git status --short
git diff -- app\models.py app\main.py app\services\vector_store.py app\services\rag_service.py scripts\compare_top_k.py docs\Day24.md
```

今天正常应修改或新增：

```text
app/models.py
app/main.py
app/services/vector_store.py
app/services/rag_service.py
scripts/compare_top_k.py
docs/Day24.md
```

确认：

```text
没有修改 CHUNK_SIZE、CHUNK_OVERLAP 或 TOP_K
没有重新生成并覆盖 top_k_comparison.json
每个 Chunk 在生成向量前已经记录 PDF 页码
FAISS 索引位置与 Chunk 元数据顺序一致
Prompt 使用的仍然只是来源文本
API 每条来源都包含 text、page 和 score
响应中没有 .env、API Key 或其他秘密信息
```

测试成功后暂存：

```powershell
git add app\models.py app\main.py app\services\vector_store.py app\services\rag_service.py scripts\compare_top_k.py docs\Day24.md
git diff --cached --stat
git status
```

确认暂存内容正确后提交：

```powershell
git commit -m "feat: return RAG source metadata"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看笔记说明：为什么页码必须在切块时保存，FAISS 返回的索引位置怎样找回来源元数据，`SearchResult` 与 `RAGSource` 的职责有什么区别，以及为什么相似度分数不能理解成回答正确率。

---

# Day 24 完成标准

- [ ] 能解释当前页码和相似度原本分别丢失在哪一步
- [ ] 能解释 FAISS 索引位置与 Chunk 元数据列表为什么必须保持相同顺序
- [ ] 已创建内部数据类型 `DocumentChunk` 和 `SearchResult`
- [ ] 上传 PDF 时已使用从 1 开始的页码标记每个 Chunk
- [ ] `FAISSVectorStore` 能保存 Chunk 元数据并返回文本、页码和分数
- [ ] 已创建 Pydantic 响应模型 `RAGSource`
- [ ] `RAGChatResponse.sources` 已从字符串列表改为来源对象列表
- [ ] `RAGService` 构造 Prompt 时使用文本，同时保留完整检索结果
- [ ] 已同步更新 `scripts/compare_top_k.py`，且没有覆盖 Day 23 的人工评分结果
- [ ] 不调用 LLM 的元数据对应测试已经通过
- [ ] `/upload` 仍能成功建立 PDF 索引
- [ ] `/rag/chat` 返回的三条来源都包含 `text`、`page` 和 `score`
- [ ] 能解释相似度用于排序，但不是正确概率或模型置信度
- [ ] 已确认没有修改切块参数、top-k 或 RAG Prompt
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
