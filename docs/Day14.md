# Day 14：用中文 Embedding 模型把文本转换成向量

Day 13 已经完成第二周收尾：`/chat`、SQLite 消息历史、异常处理、异步模型调用和 README 都已整理到真实进度。今天开始进入最小 RAG 阶段，先学习整条检索链路的基础：Embedding。

今天只做一件事：使用本地中文模型 `BAAI/bge-small-zh-v1.5`，把一个查询和两段文本转换成归一化向量，再用点积比较相似度。完成后，你应该能够解释“文本为什么能被检索”，并得到一个可供后续 PDF Chunk 和 FAISS 使用的 `EmbeddingService`。

---

# 一、先理解 Embedding 是什么

打开项目：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
code .
```

目前调用 DeepSeek 时，输入和输出都是自然语言：

```text
用户问题文本
→ 大模型
→ 回答文本
```

Embedding 模型做的是另一件事：

```text
一段文本
→ Embedding 模型
→ 一串固定长度的数字
```

例如下面只是为了帮助理解而简化的示意，不是真实模型输出：

```text
“RAG 会检索外部知识”
→ [0.12, -0.36, 0.81, ...]
```

这一串数字叫作向量。向量中的单个数字通常不能单独解释成“是否包含 RAG”或“是否谈论数据库”；真正有用的是不同文本向量之间的整体位置关系。

Embedding 模型经过训练后，语义比较接近的文本通常会得到方向更接近的向量：

```text
“RAG 会先检索相关资料”
“检索增强生成会使用外部知识”
→ 向量通常比较接近

“RAG 会先检索相关资料”
“今天成都天气晴朗”
→ 向量通常相对更远
```

它在当前项目中的作用是：以后用户提问时，把问题和 PDF 文本块都转换成向量，再寻找与问题最相近的文本块。

---

# 二、理解 Embedding 和大模型回答的区别

这两个模型都接收文本，但输出和用途不同。

```text
LLM
输入文本，输出自然语言回答

Embedding 模型
输入文本，输出固定维度的数字向量
```

例如用户问：

```text
RAG 为什么能减少幻觉？
```

大模型可能直接生成解释；Embedding 模型不会回答问题，只会输出向量。这个向量用来从文档中找到类似下面的内容：

```text
RAG 在生成前检索外部资料，使回答能够参考可验证的信息。
```

所以完整 RAG 中两类模型的分工是：

```text
Embedding 模型负责“找资料”
LLM 负责“结合资料组织回答”
```

今天只学习前半部分，不调用 DeepSeek，也不增加新的 FastAPI 路由。

---

# 三、今天为什么选择这个模型

今天只选择一个模型：

```text
BAAI/bge-small-zh-v1.5
```

它是中文 Embedding 模型，输出 512 维向量，模型权重约 96 MB，适合当前以中文科研文本为主、先在本地跑通基础检索的学习项目。模型官方页面提供了 Sentence Transformers 的使用方式，并说明短查询检索长文本时，应给查询添加检索指令，而文档正文不需要添加指令：

- [BAAI/bge-small-zh-v1.5 模型页面](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- [Sentence Transformers 的 SentenceTransformer 文档](https://sbert.net/docs/package_reference/sentence_transformer/model.html)

这里的 `small` 不表示向量只有几个数字，而是相对于同系列的 base、large 模型，参数量和资源占用更小。今天的目标是理解链路，不进行模型排行榜比较，也不同时测试多个 Embedding 模型。

第一次运行时需要从 Hugging Face 下载模型文件，可能需要几分钟；以后会使用本机缓存，不会每次重新下载。

---

# 四、安装 Sentence Transformers

在项目根目录激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

安装：

```powershell
python -m pip install sentence-transformers
```

这个包会同时安装运行 Transformer 模型需要的依赖，下载量可能明显大于模型权重本身。等待命令正常结束，不要中途反复执行安装命令。

安装后检查：

```powershell
python -c "from sentence_transformers import SentenceTransformer; print(SentenceTransformer)"
```

正常会看到类似：

```text
<class 'sentence_transformers.SentenceTransformer.SentenceTransformer'>
```

如果出现磁盘空间或网络下载错误，先记录错误摘要，不要临时改装多个相似框架。确认网络和虚拟环境后，只重试一次。

把当前环境依赖写回：

```powershell
python -m pip freeze > requirements.txt
```

由于 Sentence Transformers 依赖 PyTorch、Transformers 等包，`requirements.txt` 会比以前长很多，这是正常的。

---

# 五、创建 `EmbeddingService`

新建：

```text
app/services/embedding_service.py
```

写入：

```python
from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class EmbeddingService:
    """负责把查询和文档文本转换成向量。"""

    def __init__(self) -> None:
        self.model = SentenceTransformer(MODEL_NAME)

    def embed_query(self, query: str) -> list[float]:
        """把一个短查询转换成归一化向量。"""
        text = f"{QUERY_INSTRUCTION}{query}"
        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )
        return vector.tolist()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """把多段文档文本转换成归一化向量。"""
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )
        return vectors.tolist()
