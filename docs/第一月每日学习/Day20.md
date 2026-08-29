# Day 20：完成 PDF 上传和 RAG 问答接口

昨天已经完成了 RAG 的核心服务链路：`RAGService.answer()` 会把问题转换成向量、从 FAISS 检索 top-3 Chunk、构造 Context，并让大模型根据资料回答。现在这条链路只能在 PowerShell 脚本中调用，外部用户还不能通过 HTTP 使用。今天要把它接入 FastAPI，完成 `POST /upload` 和 `POST /rag/chat`，最终通过两个接口跑通“上传 PDF，再针对 PDF 提问并返回回答与来源”。

---

# 一、先理解两个接口为什么要分开

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

今天实现的两个接口职责不同。

第一个接口：

```http
POST /upload
```

负责完成一次文档准备：

```text
接收 PDF
→ 提取文字
→ 切成 Chunk
→ 生成文档向量
→ 创建 FAISS 索引
→ 准备 RAGService
```

第二个接口：

```http
POST /rag/chat
```

负责回答问题：

```text
接收 question
→ 使用已准备好的 RAGService
→ 检索 top-3 Chunk
→ 调用大模型
→ 返回 answer 和 sources
```

不应该在每次提问时重新解析 PDF 和生成全部文档向量。文档准备通常比一次检索更重，所以先上传并建立索引，之后可以针对同一份文档连续提问。

今天先做最简单的内存版本：

```text
只保存最近一次上传的 PDF 索引
后上传的 PDF 会替换前一个索引
服务重启后索引会消失，需要重新上传
```

这足以完成月计划中的最小 RAG 后端。今天不增加多文档 ID、磁盘持久化、用户隔离或数据库表。

---

# 二、安装文件上传需要的依赖

FastAPI 接收文件时，请求体使用的是：

```text
multipart/form-data
```

它与 `/rag/chat` 使用的 JSON 请求体不是同一种格式。FastAPI 处理上传表单需要 `python-multipart`，先安装：

```powershell
python -m pip install python-multipart
```

验证安装位置和版本：

```powershell
python -m pip show python-multipart
```

然后更新依赖快照：

```powershell
python -m pip freeze > requirements.txt
```

