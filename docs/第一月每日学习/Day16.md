# Day 16：实现带 overlap 的文本切块

Day 15 已经使用 `pypdf` 按页提取了 `data/documents/sample.pdf` 的文字，`PDFService.extract_pages()` 会返回一个与原页码对应的 `list[str]`。现在已经有了文本，但还不能把整页甚至整篇文档直接拿去检索：内容太长时，一个向量会混合多个主题，检索结果也很难准确定位到具体段落。

今天只做一件事：实现最简单的字符切块函数 `split_text()`，理解 `chunk_size` 和 `overlap`，再把现有 PDF 的每一页切成较短文本块。完成后，你会得到一个 `app/services/chunk_service.py`，为下一步“Chunk → Embedding → FAISS”准备输入。今天不安装新依赖，不调用 Embedding、DeepSeek，也不新增 FastAPI 接口。

---

# 一、先复习 PDF 文本现在是什么结构

打开项目：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
code .
```

查看：

```text
app/services/pdf_service.py
```

当前方法：

```python
pages = PDFService().extract_pages(
    "data/documents/sample.pdf"
)
```

返回结果可以理解为：

```python
[
    "第一页的全部文字……",
    "第二页的全部文字……",
    "第三页的全部文字……",
]
```

这已经保留了页码关系：

```text
pages[0] → 第 1 页
pages[1] → 第 2 页
```

但一页可能有几千个字符，并且可能同时包含论文背景、方法和实验等不同主题。如果直接给整页生成一个向量，用户只问其中一个具体概念时，这个大向量表达的内容会比较混杂。

所以今天要在 PDF 解析和 Embedding 中间加入：

```text
一页长文本
→ split_text()
→ 多个较短 Chunk
```

先尝试回答：

```text
为什么已经按页提取文本以后，还需要继续切块？
一个 Chunk 在后续 RAG 中会用来做什么？
```

可以简单回答：页码是文档的版面单位，不一定是合适的语义检索单位；每个 Chunk 后面会单独生成向量，用户提问时再找出最相似的几个 Chunk。

---

# 二、理解 Chunk、chunk_size 和 overlap

## 1. Chunk 是什么

Chunk 就是从长文本中切出的一小段文本。

例如原文是：

```text
RAG 会先把文档切成多个文本块。每个文本块会生成向量。用户提问时，系统检索最相关的文本块，再让大模型根据这些资料回答。
```

切块后可能变成：

```text
Chunk 1：RAG 会先把文档切成多个文本块……
Chunk 2：每个文本块会生成向量……
Chunk 3：用户提问时，系统检索最相关的文本块……
```

后续不是为整篇 PDF 只生成一个向量，而是：

```text
Chunk 1 → 向量 1
Chunk 2 → 向量 2
Chunk 3 → 向量 3
```

这样用户的问题只和某一小段有关时，系统可以直接找出那一段。

## 2. `chunk_size` 是什么

今天按 Python 字符串长度切块：

```python
chunk_size = 500
```

表示每个 Chunk 最多取 500 个字符。这里计算的是：

```python
len(text)
```

不是大模型 Token 数量。中文字符、英文字母、标点和空格都会参与字符串长度计算；字符数和 Token 数也不是固定的一一对应关系。

`chunk_size` 太大时：

```text
一个 Chunk 可能包含多个主题
检索结果不够精确
传给大模型的无关内容变多
```

`chunk_size` 太小时：

```text
一句完整的话可能被拆开
定义和解释可能落入不同 Chunk
检索到的片段缺少上下文
```

今天先用 `500` 作为容易观察的起点，不把它当成永远正确的答案。后面建立测试问题集后，还要根据检索效果调整。

## 3. `overlap` 是什么

如果每 500 个字符直接切一刀，边界附近的一句话可能被拆成两半。`overlap` 表示相邻 Chunk 之间重复保留一部分内容。

例如：

```text
chunk_size = 10
overlap = 3
```

对字母串：

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZ
```

