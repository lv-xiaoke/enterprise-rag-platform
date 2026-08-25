# Day 11：处理大模型调用异常并返回清楚的 HTTP 错误

Day 10 已经完成了 `/chat`、SQLite 消息保存和 `/history` 查询，第二周的主要接口链路已经跑通。现在最明显的问题是：如果 API Key 缺失、网络连接失败、请求超时，或者 DeepSeek 返回的数据格式异常，异常会直接冒到 FastAPI，客户端通常只能看到含义不清楚的 500。

今天只学习异常处理：在 `LLMService` 中把外部模型调用可能出现的问题转换成安全、易懂的 Python 异常，再在 `/chat` 中使用 `HTTPException` 返回合适的 HTTP 状态码。完成后，输入错误仍然返回 400/422；项目配置错误返回 500；外部模型服务错误返回 502。

---

# 一、先复习当前已经有哪些错误处理

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

当前 `/chat` 已经处理了两类用户输入问题。

## 1. Pydantic 自动返回 422

`ChatRequest` 中有：

```python
message: str = Field(
    min_length=1,
    max_length=1000,
)
```

所以缺少 `message`、空字符串或超过最大长度时，Pydantic 会在路由执行前返回 422。

## 2. 路由主动返回 400

```python
message = request.message.strip()

if not message:
    raise HTTPException(
        status_code=400,
        detail="message 不能只包含空格",
    )
```

只包含空格的字符串能通过长度校验，但 `.strip()` 后没有实际内容，所以路由返回 400。

今天不修改这两层输入校验。要补的是后面的模型调用：

```text
用户输入通过校验
→ 保存 user 消息
→ 调用 DeepSeek
→ 这里可能发生配置、网络、超时、状态码或响应格式异常
```

---

# 二、理解 `try`、`except` 和异常转换

最基本的异常处理结构是：

```python
try:
    可能失败的代码
except 某种异常:
    失败以后怎样处理
```

可以把它理解成寄快递：正常情况下按原路线送达；如果遇到地址错误、道路中断或超时，就走对应的处理分支，而不是让整个程序无说明地中断。

今天会使用“异常转换”：

```text
httpx.TimeoutException
→ RuntimeError("大模型请求超时")
→ HTTPException(status_code=502, ...)
→ 客户端收到清楚的 JSON 错误
```

为什么不让路由直接处理所有 `httpx` 异常？

```text
LLMService
知道外部 HTTP 请求是怎样发送的，负责把 httpx 细节整理成服务层错误

FastAPI 路由
知道客户端应该收到哪个 HTTP 状态码，负责把服务层错误变成 HTTPException
```

这样 `app/main.py` 不需要知道 DeepSeek 请求的 URL、响应结构和所有 `httpx` 细节。

---

# 三、整理 `LLMService.chat()` 的请求异常

打开：

```text
app/services/llm_service.py
```

保留原来的配置检查：

```python
if not self.is_configured():
    raise ValueError("大模型配置不完整，请检查 .env")
```

这里继续使用 `ValueError`，表示程序所需的配置值不完整。

找到当前请求代码：

```python
response = httpx.post(
    url,
    headers=headers,
    json=payload,
    timeout=60.0,
)
response.raise_for_status()
```

把它放入下面的 `try/except`：

```python
try:
    response = httpx.post(
        url,
        headers=headers,
        json=payload,
        timeout=60.0,
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

异常顺序很重要：

```text
TimeoutException
是 RequestError 的一种，所以必须先捕获

HTTPStatusError
表示已经收到响应，但状态码是 4xx 或 5xx

RequestError
处理其他请求问题，例如连接失败、DNS 问题等
```

今天的错误消息只包含安全摘要和状态码，不返回上游响应正文，也不打印请求头。这样可以减少 API Key、服务内部信息或其他敏感内容进入客户端响应和日志的风险。

`raise ... from exc` 表示新异常是由原异常引起的。客户端只看到我们整理过的消息，开发时的 traceback 仍然能保留原始原因，方便排查。

---

# 四、处理模型响应格式异常

当前代码直接执行：

```python
data = response.json()
return data["choices"][0]["message"]["content"]
```

它假设响应一定是合法 JSON，并且一定有完整的：

```text
choices
→ 第 0 项
→ message
→ content
```

如果上游返回空数组、缺少字段、不是 JSON，或者 `content` 不是有效字符串，代码可能出现：

```text
ValueError
KeyError
IndexError
TypeError
```

把原来的解析部分修改为：

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

这里分两步检查：

```text
第一步
能否解析 JSON，并找到 choices[0].message.content

第二步
content 是否真的是非空字符串
```

今天不把原始响应完整写进错误消息，因为响应中可能包含不适合直接暴露给客户端的信息。

---

# 五、理解修改后的服务层结果

完成后，`LLMService.chat()` 对外只保留三种结果：

```text
成功
→ 返回模型回答字符串

配置不完整
→ 抛出 ValueError

外部请求或响应异常
→ 抛出 RuntimeError，并携带安全的中文摘要
```

这叫作“收窄异常边界”：路由不需要分别了解 `TimeoutException`、`HTTPStatusError`、`KeyError` 等所有底层异常，只需要处理服务层整理后的两类失败。

不要写成：

```python
except Exception:
    raise RuntimeError("出错了")
```

因为它会把代码拼写错误、类型错误等本应暴露给开发者的问题也全部吞掉，而且“出错了”不能帮助判断原因。今天只捕获明确知道怎样处理的异常。

---

# 六、先用模拟异常测试 `LLMService`

异常很难每次靠真实网络稳定触发。今天使用 Python 标准库中的 `unittest.mock.patch`，临时让 `httpx.post()` 抛出指定错误，不修改 `.env`，也不会真的发送网络请求。

先激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

## 1. 测试配置缺失

运行：

```powershell
@'
from app.services.llm_service import LLMService