FastAPI 官方文件上传说明可以作为参考：[Request Files](https://fastapi.tiangolo.com/tutorial/request-files/)。其中要先记住两点：

```text
UploadFile 提供文件名、Content-Type 和文件内容
在 async 路由中读取上传内容要使用 await file.read()
```

今天只上传几页的小 PDF，可以一次读取为 `bytes`。大型文件的流式处理和大小限制以后再做。

---

# 三、让 PDFService 支持上传得到的 bytes

当前 `PDFService.extract_pages()` 只能接收磁盘路径：

```python
PDFService().extract_pages("data/documents/sample.pdf")
```

但 `UploadFile` 读取后得到的是：

```python
pdf_bytes = await file.read()
```

今天不把上传文件永久写入 `data/documents`，而是使用 `BytesIO` 把内存中的 `bytes` 包装成文件流，再交给 `PdfReader`。
（以前你的 PDF 解析代码只能读取“硬盘上的 PDF 文件”；现在要支持“用户上传的 PDF”，而且不想先把上传文件保存到硬盘，所以把上传得到的二进制数据放在内存里，伪装成一个文件，再交给 `PdfReader` 读取。）

打开：

```text
app/services/pdf_service.py
```

在文件顶部增加导入：

```python
from io import BytesIO
```

然后把类整理成：

```python
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PDFService:
    """负责从文本型 PDF 中提取每一页的文字。"""

    def extract_pages(
        self,
        pdf_path: str | Path,
    ) -> list[str]:
        """从本地 PDF 路径中按页提取文字。"""
        path = Path(pdf_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF 文件不存在：{path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("只支持 PDF 文件")

        reader = PdfReader(path)
        return self._extract_text(reader)

    def extract_pages_from_bytes(
        self,
        pdf_bytes: bytes,
    ) -> list[str]:
        """从上传得到的 PDF 字节中按页提取文字。"""
        if not pdf_bytes:
            raise ValueError("PDF 文件不能为空")

        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            return self._extract_text(reader)
        except (PdfReadError, EOFError) as exc:
            raise ValueError("PDF 文件无法解析") from exc

    def _extract_text(
        self,
        reader: PdfReader,
    ) -> list[str]:
        """复用按页提取文字的共同逻辑。"""
        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())

        if not any(pages):
            raise ValueError(
                "没有提取到文本，请确认 PDF 包含可复制的文字"
            )

        return pages
```

这里没有保留两份相同的“遍历页面”代码，而是让两种输入最后都调用：

```python
self._extract_text(reader)
```

可以把它理解为：

```text
本地路径 ─┐
           ├→ PdfReader → _extract_text() → list[str]
上传 bytes ┘
```

`BytesIO(pdf_bytes)` 不会修改 PDF 内容，它只是让一串内存字节表现得像一个可读取的文件。

---

# 四、定义上传和 RAG 问答的数据模型

打开：

```text
app/models.py
```

在现有模型后面增加：

```python
class UploadResponse(BaseModel):
    """PDF 上传并建立索引后的响应。"""

    filename: str
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)


class RAGChatRequest(BaseModel):
    """RAG 问答请求。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对已上传 PDF 提出的问题",
    )


class RAGChatResponse(BaseModel):
    """RAG 问答响应。"""

    answer: str
    sources: list[str]
```

三个模型分别描述：

```text
UploadResponse：上传后返回文件名、页数和 Chunk 数
RAGChatRequest：客户端发送的问题
RAGChatResponse：模型回答和检索到的原始文本
```

`sources` 今天直接返回字符串列表，与现有 `RAGService.answer()` 的返回值保持一致。页码和相似度要等后面的“引用来源”阶段再加入。

给接口声明 `response_model` 后，FastAPI 会使用模型生成接口文档，并检查返回数据是否符合约定。可参考官方说明：[Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)。

---

# 五、在 main.py 中准备可复用的 RAG 状态

打开：

```text
app/main.py
```

先修改 FastAPI 导入：

```python
from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
```

把模型导入改为：

```python
from app.models import (
    ChatRequest,
    ChatResponse,
    Message,
    RAGChatRequest,
    RAGChatResponse,
    UploadResponse,
)
```

再增加今天需要的服务导入：

```python
from app.services.chunk_service import split_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.vector_store import FAISSVectorStore
```

在现有：

```python
llm_service = LLMService()
```

下面增加：

```python
pdf_service = PDFService()
embedding_service = EmbeddingService()
rag_service: RAGService | None = None

CHUNK_SIZE = 200
CHUNK_OVERLAP = 40
TOP_K = 3
```

这里的 `rag_service` 一开始是 `None`，因为用户还没有上传 PDF，系统中没有文档向量库。上传成功后，它才会指向一个真正的 `RAGService` 对象。

```text
刚启动：rag_service = None
上传成功：rag_service = RAGService(...)
后续提问：重复使用这个对象中的 FAISS 索引
```

`EmbeddingService()` 会在应用加载时加载本地 Embedding 模型，所以 Uvicorn 第一次启动可能比以前慢。看到“Application startup complete”后再测试接口。

---

# 六、实现 POST /upload

在 `app/main.py` 的现有路由后增加：

```python
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile) -> UploadResponse:
    global rag_service

    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="只支持上传 PDF 文件",
        )

    pdf_bytes = await file.read()

    try:
        pages = pdf_service.extract_pages_from_bytes(pdf_bytes)

        chunks: list[str] = []
        for page_text in pages:
            chunks.extend(
                split_text(
                    page_text,
                    chunk_size=CHUNK_SIZE,
                    overlap=CHUNK_OVERLAP,
                )
            )

        if not chunks:
            raise ValueError("PDF 没有生成任何 Chunk")

        document_vectors = (
            embedding_service.embed_documents(chunks)
        )

        vector_store = FAISSVectorStore(
            dimension=len(document_vectors[0])
        )
        vector_store.add(chunks, document_vectors)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    rag_service = RAGService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_service=llm_service,
    )

    return UploadResponse(
        filename=filename,
        page_count=len(pages),
        chunk_count=len(chunks),
    )
```

逐步看这段路由。

## 1. 为什么需要 `global rag_service`

路由不是只读取现有对象，而是要执行：

```python
rag_service = RAGService(...)
```

也就是把模块级变量从 `None` 替换为新对象。函数内部对模块变量重新赋值时，需要先声明：

```python
global rag_service
```

它不是让状态永久保存，只是让本次 Python 进程中的后续请求可以访问新对象。

## 2. 为什么先建立局部 vector_store，再替换 rag_service

只有 PDF 解析、切块、Embedding 和 FAISS 写入全部成功后，才执行：

```python
rag_service = RAGService(...)
```

如果新上传的文件解析失败，原来的 `rag_service` 不会在处理到一半时被替换成坏状态。

## 3. `await file.read()` 是不是让 PDF 解析和 Embedding 都异步了

不是。它只异步读取上传文件。后面的 `pypdf`、切块、Embedding 和 FAISS 当前仍是同步计算，小项目先接受这个限制。不要因为路由写了 `async def`，就认为里面每一步都会自动并行或加速。

## 4. 为什么今天不保存 PDF 到磁盘

上传内容只在内存中用于建立索引，接口不会创建用户文件，也不会把 PDF 加入 Git。这让今天更专注于完整接口链路。服务重启后需要重新上传，是当前版本明确接受的限制。

---

# 七、实现 POST /rag/chat

继续在 `app/main.py` 中增加：

```python
@app.post("/rag/chat", response_model=RAGChatResponse)
async def rag_chat(
    request: RAGChatRequest,
) -> RAGChatResponse:
    if rag_service is None:
        raise HTTPException(
            status_code=400,
            detail="请先上传 PDF",
        )

    try:
        answer, sources = await rag_service.answer(
            question=request.question,
            top_k=TOP_K,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return RAGChatResponse(
        answer=answer,
        sources=sources,
    )
```

这个路由本身很短，因为检索、Prompt 和模型调用已经封装在：

```python
RAGService.answer()
```

路由只负责：

```text
接收并校验 HTTP 请求
检查是否已经上传 PDF
调用服务
把业务异常转换成 HTTP 状态码
按响应模型返回 JSON
```

这里不需要写 `global rag_service`，因为函数只读取它，没有为它重新赋值。

今天暂时不把 RAG 问答写入原来的 `messages` 表。普通 `/chat` 的历史与 PDF 问答来源结构不同，等接口链路稳定以后再决定是否统一保存。

---

# 八、启动服务并按顺序测试

今天需要两个终端。

## 终端 A：启动 FastAPI

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
python -m uvicorn app.main:app --reload
```

第一次加载 Embedding 模型可能稍慢。等终端出现：

```text
Application startup complete
```

再打开：

```text
http://127.0.0.1:8000/docs
```

确认 Swagger 中出现：

```text
POST /upload
POST /rag/chat
```

如果启动时报错提示需要 `python-multipart`，检查终端是否激活了正确的 `.venv`，再执行：

```powershell
python -m pip show python-multipart
```

## 终端 B：先验证未上传时不能提问

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
$body = @{
    question = "什么是 RAG？"
} | ConvertTo-Json
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

try {
    Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/rag/chat" `
        -Method Post `
        -ContentType "application/json; charset=utf-8" `
        -Body $bodyBytes
} catch {
    $_.ErrorDetails.Message
}
```

预期返回 400，内容包含：

```json
{
  "detail": "请先上传 PDF"
}
```

这个测试说明接口不会在没有知识库的情况下悄悄退化成普通聊天。

## 终端 B：上传 sample.pdf

Windows 自带的 `curl.exe` 可以直接构造文件表单：

```powershell
curl.exe `
    -X POST `
    -F "file=@data/documents/sample.pdf;type=application/pdf" `
    "http://127.0.0.1:8000/upload"
```

