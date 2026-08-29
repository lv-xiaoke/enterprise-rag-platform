# Day 15：用 pypdf 按页提取 PDF 文本

Day 14 已经完成中文 Embedding：项目现在能把查询和文档文本转换成归一化向量，并比较语义相似度。Embedding 的输入仍然是普通字符串，所以今天继续完成 RAG 的上游步骤：从 PDF 中取得可以交给后续 Chunk 的文本。

今天只做一件事：选择一个 2～5 页、能够直接复制文字的小型 PDF，使用 `pypdf` 按页提取文本。完成后，你会得到 `PDFService.extract_pages()`，它返回一个按原页码排列的字符串列表；下一次学习 Chunk 时，可以直接使用今天提取出的文本。今天不做 PDF 上传接口、不做 OCR，也不调用 Embedding 或 DeepSeek。

---

# 一、先复习 RAG 中 PDF 和 Embedding 的先后顺序

打开项目：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
code .
```

Day 14 已经创建：

```text
app/services/embedding_service.py
```

它可以处理这样的输入：

```python
documents = [
    "RAG 在生成回答前会先检索外部资料。",
    "Embedding 模型会把文本转换成向量。",
]
```

但是用户真正提供的科研资料通常是一个 PDF 文件，而不是已经整理好的 `list[str]`。因此完整顺序应该是：

```text
PDF 文件
→ 提取每一页的文本
→ 把长文本切成 Chunk
→ 为每个 Chunk 生成 Embedding
→ 放入 FAISS 检索
```

今天只完成前两步中的“提取每一页文本”。暂时不要把整篇 PDF 直接交给 Embedding，因为长文档需要先在下一次学习中切块。

先尝试回答：

```text
EmbeddingService 为什么不能直接理解一个 PDF 文件路径？
为什么 PDF 文本提取应该发生在 Chunk 和 Embedding 之前？
```

可以这样理解：`EmbeddingService` 接收的是字符串，不负责认识 PDF 的内部文件格式；必须先用 PDF 解析工具取出文字，才能继续切块和向量化。

---

# 二、理解 PDF 文本提取是什么

PDF 更像一份“如何把内容画在页面上”的说明，而不是结构清楚的文章数据。页面中可能包含：

```text
文字
图片
公式
页眉和页脚
多栏排版
扫描得到的整页图片
```

今天使用的 `pypdf` 会读取 PDF 中已有的文字层，再通过：

```python
page.extract_text()
```

取得一页的文字。最基本的过程是：

```python
from pypdf import PdfReader

reader = PdfReader("sample.pdf")
page = reader.pages[0]
text = page.extract_text()
```

这里：

```text
PdfReader(...)
打开并解析 PDF

reader.pages
按顺序保存 PDF 的所有页面

reader.pages[0]
取得第一页；Python 的下标从 0 开始

page.extract_text()
提取当前页文字
```

可以参考 `pypdf` 的官方说明：

- [pypdf：Extract Text from a PDF](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
- [pypdf：PdfReader](https://pypdf.readthedocs.io/en/latest/modules/PdfReader.html)

今天先使用普通文本提取，不使用 `layout` 模式、坐标回调、表格解析或页眉页脚过滤。先把基础链路跑通，后面根据真实检索效果再决定是否清理版面噪声。

---

# 三、先选择适合今天测试的 PDF

当前项目中还没有测试 PDF。今天准备一个满足下面条件的文件：

```text
只有 2～5 页
文件没有密码
用鼠标能够选中并复制正文文字
内容中有几句你认识的文字，方便核对提取结果
不包含不适合提交到 Git 的敏感资料
```

不要一开始就使用上百页论文。文件太大时，终端输出不容易核对，也会把“基础代码是否正确”和“复杂 PDF 排版问题”混在一起。

创建本地文档目录：

```powershell
New-Item -ItemType Directory -Force data\documents
```

把选好的 PDF 复制进去，并命名为：

```text
data/documents/sample.pdf
```

可以使用文件资源管理器手动复制，也可以把下面的源路径换成自己的真实 PDF 路径：

```powershell
Copy-Item `
    -LiteralPath "D:\你的PDF所在目录\你的文件.pdf" `
    -Destination "data\documents\sample.pdf"
```

确认文件存在：

```powershell
Get-Item data\documents\sample.pdf |
    Select-Object Name, Length, FullName