切块位置是：

```text
Chunk 1：ABCDEFGHIJ
Chunk 2：HIJKLMNOPQ
Chunk 3：OPQRSTUVWX
Chunk 4：VWXYZ
```

可以观察到：

```text
Chunk 1 结尾 HIJ = Chunk 2 开头 HIJ
Chunk 2 结尾 OPQ = Chunk 3 开头 OPQ
```

每次真正向前移动的字符数是：

```text
step = chunk_size - overlap
```

上面的例子中：

```text
step = 10 - 3 = 7
```

所以每个新 Chunk 从上一个起点向后移动 7 个字符，而不是 10 个字符。

---

# 三、先想清楚参数为什么需要限制

今天的函数允许调用者传入：

```python
split_text(text, chunk_size=500, overlap=100)
```

但下面这些参数不合理：

```text
chunk_size = 0
chunk_size = -10
overlap = -1
overlap >= chunk_size
```

特别是：

```text
overlap >= chunk_size
```

会使：

```text
step = chunk_size - overlap
```

变成 0 或负数。循环起点无法正常向前移动，程序可能陷入无限循环。

所以函数开始时要明确检查：

```text
chunk_size 必须大于 0
overlap 不能小于 0
overlap 必须小于 chunk_size
```

这和以前的 Pydantic 校验思路相似：先拒绝不合法输入，再执行真正的业务逻辑。

---

# 四、创建 `chunk_service.py`

新建：

```text
app/services/chunk_service.py
```

写入：

```python
def split_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """按字符数切分文本，并在相邻文本块之间保留重叠。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if overlap < 0:
        raise ValueError("overlap 不能小于 0")

    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0

    while start < len(cleaned_text):
        end = start + chunk_size
        chunk = cleaned_text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(cleaned_text):
            break

        start += step

    return chunks
```

这里使用普通函数，不定义 `ChunkService` 类。原因是今天的切块逻辑只依赖传入的文本和参数，不需要像 `EmbeddingService` 那样加载模型，也不需要像 `PDFService` 那样保存额外状态。对于这种明确、独立的计算，普通函数更直接。

```
需要长期保存并复用 self.xxx
→ 类通常更合适

输入数据 → 计算 → 返回结果
不需要保存 self.xxx
→ 普通函数通常更直接
```

---

# 五、逐步理解 `while` 切块过程

## 1. 清理空白输入

```python
cleaned_text = text.strip()

if not cleaned_text:
    return []
```

如果输入是空字符串或只有空格，没有内容可以切分，就返回空列表：

```python
[]
```

这不属于程序崩溃，所以不需要抛异常。

## 2. 计算每次向前移动的距离

```python
step = chunk_size - overlap
```

默认参数下：

```text
chunk_size = 500
overlap = 100
step = 400
```

因此切块起点依次是：

```text
0
400
800
1200
……
```

第一个 Chunk 读取 `[0:500]`，第二个读取 `[400:900]`，所以中间的 `[400:500]` 会重复出现在两个 Chunk 中。

## 3. Python 切片不会越界报错

```python
chunk = cleaned_text[start:end]
```

如果最后剩余文本不足 500 个字符，Python 会直接取到字符串结尾，不会因为 `end` 超过长度而报错。

例如只剩 120 个字符时，最后一个 Chunk 的长度就是 120。

## 4. 为什么需要主动 `break`

```python
if end >= len(cleaned_text):
    break
```

说明本次切片已经覆盖文本结尾，不需要再为了 overlap 产生一个几乎重复的尾部 Chunk。随后退出循环并返回结果。

---

# 六、先用短字符串验证切块边界

今天先用能够手工核对的字母串测试，不要一上来只看几千字 PDF，因为短例子更容易发现起点计算是否正确。

激活虚拟环境并统一输出编码：

