# Day 27：结合 Mini RAG 项目准备 Python 与后端面试回答

Day 26 已经更新了 README 和 RAG 架构图，并完成 Git 提交。项目现在不仅能运行，也已经有了可以对外展示的说明。按照月计划，今天不再增加新功能，而是把做项目时实际用过的 Python 和后端知识整理成面试时能讲出口的答案。

今天围绕 9 个常见问题展开：`list` 与 `tuple`、`dict`、深浅拷贝、生成器、装饰器、`async/await`、GET 与 POST、Pydantic、FastAPI。目标不是背定义，而是每道题都能先解释概念，再用当前 Mini RAG 项目举例，最后说清一个容易误解的边界。

---

# 一、先从项目中找出今天要讲的代码证据

打开项目：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
code .
```

检查当前状态：

```powershell
git status --short
git log -2 --oneline
```

当前工作区应该干净，最近一次提交应当是 Day 26 的 README 和架构图。

今天不需要启动 FastAPI，也不调用大模型。先运行下面的搜索，观察这些面试知识点已经怎样出现在项目里：

```powershell
Select-String `
    -Path app\main.py,app\models.py,app\services\*.py `
    -Pattern '@app\.|async def|await |list\[|tuple\[|dict\[|chunks.extend'
```

可以先建立下面的对应关系：

```text
list
→ pages、chunks、sources、search_results

tuple
→ RAGService.answer() 返回 answer 和 search_results

dict
→ LLM 请求的 headers、payload，以及 FastAPI 返回的简单 JSON 对象

generator expression
→ upload_pdf() 中创建 DocumentChunk 的表达式

decorator
→ @app.get(...)、@app.post(...)

async / await
→ LLMService.chat()、RAGService.answer()、FastAPI 路由

GET / POST
→ /history、/health 与 /chat、/upload、/rag/chat

Pydantic
→ ChatRequest、Message、RAGSource、RAGChatResponse

FastAPI
→ 路由、请求解析、响应模型、Swagger 文档
```

面试时如果只会背书本定义，回答容易显得抽象。今天每道题都至少使用一个项目中的真实例子。

---

# 二、先建立一分钟回答的固定结构

面试官问一个概念时，可以按下面四步回答：

```text
第一句：它是什么
第二句：最重要的特点或区别
第三句：在当前项目中的使用例子
第四句：补充一个边界、限制或取舍
```

例如回答“什么是 async/await”时，不要一开始就讲事件循环源码。先说：

```text
async def 定义协程函数，调用后得到协程对象；
await 用来等待异步操作的结果，等待 I/O 时可以让出执行机会；
项目中调用 DeepSeek 使用 await client.post()；
它不会让模型生成得更快，也不会自动让 Embedding 这种同步计算变快。
```

为了保存自己的表达，今天创建一份面试回答笔记：

```text
docs/附件/Day27-Python与后端面试回答.md
```

如果文件不存在，可以在 VS Code 中创建，或者执行：

```powershell
New-Item `
    -Path "docs\附件\Day27-Python与后端面试回答.md" `
    -ItemType File
```

在文件中先写出 9 个标题：

```markdown
# Day 27：Python 与后端面试回答

## 1. list 和 tuple 有什么区别？
## 2. dict 的基本原理和使用场景是什么？
## 3. 深拷贝和浅拷贝有什么区别？
## 4. generator 是什么？
## 5. decorator 是什么？
## 6. async 和 await 是什么？
## 7. GET 和 POST 有什么区别？
## 8. Pydantic 有什么作用？
## 9. FastAPI 有什么优势？
```

下面每学完一道题，就用自己的话在对应标题下写 4～6 句。参考答案只帮助理解，不要逐字复制成长篇背诵稿。

[[Day27-Python与后端面试回答]]

---

# 三、问题一：`list` 和 `tuple` 有什么区别

## 它们是什么

`list` 和 `tuple` 都是有顺序的 Python 容器，都可以按下标读取，也都能保存不同类型的对象。

最核心的区别是：

```text
list 是可变序列
→ 可以 append、extend、删除或替换元素

tuple 是不可变序列
→ 创建后不能增加、删除或替换其中的元素引用
```

项目中：

```python
chunks: list[DocumentChunk] = []
```

上传 PDF 时，Chunk 数量会逐步增加，所以使用 `list`，后面可以：

```python
chunks.extend(...)
```

而 `RAGService.answer()` 返回两个位置固定的结果：

```python
) -> tuple[str, list[SearchResult]]:
    ...
    return answer, search_results
