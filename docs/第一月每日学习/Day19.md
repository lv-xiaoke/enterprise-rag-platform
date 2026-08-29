# Day 19：把检索结果交给大模型生成回答

昨天已经实现了 `FAISSVectorStore.search()`，能够把用户问题转换成查询向量，并返回最相关的 top-3 Chunk。现在系统虽然能“找到资料”，却还只能把原文打印到终端。今天要把检索结果拼成 Context，构造一个明确约束回答范围的 Prompt，再调用现有的 `LLMService` 生成回答，跑通 `问题 → 检索 → Context → 大模型 → 回答`。今天不新增 FastAPI 接口，先把 RAG 的核心服务链路单独做通。

---

# 一、先分清检索和生成的职责

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

昨天完成的链路是：

```text
用户问题
→ EmbeddingService.embed_query()
→ FAISSVectorStore.search()
→ top-3 Chunk
```

这部分叫检索。它负责从已有文档中找资料，但不会自己组织自然语言答案。

今天新增的部分是：

```text
top-3 Chunk
→ 拼成 Context
→ 和用户问题一起构造 Prompt
→ LLMService.chat()
→ 自然语言回答
```

这部分叫生成。大模型不是直接凭自己的记忆回答，而是先看到我们检索出的参考资料，再按照 Prompt 的要求作答。

可以把它理解成开卷考试：

```text
FAISS：从资料库中翻出最相关的几页
Context：把这几页摆到答题者面前
Prompt：说明题目和作答规则
LLM：阅读资料后组织答案
```

RAG 的关键不只是“调用了大模型”，而是让模型回答之前先拿到与问题相关的外部资料。

---

# 二、理解 Context 和 RAG Prompt

假设检索得到三段文字：

```text
Chunk 1：RAG 是 Retrieval-Augmented Generation 的缩写……
Chunk 2：基础流程包括接收问题、检索文档、拼接上下文……
Chunk 3：Chunk 是文档切分后的文本片段……
```

代码会把它们拼成一段 Context：

```text
[参考资料 1]
RAG 是 Retrieval-Augmented Generation 的缩写……

[参考资料 2]
基础流程包括接收问题、检索文档、拼接上下文……

[参考资料 3]
Chunk 是文档切分后的文本片段……
```

然后构造完整 Prompt：

```text
请根据下面的参考资料回答问题。

参考资料：
{context}

用户问题：
{question}

如果参考资料中没有答案，请明确说明不知道。
```

这里的最后一句很重要：

```text
如果参考资料中没有答案，请明确说明不知道。
```

它是在告诉模型回答边界，尽量减少模型脱离资料自由发挥。不过要注意：Prompt 只能降低幻觉风险，不能数学上保证模型永远不出错。后面仍然需要检查检索结果和模型回答。

今天给每段资料加上 `[参考资料 N]`，是为了让不同 Chunk 的边界更清楚。暂时不加入页码、文件名和相似度，这些信息会在后面的“引用来源”阶段完善。

---

# 三、创建 `rag_service.py`

新建：

```text
app/services/rag_service.py
```

写入：

