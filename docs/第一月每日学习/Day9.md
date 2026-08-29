# Day 9：让 `/chat` 自动保存用户问题和模型回答

Day 8 已经创建了 `data/chat.db` 和 `messages` 表，也亲手练习了 `INSERT`、`SELECT`、`ORDER BY`。但目前只有手动运行 Python 命令时才会写入测试消息，真正调用 `/chat` 时，用户问题和 DeepSeek 回答仍然不会保存。

今天只完成“保存聊天记录”这一条链路：在 `app/database.py` 中封装 `save_message()`，然后修改 `app/main.py`，按照“保存用户问题 → 调用 DeepSeek → 保存模型回答”的顺序执行。完成后，每次成功调用 `/chat`，数据库中都会新增一条 `user` 消息和一条 `assistant` 消息。

---

# 一、先复习 Day 8 的数据库代码

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

查看 `app/database.py`，先确认自己能大致解释：

```text
DATABASE_PATH 指向哪里
get_connection() 为什么每次返回一个连接
init_database() 为什么使用 CREATE TABLE IF NOT EXISTS
commit() 和 close() 分别有什么作用
```

当前程序已经能创建这张表：

```text
messages
├── id
├── role
├── content
└── created_at
```

但是 `app/main.py` 的 `/chat` 目前只有：

```text
接收用户问题
→ 调用 llm_service.chat()
→ 返回模型回答
```

今天要在这条链路中加入两次数据库写入：

```text
接收用户问题
→ 保存 role=user 的消息
→ 调用 llm_service.chat()
→ 保存 role=assistant 的消息
→ 返回模型回答
```

---

# 二、为什么要把 SQL 封装成函数

Day 8 的测试命令直接写了：

```python
connection.execute(
    "INSERT INTO messages (role, content) VALUES (?, ?)",
    ("user", "SQLite 测试消息"),
)
```

如果把这段连接、执行、提交和关闭代码全部复制进 `/chat`，`app/main.py` 会同时负责接口、模型调用和数据库细节，后面会越来越难读。

今天把数据库操作封装为：

```python
save_message("user", message)
save_message("assistant", reply)
```

可以这样理解：

```text
app/main.py
决定什么时候保存、保存什么业务数据

app/database.py
负责怎样连接 SQLite、执行 SQL、提交并关闭连接
```

这和前面把模型调用放进 `LLMService` 是同一个思路：路由负责组织流程，具体操作交给对应服务或模块。

---

# 三、在 `app/database.py` 中添加 `save_message()`

打开：

```text
app/database.py
```

在文件顶部增加导入：

```python
from typing import Literal
```

Literal（字面上的，刻板的）：表示这个参数只能取我明确写出来的几个固定值。

然后在 `init_database()` 后面添加：

```python
def save_message(
    role: Literal["user", "assistant"],
    content: str,
) -> None:
    """保存一条用户或模型消息。"""
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO messages (role, content)
            VALUES (?, ?)
            """,
            (role, content),
        )
        connection.commit()
    finally:
        connection.close()
```

今天新增的核心仍然是 Day 8 已练习过的 SQL：

```sql
INSERT INTO messages (role, content)
VALUES (?, ?)
```

`id` 和 `created_at` 不需要由 Python 手动填写：

```text
id
由 AUTOINCREMENT 自动生成

created_at
由 DEFAULT CURRENT_TIMESTAMP 自动生成
```

参数值继续单独传入：

```python
(role, content)
```

不要使用 f-string 把聊天内容直接拼进 SQL。用户问题可能包含单引号等字符，参数化查询能正确处理，也能避免 SQL 注入。

这里使用的：

```python
Literal["user", "assistant"]
```

和 Day 7 的 `Message.role` 一样，表示代码中的角色只应该是这两个值。数据库表中的 `CHECK` 约束还会再检查一次实际写入的数据。

---

# 四、先单独测试 `save_message()`

今天先把数据库函数单独验证成功，再修改 `/chat`。在项目根目录激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

执行：

```powershell
python -c "from app.database import init_database, save_message; init_database(); save_message('user', 'save_message 函数测试')"
```

命令正常结束且没有输出是正常的。再查询数据库：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); rows = connection.execute('SELECT id, role, content, created_at FROM messages ORDER BY id ASC').fetchall(); [print(dict(row)) for row in rows]; connection.close()"
```

结果中应该出现类似：

```text
{'id': 2, 'role': 'user', 'content': 'save_message 函数测试', 'created_at': '2026-08-09 13:10:00'}
```

实际 `id` 和时间可能不同，因为 Day 8 的测试消息仍然保存在数据库中。

如果出现：

```text
no such table: messages
```

说明数据库还没有初始化。确认测试命令先执行了 `init_database()`，并检查建表 SQL 是否仍然完整。

如果出现：

```text
CHECK constraint failed
```

先检查传入的角色是否准确写成：

```text
user
assistant
```

不要写成 `system`、`bot` 或中文角色名。

---

# 五、让 FastAPI 启动时确认数据库表存在

打开：

```text
app/main.py
```

在现有导入附近增加：

```python
from app.database import init_database, save_message
```

当前代码中已经有：

```python
llm_service = LLMService()
```

在它的下一行调用：

```python
init_database()
```

这一小段最终是：

```python
llm_service = LLMService()
init_database()
```

Uvicorn 导入 `app.main` 时会执行 `init_database()`。由于建表 SQL 使用了：

```sql
CREATE TABLE IF NOT EXISTS messages
```

所以第一次启动会创建表，后面重复启动只会确认表已经存在，不会清空原有消息。

今天先使用这种直观方式理解应用启动和数据库初始化。以后项目结构变复杂时，可以再把初始化移动到 FastAPI 的 lifespan 启动逻辑中；今天不要提前引入这个新概念。

---

# 六、在 `/chat` 中保存两条消息

找到当前 `/chat` 路由中的核心部分：

```python
response.headers["Content-Type"] = "application/json; charset=utf-8"
reply = llm_service.chat(message)

