# Day 13：整理项目结构并完成第二周回归测试

Day 12 已经把 DeepSeek 请求改成了真正的异步调用，`/chat`、SQLite 消息保存、`/history` 和异常处理也都已经跑通。按照月计划，第二周还剩最后一步：检查每个文件的职责，确认重构没有破坏原有接口，并把仍停留在 Day 3 的 README 更新到真实进度。

今天围绕“第二周收尾”展开：把 `ChatRequest` 和 `ChatResponse` 移到统一的数据模型文件，完整测试现有接口，再更新项目说明。完成后，项目会有更清楚的代码结构和一份与当前功能一致的 README，下一次就可以进入 Embedding。

---

# 一、先复习当前项目的四层职责

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

先查看这四个文件，不要马上修改：

```text
app/main.py
app/models.py
app/database.py
app/services/llm_service.py
```

尝试不看以前的笔记，用自己的话说出它们现在分别负责什么：

```text
main.py
创建 FastAPI 应用、定义路由，并组织一次请求的处理顺序

models.py
定义进入和离开接口的数据应该是什么结构

database.py
连接 SQLite，负责建表、保存和查询消息

llm_service.py
使用 HTTPX 调用 DeepSeek，并处理模型服务的异常响应
```

再复习 Day 12 的两个关键点：

```text
async/await 不会让 DeepSeek 自己生成得更快，
但等待网络时可以让出执行机会，让服务器处理其他请求。

只有 async def 还不够，内部还要使用 AsyncClient 和 await，
网络等待才是真正的异步等待。
```

今天的重构不改变接口行为，只调整代码放在哪里。可以先把“重构”理解成：

> 在功能保持不变的前提下，让代码职责更清楚、更容易继续维护。

---

# 二、把请求和响应模型统一放进 `models.py`

目前 `Message` 已经放在 `app/models.py`，但 `ChatRequest` 和 `ChatResponse` 还定义在 `app/main.py`。它们本质上都是 Pydantic 数据模型，统一放在一个文件中会更容易找到。

打开：

```text
app/models.py
```

在 `Message` 前面加入下面两个模型：

```python
class ChatRequest(BaseModel):
    """客户端发送的聊天请求。"""

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="用户发送的消息",
    )


class ChatResponse(BaseModel):
    """服务器返回的聊天响应。"""

    reply: str
```

修改后，`app/models.py` 中应该有三个模型：

```text
ChatRequest     检查 POST /chat 的请求体
ChatResponse    规定 POST /chat 的响应体
Message         表示数据库和 GET /history 中的一条消息
```

这里不要修改 `Message` 的字段，也不要顺便增加 `conversation_id`。当前月计划只需要一组简单聊天历史。

---

# 三、整理 `main.py` 的导入和模型定义

打开：

```text
app/main.py
```

把文件顶部的导入整理为：

```python
from fastapi import FastAPI, Header, HTTPException, Response

from app.database import get_messages, init_database, save_message
from app.models import ChatRequest, ChatResponse, Message
from app.services.llm_service import LLMService
```

因为 `BaseModel` 和 `Field` 已经只在 `models.py` 中使用，所以从 `main.py` 删除：

```python
from pydantic import BaseModel, Field
```

再从 `main.py` 删除原来的两个类定义：

```python
class ChatRequest(BaseModel):
    ...


class ChatResponse(BaseModel):
    ...
```

路由中的这些代码都不要改：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, response: Response) -> ChatResponse:
    ...


@app.get("/history", response_model=list[Message])
async def history(response: Response) -> list[Message]:
    ...
```

它们仍然使用相同的模型，只是模型的定义位置从 `main.py` 变成了 `models.py`。

今天也先保留：

```python
init_database()
```

以后可以再学习 FastAPI 的 lifespan，把启动和关闭阶段的操作集中管理；今天不要为了重构同时引入新的生命周期概念。

---

# 四、先做不调用模型的结构检查

在项目根目录激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

先检查三个模型能否从新位置导入：

```powershell
python -c "from app.models import ChatRequest, ChatResponse, Message; print(ChatRequest, ChatResponse, Message)"
```

预期会看到三个类的名称，并且没有 `ImportError` 或 `NameError`。

再检查 FastAPI 应用能否正常导入：

```powershell
python -c "from app.main import app; print(app.title)"
```

预期输出：

```text
Mini RAG Backend
```

最后查看当前路由：

```powershell
python -c "from app.main import app; print([(sorted(route.methods), route.path) for route in app.routes if getattr(route, 'methods', None)])"
```

输出中除了 FastAPI 自动提供的文档路由，还应该包含：

```text
GET  /
GET  /health
POST /chat
GET  /history
GET  /request-info
```

这些检查不会调用 DeepSeek，也不会消耗 API 额度。如果这里失败，先检查 `app.models` 的导入名称和是否已经删除了重复类，不要急着启动服务。

---

# 五、启动服务并做完整回归测试

“回归测试”可以先理解成：

> 修改代码结构以后，把以前已经成功的功能重新走一遍，确认没有被意外破坏。

打开终端 A，持续运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

保持终端 A 不要关闭，再打开终端 B。

## 1. 测试健康检查

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get
```

预期状态码为 200，并返回：

```text
status = ok
llm_configured = True
```

如果你还没有配置模型，`llm_configured` 可以是 `False`；它反映的是本地配置是否完整，不表示健康接口坏了。

## 2. 测试已有聊天历史

```powershell
$history = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get

$history | Select-Object -Last 2 | ConvertTo-Json -Depth 3
```

预期状态码为 200。历史可以为空；如果已有消息，每一项都应该包含：