```

今天先不把模型名称放进 `.env`，也不把服务对象放进 `app/main.py`。等后面开始真正的 PDF 检索链路时，再统一考虑配置和启动加载位置。

---

# 六、理解查询和文档为什么分开编码

当前服务提供两个方法：

```python
embed_query(query)
embed_documents(texts)
```

查询通常很短，例如：

```text
RAG 为什么能减少幻觉？
```

文档段落通常更长，例如：

```text
RAG 在生成回答前检索外部资料，使模型能够根据可验证的上下文作答。
```

根据这个 BGE 模型的使用说明，短查询检索长文档时，给查询加上：

```text
为这个句子生成表示以用于检索相关文章：
```

而文档正文保持原样。

因此 `embed_query()` 会先拼接检索指令，`embed_documents()` 不会。

这条指令不是让模型生成中文回答，而是告诉 Embedding 模型：当前文本将作为检索查询使用。

---

# 七、理解 `encode()` 和归一化

核心代码是：

```python
self.model.encode(
    texts,
    normalize_embeddings=True,
)
```

`encode()` 负责把文本送入模型，得到向量。

如果输入一条查询，得到一条向量：

```text
str
→ 一维向量
→ list[float]
```

如果输入多段文档，得到多条向量：

```text
list[str]
→ 二维向量集合
→ list[list[float]]
```

```python
normalize_embeddings=True
```

表示把每条向量缩放到长度为 1，但保留方向。归一化后，两条向量的点积就等于它们的余弦相似度，后面的比较会更方便。

模型返回的是 NumPy 数组：

```python
vector
```

当前项目其他接口主要使用普通 Python 类型，所以通过：

```python
vector.tolist()
```

把它转换成普通列表。

---

# 八、生成真实向量并比较相似度

在项目根目录运行：

运行测试代码之前，先运行下面这段代码，防止中文不能正常显示：

```PowerShell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

```powershell
@'
from app.services.embedding_service import EmbeddingService


service = EmbeddingService()

query = "RAG 为什么能减少幻觉？"
documents = [
    "RAG 在生成回答前检索外部资料，使模型能够参考可验证的上下文。",
    "今天成都天气晴朗，适合在公园散步。",
]

query_vector = service.embed_query(query)
document_vectors = service.embed_documents(documents)

print("文档数量：", len(document_vectors))
print("向量维度：", len(query_vector))

for text, vector in zip(documents, document_vectors):
    score = sum(
        query_value * document_value
        for query_value, document_value in zip(
            query_vector,
            vector,
        )
    )
    print("相似度：", round(score, 4))
    print("文本：", text)
'@ | python -
```

第一次运行会下载并加载模型。正常情况下会看到：

```text
文档数量： 2
向量维度： 512
```

与 RAG 相关的第一段文本，相似度应该高于天气文本。具体分数可能因依赖版本和运行环境略有差异，不要求等于某个固定数字。

如果运行很久没有输出，先观察终端是否正在下载模型文件。不要因为第一次加载较慢，就直接判断程序卡死。

如果出现无法连接 Hugging Face 的错误，记录不含本地隐私的错误摘要，检查网络后再重试。今天不要同时换用云端 Embedding API，以免把“模型下载问题”和“Embedding 概念”混在一起。

---

# 九、理解余弦相似度

余弦相似度比较的是两个向量方向是否接近：

```text
方向越接近
→ 余弦相似度越高
→ 文本语义通常越接近
```

公式是：

```text
cos(a, b) = (a · b) / (||a|| × ||b||)
```

其中：

```text
a · b
两个向量的点积

||a|| 和 ||b||
两个向量的长度
```

今天已经把向量归一化到长度 1，所以：

```text
||a|| = 1
||b|| = 1
```

公式变成：

```text
cos(a, b) = a · b
```

这就是测试代码为什么直接计算：

```python
sum(a * b for a, b in zip(vector_a, vector_b))
```

相似度是排序依据，不是“正确答案概率”。不要把某个固定分数机械解释成百分之多少相似。后面真正检索 PDF 时，重点先比较哪些文本块排名更靠前。

---

# 十、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- requirements.txt app/services/embedding_service.py
git check-ignore -v .env
git check-ignore -v data\chat.db
```

新建的 `embedding_service.py` 可能不会出现在普通 `git diff` 中，可以在 VS Code 中复查，或者执行：

```powershell
Get-Content app\services\embedding_service.py
```

确认：

```text
只使用一个中文 Embedding 模型
代码没有调用 DeepSeek，也没有读取或输出 API Key
查询添加检索指令，文档正文没有添加
向量使用 normalize_embeddings=True
相似文本得分高于无关文本
.env、模型缓存和 data/chat.db 没有进入 Git 状态
```

所有测试成功后添加：

```powershell
git add requirements.txt app/services/embedding_service.py docs/Day14.md
git status
```

确认暂存区没有模型权重、`.env` 和数据库文件，然后提交：

```powershell
git commit -m "feat: add local Chinese embedding service"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后不看代码，尝试用自己的话讲清楚：Embedding 模型输出什么，查询和文档为什么分开编码，归一化有什么作用，余弦相似度为什么能用于文本检索，以及 Embedding 和 LLM 在 RAG 中分别负责什么。

---

# Day 14 完成标准

```text
[ ] 能解释 Embedding 与 LLM 输出和用途的区别
[ ] 已安装 sentence-transformers 并更新 requirements.txt
[ ] 已创建 app/services/embedding_service.py
[ ] 能用 BAAI/bge-small-zh-v1.5 生成查询和文档向量
[ ] 能说明为什么查询添加检索指令而文档不添加
[ ] 确认每条向量是 512 维，并已归一化
[ ] RAG 相关文本的相似度高于无关天气文本
[ ] 能解释余弦相似度、点积以及相似度不是概率
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