预期返回类似：

```json
{
  "filename": "sample.pdf",
  "page_count": 3,
  "chunk_count": 10
}
```

`chunk_count` 取决于实际提取文本和切块结果，不要求一定等于示例中的 `10`，但必须大于 0。

如果返回“PDF 文件无法解析”，先确认上传的是项目中的真实 `sample.pdf`，而不是同名文本文件。如果返回“没有提取到文本”，说明 PDF 可能只有扫描图片；今天仍然不加入 OCR。

## 终端 B：针对已上传 PDF 提问

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
$result.sources
```

这次请求会调用大模型并消耗少量 API 额度，成功一次即可。预期：

```text
answer 是根据 PDF 内容组织的自然语言回答
sources 包含最多 3 个从 PDF 中检索到的原始 Chunk
```

人工检查回答中的关键事实能否在 `sources` 中找到依据。不能只看到状态码 200 就认为 RAG 一定正确。

---

# 九、补充错误输入和回归检查

## 1. 上传非 PDF 文件

```powershell
curl.exe `
    -i `
    -X POST `
    -F "file=@README.md;type=text/markdown" `
    "http://127.0.0.1:8000/upload"
```

预期状态码：

```text
400 Bad Request
```

响应应包含：

```text
只支持上传 PDF 文件
```

## 2. 检查原有接口

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
Invoke-RestMethod "http://127.0.0.1:8000/history"
```

