# Day 18：用 FAISS 检索 top-3 文本块

昨天已经把 PDF 文本切成 Chunk，使用 `EmbeddingService` 生成向量，并通过 `FAISSVectorStore.add()` 把向量和原文保存到了内存索引中。现在索引只能写入，还不能真正回答“哪几个 Chunk 和用户问题最相似”。今天要为向量库实现 `search()`，跑通 `用户问题 → 问题向量 → FAISS 搜索 → top-3 原始文本`，并能看懂 FAISS 返回的编号和相似度。今天只做检索，不调用大模型，也不新增 FastAPI 接口。

---

# 一、复习昨天留下的索引状态

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

打开：

```text
app/services/vector_store.py
```

当前 `FAISSVectorStore` 保存了两份顺序一致的状态：

```python
self.index
self.texts
```

加入三个 Chunk 后，可以把它们想成：

```text
FAISS 编号 0 ↔ self.texts[0]
FAISS 编号 1 ↔ self.texts[1]
FAISS 编号 2 ↔ self.texts[2]
```

`self.index` 负责保存和比较向量，`self.texts` 负责保存业务上真正需要返回的原文。FAISS 搜索后给我们的不是 Chunk 文字，而是向量编号和分数；代码要根据编号回到 `self.texts` 中取出文字。

今天会在同一个类中增加：

```python
search(query_vector, top_k=3)
```

它会复用对象中已经保存的索引和文本，因此仍然适合写成 `FAISSVectorStore` 的实例方法。

---

# 二、先理解 top-k 搜索会返回什么

`top-k` 的意思是：只取相似程度排在最前面的 k 个结果。

今天设置：

```text
top_k = 3
```

调用 FAISS 时会写成：

```python
scores, indices = self.index.search(query_matrix, k)
```

如果只搜索一个问题，而且 `k=3`，两个返回值的形状都是：

```text
(1, 3)
```

可以想象成：

```python
indices = [[4, 1, 7]]
scores = [[0.91, 0.83, 0.76]]
```

含义是：

```text
第 1 名：向量编号 4，相似度 0.91
第 2 名：向量编号 1，相似度 0.83
第 3 名：向量编号 7，相似度 0.76
```

当前索引使用的是：

```python
faiss.IndexFlatIP(dimension)
```

`IP` 计算内积。文档向量和问题向量都经过 L2 归一化以后，内积就可以作为余弦相似度使用，因此今天的分数越大，表示方向越接近，文本通常也越相关。

但相似度不是概率。`0.85` 不能解释成“有 85% 的概率正确”，它只用于比较这批候选文本的相关程度。

FAISS 官方入门资料说明了 `search()` 返回距离（或分数）矩阵和编号矩阵，以及单条查询的矩阵形状：[FAISS Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started)。归一化向量配合内积进行余弦检索，可以参考：[MetricType and distances](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)。

---

# 三、实现 `search()` 方法

打开：

```text
app/services/vector_store.py
```

在现有 `add()` 方法后面增加：

```python
    def search(
        self,
        query_vector: list[float],
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
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

        query_matrix = np.ascontiguousarray(query_matrix)
        faiss.normalize_L2(query_matrix)

        k = min(top_k, self.count)
        scores, indices = self.index.search(query_matrix, k)

        results: list[tuple[str, float]] = []

        for index, score in zip(indices[0], scores[0]):
            if index < 0:
                continue

            results.append(
                (
                    self.texts[int(index)],
                    float(score),
                )
            )

        return results
```

不要重写昨天的 `add()`。今天只在现有类中增加检索能力。

逐段理解几个关键点。

## 1. 为什么写成 `[query_vector]`

`EmbeddingService.embed_query()` 返回一条一维向量，形状可以理解为：

```text
(512,)
```

FAISS 的 `search()` 接收二维矩阵。外面再包一层列表以后，形状变成：

```text
(1, 512)
```

这里的 `1` 表示本次只搜索一个用户问题。

## 2. 为什么搜索时还要归一化

当前 `embed_query()` 已经使用了 `normalize_embeddings=True`，但向量库仍然自己执行：

```python
faiss.normalize_L2(query_matrix)
```

