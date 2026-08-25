# Day 4：理解 Pydantic 请求模型和参数校验

Day 3 已经完成了月计划 Day 4 中的大部分 FastAPI 基础：你已经写出了路由、请求模型、响应模型，也测试过 `/docs` 和 `/chat`。所以今天不需要重新创建接口，而是在现有代码上继续学习月计划的下一项内容：**Pydantic 参数校验**。

今天大约学习 1 小时。最终要让 `/chat` 能自动拒绝空字符串和过长消息，并且能够解释：为什么有些错误由 Pydantic 返回 422，有些错误由路由代码返回 400。

---

# 一、先复习现有的 `/chat`

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

code . :可以从当前文件夹打开vscode

查看 `app/main.py` 中已有的代码：

```python
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
```

以及：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    reply = f"模拟大模型回复：你发送了「{message}」"
    return ChatResponse(reply=reply)
```

先不看 Day 3 的答案，尝试解释下面四件事：

```text
ChatRequest 用来检查什么
ChatResponse 用来检查什么
request.message 从哪里来
response_model=ChatResponse 有什么作用
```

[[Day4-前情复习]]

如果能大致讲清楚，就继续今天的新内容；如果讲不清，只复习 Day 3 的相关部分 5 分钟，不需要把整篇重新学一遍。

---

# 二、Pydantic 可以理解成什么

Pydantic 可以先理解成：

> FastAPI 接口前面的一张数据检查表。

假设你设计了一张报名表，要求“姓名必须是文字，而且不能不填”。用户提交以后，系统会先检查表格是否符合要求，格式正确才交给后面的业务代码处理。

在当前项目中：

```python
class ChatRequest(BaseModel):
    message: str
```

表示 `/chat` 接收的 JSON 必须包含 `message`，而且 `message` 必须是字符串。

客户端发送：

```json
{
  "message": "什么是 RAG？"
}
```

FastAPI 会先让 Pydantic 把它转换成一个 `ChatRequest` 对象。只有校验通过以后，下面的路由函数才会开始执行：

```python
async def chat(request: ChatRequest) -> ChatResponse:
```

---

# 三、为什么还要使用 `Field`

现在的 `message: str` 只说明它应该是字符串，没有说明字符串可以多长。

例如下面的内容虽然不合理，但仍然属于字符串：

```json
{
  "message": ""
}
```

今天使用 Pydantic 的 `Field` 增加两个规则：

```text
消息至少包含 1 个字符
消息最多包含 2000 个字符
```

`Field` 可以理解成给字段补充更具体的填写要求。

这里仍然保留原来的 `.strip()` 和 400 判断，因为只包含空格的字符串长度并不是 0。它可以通过长度校验，但去掉空格后没有实际内容，应该由路由中的业务代码继续拒绝。

这样正好可以观察两层校验的区别：

```text
空字符串或超过 2000 个字符
→ Pydantic 校验失败
→ 路由函数不会执行
→ 返回 422

只包含空格
→ 先通过 Pydantic 的长度校验
→ 进入 chat() 后被 strip() 处理
→ 返回 400
```

---

# 四、给 `message` 增加长度限制

打开：

```text
app/main.py
```

先修改导入：

```python
from pydantic import BaseModel, Field
```

然后修改 `ChatRequest`：

```python
class ChatRequest(BaseModel):
    """客户端发送的聊天请求。"""

    message: str = Field(
        min_length=1,
        max_length=2000,
        description="用户发送的聊天消息",
    )
