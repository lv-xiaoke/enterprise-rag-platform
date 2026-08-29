# Day 17：用 FAISS 保存 Chunk 向量

## 今天要完成什么

昨天已经把 PDF 文本切成了多个 Chunk，前面也已经实现了 `EmbeddingService`，可以把文本转换为向量。今天把这两部分接起来：

```text
PDF → 提取每页文本 → 切成 Chunk → 生成向量 → 加入 FAISS 索引
```

今天只完成“建立索引”，暂时不做用户问题的检索，也不调用大模型生成答案。完成后，项目会拥有一个最小的内存向量库：它能保存 Chunk 对应的向量，并保留向量编号与原文之间的对应关系。

预计用时：约 1 小时。

---

## 一、先理解：为什么有了向量，还需要 FAISS

`EmbeddingService.embed_documents()` 返回的是二维列表。例如有 20 个 Chunk，每个向量有 512 个数字，数据形状大致是：

```text
(20, 512)
```

这些数字只是普通数据。以后用户提出问题时，我们还需要快速找出“与问题向量最相似的几个 Chunk 向量”。如果每次都自己遍历全部向量并计算相似度，数据变多后，管理和检索都会越来越麻烦。

FAISS 是专门用于向量相似度检索的库。今天先用它最简单的索引 `IndexFlatIP`：

-  `Index`：就是：FAISS 的向量索引。
- `Flat` 表示直接保存并逐个比较全部向量，结果精确，适合当前的小项目；
- `IP` 表示使用 inner product，也就是内积，衡量向量之间的相似程度；
- 当两个向量都做过 L2 归一化时，内积与余弦相似度等价；
- 当前的 `EmbeddingService` 已经使用 `normalize_embeddings=True`，今天仍会在写入 FAISS 前再统一做一次归一化，让向量库自身不依赖调用者是否记得归一化。

FAISS 要求加入索引的数据是二维 NumPy 数组，并使用 `float32` 类型。因此，今天还要理解这次转换：

```python
matrix = np.asarray(vectors, dtype=np.float32)
```

可以参考以下官方资料，不需要一次读完：

