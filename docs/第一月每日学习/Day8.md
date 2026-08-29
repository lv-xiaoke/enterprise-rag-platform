# Day 8：用 SQLite 创建消息表并练习基本 SQL

Day 7 已经在 `app/models.py` 中定义了一条聊天消息的四个字段：`id`、`role`、`content`、`created_at`。不过 Pydantic 只负责描述和校验 Python 对象，程序结束以后，对象仍然会消失。

今天开始学习 SQLite：在 `app/database.py` 中创建本地数据库和 `messages` 表，再亲手执行一次 `INSERT`、`SELECT` 和 `ORDER BY`。今天只学习数据库的最小基础，不把它接入 `/chat`，下一次再让聊天接口自动保存用户问题和模型回答。

---

# 一、先复习 Pydantic 模型和数据库的区别

打开项目：

```powershell
cd D:\my_develop\A_work_program\260804_mini-rag-backend
code .
```

查看 `app/models.py`：

```python
class Message(BaseModel):
    id: int = Field(gt=0)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)
    created_at: datetime
```

先尝试解释：这段代码为什么不能让消息在程序重启后继续存在？

可以这样理解：

```text
Pydantic Message
像一张规定填写格式的表单，负责检查数据是否合法

SQLite messages 表
像一个保存表单的文件柜，负责把数据长期存到磁盘
```

今天要让数据库表和 Pydantic 模型保持同样的四个字段：

```text
Python / Pydantic        SQLite
id: int                  id INTEGER
role: str                role TEXT
content: str             content TEXT
created_at: datetime     created_at TEXT
```

SQLite 没有单独的 `datetime` 类型，所以今天把时间保存成文本。只要使用统一的时间格式，后面仍然可以排序和转换。

---

# 二、理解 SQLite 是什么

SQLite 是一个轻量级关系型数据库。它不需要单独启动数据库服务器，整个数据库可以保存在一个本地文件中。

当前项目会使用：

```text
data/chat.db
```

可以把它理解成：

```text
chat.db
└── messages 表
    ├── 第 1 行消息
    ├── 第 2 行消息
    └── ……
```

它和普通文本文件的区别是：SQLite 可以使用 SQL 按规则插入、查询和排序数据。

Python 自带 `sqlite3` 标准库，因此今天不需要执行 `pip install`，也不需要修改 `requirements.txt`。先激活虚拟环境并确认它可用：

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

预期会输出一个 SQLite 版本号，例如：

```text
3.50.4
```

实际版本可能不同，只要命令没有报错即可。

---

# 三、创建 `app/database.py`

在项目根目录执行：

```powershell
New-Item app\database.py -ItemType File
```

如果你已经在 VS Code 中手动创建了文件，就不要重复执行命令。

在 `app/database.py` 中写入：

```python
import sqlite3

from app.config import BASE_DIR


DATABASE_PATH = BASE_DIR / "data" / "chat.db"


def get_connection() -> sqlite3.Connection:
    """创建并返回一个 SQLite 数据库连接。"""
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    """创建项目需要的数据库表。"""
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()
```

先不要急着复制完就跳到测试，逐段理解下面几个部分。

---

# 四、理解连接和数据库路径

## 1. `DATABASE_PATH`

```python
DATABASE_PATH = BASE_DIR / "data" / "chat.db"
```

`BASE_DIR` 已经在 `app/config.py` 中表示项目根目录。这行代码会得到：

```text
项目根目录/data/chat.db
```

这样无论从哪个终端位置启动项目，数据库路径都不会依赖当前工作目录。

## 2. 自动创建 `data` 目录

```python
DATABASE_PATH.parent.mkdir(exist_ok=True)
```

`DATABASE_PATH.parent` 是 `data` 目录。`exist_ok=True` 表示目录已经存在时不要报错。

## 3. 创建连接

```python
connection = sqlite3.connect(DATABASE_PATH)
```

连接可以理解成 Python 和 SQLite 之间的一条通道。后面的建表、插入和查询都通过它完成。

如果 `chat.db` 不存在，SQLite 会在第一次连接时创建它；如果已经存在，就打开原来的数据库。

## 4. 让查询结果带字段名

```python
connection.row_factory = sqlite3.Row
```

设置以后，查询结果不仅能按位置读取，也可以转换成类似字典的形式：

```python
dict(row)
```

这会让以后构造 `/history` 的 JSON 更方便。

---

# 五、理解 `CREATE TABLE`

今天最重要的 SQL 是：

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

逐项理解：

```text
CREATE TABLE
创建一张新表

IF NOT EXISTS
如果 messages 已经存在，就不要重复创建或报错

PRIMARY KEY
id 是每一行数据的唯一标识

AUTOINCREMENT
插入消息时不需要手动填写 id，SQLite 会依次生成 1、2、3……

NOT NULL
这个字段不能缺少值

CHECK
role 只能是 user 或 assistant

DEFAULT CURRENT_TIMESTAMP
没有手动提供 created_at 时，由 SQLite 写入当前 UTC 时间
```

`connection.commit()` 表示确认并保存这次数据库修改。可以把它理解成文档编辑完成后的“保存”。如果只执行 SQL 却不提交，修改可能不会真正写入数据库文件。

`finally` 中的 `connection.close()` 保证无论建表成功还是失败，最后都会关闭连接，避免数据库连接一直占用文件。

---

# 六、初始化数据库并检查表结构

在项目根目录执行：

```powershell
python -c "from app.database import DATABASE_PATH, init_database; init_database(); print(DATABASE_PATH); print(DATABASE_PATH.exists())"
```

预期输出类似：

```text
D:\my_develop\A_work_program\260804_mini-rag-backend\data\chat.db
True
```