```

这里：

```text
min_length=1
```

表示字符串至少有 1 个字符。

```text
max_length=2000
```

表示字符串最多有 2000 个字符。

```text
description="用户发送的聊天消息"
```

会把字段说明加入接口文档，方便前端开发者或其他接口使用者理解这个参数。

原来的 `/chat` 路由和空格判断不要删除。今天只修改导入和 `ChatRequest`，不要顺便重构其他代码。

---

# 五、启动项目并查看 Swagger

打开终端 A，进入项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

浏览器访问：

```text
http://127.0.0.1:8000/docs
```

找到 `POST /chat`，查看它的请求模型。修改成功后，Swagger 生成的模型说明中应该能够看到 `message` 的长度限制和描述。

如果启动时报错：

```text
NameError: name 'Field' is not defined
```

先检查 `app/main.py` 顶部是否已经写成：

```python
from pydantic import BaseModel, Field
```

---

# 六、测试 200、400 和 422

## 1. 测试正常消息

在 Swagger 中向 `POST /chat` 发送：

```json
{
  "message": "什么是 RAG？"
}
```

预期状态码：

```text
200 OK
```

响应应该类似：

```json
{
  "reply": "模拟大模型回复：你发送了「什么是 RAG？」"
}
```

## 2. 测试空字符串

发送：

```json
{
  "message": ""
}
```

预期状态码：

```text
422 Unprocessable Entity
```

这是因为 `message` 没有达到 `min_length=1`。Pydantic 在进入 `chat()` 之前就阻止了请求。

## 3. 测试只有空格的消息

发送：

```json
{
  "message": "   "
}
```

预期状态码：

```text
400 Bad Request
```

它的原始长度大于 1，所以能够通过 `Field` 的长度校验；进入路由后，`.strip()` 把空格去掉，原来的业务判断返回 400。

## 4. 测试缺少 `message`

发送：

```json
{}
```

预期状态码：

```text
422 Unprocessable Entity
```

因为 `ChatRequest` 要求必须提供 `message` 字段。

## 5. 测试超过最大长度

保持终端 A 中的服务运行，再打开终端 B：

```powershell
$longBody = @{
    message = "a" * 2001
} | ConvertTo-Json

try {
    Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $longBody
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

[[Day4-测试最大长度]]

预期输出：

```text
422
```

这说明 `max_length=2000` 已经生效。

---

# 七、理解完整的校验顺序

今天完成后，需要能看懂下面这条链路：

```text
客户端发送 JSON
→ FastAPI 接收请求
→ Pydantic 按 ChatRequest 校验
→ 校验通过后执行 chat()
→ 路由处理业务规则
→ ChatResponse 检查返回结果
→ FastAPI 返回 JSON
```

在 FastAPI 里，**路由就是“某个 URL + 某种请求方式，对应执行哪个 Python 函数**

可以简单记成：

> Pydantic 主要负责检查数据格式和字段规则，路由函数负责处理具体业务逻辑。

422 通常表示请求数据没有通过模型校验；今天代码中的 400 表示请求虽然符合基本格式，但内容只有空格，不符合聊天业务要求。

---

# 八、提交 Day 4 代码

所有测试都成功以后，在终端 A 按：

```text
Ctrl + C
```

然后检查修改：

```powershell
git status
git diff -- app/main.py
```

`git diff -- app/main.py` 的意思是：查看 `app/main.py` 这个文件当前有哪些还没有提交的修改。

确认只修改了今天需要的内容，再执行：

```powershell
git add app/main.py
git commit -m "feat: validate chat message length"
```

不要在测试失败时提交。如果还有问题，先把报错记录在本文末尾，下一次继续处理。

---

# Day 4 完成标准

今天结束时，检查自己能否做到：

```text
 能解释 ChatRequest 和 ChatResponse 分别检查什么
[ ] 能解释 BaseModel 和 Field 的作用
[ ] 已为 message 增加 1～2000 个字符的长度限制
[ ] 正常消息返回 200
[ ] 空字符串、缺少字段和超长消息返回 422
[ ] 只有空格的消息返回 400
[ ] 能解释 Pydantic 校验为什么发生在 chat() 之前
[ ] 测试成功后完成 Git commit
```

实际完成：全部完成

遇到的卡点：暂无

Git commit：完成