```python
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store import FAISSVectorStore


def build_rag_prompt(
    question: str,
    contexts: list[str],
) -> str:
    """把参考资料和用户问题组合成 RAG Prompt。"""
    cleaned_question = question.strip()
    cleaned_contexts = [
        context.strip()
        for context in contexts
        if context.strip()
    ]

    if not cleaned_question:
        raise ValueError("question 不能为空")
    if not cleaned_contexts:
        raise ValueError("contexts 不能为空")

    context_text = "\n\n".join(
        f"[参考资料 {index}]\n{context}"
        for index, context in enumerate(
            cleaned_contexts,
            start=1,
        )
    )

    return (
        "请根据下面的参考资料回答问题。\n\n"
        f"参考资料：\n{context_text}\n\n"
        f"用户问题：\n{cleaned_question}\n\n"
        "如果参考资料中没有答案，请明确说明不知道。"
    )


class RAGService:
    """负责组织检索和大模型生成流程。"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: FAISSVectorStore,
        llm_service: LLMService,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.llm_service = llm_service

    async def answer(
        self,
        question: str,
        top_k: int = 3,
    ) -> tuple[str, list[str]]:
        """检索相关文本，并让大模型根据文本回答。"""
        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError("question 不能为空")

        query_vector = self.embedding_service.embed_query(
            cleaned_question
        )
        search_results = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
        )

        if not search_results:
            raise ValueError("没有检索到可用的参考资料")

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

今天不要修改 `app/main.py`，也不要把这段流程直接塞进 `/chat` 路由。`RAGService` 先负责组织 RAG 核心流程；下一次实现接口时，路由只需要接收问题并调用它。

---

# 四、理解为什么这里既有普通函数又有类

## 1. `build_rag_prompt()` 为什么是普通函数

它的行为是：

```text
输入 question 和 contexts
→ 整理字符串
→ 返回 Prompt
```

函数执行结束后，不需要长期保存 `self.xxx`，所以普通函数已经足够直接。

## 2. `RAGService` 为什么使用类

它需要在多次回答问题时继续复用：

```python
self.embedding_service
self.vector_store
self.llm_service
```

特别是 `vector_store` 中已经保存了文档向量和 Chunk 原文，不能每次问问题时都创建一个空索引。因此把三个服务作为对象状态保存下来更合适。

创建 `RAGService` 时，把已经准备好的对象传进去：

```python
rag_service = RAGService(
    embedding_service=embedding_service,
    vector_store=vector_store,
    llm_service=llm_service,
)
```

这种写法表示 `RAGService` 负责协调三个已有服务，而不是把 PDF 解析、向量计算、FAISS 和 HTTP 请求的所有代码重新写一遍。

## 3. 为什么 `answer()` 是 `async def`

前半段的 Embedding 和 FAISS 检索目前仍然是同步操作，但最后会调用：

```python
await self.llm_service.chat(prompt)
```

`LLMService.chat()` 是异步函数，所以调用它的 `answer()` 也需要是异步函数，并使用 `await` 等待网络响应。

这不代表 Embedding 和 FAISS 自动变快了。异步的主要作用仍然是：等待外部大模型返回期间，事件循环有机会处理其他任务。今天在 PowerShell 中只运行一次请求，重点是把调用关系写正确。

---

# 五、先单独检查 Prompt，不调用大模型

在真实调用模型前，先确认 Prompt 的格式符合预期。这样如果最终回答不合理，可以先排除“参考资料根本没有正确放进 Prompt”这种问题。

运行：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

@'
from app.services.rag_service import build_rag_prompt


prompt = build_rag_prompt(
    question="什么是 RAG？",
    contexts=[
        "RAG 是检索增强生成。",
        "RAG 会先检索资料，再让大模型生成回答。",
    ],
)

print(prompt)

assert "[参考资料 1]" in prompt
assert "[参考资料 2]" in prompt
assert "什么是 RAG？" in prompt
assert "如果参考资料中没有答案" in prompt

print("\nPrompt 格式验证通过")
'@ | python -
```

预期输出中应该清楚分成：

```text
作答要求
参考资料
用户问题
资料中没有答案时的限制
```

如果输出里出现字面量 `\n`，而不是实际换行，检查代码中是否误写成了：

```python
"\\n"
```

Python 字符串中的实际换行应当写成：

```python
"\n"
```

---

# 六、跑通完整 RAG 服务链路

Prompt 检查通过后，再使用现有的 `sample.pdf` 完成一次真实调用。这一步会请求大模型并消耗少量 API 额度，成功一次即可，不需要反复运行。

执行：

