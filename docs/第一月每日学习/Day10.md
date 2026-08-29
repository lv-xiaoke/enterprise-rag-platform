# Day 10：实现 `GET /history` 查询聊天记录

Day 9 已经让一次成功的 `/chat` 请求按顺序向 SQLite 写入两条记录：用户问题保存为 `user`，DeepSeek 回答保存为 `assistant`。现在数据库能保存消息，但客户端还不能通过接口读取它们。

今天只完成查询链路：在 `app/database.py` 中实现 `get_messages()`，把 SQLite 查询结果转换成 Day 7 定义的 `Message` 对象，再在 `app/main.py` 中新增 `GET /history`。完成后，不需要调用模型，也能从浏览器或 PowerShell 看到按顺序排列的聊天历史。

---

# 一、先复习“保存”和“查询”是两个方向

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

当前已经完成的保存方向是：

```text
POST /chat
→ save_message("user", message)
→ DeepSeek 生成回答
→ save_message("assistant", reply)
→ SQLite messages 表
```

今天要完成相反方向：

```text
客户端发送 GET /history
→ get_messages() 查询 SQLite
→ 每一行转换成 Message 对象
→ FastAPI 转换成 JSON 数组
→ 客户端收到聊天历史
```

先尝试回答：

```text
为什么 /chat 使用 POST，而 /history 使用 GET？
```

可以简单回答：

```text
POST /chat
向服务器提交问题，并产生新的消息数据

GET /history
只读取已经存在的聊天记录
```

---

# 二、理解今天的返回结果

数据库中一行消息包含：

```text
id
role
content
created_at
```

Day 7 的 `app/models.py` 已经定义了相同结构：

```python
class Message(BaseModel):
    id: int = Field(gt=0)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)
    created_at: datetime
```

所以 `/history` 会返回一个由多条 `Message` 组成的 JSON 数组：

```json
[
  {
    "id": 3,
    "role": "user",
    "content": "什么是 RAG？",
    "created_at": "2026-08-10T00:30:00"
  },
  {
    "id": 4,
    "role": "assistant",
    "content": "RAG 是检索增强生成……",
    "created_at": "2026-08-10T00:30:02"
  }
]
```

这里最外层的：

```text
[
  ...
]
```

表示列表，因为历史中可能有零条、一条或很多条消息。

如果数据库中没有消息，合理结果是：

```json
[]
```

这表示查询成功，只是历史为空，不需要返回 404。

---

# 三、在数据库层实现 `get_messages()`

打开：

```text
app/database.py
```

在现有导入中增加：

```python
from app.models import Message
```

然后在 `save_message()` 后面添加：

```python
def get_messages() -> list[Message]:
    """按消息产生顺序返回全部聊天记录。"""
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        connection.close()

    messages: list[Message] = []

    for row in rows:
        messages.append(
            Message(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
        )

    return messages
```

今天先使用清楚的 `for` 循环，不需要为了少写几行而改成复杂的列表推导式。

---

# 四、理解查询结果如何变成 `Message`

## 1. `fetchall()` 得到多行数据

这段 SQL：

```sql
SELECT id, role, content, created_at
FROM messages
ORDER BY id ASC
```

会查询所有消息，并按 `id` 从小到大排列。

```python
.fetchall()
```

表示一次取出全部查询结果。当前学习项目的数据量很小，可以先这样做。以后数据很多时才需要考虑分页，今天不要提前增加 `limit`、`offset` 或复杂查询。

## 2. 为什么可以写 `row["role"]`

Day 8 的 `get_connection()` 已经设置：

```python
connection.row_factory = sqlite3.Row
```

因此一行数据既可以按位置读取，也可以按字段名读取：

```python
row["id"]
row["role"]
row["content"]
row["created_at"]
```

按字段名读取更清楚，不需要记住第 0、1、2、3 列分别是什么。

## 3. 为什么还要转换成 `Message`

SQLite 返回的是数据库行，FastAPI 接口需要的是明确的数据模型。下面这一步：

```python
Message(
    id=row["id"],
    role=row["role"],
    content=row["content"],
    created_at=row["created_at"],
)
```

会再次验证数据库中的数据是否符合约定：

```text
id 必须大于 0
role 必须是 user 或 assistant
content 不能为空字符串
created_at 必须能解析成日期时间
```

SQLite 保存的 `created_at` 是文本，例如：

```text
2026-08-10 00:30:00
```

Pydantic 会把它解析成 Python 的 `datetime`，FastAPI 返回 JSON 时再把它转换成标准日期时间字符串。

---

# 五、先单独测试数据库查询函数

今天仍然先测试底层函数，再接 FastAPI。激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

执行：

```powershell
python -c "from app.database import init_database, get_messages; init_database(); messages = get_messages(); [print(message.model_dump()) for message in messages]"
```

`model_dump()` 会把它转换成 Python 字典：

应该能看到数据库中已有的测试消息和真实聊天记录，例如：

```text
{'id': 1, 'role': 'user', 'content': 'SQLite 测试消息', 'created_at': datetime.datetime(...)}
{'id': 3, 'role': 'user', 'content': '请用一句话解释向量数据库', 'created_at': datetime.datetime(...)}
{'id': 4, 'role': 'assistant', 'content': '向量数据库是一种……', 'created_at': datetime.datetime(...)}
```

实际消息、`id` 和时间以本地数据库为准。重点确认：

```text
命令没有出现 ValidationError
输出顺序按 id 从小到大
列表中的每一项都是 Message 对象
```

再确认返回类型：

```powershell
python -c "from app.database import get_messages; messages = get_messages(); print(type(messages)); print(type(messages[0]) if messages else '历史为空')"
```

有历史记录时，预期类似：

```text
<class 'list'>
<class 'app.models.Message'>
```

