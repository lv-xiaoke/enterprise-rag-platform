# Day 5：用 HTTPX 调用 DeepSeek API

Day 1～Day 4 已经完成了项目初始化、Python 项目结构、HTTP、FastAPI 和 Pydantic 参数校验，最新的 Git 提交也已经包含 Day 4 的代码。项目里已经安装了 `httpx`，`config.py` 也能读取三项大模型配置，但 `LLMService` 目前还只能判断配置是否完整。

今天只做一件事：在 `app/services/llm_service.py` 中实现真实的 DeepSeek API 请求，并从 PowerShell 直接得到一次模型回复。今天先不修改 `app/main.py`，下一次学习再把真实模型调用接入 `/chat`，这样更容易分清“调用外部模型”和“实现本地接口”这两层逻辑。

---

# 一、先复习两种 HTTP 请求

目前你已经测试过：

```text
浏览器或 PowerShell
→ 向自己的 FastAPI 发送 POST /chat
→ FastAPI 返回模拟回复
```

今天会新增另一段 HTTP 通信：

```text
你的 Python 代码
→ 向 DeepSeek 发送 POST /chat/completions
→ DeepSeek 返回真实模型回复
```

同一个项目在两段通信里的身份不同：

```text
用户调用 /chat 时：你的 FastAPI 是服务器
FastAPI 调用 DeepSeek 时：你的项目又是客户端
```

可以把它想成一家餐厅：顾客向服务员点菜时，服务员负责接收请求；服务员再去后厨报菜名时，服务员又成了发出请求的一方。

先尝试用自己的话回答：

```text
httpx 在今天的代码中扮演什么角色？
为什么自己的 FastAPI 既可能是服务器，又可能是客户端？
```

---

# 二、理解调用大模型需要的五项内容

今天只使用 DeepSeek，不同时研究其他平台。调用 Chat Completion 接口时，至少要理解下面五项内容。

## 1. API Key

API Key 用来证明调用者是谁，可以把它理解成访问模型服务的通行证。

它会放进请求头：

```http
Authorization: Bearer 你的API Key
```

真实 Key 只能保存在 `.env` 中，不要写进 Python、学习笔记、Git 提交、报错截图或聊天消息。

## 2. Base URL

Base URL 是模型服务的基础地址。DeepSeek 当前的 OpenAI 兼容接口地址是：

```text
https://api.deepseek.com
```

代码会在后面拼上：

```text
/chat/completions
```

最终请求地址是：

```text
https://api.deepseek.com/chat/completions
```

## 3. 模型名称

今天使用：

```text
deepseek-v4-flash
```

旧笔记中的 `deepseek-chat` 已经过时，不要继续照抄。模型和接口信息可查看 [DeepSeek 官方更新记录](https://api-docs.deepseek.com/updates) 与 [Chat Completion 接口文档](https://api-docs.deepseek.com/api/create-chat-completion)。

## 4. messages

大模型聊天接口不是只发送一段裸字符串，而是发送一组带角色的消息：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个回答简洁的 AI 助手。"
    },
    {
      "role": "user",
      "content": "请用一句话解释 RAG。"
    }
  ]
}
```

先记住三个常见角色：

```text
system      规定模型的身份和总体要求
user        用户发送的问题
assistant   模型已经给出的回复
```

今天只需要发送 `system` 和 `user`。等以后实现多轮对话时，才会把以前的 `assistant` 回复也放进 `messages`。

## 5. 模型返回的数据

模型的回复不是直接的一行文字，而是一个 JSON 对象。今天需要从下面这条路径取出最终回答：

```text
choices
→ 第 0 个结果
→ message
→ content
```

对应 Python 代码是：

```python
data["choices"][0]["message"]["content"]
```

---

# 三、配置 `.env`，但不要显示真实密钥

在项目根目录的 `.env` 中填写自己的配置：

```env
LLM_API_KEY=在这里填写自己的真实Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

不要在终端运行下面这种命令：

```powershell
Get-Content .env
```

因为它会直接把真实 API Key 显示在屏幕上。