- [faiss-cpu 的 PyPI 页面](https://pypi.org/project/faiss-cpu/)
- [FAISS Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started)
- [FAISS 索引类型说明](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes)
- [FAISS 的距离与余弦相似度说明](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)

---

## 二、安装并验证 faiss-cpu

先确认终端位于项目根目录，并且已经激活项目虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

安装 CPU 版本的 FAISS：

```powershell
python -m pip install faiss-cpu
```

验证当前 Python 能正常导入：

```powershell
python -c "import faiss; print(faiss.__version__)"
```

如果能够输出版本号，就更新依赖文件：

```powershell
python -m pip freeze > requirements.txt
```

如果安装或导入失败，先检查命令是否使用了虚拟环境里的 Python：

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m pip show faiss-cpu
```

今天的环境是 Python 3.11，当前 PyPI 提供 Windows x86-64 对应的预编译 wheel，通常不需要自己编译 FAISS。

---

## 三、设计一个有状态的向量库类

新建文件：

```text
app/services/vector_store.py
```

今天适合使用类，因为向量加入以后，需要在后续方法调用中继续保存并复用两份状态：

```python
self.index
self.texts
```

其中：

- `self.index` 保存 FAISS 索引及其中的向量；
- `self.texts` 按相同顺序保存每个向量对应的 Chunk 原文。

这正好可以和昨天的普通切块函数作对比：

```text
split_text：输入文本 → 计算 → 返回结果，调用结束后不保留状态
FAISSVectorStore：add 调用结束后，索引和文本仍要留在对象中供后续检索使用
```

FAISS 默认会按照添加顺序为向量分配编号。第一次加入的向量编号是 `0`，第二次是 `1`。因此，只要 `self.texts` 和向量使用相同的添加顺序，以后 FAISS 返回编号 `3` 时，就可以通过 `self.texts[3]` 找回原文。

---

## 四、实现 FAISSVectorStore

在 `app/services/vector_store.py` 中写入：

```python
import faiss
import numpy as np


class FAISSVectorStore:
    def __init__(self, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("dimension 必须大于 0")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.texts: list[str] = []

    @property
    def count(self) -> int:
        return self.index.ntotal

    def add(
        self,
        texts: list[str],
        vectors: list[list[float]],
    ) -> None:
        if not texts:
            raise ValueError("texts 不能为空")
        if len(texts) != len(vectors):
            raise ValueError("texts 和 vectors 的数量必须一致")

        matrix = np.asarray(vectors, dtype=np.float32)

        if matrix.ndim != 2:
            raise ValueError("vectors 必须是二维数组")
        if matrix.shape[1] != self.dimension:
            raise ValueError(
                f"向量维度应为 {self.dimension}，实际为 {matrix.shape[1]}"
            )

        matrix = np.ascontiguousarray(matrix)
        faiss.normalize_L2(matrix)

        self.index.add(matrix)
        self.texts.extend(texts)
```

逐段理解这段代码。

### 1. `dimension` 为什么必须在创建索引时确定

同一个 FAISS 索引中的所有向量维度必须相同。当前 BGE 模型生成的是固定维度向量，但代码不要直接写死 `512`，测试时可以从实际向量中取得：

```python
dimension = len(vectors[0])
```

这样以后更换 Embedding 模型时，向量库不需要跟着修改常量。

### 2. 为什么检查文本数和向量数

下面两份数据依靠相同下标建立对应关系：

```text
texts[0]   ↔   FAISS 中编号为 0 的向量
texts[1]   ↔   FAISS 中编号为 1 的向量
```

如果有 10 段文本，却只有 9 个向量，对应关系会错位，所以应当在加入索引前立即报错。

### 3. 为什么转换为 `float32`

`embed_documents()` 为了方便 API 使用，返回了 Python 的 `list[list[float]]`；FAISS 的 Python 接口接收 NumPy `float32` 矩阵。这里的转换是在两个模块之间适配数据格式，并不是重新生成向量。

### 4. 为什么调用 `np.ascontiguousarray`

FAISS 需要连续存放的内存数据。当前 `np.asarray()` 得到的数组通常已经连续，但显式转换能够让输入要求更稳定。

### 5. `normalize_L2` 和 `IndexFlatIP` 如何配合

`normalize_L2` 会把每个向量缩放为长度 1，然后 `IndexFlatIP` 计算内积。对归一化向量来说，这个内积就是余弦相似度。明天真正检索问题向量时，也要对问题向量执行相同的归一化。

---

## 五、串起 PDF、Chunk、Embedding 和 FAISS

今天先直接在 PowerShell 中运行一段集成测试，不急着创建 API 路由。

项目里已经有被 `.gitignore` 忽略的测试文件：

```text
data/documents/sample.pdf
```

在项目根目录执行：


```powershell
.\.venv\Scripts\Activate.ps1
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```


```powershell
@'
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.vector_store import FAISSVectorStore


pages = PDFService().extract_pages("data/documents/sample.pdf")

chunks: list[str] = []
for page_text in pages:
    chunks.extend(
        split_text(
            page_text,
            chunk_size=500,
            overlap=100,
        )
    )

if not chunks:
    raise RuntimeError("PDF 没有生成任何 Chunk")

embedding_service = EmbeddingService()
vectors = embedding_service.embed_documents(chunks)

dimension = len(vectors[0])
vector_store = FAISSVectorStore(dimension=dimension)
vector_store.add(chunks, vectors)

print("PDF 页数：", len(pages))
print("Chunk 数量：", len(chunks))
print("向量数量：", len(vectors))
print("向量维度：", dimension)
print("FAISS 是否已训练：", vector_store.index.is_trained)
print("FAISS 向量数量：", vector_store.count)
print("保存的文本数量：", len(vector_store.texts))

assert vector_store.count == len(chunks)
assert len(vector_store.texts) == vector_store.count
assert vector_store.texts[0] == chunks[0]

print("FAISS 写入验证通过")
'@ | python -
```

第一次加载 Embedding 模型可能稍慢。测试通过时，重点观察这几个关系：

```text
Chunk 数量 = 向量数量 = FAISS 向量数量 = 保存的文本数量
```

`IndexFlatIP` 不需要训练，因此 `is_trained` 应当为 `True`。这里的“已训练”指索引是否可以直接接收向量，并不表示今天又训练了 Embedding 模型。

今天暂时不调用：

```python
vector_store.index.search(...)
```

搜索问题向量、取得 top-k 编号、再根据编号找回 Chunk，是下一次学习的主线。

---

## 六、补一个错误输入验证

除了正常流程，再确认文本数量和向量数量不一致时会明确报错：

```powershell
@'
from app.services.vector_store import FAISSVectorStore


store = FAISSVectorStore(dimension=3)

try:
    store.add(
        texts=["第一段", "第二段"],
        vectors=[[1.0, 0.0, 0.0]],
    )
except ValueError as exc:
    print(type(exc).__name__, exc)
else:
    raise AssertionError("预期这里抛出 ValueError")
'@ | python -
```

预期输出包含：

```text
ValueError texts 和 vectors 的数量必须一致
```

这个验证的意义是：宁可在写入时立即失败，也不要让文本与向量之间悄悄错位。

---

## 七、今天需要真正掌握的三个概念

### 1. FAISS 保存的主要是向量，不是业务原文

FAISS 负责的是向量索引和相似度检索。Chunk 原文仍由我们的 Python 代码保存。当前最小实现用 `self.texts` 保存原文，后面可以逐步扩展为包含页码、文件名等信息的 metadata。

### 2. 向量编号是连接索引和原文的桥梁

加入顺序必须保持一致：

```text
FAISS 返回向量编号 → 用编号访问 texts → 得到 Chunk 原文
```

今天虽然还没有执行搜索，但已经为下一步建立了这个映射。

### 3. `index.add()` 不是写入磁盘

今天的 `FAISSVectorStore` 是内存对象。程序退出后，索引和 `self.texts` 都会消失。当前目标只是先跑通 RAG 的最小链路，因此不增加磁盘持久化。

以后如果需要重启后继续使用，可以学习：

```python
faiss.write_index(...)
faiss.read_index(...)
```

同时还要把 Chunk 原文和 metadata 单独持久化，不能只保存 FAISS 索引。这个扩展今天不做。

---

## 八、检查今天的改动

查看 Git 状态：

```powershell
git status --short
```

今天正常应当只包含：

```text
requirements.txt
app/services/vector_store.py
docs/Day17.md
```

查看改动内容：

```powershell
git diff -- requirements.txt app/services/vector_store.py docs/Day17.md
```

确认没有把 `.env`、虚拟环境、模型缓存或 `sample.pdf` 加入 Git。

---

## 九、提交 Git

完成代码和验证以后执行：

```powershell
git add requirements.txt app/services/vector_store.py docs/Day17.md
git commit -m "feat: add FAISS vector store"
```

再确认工作区状态：

```powershell
git status --short
```

如果没有输出，说明本次改动已经全部提交。

---

## 今日完成标准

- [ ] 已安装 `faiss-cpu`，并能在当前虚拟环境中正常导入
- [ ] 已理解 FAISS 索引、向量维度、`float32` 和向量编号的作用
- [ ] 已创建 `app/services/vector_store.py`
- [ ] 已实现有状态的 `FAISSVectorStore`
- [ ] 已使用 `IndexFlatIP` 和 L2 归一化保存 Chunk 向量
- [ ] 已跑通 `PDF → Chunk → Embedding → FAISS` 集成测试
- [ ] 已确认 Chunk、向量、FAISS 记录和文本数量完全一致
- [ ] 已验证文本数与向量数不一致时会抛出 `ValueError`
- [ ] 已确认今天没有提前实现 query 检索和 top-k
- [ ] 已完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
