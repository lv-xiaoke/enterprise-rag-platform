# Day 6：把 `/chat` 接入真实 DeepSeek 回复

Day 5 已经在 `app/services/llm_service.py` 中实现了 `LLMService.chat()`，并且从 PowerShell 直接得到了真实模型回复。现在还差最后一段连接：本地 `/chat` 仍然返回模拟文字，没有调用这个服务。

今天只修改 `app/main.py`，让用户发送的 JSON 经过 FastAPI 和 Pydantic 校验后，交给 `LLMService`，再把 DeepSeek 的回答包装成 `ChatResponse` 返回。完成后，项目就能跑通第一条完整链路：客户端 → FastAPI → DeepSeek → FastAPI → 客户端。

---

# 一、先复习已经完成的两层代码

先打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

查看 `app/services/llm_service.py` 中已有的方法：

```python
def chat(self, message: str) -> str:
    ...
```

它接收一个普通字符串，向 DeepSeek 发送请求，最后返回模型回答字符串：

```text
用户问题字符串
→ httpx.post()
→ DeepSeek API
→ choices[0].message.content
→ 回答字符串
```

再查看 `app/main.py` 中已有的 `/chat`：

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

这段路由已经负责了三件事：

```text
用 ChatRequest 接收并校验 JSON
去除消息首尾空白并拒绝纯空格
用 ChatResponse 规定响应格式
```

今天不重写这两层，只把它们连接起来。

---

# 二、理解路由层和服务层为什么要分开

可以把当前项目理解成餐厅中的两种岗位：

```text
app/main.py
像前台，负责接收请求、检查格式、返回结果

app/services/llm_service.py
像后厨，负责真正调用模型并取得回答
```

如果把 DeepSeek 的 URL、请求头和 `httpx.post()` 全部写进 `/chat` 路由，接口代码会越来越长。以后增加聊天记录、异常处理和 RAG 时，也会更难区分每部分的职责。

现在已经有全局服务对象：

```python
llm_service = LLMService()
```

所以路由只需要调用：

```python
llm_service.chat(message)
```

注意，当前 `LLMService.chat()` 使用普通的 `def` 定义，因此今天调用时不写 `await`：

```python
reply = llm_service.chat(message)
```

月计划后面会单独学习 `async` 和 `await`，到时再把外部 HTTP 请求改成异步。今天先把完整功能跑通，不提前扩展异步和复杂异常处理。

---

# 三、修改 `app/main.py`

打开：

```text
app/main.py
```

找到 `/chat` 路由中的模拟回复：

```python
# Day 3 暂时不调用真实大模型
reply = f"模拟大模型回复：你发送了「{message}」"
```

替换为：

```python
reply = llm_service.chat(message)
```

修改后的完整路由应该是：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    reply = llm_service.chat(message)
    return ChatResponse(reply=reply)
```

今天不需要修改下面这些内容：

```text
ChatRequest 的长度限制
ChatResponse 的 reply 字段
LLMService.chat() 的请求代码
.env 中已经验证成功的配置
```

修改后先做一次不调用模型的语法和导入检查：

```powershell
python -m uvicorn app.main:app --reload
```

正常情况下会看到各模块被检查或编译，并且没有 `SyntaxError`、`ImportError` 等报错。

---

# 四、启动服务并确认配置状态

打开终端 A，用它持续运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

看到下面的信息说明服务启动成功：

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete
```

保持终端 A 不要关闭。再打开终端 B，先检查健康接口：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get
```

今天预期得到：

```text
status llm_configured
------ --------------
ok               True
```

如果 `llm_configured` 是 `False`，先停止终端 A 中的服务，检查 `.env` 的三个变量名和值是否完整，然后重新启动服务。不要使用 `Get-Content .env`，也不要把真实 API Key 复制到终端输出或聊天中。

之所以需要重新启动，是因为 `llm_service = LLMService()` 会在应用导入时读取配置；只修改 `.env` 不一定会触发 `--reload`。

---

# 五、从终端调用本地 `/chat`

保持终端 A 中的服务运行，在终端 B 创建请求体：

```powershell
$body = @{
    message = "请用一句话解释什么是 RAG"
} | ConvertTo-Json
```

然后把 JSON 发送给自己的 FastAPI：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

成功时会得到类似结果：

```text
reply
-----
RAG 是一种先检索外部知识，再让大模型结合检索结果生成回答的方法。
```

回答内容不必和示例完全相同，只要它来自真实模型并与问题相关即可。确认成功一次就够了，不需要反复消耗 API 额度。

这次完整过程是：

```text
终端 B 发送 POST /chat
→ FastAPI 把 JSON 转成 ChatRequest
→ chat() 取得并清理 message
→ llm_service.chat(message)
→ httpx 向 DeepSeek 发送请求
→ DeepSeek 返回回答
→ ChatResponse(reply=reply)
→ FastAPI 返回 JSON
```

如果本地接口返回 500，先看终端 A 中的错误摘要：

```text
ValueError：检查三项模型配置是否完整
401 或 403：检查 API Key 是否有效
404：检查 Base URL 和模型名称
ConnectError 或 Timeout：检查网络，稍后只重试一次
```

今天先观察并记录外部服务异常，不要急着加入一大段 `try/except`。月计划 Day 12 会专门处理 API Key 缺失、网络失败和超时，并把它们转换成更清晰的 HTTP 响应。

---

# 六、确认原来的参数校验仍然有效

接入真实模型后，原来的 Pydantic 和空格校验不能失效。继续在终端 B 测试纯空格消息：

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

再测试缺少 `message` 字段：

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

这两种错误都应该在调用 DeepSeek 之前被拦住，因此不会消耗模型额度。测试完成后，在终端 A 按 `Ctrl + C` 停止服务。

---

# 七、检查改动并提交 Git

先检查工作区：

```powershell
git status --short
git diff -- app/main.py
```

确认 `app/main.py` 只把模拟回复替换成了真实服务调用，并确认 `.env` 没有出现在 Git 状态中。

今天的学习计划文件也会出现在状态中，所以测试全部成功后添加这两个文件：

```powershell
git add app/main.py docs/Day6.md
git status
```

再次确认暂存区没有 `.env`，然后提交：

```powershell
git commit -m "feat: connect chat endpoint to DeepSeek"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后尝试不看代码，用自己的话讲清楚：为什么 `/chat` 属于接口层，`LLMService` 属于服务层，以及一次用户问题如何经过这两层得到真实回答。

---

# Day 6 完成标准

```text
[ ] 能解释 app/main.py 和 llm_service.py 的职责区别
[ ] 能解释为什么当前调用 llm_service.chat(message) 时不写 await
[ ] 已把 /chat 的模拟回复替换为 LLMService 调用
[ ] GET /health 显示 llm_configured 为 True
[ ] POST /chat 成功返回一次真实 DeepSeek 回答
[ ] 纯空格消息仍返回 400，缺少 message 仍返回 422
[ ] 能完整说明客户端 → FastAPI → DeepSeek → FastAPI → 客户端的调用链
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
