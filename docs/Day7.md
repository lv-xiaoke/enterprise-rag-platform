# Day 7：设计聊天消息的数据结构

Day 6 已经跑通了“客户端 → FastAPI → DeepSeek → FastAPI → 客户端”的完整链路，第一周的真实 `/chat` 已经完成。接下来进入月计划第二周：给聊天增加历史记录。

今天先不急着安装 SQLite 或实现 `/history`，只围绕一件事展开：确定一条聊天消息应该包含哪些字段，并在 `app/models.py` 中写成可验证的 Pydantic 模型。完成后，你会得到后续数据库表和历史接口共同使用的数据结构基础。

---

# 一、先复习 `/chat` 现在处理了什么

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

查看 `app/main.py` 中的 `/chat`。当前流程是：

```text
客户端发送 message
→ ChatRequest 校验请求
→ llm_service.chat(message)
→ DeepSeek 返回回答
→ ChatResponse 返回 reply
```

现在的问题是：请求结束后，用户问题和模型回答没有被保存。下一次请求到来时，程序不知道前面聊过什么；以后实现 `GET /history` 时，也没有数据可以返回。

先尝试回答：

```text
当前 /chat 收到了哪两条消息？
程序为什么无法在下一次请求中找回它们？
```

答案应该包含：一条 `user` 消息和一条 `assistant` 消息；目前代码只把它们临时放在函数执行过程中，没有持久化到数据库。

---

# 二、理解 message、history 和 conversation

这三个词容易混在一起，可以先这样区分。

## 1. message：一条消息

一条用户提问：

```text
什么是 RAG？
```

是一条 message。模型返回的一段回答也是另一条 message。

## 2. history：按顺序排列的多条消息

例如：

```text
user：什么是 RAG？
assistant：RAG 是检索增强生成……
user：它为什么能减少幻觉？
assistant：因为回答时会参考检索到的资料……
```

这些消息按时间排列以后，就是聊天历史 history。

## 3. conversation：一组属于同一次对话的消息

conversation 可以理解成聊天软件中的一个会话窗口，一个会话里包含多条 message。

当前项目先只支持一组简单历史，因此月计划规定的最小字段已经够用：

```text
id
role
content
created_at
```

暂时不增加 `conversation_id`、用户表或复杂会话管理。以后真正需要支持多个会话时，再扩展这些字段。

---

# 三、理解四个字段分别解决什么问题

## `id`：区分每一条消息

即使两条消息内容完全相同，它们也应该有不同的 `id`：

```text
id=1  user       什么是 RAG？
id=2  assistant  RAG 是……
```

今天先规定 `id` 必须是大于 0 的整数。以后接入 SQLite 后，数据库会自动生成它。

## `role`：说明是谁说的

当前历史只保存两种角色：

```text
user         用户的问题
assistant    模型的回答
```

如果只保存内容，不保存角色，重新读取历史时就无法判断哪句话来自用户、哪句话来自模型。

DeepSeek 请求中还出现过 `system`，但它是程序设置的行为说明，不是今天要保存的聊天记录，所以当前模型只接受 `user` 和 `assistant`。

## `content`：消息的实际文字

例如：

```text
什么是 RAG？
```

今天要求它至少包含一个字符。纯空格的业务判断仍然由现有 `/chat` 负责，不在今天重复实现。

## `created_at`：记录消息产生的时间

时间可以帮助 `/history` 按消息产生顺序返回结果。Python 中使用 `datetime` 类型，而不是随意拼接的字符串，这样以后排序和写入数据库会更可靠。

今天创建时间时使用带时区的 UTC 时间：

```python
datetime.now(timezone.utc)
```

可以先把 UTC 理解为统一的标准时间。将来前端展示时，再转换成用户所在时区。

---

# 四、创建 `app/models.py`

先在项目根目录创建文件：

```powershell
New-Item app\models.py -ItemType File
```

如果你已经在 VS Code 中手动创建了这个文件，就不要重复执行命令。

在 `app/models.py` 中写入：

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """一条聊天消息的数据结构。"""

    id: int = Field(gt=0)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)
    created_at: datetime