这说明数据库文件已经创建。

再查看 `messages` 表的字段：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); rows = connection.execute('PRAGMA table_info(messages)').fetchall(); [print(dict(row)) for row in rows]; connection.close()"
```

##### `PRAGMA table_info(messages)` 是什么？

这是 SQLite 提供的特殊命令。
它的意思是：

> 查看 `messages` 这张表的结构。

注意，它不是查看：

```
messages 表里面存了哪些聊天消息
```

而是查看：

```
messages 表有哪些列
每一列叫什么
每一列是什么类型
是不是主键
能不能为 NULL
```

##### `.fetchall()` 是什么？

```
.fetchall()
```

意思是：

> 把查询得到的所有结果全部取出来。


输出中应该能找到四个字段：

```text
id
role
content
created_at
```

如果出现：

```text
ModuleNotFoundError: No module named 'app'
```

先执行 `pwd`，确认当前目录是包含 `app` 文件夹的项目根目录。

如果出现：

```text
no such table: messages
```

说明还没有成功执行 `init_database()`。重新检查 `CREATE TABLE` 的拼写和括号，再运行初始化命令。

---

# 七、练习 `INSERT`、`SELECT` 和 `ORDER BY`

现在插入一条测试消息，再把表中的消息查询出来：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); connection.execute('INSERT INTO messages (role, content) VALUES (?, ?)', ('user', 'SQLite 测试消息')); connection.commit(); rows = connection.execute('SELECT id, role, content, created_at FROM messages ORDER BY id ASC').fetchall(); [print(dict(row)) for row in rows]; connection.close()"
```

预期输出类似：

```text
{'id': 1, 'role': 'user', 'content': 'SQLite 测试消息', 'created_at': '2026-08-09 12:30:00'}
```

实际时间和 `id` 可能不同。拆开理解这两条 SQL。

## `INSERT`

```sql
INSERT INTO messages (role, content)
VALUES (?, ?)
```

表示向 `messages` 表插入一行，只填写 `role` 和 `content`。`id` 由 SQLite 自动生成，`created_at` 使用默认时间。

参数值单独写成：

```python
("user", "SQLite 测试消息")
```

SQL 中的两个 `?` 会依次接收这两个值。不要使用 f-string 直接拼接用户输入；参数化写法可以正确处理引号，也能降低 SQL 注入风险。

## `SELECT`

```sql
SELECT id, role, content, created_at
FROM messages
```

表示从 `messages` 表查询四个字段。

## `ORDER BY`

```sql
ORDER BY id ASC
```

表示按 `id` 从小到大排列：

```text
ASC     升序，小到大
DESC    降序，大到小
```

聊天历史需要从较早的消息排到较新的消息，因此当前使用 `ASC`。

---

# 八、验证消息确实保存在磁盘中

上一条命令已经结束，原来的 Python 进程也已经退出。现在使用一个新的 Python 进程再次查询：

```powershell
python -c "from app.database import get_connection; connection = get_connection(); rows = connection.execute('SELECT id, role, content, created_at FROM messages ORDER BY id ASC').fetchall(); [print(dict(row)) for row in rows]; connection.close()"
```

如果仍然能够看到刚才的测试消息，就说明数据保存在 `data/chat.db` 中，而不是只存在于上一个 Python 进程的内存里。

可以这样对比：

```text
Day 7 的 Message 对象
Python 进程结束后消失

Day 8 的 SQLite 数据
Python 进程结束后仍保存在 chat.db
```

如果遇到：

```text
database is locked
```

先检查是否有另一个 Python 命令或数据库工具仍然占用 `chat.db`。关闭它以后再重试，不要直接删除数据库文件。

---

# 九、忽略本地数据库文件

数据库中以后会保存本地聊天内容，它属于运行数据，不应该和源代码一起提交。打开 `.gitignore`，在末尾加入：

```gitignore

# SQLite 本地数据库
data/*.db
data/*.db-*
```

然后执行：

```powershell
git check-ignore -v data\chat.db
```

预期会显示它匹配了 `.gitignore` 中的 `data/*.db` 规则。

再执行：

```powershell
git status --short
```

应该看到：

```text
app/database.py
.gitignore
docs/Day8.md
```

不应该看到：

```text
data/chat.db
```

如果 `chat.db` 仍出现在 Git 状态中，先不要提交，检查忽略规则的路径和拼写。

---

# 十、检查改动并提交 Git

今天不修改 `/chat`，也不把测试消息接入接口。先检查：

```powershell
git diff -- app/database.py .gitignore
git status --short
```

新建的 `app/database.py` 可能不会出现在普通 `git diff` 中，可以直接用 VS Code 复查，或者执行：

```powershell
Get-Content app\database.py
```

确认数据库可以重复执行初始化、测试消息能在新进程中查询到，并且 `data/chat.db` 已被忽略后，添加代码和计划：

```powershell
git add app/database.py .gitignore docs/Day8.md
git status
```

确认暂存区没有 `data/chat.db` 和 `.env`，然后提交：

```powershell
git commit -m "feat: initialize SQLite message database"
```

查看最新提交：

```powershell
git log -1 --oneline
```

---

# Day 8 完成标准

```text
[ ] 能解释 SQLite 和 Pydantic Message 的职责区别
[ ] 能解释连接、执行 SQL、commit 和 close 的作用
[ ] 已创建 app/database.py 和 data/chat.db
[ ] messages 表包含 id、role、content、created_at 四个字段
[ ] 能解释 CREATE TABLE、INSERT、SELECT、ORDER BY 的作用
[ ] 已插入一条测试消息，并能在新的 Python 进程中再次查询到
[ ] data/chat.db 已被 .gitignore 忽略
[ ] 测试成功后完成 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