```

这里的 tuple 表达“第一个是回答，第二个是检索结果”，结构固定。

## 容易误解的地方

tuple 不可变，指的是 tuple 自己保存的元素引用不能替换。如果 tuple 内部装着一个 list，那个 list 自身仍然可能被修改。

因此不要简单回答：

```text
tuple 里面的所有数据都绝对不能变
```

## 一分钟回答示例

> list 和 tuple 都是有序容器，主要区别是 list 可变，tuple 创建后不能增删或替换元素。需要动态收集数据时我会用 list，例如项目上传 PDF 时不断向 chunks 中加入文本块；返回结构固定的多个结果时可以用 tuple，例如 RAGService.answer() 返回 answer 和 search_results。tuple 的不可变是指容器中的引用不能替换，如果内部元素本身是可变对象，它仍可能发生变化。

把这段关掉后，用自己的话重新说一次，再写进面试回答笔记。

---

# 四、问题二：`dict` 的基本原理和使用场景是什么

## 它是什么

`dict` 保存键和值之间的映射：

```python
{
    "model": "deepseek-v4-flash",
    "stream": False,
}
```

Python 字典的核心实现思路是哈希表。查找一个键时，会先根据键计算哈希值，再定位到对应位置，因此平均情况下查找、插入和删除可以看作 `O(1)`。

不同键可能产生需要处理的哈希冲突，所以不能把 `O(1)` 理解为所有情况下永远只执行一步。字典通常也会使用比实际数据更多的内存，换取快速查找。

## 项目中的例子

打开：

```text
app/services/llm_service.py
```

这里使用字典组织请求头和 JSON 请求体：

```python
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json",
}

payload = {
    "model": self.model,
    "messages": [...],
    "stream": False,
}
```

键适合表达字段名称，值保存对应配置或数据。HTTPX 会把 `payload` 转换成 JSON 请求体。

## 容易误解的地方

字典的键必须是可哈希的对象，例如字符串、整数和满足条件的 tuple。普通 list 会变化，不能直接作为字典键。

现代 Python 字典会保留插入顺序，但“保留插入顺序”不表示它会自动按键的大小排序。

## 一分钟回答示例

> dict 是键值映射，底层核心思路是哈希表，平均情况下按键查找、插入和删除是 O(1)。它适合通过字段名快速找到数据，例如项目中用 dict 组织 LLM 请求的 headers 和 payload，再由 HTTPX 转成 HTTP 请求。字典键必须可哈希，另外它会保留插入顺序，但不会自动按照键排序。哈希表也会用一定的额外内存来换取查询速度。

---

# 五、问题三：深拷贝和浅拷贝有什么区别

## 先理解“复制了哪一层”

赋值不是复制：

```python
b = a
```

只是让 `a` 和 `b` 指向同一个对象。

浅拷贝会创建一个新的最外层容器，但内部嵌套对象仍然与原对象共享。深拷贝会递归复制嵌套对象，使副本尽量与原对象分离。

运行一个小实验：

```powershell
@'
import copy


original = {
    "sources": [
        {"page": 1, "text": "RAG 来源"}
    ]
}

shallow = copy.copy(original)
shallow["sources"][0]["page"] = 9

print("浅拷贝后 original：", original)

deep = copy.deepcopy(original)
deep["sources"][0]["page"] = 2

print("深拷贝后 original：", original)
print("deep：", deep)
'@ | python -
```

浅拷贝修改了嵌套的 `page` 后，`original` 也会变化，因为两者仍共享内部的 `sources` 列表和字典。深拷贝后的嵌套修改不会继续影响原对象。

## 项目场景

评估脚本读取的 JSON 是嵌套的字典和列表。如果希望保留一份完全不受后续评分修改影响的原始结构，浅拷贝可能不够；但深拷贝会增加时间和内存开销，也不应该在任何场景都无脑使用。

## 一分钟回答示例

> 普通赋值只会增加一个指向同一对象的引用。浅拷贝会复制最外层容器，但内部嵌套对象仍然共享；深拷贝会递归复制嵌套对象。比如评估数据是 dict 中包含 sources 列表和来源字典，浅拷贝后修改嵌套来源仍可能影响原数据，deepcopy 才能把这层结构分离。不过深拷贝成本更高，还可能遇到不能合理复制的资源对象，所以要根据是否需要隔离嵌套状态来选择。

---

# 六、问题四：generator 是什么

## 它是什么

生成器是一种惰性产生数据的迭代器。它不会先把全部结果一次性放进内存，而是在迭代到某一步时才计算并给出当前结果。

常见写法有两种：

```python
def numbers():
    yield 1
    yield 2