```

逐行理解：

```python
id: int = Field(gt=0)
```

表示 `id` 必须是整数，而且必须大于 0。

```python
role: Literal["user", "assistant"]
```

表示 `role` 只能从两个固定字符串中选择。如果写成 `system` 或其他值，Pydantic 会拒绝。

```python
content: str = Field(min_length=1)
```

表示消息内容必须是字符串，长度至少为 1。

```python
created_at: datetime
```

表示创建时间必须能够被 Pydantic 解析为日期时间。

这里的 `Message` 是应用中的数据模型，负责描述和校验一条消息。它目前还不是 SQLite 数据表，也不会自动保存数据；数据库持久化会在下一步学习。

---

# 五、创建并查看一条用户消息

今天不需要启动 FastAPI。激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

先检查模块能否导入：

```powershell
python -c "from app.models import Message; print(Message)"
```

预期看到类似：

```text
<class 'app.models.Message'>
```

然后创建一条用户消息并输出 JSON：

```powershell
python -c "from datetime import datetime, timezone; from app.models import Message; message = Message(id=1, role='user', content='什么是 RAG？', created_at=datetime.now(timezone.utc)); print(message.model_dump_json(indent=2))"
```

预期输出类似：

```json
{
  "id": 1,
  "role": "user",
  "content": "什么是 RAG？",
  "created_at": "2026-08-09T03:30:00Z"
}
```

实际时间会不同，这是正常的。重点观察两件事：

```text
Python 中创建的是 Message 对象
model_dump_json() 把这个 Pydantic 的 `Message` 对象转换成 JSON 字符串。
indent=2 只是为了让 JSON 格式更好看。
```

`datetime` 在 Python 中是日期时间对象，输出为 JSON 时会变成 ISO 8601 格式的字符串。末尾的 `Z` 表示 UTC。

UTC 时间你可以先把它理解成：

**全世界统一参考的一套“标准时间”。**

比如中国使用的是：

```
北京时间 = UTC + 8 小时
```

如果出现：

```text
ModuleNotFoundError: No module named 'app'
```

先执行 `pwd`，确认当前目录是包含 `app` 文件夹的项目根目录。

---

# 六、验证错误数据会被拒绝

现在故意创建一条错误消息：

```powershell
python -c "from datetime import datetime, timezone; from app.models import Message; Message(id=0, role='system', content='', created_at=datetime.now(timezone.utc))"
```

这条命令预期失败，并显示 `ValidationError`。错误信息中应该能看到三个问题：

```text
id 必须大于 0
role 必须是 user 或 assistant
content 至少需要 1 个字符
```

这次失败正是测试成功的表现：说明 `Message` 没有接受不符合设计的数据。

再创建一条合法的模型回复：

```powershell
python -c "from datetime import datetime, timezone; from app.models import Message; message = Message(id=2, role='assistant', content='RAG 是检索增强生成。', created_at=datetime.now(timezone.utc)); print(message.role, message.content)"
```

预期输出：

```text
assistant RAG 是检索增强生成。
```

到这里，你已经用代码验证了用户消息和模型消息都能使用同一种数据结构表示，同时错误角色和错误字段会被自动拒绝。

---

# 七、想清楚它和后续 SQLite 的关系

今天的数据在命令结束后就消失了，因为它只存在于内存中：

```text
创建 Message 对象
→ 打印结果
→ Python 进程结束
→ 对象消失
```

下一步使用 SQLite 后，流程会变成：

```text
用户问题
→ 创建并保存 user 消息
→ 调用 DeepSeek
→ 创建并保存 assistant 消息
→ 以后通过 /history 重新查询
```

Pydantic 模型和数据库的职责不同：

```text
Pydantic Message
负责描述 Python 中一条合法消息应该长什么样

SQLite 消息表
负责把消息长期保存在磁盘中，并在程序重启后找回来
```

今天不要提前安装新的数据库库，也不要实现 `/history`。先确保自己能够解释四个字段和两种角色，下一次再学习最基本的 SQLite 操作。

---

# 八、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/models.py
```

新文件第一次创建时，`git diff -- app/models.py` 可能不显示内容，因为未跟踪文件默认不在普通 diff 中。可以直接在 VS Code 中复查，或者执行：

```powershell
Get-Content app\models.py
```

确认文件中没有 API Key 等敏感信息，并且今天没有修改 `app/main.py`、`app/services/llm_service.py` 或 `.env`。

所有验证都符合预期后，添加今天的代码和学习计划：

```powershell
git add app/models.py docs/Day7.md
git status
```

再次确认暂存内容正确，然后提交：

```powershell
git commit -m "feat: define chat message model"
```

查看最新提交：

```powershell
git log -1 --oneline
```

---

# Day 7 完成标准

```text
[ ] 能解释 message、history 和 conversation 的区别
[ ] 能解释 id、role、content、created_at 四个字段的用途
[ ] 能解释 user 和 assistant 分别表示谁
[ ] 已在 app/models.py 中定义 Message 模型
[ ] 能使用 Message 创建并输出一条合法消息
[ ] 错误的 id、role 和 content 会触发 Pydantic ValidationError
[ ] 能解释 Pydantic 模型和 SQLite 数据表的职责区别
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