```powershell
@'
import asyncio

from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.vector_store import FAISSVectorStore


async def main() -> None:
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
    document_vectors = (
        embedding_service.embed_documents(chunks)
    )

    vector_store = FAISSVectorStore(
        dimension=len(document_vectors[0])
    )
    vector_store.add(chunks, document_vectors)

    rag_service = RAGService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_service=LLMService(),
    )

    question = "什么是 RAG，基础流程包括哪些步骤？"
    answer, sources = await rag_service.answer(
        question=question,
        top_k=3,
    )

    print("问题：")
    print(question)

    print("\n检索到的参考资料：")
    for index, source in enumerate(sources, start=1):
        print(f"\n[来源 {index}]")
        print(source)

    print("\n大模型回答：")
    print(answer)

    assert answer.strip()
    assert len(sources) == min(3, vector_store.count)
    assert any("RAG" in source for source in sources)

    print("\n完整 RAG 链路验证通过")


asyncio.run(main())
'@ | python -
```


这次测试要人工检查三件事：

```text
1. 来源确实是 sample.pdf 中检索到的原文
2. 回答内容能在这些来源中找到依据
3. 回答没有明显加入来源中不存在的关键事实
```

如果模型回答与资料无关，按顺序检查：

```text
先看 sources：相关 Chunk 是否进入 top-3
再看 Prompt：Context 和 question 是否都已放进去
最后看 answer：模型是否遵守了资料约束
```

这个排查顺序很重要，因为 RAG 的错误可能发生在两个不同阶段：

```text
检索错误：相关资料没有进入 top-3
生成错误：资料正确，但模型没有根据资料回答
```

今天不调整 `chunk_size`、`overlap` 或 `top_k`。先保证固定参数下的完整链路能够工作，后面的评估阶段再比较参数效果。

---

# 七、确认普通 `/chat` 没有被影响

今天没有修改 `LLMService.chat()`，只是让 `RAGService` 把完整 RAG Prompt 当作一条用户消息交给它。因此原来的普通聊天链路仍然是：

```text
POST /chat
→ LLMService.chat(message)
→ 普通大模型回答
```

新的 RAG 服务链路是：

```text
RAGService.answer(question)
→ 检索 top-3
→ 构造 RAG Prompt
→ LLMService.chat(prompt)
→ 基于资料回答
```

两条链路复用了同一个 `LLMService`，但传给模型的用户消息不同。今天不要把 `/chat` 改成 RAG，也不要修改聊天历史数据库。

---

# 八、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/services/rag_service.py docs/Day19.md
```

今天正常只应新增：

```text
app/services/rag_service.py
docs/Day19.md
```

新文件不会显示在普通 `git diff` 中时，可以直接检查：

```powershell
Get-Content app\services\rag_service.py
```

确认没有修改：

```text
app/main.py
app/models.py
app/services/llm_service.py
requirements.txt
.env
```

测试全部成功后执行：

```powershell
git add app/services/rag_service.py docs/Day19.md
git status
```

确认暂存区只有今天的两个文件，再提交：

```powershell
git commit -m "feat: connect retrieval to LLM"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看代码讲清楚完整链路：用户问题先怎样检索出 Chunk，这些 Chunk 怎样变成 Context，Prompt 怎样限制回答范围，为什么 `RAGService.answer()` 需要 `await`，以及如何区分检索错误和生成错误。

---

# Day 19 完成标准

- [ ] 能解释检索、Context、Prompt 和生成分别负责什么
- [ ] 已创建 `app/services/rag_service.py`
- [ ] 已实现 `build_rag_prompt(question, contexts)`
- [ ] Prompt 中包含参考资料、用户问题和“资料中没有答案时说明不知道”的约束
- [ ] 已实现异步的 `RAGService.answer()`
- [ ] `answer()` 会依次完成问题 Embedding、FAISS top-3 检索、Context 拼接和 LLM 调用
- [ ] 能解释为什么 `build_rag_prompt()` 使用普通函数，而 `RAGService` 使用类
- [ ] 已在不调用大模型的情况下单独验证 Prompt 格式
- [ ] 已使用 `sample.pdf` 得到一次有来源的真实大模型回答
- [ ] 能根据 sources 和 answer 区分检索错误与生成错误
- [ ] 已确认今天没有修改普通 `/chat`，也没有新增 FastAPI 接口
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交