service = LLMService()
service.api_key = ""

try:
    service.chat("测试问题")
except ValueError as exc:
    print(type(exc).__name__)
    print(str(exc))
'@ | python -
```

##### `@' ... '@` 是什么？

这是 PowerShell 的 **Here-String（多行字符串）**。

预期输出：

```text
ValueError
大模型配置不完整，请检查 .env
```

这里只修改当前测试进程中的 `service.api_key`，没有读取、显示或改写真实 `.env`。

`-` 很重要，意思是：平时 Python 运行代码，通常是从一个 `.py` 文件里读；而 `python -` 里的这个 `-` 表示“不要去找文件了，直接从命令行传进来的内容里读代码”。

## 2. 测试请求超时

运行：

```powershell
@'
from unittest.mock import patch

import httpx

from app.services.llm_service import LLMService

service = LLMService()
service.api_key = "test-key"
service.base_url = "https://example.com"
service.model = "test-model"

with patch(
    "app.services.llm_service.httpx.post",
    side_effect=httpx.TimeoutException("模拟超时"),
):
    try:
        service.chat("测试问题")
    except RuntimeError as exc:
        print(type(exc).__name__)
        print(str(exc))
'@ | python -
```

预期输出：

```text
RuntimeError
大模型请求超时
```

`patch()` 只在 `with` 代码块中临时替换 `httpx.post()`，离开代码块后会自动恢复，不会调用 `example.com`。

## 3. 测试异常响应结构

运行：

```powershell
@'
from unittest.mock import Mock, patch

from app.services.llm_service import LLMService

service = LLMService()
service.api_key = "test-key"
service.base_url = "https://example.com"
service.model = "test-model"

fake_response = Mock()
fake_response.raise_for_status.return_value = None
fake_response.json.return_value = {}

with patch(
    "app.services.llm_service.httpx.post",
    return_value=fake_response,
):
    try:
        service.chat("测试问题")
    except RuntimeError as exc:
        print(type(exc).__name__)
        print(str(exc))
'@ | python -
```

预期输出：

```text
RuntimeError
大模型返回格式异常
```

这些测试不使用真实 API 额度，也不会向数据库写入消息。

---

# 七、在 `/chat` 中转换成 `HTTPException`

打开：

```text
app/main.py
```

当前核心代码是：

```python
save_message(role="user", content=message)
reply = llm_service.chat(message)
save_message(role="assistant", content=reply)
```

修改为：

```python
save_message(role="user", content=message)

try:
    reply = llm_service.chat(message)
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

save_message(role="assistant", content=reply)
```

状态码可以这样理解：

```text
500 Internal Server Error
项目自身配置不完整，例如缺少 API Key、Base URL 或模型名称

502 Bad Gateway
当前 FastAPI 作为中间服务调用上游模型时，上游请求或响应出了问题
```

FastAPI 会把 `HTTPException` 转成 JSON，例如：

```json
{
  "detail": "大模型请求超时"
}
```

Day 9 已经确定：先保存用户问题，再调用模型。因此模型失败时，数据库中会保留 `user` 消息，但不会保存不存在的 `assistant` 回答。今天继续保持这个行为，不引入事务回滚。

---

# 八、启动服务并做回归测试

打开终端 A，运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

保持终端 A 运行。打开终端 B，先测试原来的输入错误。

## 1. 纯空格仍返回 400

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

预期：

```text
400
```

## 2. 缺少字段仍返回 422

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

预期：

```text
422
```

## 3. 正常请求仍能成功

```powershell
$body = @{
    message = "请用一句话解释异常处理的作用"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

预期返回一段真实回答。这一步只调用一次模型，确认新异常处理没有破坏正常链路。

再查询历史：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get | Select-Object -Last 2 | ConvertTo-Json -Depth 3
```

最后两条应该是本次成功请求的 `user` 和 `assistant` 消息。

测试完成后，在终端 A 按 `Ctrl + C` 停止服务。

---

# 九、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/services/llm_service.py app/main.py
git check-ignore -v .env
git check-ignore -v data\chat.db
```

确认：

```text
llm_service.py 只增加明确的请求和响应异常处理
main.py 把 ValueError 转成 500，把 RuntimeError 转成 502
原来的 400、422、消息保存和 /history 没有被删除
错误消息中没有 API Key、请求头或完整上游响应
.env 和 data/chat.db 仍然被忽略
```

所有模拟测试和接口回归测试成功后，添加今天的文件：

```powershell
git add app/services/llm_service.py app/main.py docs/Day11.md
git status
```

确认暂存区没有 `.env` 和数据库文件，然后提交：

```powershell
git commit -m "feat: handle LLM service errors"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后尝试不看代码讲清楚：`try/except` 在哪里捕获什么异常、为什么服务层使用 `RuntimeError`、为什么路由再把它转换成 `HTTPException`，以及 400、422、500、502 分别代表哪一层的问题。

---

# Day 11 完成标准

```text
[ ] 能解释 try、except 和 raise ... from exc 的作用
[ ] LLMService 能区分配置缺失、超时、HTTP 错误、连接失败和响应格式异常
[ ] 错误响应不会包含 API Key、请求头或完整上游响应
[ ] /chat 会把配置错误转换成 500
[ ] /chat 会把外部模型服务错误转换成 502
[ ] 空格消息仍返回 400，缺少字段仍返回 422
[ ] 正常 /chat、消息保存和 /history 仍然可用
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