squares = (number * number for number in range(10))
```

第一种是包含 `yield` 的生成器函数，第二种是生成器表达式。

## 项目中的例子

`app/main.py` 创建 `DocumentChunk` 时使用：

```python
chunks.extend(
    DocumentChunk(
        text=chunk_text,
        page=page_number,
    )
    for chunk_text in page_chunks
)
```

括号内部是生成器表达式。它逐个创建 `DocumentChunk`，再由 `extend()` 消费，不需要先额外创建一个临时 list。

## 容易误解的地方

生成器通常只能按顺序消费一次。它适合流式处理和大数据迭代，但如果需要反复随机访问、计算长度或多次遍历，list 可能更方便。

生成器也不是“让代码自动异步”。惰性计算与 `async/await` 是两个不同概念。

## 一分钟回答示例

> generator 是惰性产生元素的迭代器，可以用 yield 或生成器表达式创建。与一次性构造完整 list 相比，它只在迭代时生成当前元素，适合数据量大或流式处理的场景。项目上传 PDF 时，用生成器表达式逐个创建 DocumentChunk，再交给 chunks.extend() 消费，避免额外的临时列表。它通常只能顺序消费一次，如果需要随机访问或重复遍历，list 会更合适。

---

# 七、问题五：decorator 是什么

## 它是什么

装饰器接收一个函数或类，并返回一个经过处理的对象。它允许在不改动函数主体的情况下，为函数增加行为或完成注册。

下面两种写法可以先理解为等价的语法关系：

```python
@decorator
def function():
    pass
```

```python
def function():
    pass

function = decorator(function)
```

## 项目中的例子

FastAPI 路由使用：

```python
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile) -> UploadResponse:
    ...
```

`app.post(...)` 会返回一个装饰器。模块导入时，装饰器把 `upload_pdf` 注册成 `POST /upload` 的处理函数，FastAPI 才知道收到这个路径的请求时应该执行谁。

## 容易误解的地方

装饰器不一定只是“在函数前后打印日志”。FastAPI 的主要用途是注册路由和附加响应模型等元数据。

自己编写会包裹原函数的装饰器时，通常还要注意使用 `functools.wraps` 保留原函数名称和文档信息；今天知道这个追问即可，不需要现场实现复杂装饰器。

## 一分钟回答示例

> decorator 本质上是接收函数或类并返回处理后对象的可调用对象，@decorator 是一种语法糖。它可以在不改函数主体的情况下增加行为或完成注册。项目中的 @app.post('/upload') 会在模块导入时把 upload_pdf 注册为 POST /upload 的路由处理函数，并记录 response_model 等信息。自己写包装型装饰器时，还要注意用 functools.wraps 保留原函数元数据。

---

# 八、问题六：`async` 和 `await` 是什么

## 它们是什么

```python
async def function():
    ...
```

定义协程函数。调用协程函数时，先得到协程对象；通常需要在异步环境中使用 `await`，才能等待并取得最终结果。

`await` 遇到网络、文件等可等待的 I/O 时，可以暂时让出执行机会，使事件循环处理其他任务。它改善的是等待方式，不会让远程模型本身生成得更快。

## 项目中的例子

外部 LLM 请求：

```python
async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.post(...)
```

RAG 服务继续等待 LLM：

```python
answer = await self.llm_service.chat(prompt)
```

上传接口读取文件：

```python
pdf_bytes = await file.read()
```

## 容易误解的地方

当前 PDF 解析、Embedding 和 FAISS 搜索仍是同步代码。即使它们写在 `async def` 路由中，也不会自动变成异步或自动利用多个 CPU 核心；耗时的同步计算仍可能阻塞事件循环。

## 一分钟回答示例

> async def 定义协程函数，调用后先得到协程对象，await 用来等待它的结果。对于网络 I/O，await 等待期间可以把执行机会交还事件循环，所以服务器能更有效地处理其他请求。项目中用 await client.post() 等待 DeepSeek，用 await file.read() 读取上传文件。不过异步不会让模型生成更快，PDF 解析、Embedding 和 FAISS 当前仍是同步计算，也不会因为外层路由是 async def 就自动加速。

---

# 九、问题七：GET 和 POST 有什么区别

## 先从语义区分

```text
GET
→ 获取资源或查询状态
→ 按设计应当是安全的，不应该因为读取而改变服务器业务状态
→ 重复相同请求通常应得到相同语义结果