如果出现：

```text
NameError: name 'Message' is not defined
```

检查 `app/database.py` 顶部是否已经导入：

```python
from app.models import Message
```

如果 `created_at` 出现 Pydantic 校验错误，先打印对应数据库行，确认保存格式仍然是 SQLite 默认的 `YYYY-MM-DD HH:MM:SS`，不要直接修改或删除数据库文件。

---

# 六、在 `app/main.py` 中新增 `/history`

打开：

```text
app/main.py
```

把数据库导入从：

```python
from app.database import init_database, save_message
```

修改为：

```python
from app.database import get_messages, init_database, save_message
```

再导入 Day 7 定义的模型：

```python
from app.models import Message
```

然后在 `/chat` 路由后面添加：

```python
@app.get("/history", response_model=list[Message])
async def history(response: Response) -> list[Message]:
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return get_messages()
```

逐部分理解：

```python
@app.get("/history")
```

表示注册：

```http
GET /history
```

```python
response_model=list[Message]
```

告诉 FastAPI：响应应该是一个列表，列表中的每一项都必须符合 `Message` 模型。

```python
-> list[Message]
```

是 Python 返回值类型提示，让读代码的人和编辑器知道这个函数返回什么。

```python
return get_messages()
```

路由不直接编写 SQL，只调用数据库层提供的查询函数。

手动设置带 `charset=utf-8` 的响应头，是为了延续当前 `/chat` 的处理方式，避免部分 PowerShell 环境显示中文时出现乱码。

---

# 七、启动服务并查看 Swagger

打开终端 A，用它持续运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

浏览器打开：

```text
http://127.0.0.1:8000/docs
```

现在应该能看到：

```text
POST /chat
GET  /history
```

在 Swagger 中展开 `GET /history`，点击：

```text
Try it out → Execute
```

预期状态码：

```text
200 OK
```

响应体应该是一个 JSON 数组，并且每项都有：

```text
id
role
content
created_at
```

`GET /history` 只查询本地 SQLite，不调用 DeepSeek，因此测试它不会消耗模型 API 额度。

---

# 八、从 PowerShell 测试 `/history`

保持终端 A 中的服务运行，再打开终端 B：

```powershell
$history = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get

$history | ConvertTo-Json -Depth 3
```

-Depth 3 ： 表示 **JSON 转换时最多展开到 3 层嵌套结构**。

预期输出类似：

```json
[
  {
    "id": 1,
    "role": "user",
    "content": "SQLite 测试消息",
    "created_at": "2026-08-09T12:30:00"
  },
  {
    "id": 3,
    "role": "user",
    "content": "请用一句话解释向量数据库",
    "created_at": "2026-08-10T00:30:00"
  },
  {
    "id": 4,
    "role": "assistant",
    "content": "向量数据库是一种……",
    "created_at": "2026-08-10T00:30:02"
  }
]
```

实际内容以数据库为准。检查相邻的真实聊天记录是否保持：

```text
user
assistant
user
assistant
```

并确认 `id` 从小到大排列。

如果返回 500，查看终端 A：

```text
no such table: messages
→ 检查应用启动时是否仍然调用 init_database()

ValidationError
→ 检查报错指出的具体数据库行和字段

NameError 或 ImportError
→ 检查 get_messages 和 Message 的导入名称
```

---

# 九、验证新增聊天会出现在历史中

继续保持服务运行。先记住当前 `$history.Count`：

```powershell
$history.Count
```

然后发送一次新的聊天请求：

```powershell
$body = @{
    message = "请用一句话说明 SQLite 的特点"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

上面这个会发现发送过去的是？？？？？：
这个现象和你前面遇到的 `????????` 基本是同一类问题：**PowerShell 在发送中文请求体时发生了编码问题**。

 推荐你直接改成这样：

```powershell
$body = @{
    message = "请用一句话解释异常处理的作用"
} | ConvertTo-Json

$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body $utf8Body
```



模型成功回答后，再查询历史：

```powershell
$newHistory = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/history" `
    -Method Get

$newHistory.Count
$newHistory | Select-Object -Last 2 | ConvertTo-Json -Depth 3
```

预期：

```text
新的消息总数比原来增加 2
最后两条依次是 user 问题和 assistant 回答
```

这就验证了保存和读取两条链路已经连接起来：

```text
POST /chat 负责产生并保存消息
GET /history 负责查询并返回消息
```

这次 `/chat` 会使用少量模型额度，只需要成功测试一次。

测试完成后，在终端 A 按 `Ctrl + C` 停止服务。

---

# 十、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- app/database.py app/main.py
git check-ignore -v data\chat.db
```

确认：

```text
database.py 新增了 get_messages()
main.py 新增了 GET /history 和必要导入
原来的 POST /chat 保存逻辑没有被删除
data/chat.db 仍被忽略
.env 没有出现在 Git 状态中
```

所有测试成功后，添加今天的代码和学习计划：

```powershell
git add app/database.py app/main.py docs/Day10.md
git status
```

确认暂存区正确后提交：

```powershell
git commit -m "feat: add chat history endpoint"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后尝试不看代码讲清楚：数据库行怎样变成 `Message` 对象，`list[Message]` 表示什么，以及 FastAPI 怎样把这个列表转换成 JSON 数组。

---

# Day 10 完成标准

```text
[ ] 能解释 POST /chat 和 GET /history 的职责区别
[ ] 已在 app/database.py 中实现 get_messages()
[ ] get_messages() 会按 id 从小到大返回 list[Message]
[ ] 已在 app/main.py 中实现 GET /history
[ ] /history 返回 200 和包含四个字段的 JSON 数组
[ ] /history 不会调用 DeepSeek 或消耗模型额度
[ ] 新调用一次 /chat 后，/history 的消息数量增加 2
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