```

不要打开或输出 `.env`。今天读取的只有你明确放入 `data/documents` 的测试 PDF。

---

# 四、忽略本地 PDF 文件

测试 PDF 属于本地输入数据，可能包含论文或个人资料，不应该在没有确认版权和隐私的情况下直接提交到 Git。

打开：

```text
.gitignore
```

在末尾加入：

```gitignore

# 本地 PDF 文档
data/documents/
```

然后检查规则是否生效：

```powershell
git check-ignore -v data\documents\sample.pdf
```

预期会看到 `.gitignore` 中的 `data/documents/` 规则。再执行：

```powershell
git status --short
```

`sample.pdf` 不应该出现在待提交文件中。如果仍然出现，先检查目录名和忽略规则，不要继续执行 `git add .`。

---

# 五、安装 pypdf

激活项目虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

当前项目还没有安装 `pypdf`。执行：

```powershell
python -m pip install pypdf
```

安装完成后验证导入：

```powershell
python -c "from pypdf import PdfReader; print(PdfReader)"
```

正常会输出 `PdfReader` 类的信息，并且没有 `ModuleNotFoundError`。

把新依赖写回项目：

```powershell
python -m pip freeze > requirements.txt
```

确认 `requirements.txt` 中已经出现 `pypdf`：

```powershell
Select-String -Path requirements.txt -Pattern "^pypdf=="
```

具体版本以你实际安装时的结果为准，不需要手动猜一个版本号。

---

# 六、创建 `PDFService`

新建：

```text
app/services/pdf_service.py
```

写入：

```python
from pathlib import Path

from pypdf import PdfReader