```powershell
.\.venv\Scripts\Activate.ps1
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

运行：

```powershell
@'
from app.services.chunk_service import split_text


text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
chunks = split_text(
    text,
    chunk_size=10,
    overlap=3,
)

for index, chunk in enumerate(chunks, start=1):
    print(f"Chunk {index}：{chunk}")

print("Chunk 数量：", len(chunks))
print("第 1、2 块重叠：", chunks[0][-3:], chunks[1][:3])
print("第 2、3 块重叠：", chunks[1][-3:], chunks[2][:3])
'@ | python -
```

预期输出：

```text
Chunk 1：ABCDEFGHIJ
Chunk 2：HIJKLMNOPQ
Chunk 3：OPQRSTUVWX
Chunk 4：VWXYZ
Chunk 数量： 4
第 1、2 块重叠： HIJ HIJ
第 2、3 块重叠： OPQ OPQ
```

如果第二个 Chunk 从 `K` 开始，说明代码每次移动了完整的 `chunk_size`，没有减去 `overlap`。重点检查：

```python
step = chunk_size - overlap
start += step
```

---

# 七、验证空文本和错误参数

运行：

```powershell
@'
from app.services.chunk_service import split_text


print("空文本：", split_text("   "))

test_cases = [
    {"chunk_size": 0, "overlap": 0},
    {"chunk_size": 10, "overlap": -1},
    {"chunk_size": 10, "overlap": 10},
]

for params in test_cases:
    try:
        split_text("测试文本", **params)
    except ValueError as exc:
        print(params, "→", str(exc))
'@ | python -
```

预期结果包含：

```text
空文本： []
chunk_size 必须大于 0
overlap 不能小于 0
overlap 必须小于 chunk_size
```

`**params` 表示把字典中的键和值作为函数参数传入。例如：

```python
{"chunk_size": 10, "overlap": 3}
```

等价于：

```python
split_text(
    "测试文本",
    chunk_size=10,
    overlap=3,
)
```

---

# 八、把现有 PDF 按页切块

短字符串测试通过以后，再连接 Day 15 的 PDF 文本解析。今天仍然不启动 FastAPI，只在 PowerShell 中直接调用两个 Python 模块。

运行：

```powershell
@'
from app.services.chunk_service import split_text
from app.services.pdf_service import PDFService


pdf_path = "data/documents/sample.pdf"
pages = PDFService().extract_pages(pdf_path)

all_chunks: list[tuple[int, int, str]] = []

for page_number, page_text in enumerate(pages, start=1):
    page_chunks = split_text(
        page_text,
        chunk_size=50,
        overlap=10,
    )

    for chunk_number, content in enumerate(
        page_chunks,
        start=1,
    ):
        all_chunks.append(
            (page_number, chunk_number, content)
        )

print("PDF 页数：", len(pages))
print("Chunk 总数：", len(all_chunks))

for page_number, chunk_number, content in all_chunks[:5]:
    print(
        f"\n[第 {page_number} 页 / Chunk {chunk_number} / "
        f"长度 {len(content)}]"
    )
    print(content[:200])
'@ | python -
```

实际 Chunk 数量取决于 PDF 的文字量，不要求等于固定数字。重点检查：

```text
Chunk 总数大于 0
每个普通 Chunk 的长度不超过 500
输出能看到来源页码和页内 Chunk 编号
前几个 Chunk 是 sample.pdf 中的真实文字
```

这里使用：

```python
tuple[int, int, str]
```

临时保存：

```text
页码
页内 Chunk 编号
Chunk 文本
```

今天暂时不把它设计成 Pydantic 模型或写入数据库。等后面真正返回来源时，再根据接口需要整理正式的数据结构。

---

# 九、比较没有 overlap 和有 overlap 的区别

选择 PDF 第一页做一个小实验：

```powershell
@'
from app.services.chunk_service import split_text
from app.services.pdf_service import PDFService