可以用现有的 `is_configured()` 只检查三项配置是否齐全，而不打印具体内容：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -c "from app.services.llm_service import LLMService; print(LLMService().is_configured())"
```

预期输出：

```text
True
```

如果输出 `False`，检查 `.env` 中是否准确写了下面三个变量名，以及等号后是否都有值：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

还可以确认 `.env` 仍然被 Git 忽略：

```powershell
git check-ignore -v .env
```

只要它显示匹配到了 `.gitignore` 中的规则即可，不需要输出 `.env` 的内容。

---

# 四、实现 `LLMService.chat()`

打开：

```text
app/services/llm_service.py
```

把它整理为下面的代码：

```python
import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class LLMService:
    """负责调用大语言模型服务。"""

    def __init__(self) -> None:
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL

    def is_configured(self) -> bool:
        """判断大模型配置是否完整。"""
        return bool(
            self.api_key
            and self.base_url
            and self.model
        )

    def chat(self, message: str) -> str:
        """向大模型发送一条用户消息并返回回答。"""
        if not self.is_configured():
            raise ValueError("大模型配置不完整，请检查 .env")

        url = f"{self.base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个回答简洁、准确的 AI 助手。",
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "stream": False,
        }

        response = httpx.post(
            url,
            headers=headers,
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
```

下面逐段理解今天真正新增的内容。

## `httpx.post()`

```python
response = httpx.post(...)
```

表示 Python 主动向外部服务器发送一个 POST 请求。它和你在 PowerShell 中使用 `Invoke-RestMethod -Method Post` 做的是同一类事情。

## `headers=headers`

请求头中最重要的是：

```python
"Authorization": f"Bearer {self.api_key}"
```

DeepSeek 会根据这里的 Key 判断是否允许调用。不要打印整个 `headers`，否则真实 Key 也会被打印出来。

## `json=payload`

`httpx` 会把 Python 字典转换成 JSON 请求体。`payload` 中最重要的是：

```text
model      使用哪个模型
messages   给模型哪些消息
stream     今天使用一次性返回，不做流式输出
```

## `timeout=60.0`

表示最多等待 60 秒。网络请求不能无限等待，否则程序可能一直卡住。

## `response.raise_for_status()`

如果模型服务返回 401、404、500 等错误状态码，这一行会抛出异常，而不是继续把错误响应当成正常回复处理。

## `response.json()`

把 DeepSeek 返回的 JSON 响应转换成 Python 数据，再从中取出回答文字。

今天先观察异常长什么样，不需要一次实现完整异常处理；月计划后面会单独学习网络失败、超时和 `HTTPException`。

---

# 五、从 PowerShell 直接测试真实回复

今天先不启动 FastAPI，也不修改 `app/main.py`。在项目根目录运行：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -c "from app.services.llm_service import LLMService; print(LLMService().chat('请用一句话解释什么是 RAG'))"
```

如果调用成功，终端会输出模型生成的一段真实回答，例如：

```text
RAG 是一种先从外部知识库检索相关资料，再让大模型结合资料生成回答的方法。
```

模型每次生成的文字可能不同，不要求和示例一模一样。判断成功的标准是：命令正常结束，并得到一段与问题相关的真实回答。

这次请求会使用少量 API 额度。确认第一次已经成功后，不需要反复调用很多次。

如果报错，可以先按状态检查：

```text
配置检查是 False
→ 检查 .env 中三个变量是否都有值

401 或 403
→ 检查 API Key 是否有效，但不要把 Key 发到聊天或截图中

404
→ 检查 Base URL 和模型名称是否准确

连接失败或超时
→ 先检查网络，再稍后重试一次
```

如果错误信息很长，只记录状态码和不含密钥的错误摘要。

---

# 六、确认今天没有提前改 `/chat`

今天的边界是：

```text
已完成：Python 代码可以直接调用 DeepSeek 并拿到回答
暂未完成：用户通过本地 POST /chat 拿到 DeepSeek 回答
```

这不是漏做，而是把两层功能分开学习：

```text
今天：LLMService → DeepSeek
下一次：FastAPI /chat → LLMService → DeepSeek
```

执行：

```powershell
git status --short
git diff -- app/services/llm_service.py
git diff -- app/main.py
```

`git status --short` 的意思是：

> 用简短格式查看当前 Git 仓库里哪些文件发生了变化。

预期：

```text
app/services/llm_service.py 有今天的改动
app/main.py 没有改动
.env 不出现在 Git 状态中
```

---

# 七、测试成功后提交 Git

只添加今天修改的服务文件：

```powershell
git add app/services/llm_service.py
git status
```

git add . 可以提交所有修改

再次确认暂存区没有 `.env`，然后提交：

```powershell
git commit -m "feat: call DeepSeek chat API"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后试着不看代码说清楚下面这条链路：

```text
用户问题字符串
→ LLMService.chat()
→ httpx 发送请求头和 JSON 请求体
→ DeepSeek 根据 messages 生成回答
→ response.json()
→ 取出 choices[0].message.content
→ 返回 Python 字符串
```

---

# Day 5 完成标准

```text
[ ] 能解释 API Key、Base URL 和模型名称分别有什么作用
[ ] 能解释 system、user、assistant 三种消息角色
[ ] 已在 .env 中配置 DeepSeek，且没有显示或提交真实 API Key
[ ] 已在 LLMService 中写出 chat(message) 方法
[ ] 能解释 headers、json、timeout 和 raise_for_status() 的作用
[ ] 已从 PowerShell 直接得到一次真实模型回复
[ ] 确认今天没有修改 app/main.py，/chat 暂时仍返回模拟回复
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