class PDFService:
    """负责从文本型 PDF 中提取每一页的文字。"""

    def extract_pages(
        self,
        pdf_path: str | Path,
    ) -> list[str]:
        """按原页码顺序返回每一页的文本。"""
        path = Path(pdf_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF 文件不存在：{path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("只支持 PDF 文件")

        reader = PdfReader(path)
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

今天先让这个服务只负责本地 PDF 文本提取，不要把它导入 `app/main.py`，也不要新增 `/upload` 接口。

---

# 七、逐段理解这段代码

## 1. 为什么接受 `str | Path`

```python
pdf_path: str | Path
```

表示调用者既可以传普通字符串：

```python
"data/documents/sample.pdf"
```

也可以传 `Path` 对象：

```python
Path("data/documents/sample.pdf")
```

函数内部统一执行：

```python
path = Path(pdf_path)
```

后面就可以方便地检查文件是否存在、是否为普通文件以及扩展名是否为 `.pdf`。

## 2. 为什么返回 `list[str]`

假设 PDF 有三页，返回结果类似：

```python
[
    "第一页的文字……",
    "第二页的文字……",
    "第三页的文字……",
]
```

列表下标和页码的关系是：

```text
pages[0] → 第 1 页
pages[1] → 第 2 页
pages[2] → 第 3 页
```

即使某一页没有提取到文本，代码也保留一个空字符串，而不是把这一页从列表中删除。这样 `pages[页码 - 1]` 的关系不会错位，后面实现来源页码时更容易追踪。

## 3. 为什么写 `page.extract_text() or ""`

某些页面可能没有可提取文字，`extract_text()` 可能得到 `None`。通过：

```python
page.extract_text() or ""
```

可以把它统一成空字符串，使返回值始终符合：

```python
list[str]
```

再使用：

```python
text.strip()
```

删除每页文字首尾多余的空白，但不尝试重新理解复杂的段落和表格结构。

## 4. 为什么最后检查 `any(pages)`

```python
if not any(pages):
```

表示所有页面都是空字符串。如果发生这种情况，最常见原因是 PDF 只有扫描图片，没有可复制的文字层。与其悄悄返回空内容，不如明确告诉调用者当前文件不适合今天的文本提取方式。

---

# 八、运行并检查真实提取结果

先统一 PowerShell 的终端输出编码，避免中文显示乱码：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

在项目根目录运行：

```powershell
@'
from pathlib import Path

from app.services.pdf_service import PDFService


pdf_path = Path("data/documents/sample.pdf")
service = PDFService()
pages = service.extract_pages(pdf_path)

print("PDF 页数：", len(pages))

for page_number, page_text in enumerate(pages, start=1):
    print(f"\n--- 第 {page_number} 页 ---")
    print(page_text or "[本页未提取到文本]")

full_text = "\n\n".join(
    page_text for page_text in pages if page_text
)
print("\n提取出的总字符数：", len(full_text))
'@ | python -
```

预期结果不是某段固定文字，而是：

```text
PDF 页数与文件实际页数一致
终端按照第 1 页、第 2 页……输出正文
你能在输出中找到 PDF 里原本存在的几句话
总字符数大于 0
```

这段测试最后把非空页面连接成：

```python
full_text
```

它就是下一次字符切块函数的输入。今天只观察它，不要提前实现 `split_text()`。

如果中文出现乱码，先确认 PowerShell 输出编码设置已经执行，再检查 PDF 自身是否有正常文字层。终端编码只能解决“输出显示”问题，不能修复 PDF 内部错误的字体映射。

---

# 九、认识今天不解决的 PDF 情况

`pypdf` 不是 OCR 工具。如果 PDF 每一页都是扫描图片，肉眼能看到文字，但程序可能提取不到任何内容。可以先用最简单的方法判断：

[[OCR工具]]

```text
能在 PDF 阅读器中用鼠标选中并复制正文
→ 通常存在文字层，适合今天测试

只能框选整张页面图片，不能复制正文
→ 很可能是扫描 PDF，需要 OCR
```

今天遇到扫描 PDF 时，换一个带文字层的小文件继续练习，并把问题记录在文末。不要临时安装 Tesseract、PaddleOCR 或其他 OCR 工具，因为本月当前目标是先跑通纯文本科研文档 RAG。

即使是文本型 PDF，提取结果仍可能出现：

```text
双栏论文阅读顺序不自然
页眉和页脚混入正文
单词被换行拆开
表格结构丢失
公式提取不完整
```

这些现象不一定表示代码写错了。PDF 本身缺少稳定的段落、标题和表格语义。今天的成功标准是取得可读的主体文字，不要求还原原始页面排版。

---

# 十、验证错误路径会被明确拒绝

再运行一个不需要真实 PDF 的小实验：

```powershell
@'
from app.services.pdf_service import PDFService


try:
    PDFService().extract_pages("data/documents/not-found.pdf")
except FileNotFoundError as exc:
    print(type(exc).__name__)
    print(str(exc))
'@ | python -
```

预期输出类似：

```text
FileNotFoundError
PDF 文件不存在：data\documents\not-found.pdf
```

这说明文件路径错误时，服务会给出清楚的原因，而不是让后面的 `PdfReader` 产生难以理解的异常。

今天不需要为损坏 PDF、加密 PDF 和超大 PDF 编写完整异常处理。先把遇到的真实错误摘要记下来，等接口和测试逐步完善时再处理。

---

# 十一、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- .gitignore requirements.txt app/services/pdf_service.py
git check-ignore -v data\documents\sample.pdf
git check-ignore -v .env
git check-ignore -v data\chat.db
```

新建的 `pdf_service.py` 可能不会出现在普通 `git diff` 中，可以在 VS Code 中复查，或者执行：

```powershell
Get-Content app\services\pdf_service.py
```

确认：

```text
pypdf 已写入 requirements.txt
PDFService 会按页返回 list[str]
真实 PDF 页数和提取结果能够对应
没有修改 main.py、embedding_service.py 或 llm_service.py
没有新增上传接口、Chunk、OCR、FAISS 或 RAG 调用
sample.pdf、.env 和 chat.db 都没有进入 Git 状态
```

所有测试成功后，只添加今天需要提交的代码和文档：

```powershell
git add .gitignore requirements.txt app/services/pdf_service.py docs/Day15.md
git status
```

再次确认暂存区没有测试 PDF、`.env` 和数据库文件，然后提交：

```powershell
git commit -m "feat: add PDF text extraction service"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后不看代码，尝试用自己的话讲清楚：`PdfReader` 和 `page.extract_text()` 分别做什么，为什么返回结果要按页保存，为什么有些肉眼可见的文字仍然提取不到，以及今天的输出下一步怎样交给 Chunk。

---

# Day 15 完成标准

```text
[ ] 能解释 PDF 文本提取在 Chunk 和 Embedding 之前的原因
[ ] 已准备一个 2～5 页、可以复制文字的小型 PDF
[ ] 已安装 pypdf 并更新 requirements.txt
[ ] 已创建 app/services/pdf_service.py
[ ] PDFService.extract_pages() 会按原页码返回 list[str]
[ ] 实际页数与返回列表长度一致，并能输出可读正文
[ ] 能解释 page.extract_text()、or "" 和 any(pages) 的作用
[ ] 能说明 pypdf 为什么不能替代 OCR
[ ] 测试 PDF、.env 和 chat.db 都没有进入 Git 暂存区
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
