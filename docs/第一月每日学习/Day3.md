# Day 3：HTTP 和 REST

你在 Day 1 创建的 `/health` 已经满足今天的一部分要求。今天不需要重新建项目，而是在现有项目中增加一个模拟 `/chat` 接口，完整体验：

```text
客户端发送 JSON
→ FastAPI 接收并校验
→ 执行业务逻辑
→ 返回 JSON
```

---

# 一、先理解什么是 HTTP

HTTP 可以理解为：

> 客户端和服务器之间的一套通信规则。

例如，你在浏览器访问：

```text
http://127.0.0.1:8000/health
```

这时：

```text
浏览器                 FastAPI
  │                       │
  │  GET /health          │
  │ ────────────────────> │
  │                       │ 执行 health()
  │  {"status": "ok"}     │
  │ <──────────────────── │
```

这里：

- 浏览器、前端网页、手机 App 都可以是客户端；
    
- FastAPI 项目是服务器；
    
- 客户端发送 HTTP 请求；
    
- 服务器返回 HTTP 响应。
    

---

# 二、一个 HTTP 请求包含什么

一个请求通常包含：

```text
请求方法
请求地址
请求头
请求体
```

例如客户端向 `/chat` 发送消息：

```http
POST /chat HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
X-Client-Name: day3-test

{
  "message": "你好"
}
```

逐部分理解。

## 1. 请求方法

```http
POST
```

表示客户端准备向服务器提交数据。

## 2. 请求地址

```http
/chat
```

表示要访问 FastAPI 中的 `/chat` 接口。

## 3. 请求头

```http
Content-Type: application/json
```

告诉服务器：

> 我发送的请求体是 JSON 格式。

请求头是请求的附加信息，常见请求头有：

```text
Content-Type     请求体的数据格式
Authorization    身份认证信息
User-Agent       客户端信息
Accept           客户端希望接收的数据格式
```

以后调用大模型 API 时，常见写法是：

```http
Authorization: Bearer 你的API密钥
Content-Type: application/json
```

## 4. 请求体

```json
{
  "message": "你好"
}
```

请求体是真正发送给服务器的数据。

---

# 三、GET 和 POST 的区别

## GET：获取数据

例如：

```http
GET /health
```

意思是：

> 获取服务器当前的健康状态。

FastAPI 中写作：

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

GET 一般用于：

```text
获取用户信息
获取聊天记录
获取文章列表
查询服务状态
```

例如：

```text
GET /health
GET /users
GET /history
GET /documents
```

---

## POST：提交数据

例如：

```http
POST /chat
```

意思是：

> 把一条消息提交给服务器处理。

FastAPI 中写作：

```python
@app.post("/chat")
async def chat(...):
    ...
```

POST 一般用于：

```text
发送聊天消息
创建用户
上传文档
提交表单
调用大模型
```

最简单的记忆方式是：

```text
GET  = 我想从服务器拿东西
POST = 我想向服务器提交东西
```

---

# 四、什么是 JSON

JSON 是前后端通信中常用的数据格式。

例如：

```json
{
  "message": "你好",
  "user_id": 1001,
  "stream": false
}
```

它和 Python 字典看起来很像：

```python
{
    "message": "你好",
    "user_id": 1001,
    "stream": False,
}
```

但有几个区别：

```text
Python           JSON
True             true
False            false
None             null
单引号可用        字符串必须使用双引号
```

FastAPI 可以自动完成转换：

```text
客户端 JSON
    ↓
Python 对象

Python 字典或 Pydantic 对象
    ↓
响应 JSON
```

---

# 五、修改 `app/main.py`

打开：

```text
app/main.py
```

替换为下面的完整代码：

```python
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.services.llm_service import LLMService


app = FastAPI(
    title="Mini RAG Backend",
    description="一个用于学习 RAG 和 AI 应用开发的后端项目",
    version="0.1.0",
)

llm_service = LLMService()


class ChatRequest(BaseModel):
    """客户端发送的聊天请求。"""

    message: str


class ChatResponse(BaseModel):
    """服务器返回的聊天响应。"""

    reply: str


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Mini RAG Backend is running"
    }


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "llm_configured": llm_service.is_configured(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    # Day 3 暂时不调用真实大模型
    reply = f"模拟大模型回复：你发送了「{message}」"

    return ChatResponse(reply=reply)


@app.get("/request-info")
async def request_info(
    x_client_name: str | None = Header(default=None),
) -> dict[str, str]:
    return {
        "client_name": x_client_name or "unknown"
    }
```

---

# 六、理解 `ChatRequest`

这部分代码：

```python
class ChatRequest(BaseModel):
    message: str
```

定义了客户端请求体的格式。

它表示客户端必须发送：

```json
{
  "message": "某段文字"
}
```

其中：

```python
message: str
```

表示 `message` 必须是字符串。

FastAPI 收到 JSON 后，会自动把它转换成一个 `ChatRequest` 对象。