return ChatResponse(reply=reply)
```

修改为：

```python
response.headers["Content-Type"] = "application/json; charset=utf-8"

save_message("user", message)
reply = llm_service.chat(message)
save_message("assistant", reply)

return ChatResponse(reply=reply)
```

修改后，完整路由的关键结构应该是：

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    response: Response,
) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message 不能只包含空格",
        )

    response.headers["Content-Type"] = "application/json; charset=utf-8"

    save_message("user", message)
    reply = llm_service.chat(message)
    save_message("assistant", reply)

    return ChatResponse(reply=reply)
```

注意保存顺序：

```text
先保存 user
再调用模型
最后保存 assistant
```

这样数据库中的 `id` 顺序会和真实对话顺序一致。

如果 DeepSeek 请求失败，当前版本会保留已经保存的用户问题，但不会产生 `assistant` 消息。这能帮助你知道用户曾经发起过请求。完整的网络异常处理会在月计划后面单独学习，今天不要加入复杂事务或大段 `try/except`。

---

# 七、启动接口并发送一次真实请求

打开终端 A，用它运行 FastAPI：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

保持终端 A 不要关闭。再打开终端 B，创建请求体：

```powershell
$body = @{
    message = "请用一句话解释向量数据库"
} | ConvertTo-Json
```

PowerShell 中 `$` 表示变量。@{ ... }这是 PowerShell 的 **哈希表（Hashtable）**，你暂时可以把它理解成 Python 的字典：
{
    "message": "请用一句话解释向量数据库"
}

调用本地接口：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

把 `$body` 里的 JSON 数据发送到你 FastAPI 的 `/chat` 接口。

预期得到一段真实模型回答，例如：

```text
reply
-----
向量数据库是一种专门存储并检索高维向量、用于寻找语义相似内容的数据库。
```

回答文字不需要和示例完全相同。确认成功一次即可，不要为了测试反复消耗 API 额度。

如果 `/chat` 返回 500，先看终端 A 的错误摘要：

```text
no such table
→ 检查 init_database() 是否在应用启动时执行

database is locked
→ 检查是否有其他程序仍然占用 chat.db

401、403、404 或超时
→ 属于模型 API 问题，检查配置或网络，但不要显示 API Key
```

---

# 八、查询并确认两条聊天消息

保持终端 A 运行，在终端 B 执行：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); rows = connection.execute('SELECT id, role, content, created_at FROM messages ORDER BY id ASC').fetchall(); [print(dict(row)) for row in rows]; connection.close()"
```

数据库中原有的测试数据仍然存在。在结果最后应该新增两行，顺序类似：

```text
{'id': 3, 'role': 'user', 'content': '请用一句话解释向量数据库', ...}
{'id': 4, 'role': 'assistant', 'content': '向量数据库是一种……', ...}
```

重点确认：

```text
用户问题的 role 是 user
模型回答的 role 是 assistant
user 的 id 小于紧随其后的 assistant id
两条消息都有自动生成的 created_at
```

这说明真实链路已经变成：

```text
POST /chat
→ 校验 message
→ INSERT user 消息
→ DeepSeek 生成回答
→ INSERT assistant 消息
→ 返回 reply
```

---

# 九、确认无效请求不会写入数据库

先查询当前消息数量：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); row = connection.execute('SELECT COUNT(*) AS count FROM messages').fetchone(); print(dict(row)); connection.close()"
```

记住输出中的数字。然后发送只有空格的消息：

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

预期状态码：

```text
400
```

再次运行刚才的 `COUNT(*)` 查询，消息数量应该保持不变。

原因是代码先执行：

```python
message = request.message.strip()

if not message:
    raise HTTPException(...)
```

只有校验通过以后才会执行 `save_message()`。因此无效请求不会写入数据库，也不会调用 DeepSeek。

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
database.py 只新增了 save_message()
main.py 只新增数据库导入、初始化和两次保存调用
data/chat.db 仍然被 .gitignore 忽略
.env 没有出现在 Git 状态中
```

所有测试成功后，添加今天的代码和学习计划：

```powershell
git add app/database.py app/main.py docs/Day9.md
git status
```

确认暂存区正确后提交：

```powershell
git commit -m "feat: save chat messages to SQLite"
```

查看最新提交：

```powershell
git log -1 --oneline
```

最后不看代码，尝试讲清楚为什么要先保存 `user`、再调用模型、最后保存 `assistant`，以及 `save_message()` 为什么应该放在 `database.py` 而不是直接把 SQL 全部写进路由。

---

# Day 9 完成标准

```text
[ ] 能解释为什么要把 INSERT 封装成 save_message()
[ ] 已在 app/database.py 中实现 save_message(role, content)
[ ] FastAPI 启动时会执行 init_database()
[ ] POST /chat 会先保存 user 消息，再保存 assistant 消息
[ ] 一次成功请求会在 messages 表中新增两条顺序正确的记录
[ ] 纯空格请求返回 400，且不会增加消息数量
[ ] data/chat.db 和 .env 都没有进入 Git 暂存区
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