first_page = PDFService().extract_pages(
    "data/documents/sample.pdf"
)[0]

without_overlap = split_text(
    first_page,
    chunk_size=50,
    overlap=0,
)
with_overlap = split_text(
    first_page,
    chunk_size=50,
    overlap=10,
)

print("没有 overlap 的 Chunk 数量：", len(without_overlap))
print("有 overlap 的 Chunk 数量：", len(with_overlap))

if len(with_overlap) >= 2:
    print("\n第 1 块结尾：")
    print(with_overlap[0][-100:])
    print("\n第 2 块开头：")
    print(with_overlap[1][:100])
'@ | python -
```

如果第一页文字不足 500 个字符，只会得到一个 Chunk，看不到重叠。这不是代码错误，可以改用文字更多的一页，或者只使用前面的字母串实验验证 overlap。

有 overlap 时，Chunk 数量通常会略多，因为一部分内容被重复保留。这是一种取舍：

```text
好处：降低重要句子正好被边界切断的概率
代价：向量数量、索引空间和重复检索内容会增加
```

今天不比较很多组参数。先确认 `500 + 100` 的基础行为正确，后续评估阶段再调整 `chunk_size` 和 `overlap`。

---

# 十、理解今天这种切块方式的限制

今天实现的是字符切块，它只按照位置切，不理解句子、段落或论文结构。

因此它可能：

```text
在一句话中间切开
把标题和正文分到不同 Chunk
把跨页的一段话拆开
保留页眉、页脚等 PDF 噪声
```

但它仍然适合作为第一个可运行版本，因为：

```text
代码短，容易解释
参数行为明确
可以快速连接 Embedding 和 FAISS
后面能够用测试问题观察真实效果
```

不要今天就改成按 Token、句子、Markdown 标题或递归分割，也不要引入 LangChain。先跑通简单基线，才能知道后续复杂方法到底改善了什么。

---

# 十一、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/services/chunk_service.py docs/Day16.md
git check-ignore -v data\documents\sample.pdf
git check-ignore -v .env
git check-ignore -v data\chat.db
```

新建的 `chunk_service.py` 可能不会出现在普通 `git diff` 中，可以在 VS Code 中复查，或者执行：

```powershell
Get-Content app\services\chunk_service.py
```

确认：

```text
split_text() 会检查 chunk_size 和 overlap
空白文本会返回空列表
短字符串的切块位置和重叠内容符合预期
sample.pdf 能按页产生 Chunk
没有修改 PDFService、EmbeddingService 或 main.py
没有安装新依赖，requirements.txt 不应该发生变化
没有提前实现 FAISS、检索、RAG 接口或 OCR
sample.pdf、.env 和 chat.db 都没有进入 Git 状态
```

测试成功后添加：

```powershell
git add app/services/chunk_service.py docs/Day16.md
git status
```

确认暂存区只有今天的切块代码和学习记录，然后提交：

```powershell
git commit -m "feat: add overlapping text splitter"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后不看代码，尝试用自己的话讲清楚：为什么 RAG 需要 Chunk，`chunk_size` 和 `overlap` 分别控制什么，为什么每次移动距离是 `chunk_size - overlap`，以及过大或过小的 Chunk 会对检索造成什么影响。

---

# Day 16 完成标准

```text
[ ] 能解释为什么 PDF 文本需要先切块再生成 Embedding
[ ] 能解释 chunk_size、overlap 和 step 的关系
[ ] 已创建 app/services/chunk_service.py
[ ] split_text() 能正确处理空文本和非法参数
[ ] 字母串测试得到 4 个符合预期的 Chunk
[ ] 相邻 Chunk 会重复保留指定数量的字符
[ ] sample.pdf 已按页切块，并能输出页码、Chunk 编号和文本预览
[ ] 能说明 Chunk 太大、太小以及 overlap 太大的影响
[ ] 没有修改 requirements.txt，也没有提前加入 FAISS 或新接口
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