所以接口中可以写：

```python
request.message
```

来取得客户端发送的内容。

完整过程是：

```text
客户端发送：

{
  "message": "你好"
}

        ↓ FastAPI 解析

ChatRequest 对象

        ↓ 读取属性

request.message

        ↓ 得到

"你好"
```

---

# 七、理解 `@app.post("/chat")`

[聊天接口解析](附件/聊天接口解析.md)

这段代码：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
```

可以逐部分拆解。

## `@app.post("/chat")`

表示注册一个 POST 接口：

```text
POST /chat
```

## `request: ChatRequest`

表示请求体必须符合 `ChatRequest` 格式：

```json
{
  "message": "你好"
}
```

## `-> ChatResponse`

表示这个函数最终返回 `ChatResponse` 对象。

## `response_model=ChatResponse`

表示 FastAPI 会按照 `ChatResponse` 检查和生成响应：

```json
{
  "reply": "模拟大模型回复：你发送了「你好」"
}
```

---

# 八、理解请求头接口

[请求头和请求体](附件/请求头和请求体.md)

代码：

```python
@app.get("/request-info")
async def request_info(
    x_client_name: str | None = Header(default=None),
) -> dict[str, str]:
```

其中：

```python
Header(default=None)
```

告诉 FastAPI：

> 这个参数不是从请求体读取，而是从请求头读取。

Python 参数名是：

```python
x_client_name
```

对应 HTTP 请求头：

```http
X-Client-Name: day3-test
```

FastAPI 会自动把下划线转换成连字符：

```text
x_client_name
      ↓
X-Client-Name
```

---

# 九、启动项目

在项目根目录打开终端。

确认当前目录：

```powershell
pwd
```

应该位于：

```text
mini-rag-backend
```

激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

启动 FastAPI：

```powershell
python -m uvicorn app.main:app --reload
```

上面这行命令解释：用当前 Python 环境，通过 Uvicorn 启动 `app/main.py` 里的 FastAPI `app`，并在开发时开启自动重载。

看到下面的信息表示启动成功：

```text
Uvicorn running on http://127.0.0.1:8000
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

现在应该能看到：

```text
GET  /
GET  /health
POST /chat
GET  /request-info
```

---

# 十、测试 GET `/health`

在 `/docs` 中找到：

```text
GET /health
```

点击：

```text
Try it out
```

再点击：

```text
Execute
```

响应体应该类似：

```json
{
  "status": "ok",
  "llm_configured": false
}
```

同时会看到：

```text
Response code: 200
```

这里的 `200` 就是 HTTP 状态码，表示请求成功。

---

# 十一、测试 POST `/chat`

找到：

```text
POST /chat
```

点击：

```text
Try it out
```

填写请求体：

```json
{
  "message": "你好，FastAPI"
}
```

点击：

```text
Execute
```

应该得到：

```json
{
  "reply": "模拟大模型回复：你发送了「你好，FastAPI」"
}
```

状态码：

```text
200 OK
```

这次完整过程是：

```text
1. Swagger UI 发送 POST /chat

2. 请求体是 JSON：
   {"message": "你好，FastAPI"}

3. FastAPI 把 JSON 转成 ChatRequest

4. 程序读取 request.message

5. chat() 执行业务逻辑

6. 创建 ChatResponse

7. FastAPI 把它转换成 JSON

8. 客户端收到响应
```

---

# 十二、观察不同状态码

状态码用于告诉客户端：

> 这次请求执行得怎么样。

常见状态码可以先记住这些。

## 2xx：请求成功

```text
200 OK
请求正常成功

201 Created
成功创建了一条新数据

204 No Content
成功，但不需要返回响应体
```

## 4xx：客户端请求有问题

```text
400 Bad Request
请求内容不合理

401 Unauthorized
没有登录或身份认证失败

403 Forbidden
已经识别身份，但没有权限

404 Not Found
接口或资源不存在

422 Unprocessable Entity
请求体格式不符合要求
```

## 5xx：服务器出现问题

```text
500 Internal Server Error
服务器代码发生异常

502 Bad Gateway
网关从上游服务得到错误响应

503 Service Unavailable
服务暂时不可用
```

---

## 测试 400

向 `/chat` 发送：

```json
{
  "message": "   "
}
```

代码执行：

```python
message = request.message.strip()
```

空格被删除后变成空字符串，于是触发：

```python
raise HTTPException(
    status_code=400,
    detail="message 不能只包含空格",
)
```

响应：

```json
{
  "detail": "message 不能只包含空格"
}
```

状态码：

```text
400 Bad Request
```

---

## 测试 422

向 `/chat` 发送：

```json
{}
```

但是 `ChatRequest` 要求必须有：

```python
message: str
```

FastAPI 会在进入 `chat()` 之前阻止这个请求，返回：

```text
422 Unprocessable Entity
```