这样 `search()` 的输入要求更稳定。以后即使调用者传入了没有归一化的向量，`IndexFlatIP` 仍然能按余弦相似度的方式比较。

## 3. 为什么使用 `min(top_k, self.count)`

如果索引中只有 2 个 Chunk，却要求 top-3，实际上最多只能返回 2 个有效结果：

```python
k = min(top_k, self.count)
```

这能保证返回数量不会超过索引中的真实向量数量。

## 4. 为什么要把 NumPy 类型转成 Python 类型

FAISS 返回的编号和分数通常是 NumPy 数值。代码使用：

```python
int(index)
float(score)
```

把它们转换为普通 Python 类型，后面打印、构造响应模型或转换成 JSON 会更方便。

## 5. 为什么返回 `(text, score)`

今天的方法返回：

```python
list[tuple[str, float]]
```

其中每个元素是：

```text
(Chunk 原文, 相似度)
```

月计划要求先输出检索到的原始文本。暂时保留分数，是为了观察排序是否合理；今天不额外设计 Pydantic 模型或 metadata 结构。

---

# 四、先用二维手工向量验证排序

不要一开始就加载 Embedding 模型。先用能够手工理解的二维向量，确认 `search()` 的数据形状、编号映射和排序都正确。

在 PowerShell 中运行：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

@'
from app.services.vector_store import FAISSVectorStore


store = FAISSVectorStore(dimension=2)

store.add(
    texts=[
        "苹果是一种水果",
        "汽车是一种交通工具",
        "苹果可以用来制作果汁",
    ],
    vectors=[
        [1.0, 0.0],
        [0.0, 1.0],
        [0.8, 0.2],
    ],
)

results = store.search(
    query_vector=[1.0, 0.0],
    top_k=2,
)

for rank, (text, score) in enumerate(results, start=1):
    print(f"第 {rank} 名，相似度 {score:.4f}")
    print(text)

assert len(results) == 2
assert results[0][0] == "苹果是一种水果"
assert results[0][1] >= results[1][1]

print("手工向量检索验证通过")
'@ | python -
```

预期第一名是：

```text
苹果是一种水果
```

因为查询向量 `[1.0, 0.0]` 与它的向量方向完全一致，相似度应当接近 `1.0000`。第三条文本对应的向量 `[0.8, 0.2]` 方向也比较接近，所以它应当排在汽车前面。

如果结果顺序相反，先检查：

```text
是否仍然使用 IndexFlatIP
文档和查询是否都进行了 normalize_L2
是否错误地按分数从小到大重新排序
```

FAISS 已经按当前索引的相似程度返回结果，这里不需要再手动排序。

---

# 五、跑通真实 PDF 的 top-3 检索

手工向量测试通过以后，再连接前面已经完成的 PDF、Chunk 和 Embedding。

今天使用测试 PDF 中确实存在的问题：

```text
为什么需要把长文档切成 Chunk？
```

运行：

```powershell
@'
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.vector_store import FAISSVectorStore


pages = PDFService().extract_pages(
    "data/documents/sample.pdf"
)

chunks: list[str] = []

for page_text in pages:
    chunks.extend(
        split_text(
            page_text,
            chunk_size=200,
            overlap=40,
        )
    )

if not chunks:
    raise RuntimeError("PDF 没有生成任何 Chunk")

embedding_service = EmbeddingService()
document_vectors = embedding_service.embed_documents(chunks)

vector_store = FAISSVectorStore(
    dimension=len(document_vectors[0])
)
vector_store.add(chunks, document_vectors)

question = "为什么需要把长文档切成 Chunk？"
query_vector = embedding_service.embed_query(question)
results = vector_store.search(
    query_vector=query_vector,
    top_k=3,
)

print("问题：", question)
print("Chunk 总数：", len(chunks))
print("实际返回数量：", len(results))

for rank, (text, score) in enumerate(results, start=1):
    print(f"\n第 {rank} 名，相似度：{score:.4f}")
    print(text)

assert len(results) == min(3, len(chunks))
assert all(
    results[index][1] >= results[index + 1][1]
    for index in range(len(results) - 1)
)
assert any(
    "切分" in text or "chunk" in text.lower()
    for text, _ in results
)