预期两个接口仍然返回 200。再查看 Swagger，确认原来的：

```text
POST /chat
GET /history
GET /health
```

没有因为新增 RAG 接口而消失。

完成测试后，在终端 A 按：

```text
Ctrl + C
```

停止服务。

---

# 十、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- requirements.txt app/models.py app/main.py app/services/pdf_service.py docs/Day20.md
```

今天正常涉及：

```text
requirements.txt
app/models.py
app/main.py
app/services/pdf_service.py
docs/Day20.md
```

确认：

```text
没有修改 app/services/rag_service.py 的核心流程
没有修改普通 /chat 和聊天历史逻辑
没有创建或提交上传的 PDF
.env、API Key、data/chat.db 没有进入 Git 状态
```

测试全部成功以后执行：

```powershell
git add requirements.txt app/models.py app/main.py app/services/pdf_service.py docs/Day20.md
git status
```

确认暂存区只有今天需要的文件，再提交：

```powershell
git commit -m "feat: add PDF upload and RAG chat API"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看代码讲清楚：为什么上传和提问分成两个接口，`rag_service` 在上传前后分别是什么状态，`UploadFile` 与 JSON 请求体有什么区别，上传的 PDF 怎样一路变成 FAISS 索引，以及 `/rag/chat` 为什么能返回回答和来源。

---

# Day 20 完成标准

- [ ] 能解释 `/upload` 和 `/rag/chat` 为什么要分成两个接口
- [ ] 已安装 `python-multipart` 并更新 `requirements.txt`
- [ ] `PDFService` 能从上传得到的 PDF bytes 中按页提取文字
- [ ] 已定义 `UploadResponse`、`RAGChatRequest` 和 `RAGChatResponse`
- [ ] 已实现 `POST /upload`，能够完成 PDF 解析、Chunk、Embedding 和 FAISS 建库
- [ ] 已实现 `POST /rag/chat`，固定检索 top-3 并返回 `answer` 和 `sources`
- [ ] 未上传 PDF 时调用 `/rag/chat` 会返回 400
- [ ] 非 PDF 文件上传会返回 400
- [ ] 已使用 `sample.pdf` 跑通“上传 → 提问 → 回答和来源”的完整 HTTP 链路
- [ ] 能说明 `await file.read()` 不会让 PDF 解析和 Embedding 自动异步加速
- [ ] 能说明当前索引只在内存中保存、后上传会覆盖前上传、重启后需要重新上传
- [ ] 原有 `/chat`、`/history` 和 `/health` 仍然可用
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