这说明：

> FastAPI 已经自动完成了请求体校验。

注意，此时 `chat()` 函数根本没有被执行。

---

## 测试 404

浏览器打开一个不存在的地址：

```text
http://127.0.0.1:8000/abc
```

会得到：

```json
{
  "detail": "Not Found"
}
```

状态码是：

```text
404 Not Found
```

---

# 十三、测试请求头

在 `/docs` 中找到：

```text
GET /request-info
```

点击：

```text
Try it out
```

填写：

```text
x-client-name = day3-test
```

然后点击：

```text
Execute
```

响应：

```json
{
  "client_name": "day3-test"
}
```

对应的 HTTP 请求大致是：

```http
GET /request-info HTTP/1.1
X-Client-Name: day3-test
```

---

# 十四、使用 PowerShell 发送请求

除了 `/docs`，还可以直接在终端发送 HTTP 请求。

注意：启动服务器的终端不要关闭，另外打开一个新终端。

## 测试 GET

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/health" `
  -Method Get
```

应该输出：

```text
status llm_configured
------ --------------
ok                 False
```

---

## 测试 POST

先创建 JSON 请求体：

```powershell
$body = @{
    message = "你好，FastAPI"
} | ConvertTo-Json
```

发送请求：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

应该输出：

```text
reply
-----
模拟大模型回复：你发送了「你好，FastAPI」
```

这里：

```powershell
-ContentType "application/json"
```

会生成请求头：

```http
Content-Type: application/json
```

---

## 测试请求头

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/request-info" `
  -Method Get `
  -Headers @{
      "X-Client-Name" = "powershell-client"
  }
```

应该输出：

```text
client_name
-----------
powershell-client
```

---

# 十五、什么是 REST

REST 是一种设计 Web API 的思路。

可以先简单理解成：

> 使用 URL 表示资源，使用 HTTP 方法表示对资源做什么。

例如用户资源：

```text
GET    /users       获取用户列表
GET    /users/1     获取 1 号用户
POST   /users       创建用户
PUT    /users/1     整体更新 1 号用户
PATCH  /users/1     部分更新 1 号用户
DELETE /users/1     删除 1 号用户
```

其中：

```text
/users
```

表示用户资源。

HTTP 方法表示操作：

```text
GET       查询
POST      创建或提交
PUT       整体更新
PATCH     部分更新
DELETE    删除
```

你的 `/chat` 是一个常见的 AI 应用接口：

```text
POST /chat
```

它表示：

> 向聊天服务提交一条消息。

更资源化的设计也可以是：

```text
POST /messages
```

表示创建一条聊天消息。不过学习阶段使用 `/chat` 更直观。

---

# 十六、未来调用大模型时的完整流程

现在的 `/chat` 只生成模拟回复：

```python
reply = f"模拟大模型回复：你发送了「{message}」"
```

以后接入 DeepSeek 或 Qwen 后，流程会变成：

```text
客户端
  │
  │ POST /chat
  │ {"message": "什么是RAG？"}
  ▼
FastAPI
  │
  │ 解析 JSON
  │ 校验请求体
  ▼
chat() 接口函数
  │
  │ 调用 LLMService
  ▼
LLMService
  │
  │ 使用 httpx 调用大模型 API
  │ 请求头携带 API Key
  │ 请求体携带 messages
  ▼
大模型服务器
  │
  │ 返回模型生成结果
  ▼
LLMService
  │
  ▼
FastAPI
  │
  │ 转换成 JSON
  ▼
客户端收到回复
```

你需要能够解释成一句话：

> 客户端通过 POST 请求向 `/chat` 发送 JSON，FastAPI 将 JSON 解析为 Python 对象，调用业务服务处理消息，最后把处理结果转换成 JSON 响应返回给客户端。

---

# 十七、Day 3 代码提交

测试成功后停止服务器：

```text
Ctrl + C
```

检查代码：

```powershell
git status
```

添加修改：

```powershell
git add app/main.py
```

提交：

```powershell
git commit -m "feat: add HTTP practice endpoints"
```

这里：

```text
feat
```

表示增加了新功能。

---

# Day 3 完成标准

今天结束时，你应该能够解释：

```text
GET 和 POST 有什么区别
请求头用来存放什么
请求体用来存放什么
JSON 是什么
200、400、404、422、500 分别是什么意思
FastAPI 如何把 JSON 转成 Python 对象
FastAPI 如何把 Python 对象转成 JSON
```

并且完成以下测试：

```text
[✓] GET /health 返回 200
[✓] POST /chat 接收 JSON
[✓] POST /chat 返回 JSON
[✓] 空消息返回 400
[✓] 缺少 message 返回 422
[✓] 不存在的接口返回 404
[✓] /request-info 能读取请求头
```

Day 3 最核心的代码是：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    return ChatResponse(
        reply=f"模拟大模型回复：你发送了「{message}」"
    )
```