print("\n真实 PDF top-3 检索验证通过")
'@ | python -
```

这里特意使用：

```python
embedding_service.embed_query(question)
```

不要写成：

```python
embedding_service.embed_documents([question])
```

当前 BGE 服务会给查询添加检索指令，而文档向量不添加。查询和文档虽然最终都是 512 维向量，但它们在检索任务中的角色不同，应当调用各自的方法。

测试结果不要求每个分数与示例完全相同，也不强制某段文字必须永远排在固定名次。重点检查：

```text
返回结果不超过 3 条
相似度从高到低排列
top-3 中出现与“切分文档”或“Chunk”有关的原文
输出来自 sample.pdf，而不是大模型生成的回答
```

因为测试 PDF 只有三页而且文字较短，这里暂时使用：

```text
chunk_size = 200
overlap = 40
```

目的是产生足够多个候选 Chunk，方便观察 top-3 的筛选效果。它们不是最终参数；后面的评估阶段再比较不同的切块参数。

---

# 六、验证边界输入

再做一个很短的测试，确认非法 `top_k` 会报错，而空索引会返回空列表：

```powershell
@'
from app.services.vector_store import FAISSVectorStore


empty_store = FAISSVectorStore(dimension=3)

assert empty_store.search(
    query_vector=[1.0, 0.0, 0.0],
    top_k=3,
) == []

try:
    empty_store.search(
        query_vector=[1.0, 0.0, 0.0],
        top_k=0,
    )
except ValueError as exc:
    print(type(exc).__name__, exc)
else:
    raise AssertionError("预期 top_k=0 时抛出 ValueError")

print("边界输入验证通过")
'@ | python -
```

预期能看到：

```text
ValueError top_k 必须大于 0
边界输入验证通过
```

这里选择让空索引返回 `[]`，含义是“当前没有任何可检索结果”，而不是让程序因为没有文档而崩溃。

---

# 七、检查今天是否只完成了检索

执行：

```powershell
git status --short
git diff -- app/services/vector_store.py docs/Day18.md
```

今天正常只需要修改或新增：

```text
app/services/vector_store.py
docs/Day18.md
```

确认下面这些内容没有被修改：

```text
requirements.txt：昨天已经安装 faiss-cpu，今天不需要新依赖
app/main.py：今天不新增接口
app/services/llm_service.py：今天不调用大模型
.env：不读取、不显示、不提交
```

今天完成后的链路停在：

```text
用户问题
→ embed_query()
→ FAISS search()
→ top-3 Chunk 原文和相似度
```

下一步才会把这些 Chunk 拼成 Context，并交给大模型生成回答。

---

# 八、测试成功后提交 Git

确认手工向量测试、真实 PDF 检索和边界测试都通过以后，执行：

```powershell
git add app/services/vector_store.py docs/Day18.md
git status
```

确认暂存区只有今天的两个文件，再提交：

```powershell
git commit -m "feat: add FAISS top-k retrieval"
```

查看最新提交：

```powershell
git log -1 --oneline
git status --short
```

最后尝试不看代码讲清楚：问题如何变成向量，为什么 FAISS 返回的是编号和分数，编号如何映射回 Chunk 原文，以及为什么 `IndexFlatIP` 的分数在这里越大越相关。

---

# Day 18 完成标准

- [ ] 能解释 top-k、`scores` 和 `indices` 分别表示什么
- [ ] 能解释为什么单条查询向量要转换成 `(1, dimension)` 的二维矩阵
- [ ] 已在 `FAISSVectorStore` 中实现 `search(query_vector, top_k=3)`
- [ ] `search()` 会校验查询向量、向量维度和 `top_k`
- [ ] 能根据 FAISS 返回的编号从 `self.texts` 中找回 Chunk 原文
- [ ] 已使用二维手工向量验证检索顺序
- [ ] 已跑通 `问题 → embed_query() → FAISS → top-3 Chunk` 的真实 PDF 检索
- [ ] top-3 结果按相似度从高到低排列，并包含与问题相关的原文
- [ ] 能说明相似度分数为什么不是正确概率
- [ ] 已确认今天没有调用大模型，也没有新增 FastAPI 接口
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