POST
→ 向服务器提交数据进行处理或创建状态
→ 请求可能改变服务器状态
→ 重复请求不一定产生相同结果
```

项目中的 GET：

```text
GET /health
GET /history
```

它们分别读取服务状态和聊天历史。

项目中的 POST：

```text
POST /chat
POST /upload
POST /rag/chat
```

它们需要提交消息、文件或问题，并可能调用模型、保存消息或替换内存索引。

## 容易误解的地方

不要回答：

```text
GET 不安全，POST 安全
```

是否加密由 HTTPS 决定，不是由 GET 或 POST 决定。POST 请求体也不能代替身份认证和权限控制。

也不要只说“GET 没有请求体”。HTTP 语义和工具兼容性上，不应依赖 GET 请求体，但 GET 与 POST 最重要的区别仍然是用途和语义。

## 一分钟回答示例

> GET 主要用于读取资源或查询状态，按语义应该是安全和幂等的；POST 用于提交数据进行处理或创建状态，重复请求可能产生不同结果。项目里 /health 和 /history 使用 GET，因为它们只读取；/chat、/upload 和 /rag/chat 使用 POST，因为需要提交 JSON 或文件，还可能调用模型、保存消息或替换索引。GET 和 POST 本身不决定安全性，敏感信息仍需要 HTTPS、认证和权限控制。

---

# 十、问题八：Pydantic 有什么作用

## 它是什么

Pydantic 根据 Python 类型注解定义数据模型，并负责解析和校验输入数据。FastAPI 会结合它完成：

```text
把 JSON 转换成 Python 对象
检查字段是否存在、类型是否正确
检查长度和数值范围
生成 OpenAPI / Swagger 模型说明
校验接口返回结果
```

## 项目中的例子

```python
class RAGSource(BaseModel):
    text: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float
```

它规定来源文本不能为空、页码必须大于 0、相似度必须是浮点数。

`ChatRequest` 还限制消息长度。请求不满足模型时，FastAPI 会在进入路由业务代码前返回 422。

## 容易误解的地方

Pydantic 主要负责数据结构和字段规则，不代替所有业务校验。例如只包含空格的字符串长度大于 0，项目仍然在路由中使用 `.strip()` 后返回 400。

Pydantic 也不代替数据库约束。SQLite 的 `NOT NULL`、`CHECK` 和主键仍负责持久化层的数据完整性。

## 一分钟回答示例

> Pydantic 用 Python 类型注解定义数据模型，负责把输入解析为 Python 对象并校验字段、类型、长度和范围。FastAPI 还会根据模型生成 OpenAPI 文档，并用 response_model 检查响应。项目中的 RAGSource 要求 text 非空、page 大于 0、score 是浮点数。Pydantic 主要解决数据结构校验，不代替业务规则和数据库约束，例如纯空格消息仍要在路由中 strip 后判断。

---

# 十一、问题九：FastAPI 有什么优势

## 先从当前项目回答

FastAPI 把 Python 类型注解、Pydantic 和 ASGI 异步能力结合起来，常见优势包括：

```text
路由写法清楚
自动解析和校验请求
自动生成 OpenAPI 和 Swagger 文档
原生支持 async def
响应模型和类型提示清晰
开发 API 的代码量较少
```

在当前项目中，一个 RAG 路由可以专注于：

```text
接收 RAGChatRequest
调用 RAGService
把异常转换成 HTTP 状态码
返回 RAGChatResponse
```

PDF、Embedding、FAISS 和 LLM 的具体逻辑分别放在服务模块中，FastAPI 主要负责 HTTP 边界。

## 容易误解的地方

框架不会自动提供良好的业务架构。即使使用 FastAPI，如果把 SQL、PDF 解析、向量检索和 LLM 请求全部堆进路由，代码仍然会难以维护。

FastAPI 支持异步，也不意味着所有同步库都会自动异步；项目中的 Embedding 和 FAISS 就仍然需要单独考虑阻塞问题。

## 一分钟回答示例

> FastAPI 的优势是把类型注解、Pydantic 校验、OpenAPI 文档和 ASGI 异步支持结合起来，能用较少代码写出接口边界清楚的 API。项目里请求 JSON 会自动转换成 RAGChatRequest，响应按 RAGChatResponse 校验，Swagger 也会自动展示模型结构，同时路由可以 await 异步 LLM 请求。不过 FastAPI 不会替代业务分层，也不会让 Embedding、SQLite 等同步操作自动变成异步，所以仍要把接口层和服务层分开设计。

---

# 十二、进行一轮不看答案的模拟面试

完成 9 道笔记以后，把本文件和回答笔记都暂时关掉。使用 PowerShell 随机打乱问题：

```powershell
$questions = @(
    "list 和 tuple 有什么区别？"
    "dict 的基本原理和使用场景是什么？"
    "深拷贝和浅拷贝有什么区别？"
    "generator 是什么？"
    "decorator 是什么？"
    "async 和 await 是什么？"
    "GET 和 POST 有什么区别？"
    "Pydantic 有什么作用？"
    "FastAPI 有什么优势？"
)