```text
id
role
content
created_at
```

调用 `/history` 只查询本地 SQLite，不会调用 DeepSeek。

## 3. 确认输入校验没有失效

先发送纯空格：

```powershell
$spaceBody = @{
    message = "   "
} | ConvertTo-Json

try {
    Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $spaceBody
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

预期输出：

```text
400
```

再发送缺少 `message` 的请求体：

```powershell
try {
    Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body "{}"
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

预期输出：

```text
422
```

这两次请求都应该在调用 DeepSeek 前被拒绝，不会消耗模型额度。

## 4. 最后测试一次真实聊天

前面的检查都成功，并且 `/health` 显示配置完整后，再发送一次真实请求：

```powershell
$body = @{
    message = "请用两句话说明接口层和服务层为什么要分开"
} | ConvertTo-Json

$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body $utf8Body
```

预期状态码为 200，并得到一段真实模型回答。只测试一次即可。

再次查询最后两条历史：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get |
    Select-Object -Last 2 |
    ConvertTo-Json -Depth 3
```

最后两条应该依次是：

```text
user         刚才发送的问题
assistant    DeepSeek 返回的回答
```

测试完成后，在终端 A 按 `Ctrl + C` 停止服务。

---

# 六、把 README 更新到真实进度

当前 `README.md` 仍写着 `Day 3/30`、`/chat` 只返回模拟回复、SQLite 尚未开始，这些内容已经和代码不一致。README 可以理解成项目的使用说明和对外介绍：别人不应该先读完整源码，才能知道项目能做什么、怎样运行。

打开：

```text
README.md
```

根据今天测试过的事实更新下面几部分。

## 1. 当前进度

完成今天的代码和测试后，将进度更新为：

```markdown
**当前进度：Day 13/30（约 43%）**
```

## 2. 当前已经实现

至少准确写出：

```text
FastAPI 基础接口和 Pydantic 请求、响应校验
使用 httpx.AsyncClient 异步调用 DeepSeek
API Key、Base URL 和模型名称从 .env 加载
SQLite messages 表以及用户、模型消息持久化
GET /history 按顺序返回聊天记录
用户输入、配置、网络、超时、上游状态码和响应格式异常处理
```

## 3. 当前接口

接口说明必须和代码一致：

```text
GET  /               返回服务运行提示
GET  /health         返回服务状态和模型配置状态
POST /chat           调用真实模型、保存消息并返回 reply
GET  /history        返回按 id 升序排列的聊天历史
GET  /request-info   读取可选的 X-Client-Name 请求头
```

## 4. 项目结构

目录树中补上当前已有的文件：

```text
app/database.py      SQLite 建表、保存和查询
app/models.py        ChatRequest、ChatResponse 和 Message
data/chat.db         本地运行数据，已被 Git 忽略
docs/Day1.md～Day13.md
```

不要把 `.env` 的真实内容或本地聊天记录复制到 README。

## 5. 当前限制和下一步

删除已经过时的“尚未调用真实模型”“尚无 SQLite”等描述，保留真正存在的限制：

```text
目前只有一组全局聊天历史，没有多会话管理
SQLite 操作仍是简单的同步调用
尚未实现 PDF 解析、Chunk、Embedding、FAISS 和 RAG
尚未建立自动化测试与 RAG 评估问题集
```

下一步写为：

```text
进入最小 RAG 阶段，先学习 Embedding，再按 PDF 解析、Chunk、FAISS、检索和连接大模型的顺序推进。
```

修改后全文搜索下面这些过时说法，确保没有残留：

```powershell
Select-String `
    -Path README.md `
    -Pattern "Day 3/30|模拟回复|尚无 SQLite|真实 LLM API 尚未接入|Day 4 至 Day 30 尚未完成"
```

正常情况下不应该匹配到任何内容。如果某句话是作为历史说明保留的，也要确保读者不会误以为它仍是当前状态。

---

# 七、检查改动并提交 Git

先查看工作区和具体改动：

```powershell
git status --short
git diff -- app/models.py app/main.py README.md docs/Day13.md
git check-ignore -v .env
git check-ignore -v data\chat.db
```

重点确认：

```text
ChatRequest 和 ChatResponse 只定义了一次
接口路径、请求字段和响应字段没有改变
README 描述的是实际完成的功能，不是未来计划
.env 和 data/chat.db 仍然被 Git 忽略
没有把 API Key、请求头或本地聊天内容写进文档
```

所有检查和接口测试都成功以后，添加今天的文件：

```powershell
git add app/models.py app/main.py README.md docs/Day13.md
git status
```

再次确认暂存区没有 `.env` 和 `data/chat.db`，然后提交：

```powershell
git commit -m "refactor: organize API models and refresh README"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后尝试不看代码，用自己的话完整介绍当前项目：请求如何进入 FastAPI，怎样经过 Pydantic 校验、SQLite 保存和异步 LLM 调用，为什么各部分要放在不同文件中，以及项目下一步为什么要学习 Embedding。

---

# Day 13 完成标准

```text
[ ] 能解释 main.py、models.py、database.py 和 llm_service.py 的职责
[ ] 已把 ChatRequest 和 ChatResponse 移到 app/models.py
[ ] main.py 中不再重复定义数据模型，所有现有路由仍能正常导入
[ ] GET /health 和 GET /history 返回 200
[ ] 纯空格消息返回 400，缺少 message 返回 422
[ ] POST /chat 成功返回真实回答，并在历史中新增 user 和 assistant 两条消息
[ ] README 已从 Day 3 的旧状态更新为当前真实进度
[ ] 能说明重构和回归测试分别解决什么问题
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
