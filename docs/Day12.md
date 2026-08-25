# Day 12：用 `async/await` 异步调用大模型

Day 11 已经为大模型调用补上配置、超时、网络、上游状态码和响应格式异常处理。现在 `/chat` 的功能比较完整，但 `LLMService.chat()` 仍然使用同步的 `httpx.post()`：等待 DeepSeek 返回的几秒钟里，当前执行流程会一直占着这段时间。

今天只学习异步等待：把 `LLMService.chat()` 改成 `async def`，使用 `httpx.AsyncClient` 发送请求，并在 FastAPI 路由中写 `await llm_service.chat(message)`。完成后，模型本身不会生成得更快，但服务器在等待外部网络响应期间可以把执行机会交给其他请求。

---

# 一、先复习当前哪里是同步等待

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

查看 `app/services/llm_service.py`：

```python
def chat(self, message: str) -> str:
    ...
    response = httpx.post(...)
    ...
    return content
```

再查看 `app/main.py`：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(...):
    ...
    reply = llm_service.chat(message)
```

这里出现了一个不协调的地方：FastAPI 路由已经是 `async def`，但它内部调用的模型请求仍然是同步函数。

当前流程可以简单理解为：

```text
FastAPI 开始处理 /chat
→ httpx.post() 发出模型请求
→ 一直等待 DeepSeek 返回
→ 拿到结果后继续执行
```

模型请求属于典型的 I/O 等待：程序大部分时间不是在进行复杂计算，而是在等网络上的另一台服务器回复。

---

# 二、理解 `async` 和 `await`

可以把同步等待想成在餐厅点餐后一直站在取餐口：菜还没做好，但你也不去做别的事。

异步等待更像：

```text
点完餐
→ 拿到取餐号
→ 等待期间先处理其他事情
→ 叫号后回来取餐
```

在 Python 中：

```python
async def chat(...):
```

表示这是一个异步函数。

```python
reply = await llm_service.chat(message)
```

表示当前函数需要等待模型回答，但等待网络的期间可以暂时把执行机会交出去。

先记住三条规则：

```text
1. 调用 async def 函数会先得到 coroutine（协程）对象
2. 必须使用 await，才能真正等待并取得返回值
3. await 通常只能写在另一个 async def 函数里面
```

[[为什么要有协程对象这个中间态]]

[[举一个简单的例子说明异步机制的实际作用]]

异步不会让 DeepSeek 原本 3 秒的生成时间变成 1 秒。它改善的是服务器等待期间的利用方式，特别是在多个用户同时发请求时更有价值。

今天不深入事件循环源码、线程池或高并发压测，只需要理解“等待期间让出执行机会”。

---

# 三、把 `LLMService.chat()` 改成异步函数

打开：

```text
app/services/llm_service.py
```

把函数定义从：

```python
def chat(self, message: str) -> str:
```

修改为：

```python
async def chat(self, message: str) -> str:
```

只增加一个 `async`，就表示函数调用方式已经改变。

注意返回类型仍然写：

```python
-> str
```

它表示：正确 `await` 这个函数以后，最终得到的是字符串。

如果只是直接调用：

```python
result = llm_service.chat("你好")
```

`result` 不是模型回答，而是一个 coroutine 对象。必须写：

```python
result = await llm_service.chat("你好")
```

才能真正执行并取得回答。

---

# 四、使用 `httpx.AsyncClient` 发送请求

当前同步请求部分是：

```python
try:
    response = httpx.post(
        url,
        headers=headers,
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()
except ...:
    ...
```

把它修改为：

```python
try:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
except httpx.TimeoutException as exc:
    raise RuntimeError("大模型请求超时") from exc
except httpx.HTTPStatusError as exc:
    status_code = exc.response.status_code
    raise RuntimeError(
        f"大模型服务返回错误状态码：{status_code}"
    ) from exc
except httpx.RequestError as exc:
    raise RuntimeError("无法连接大模型服务") from exc
```

今天真正新增的是：

```python
async with httpx.AsyncClient(...) as client:
```

[[httpx.AsyncClient(...)的讲解]]

创建一个异步 HTTP 客户端。离开 `async with` 代码块时，客户端会自动关闭网络连接资源。

```python
response = await client.post(...)
```

发出 POST 请求，并异步等待响应。

超时、HTTP 状态码和连接异常仍然使用 Day 11 的处理方式。`AsyncClient` 和同步 `httpx.post()` 会抛出同一组 `httpx` 异常类型，因此不需要重新设计错误消息。

后面的响应解析也保持不变：

```python
try:
    data = response.json()
    content = data["choices"][0]["message"]["content"]
except (ValueError, KeyError, IndexError, TypeError) as exc:
    raise RuntimeError("大模型返回格式异常") from exc

if not isinstance(content, str) or not content.strip():
    raise RuntimeError("大模型返回了空内容")

return content
```

`response.json()` 是在已经收到响应以后解析内存中的数据，今天不需要在它前面写 `await`。

---

# 五、先检查函数是否已经变成异步

在项目根目录激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

执行：

```powershell
python -c "import inspect; from app.services.llm_service import LLMService; print(inspect.iscoroutinefunction(LLMService.chat))"
```

预期输出：

```text
True
```

这说明 `LLMService.chat` 已经是协程函数。

再观察直接调用会得到什么：

```powershell
@'
from app.services.llm_service import LLMService

coroutine = LLMService().chat("测试问题")
print(type(coroutine))
coroutine.close()
'@ | python -
```

预期输出：

```text
<class 'coroutine'>
```

最后的 `coroutine.close()` 只是关闭这个用于观察类型、但没有真正执行的协程，避免出现“协程从未等待”的警告。真实业务代码不能用 `close()` 代替 `await`。

---

# 六、用异步模拟测试确认异常处理仍然有效

Day 11 的超时测试针对同步 `httpx.post()`。现在改用 `AsyncClient.post()` 后，模拟函数也需要变成异步。

执行：

```powershell
@'
import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.services.llm_service import LLMService


async def main() -> None:
    service = LLMService()
    service.api_key = "test-key"
    service.base_url = "https://example.com"
    service.model = "test-model"

    with patch(
        "app.services.llm_service.httpx.AsyncClient.post",
        new=AsyncMock(
            side_effect=httpx.TimeoutException("模拟超时")
        ),
    ):
        try:
            await service.chat("测试问题")
        except RuntimeError as exc:
            print(type(exc).__name__)
            print(str(exc))


asyncio.run(main())
'@ | python -
```

预期输出：

```text
RuntimeError
大模型请求超时
```

这里：

```python
asyncio.run(main())
```

用于从普通 Python 脚本启动并运行异步的 `main()`。在 FastAPI 路由中不需要自己调用 `asyncio.run()`，因为 FastAPI 已经负责运行异步环境。

`AsyncMock` 模拟的是一个需要 `await` 的异步方法。整个测试不会发出真实网络请求，也不会消耗 API 额度。

---

# 七、在 FastAPI 路由中增加 `await`

打开：

```text
app/main.py
```

找到 Day 11 的异常处理：

```python
try:
    reply = llm_service.chat(message)
except ValueError as exc:
    ...
except RuntimeError as exc:
    ...
```

只把调用行修改为：

```python
try:
    reply = await llm_service.chat(message)
except ValueError as exc:
    raise HTTPException(
        status_code=500,
        detail=str(exc),
    ) from exc
except RuntimeError as exc:
    raise HTTPException(
        status_code=502,
        detail=str(exc),
    ) from exc
```

其他逻辑保持原样：

```text
先保存 user 消息
await 等待模型回答
成功后保存 assistant 消息
失败时返回 500 或 502
```

之所以可以在这里写 `await`，是因为路由本身已经使用：

```python
async def chat(...):
```

如果忘记 `await`，`reply` 会是 coroutine 对象，不是字符串。后面的 `save_message()` 或 `ChatResponse` 会出现类型错误，也可能看到：

```text
RuntimeWarning: coroutine was never awaited
```

如果 `LLMService.chat()` 还没有改成 `async def`，却在路由中写了 `await`，则可能看到：

```text
TypeError: object str can't be used in 'await' expression
```

所以服务函数的 `async` 和调用处的 `await` 必须配套修改。

---

# 八、理解哪些地方今天仍然是同步的

当前 `/chat` 中还有：

```python
save_message(role="user", content=message)
save_message(role="assistant", content=reply)
```

它们使用同步 `sqlite3`，今天先不改。当前消息写入很短、数据量也很小，本次学习只解决最明显的外部网络等待：

```text
DeepSeek HTTP 请求
```

不要同时引入异步数据库库、连接池或新的 ORM。月计划要求先形成一条清楚、可运行的基础链路。

可以这样概括今天的边界：

```text
已改为异步
LLMService → DeepSeek 的 HTTP 等待

暂时保持同步
SQLite 的简单插入和查询
```

---

# 九、启动服务并测试完整链路

打开终端 A，运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

保持终端 A 运行。打开终端 B，发送一次正常请求：

```powershell
$body = @{
    message = "请用一句话解释 async 和 await"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

预期得到一段真实模型回答，状态码为 200。模型回复内容每次可能不同，只需要确认异步改造后完整调用仍然成功。

再查询最后两条历史：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get | Select-Object -Last 2 | ConvertTo-Json -Depth 3
```

最后两条应该是：

```text
user：请用一句话解释 async 和 await
assistant：模型的真实回答
```

继续验证纯空格消息仍然不会调用模型：

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

今天不并发发送多次真实模型请求，避免不必要地消耗 API 额度。测试成功后，在终端 A 按 `Ctrl + C` 停止服务。

---

# 十、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/services/llm_service.py app/main.py
git check-ignore -v .env
git check-ignore -v data\chat.db
```

确认：

```text
LLMService.chat() 已改成 async def
同步 httpx.post() 已替换为 httpx.AsyncClient 和 await client.post()
路由使用 await llm_service.chat(message)
Day 11 的异常处理仍然存在
消息保存和 /history 仍然可用
.env 和 data/chat.db 没有进入 Git 状态
```

所有测试成功后添加文件：

```powershell
git add app/services/llm_service.py app/main.py docs/Day12.md
git status
```

确认暂存内容正确后提交：

```powershell
git commit -m "refactor: make LLM requests asynchronous"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后不看代码，尝试讲清楚：同步请求在等待什么，`async def` 返回什么，为什么必须 `await`，以及异步为什么不会让模型本身生成得更快，却能改善服务器处理多个请求时的等待方式。

---

# Day 12 完成标准

```text
[ ] 能用自己的话解释同步等待和异步等待的区别
[ ] 能解释 async def、coroutine 和 await 的关系
[ ] LLMService.chat() 已改为 async def
[ ] 已使用 httpx.AsyncClient 和 await client.post()
[ ] /chat 路由已使用 await llm_service.chat(message)
[ ] 超时等原有异常处理在异步请求中仍然有效
[ ] 正常 /chat、消息保存、400 校验和 /history 仍然可用
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：
Day12 问题：
1. 当前把LLMService.chat() 已改为 async def有起到真正的加速的作用吗；
2. 为什么要使用 httpx.AsyncClient，这个有起到什么作用呢，给我讲解一下
Day12 问题答案：
	[[Day12问题答案]]
Git commit：已提交