$questions | Sort-Object { Get-Random }
```

按照随机顺序逐题口述。每题控制在大约一分钟，不要求一字不差，但必须包含：

```text
概念或区别
一个当前项目例子
一个边界或常见误解
```

如果某题只能背出一句定义，就回到对应源码，再补一个真实例子。重点检查下面几个容易卡住的地方：

```text
tuple 不可变不等于内部所有对象都不可变
dict 平均 O(1) 不等于任何情况都是固定一步
浅拷贝会共享嵌套对象
生成器的惰性计算不等于异步
await 不会让模型本身生成更快
POST 不会自动比 GET 更安全
Pydantic 不代替业务校验和数据库约束
FastAPI 不会自动解决代码分层和同步阻塞
```

模拟结束后，在回答笔记末尾记录：

```text
最流畅的三题：
最容易卡住的三题：
下一次需要复习：
```

---

# 十三、检查回答笔记并提交 Git

检查回答文件是否存在：

```powershell
Get-Item "docs\附件\Day27-Python与后端面试回答.md"
```

检查 9 个标题：

```powershell
Select-String `
    -Path "docs\附件\Day27-Python与后端面试回答.md" `
    -Pattern '^## [1-9]\.'
```

预期找到 9 行。再人工确认每道回答都有一个 Mini RAG 项目例子，而不是只复制定义。

查看 Git 状态：

```powershell
git status --short
```

今天正常应新增：

```text
docs/Day27.md
docs/附件/Day27-Python与后端面试回答.md
```

今天不需要修改：

```text
app 中的业务代码
README.md
requirements.txt
Dockerfile
评估 JSON
.env
```

添加今天的学习计划和回答笔记：

```powershell
git add docs/Day27.md "docs/附件/Day27-Python与后端面试回答.md"
git diff --cached --stat
git status
```

确认暂存内容正确后提交：

```powershell
git commit -m "docs: prepare Python and backend interview answers"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

---

# Day 27 完成标准

- [ ] 能用自己的话解释 list 和 tuple 的区别，并各举一个项目例子
- [ ] 能说明 dict 的哈希表思路、平均查找复杂度和可哈希键
- [ ] 能通过嵌套数据解释赋值、浅拷贝和深拷贝的区别
- [ ] 能解释 generator 的惰性计算，并指出项目中的生成器表达式
- [ ] 能解释 decorator 的语法关系和 FastAPI 路由注册作用
- [ ] 能解释 async def、协程对象和 await 的关系
- [ ] 能说明异步改善 I/O 等待，但不会让 LLM、Embedding 或 FAISS 自动加速
- [ ] 能从语义、状态变化和项目接口解释 GET 与 POST
- [ ] 能说明 GET 或 POST 本身不决定请求是否安全
- [ ] 能解释 Pydantic 的解析、校验、文档和响应模型作用
- [ ] 能区分 Pydantic 字段校验、路由业务校验和数据库约束
- [ ] 能结合当前项目说出 FastAPI 的主要优势和边界
- [ ] 已完成 `docs/附件/Day27-Python与后端面试回答.md`
- [ ] 9 道回答都包含概念、项目例子和一个边界或误区
- [ ] 已完成一轮随机顺序的口述模拟，并记录最容易卡住的三题
- [ ] 已确认今天没有修改业务代码、依赖、README 或评估数据
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
