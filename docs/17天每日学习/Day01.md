# Day 1：接通 PostgreSQL 并建立可回滚的 Alembic 基线

今天会在保留现有 SQLite 聊天链路的前提下，为企业 RAG 新增 PostgreSQL/SQLAlchemy 连接层和可回滚的 pgvector 基线迁移，解决应用尚未真正使用持久化向量数据库的问题，并让你能够在面试中解释数据库驱动、ORM 与迁移工具的职责边界。

> 预计用时：60 分钟  
> 今日唯一核心产物：可连接 PostgreSQL、可执行 `upgrade → downgrade → upgrade` 的数据库基础设施  
> 对应主计划：Day 1

## 一、开始前先明确边界

### 今天完成什么

- 将 SQLAlchemy、psycopg、pgvector Python 包和 Alembic 声明为项目直接依赖，并记录实际安装版本。
- 在 `app/config.py` 中读取 PostgreSQL 配置，新建 `app/db.py` 负责 SQLAlchemy Engine、Session 工厂和连接探针。
- 保留 `app/database.py` 的 SQLite 聊天历史职责，不迁移 `/chat` 和 `/history`。
- 初始化 `migrations/`，用第一条迁移启用 PostgreSQL 的 `vector` 扩展，并真实验证升级、回滚、再次升级。

### 今天不做什么

- 不创建 `knowledge_bases`、`documents`、`chunks` 三张业务表；这是 Day 2。
- 不实现知识库或文档 CRUD；这是 Day 3。
- 不写入 PDF Chunk 和向量；这是 Day 4。
- 不改 `/upload`、`/rag/chat` 或现有 FAISS 检索链路。
- 不删除现有 `alembic/__pycache__/`；缓存文件不是可用迁移源码，也不能作为完成证据。

### 当前真实起点

- `[当前事实]` `app/database.py` 只使用标准库 `sqlite3`，为普通 `/chat` 和 `/history` 保存消息。
- `[当前事实]` `app/config.py` 当前只读取 LLM 配置，尚未提供 PostgreSQL 应用配置。
- `[当前事实]` `requirements.txt` 没有声明 SQLAlchemy、psycopg、pgvector 和 Alembic；当前 Python 3.11.7 环境中可导入 SQLAlchemy 2.0.25，但另外三个包未安装，环境里“碰巧已安装”不能替代项目依赖声明。
- `[当前事实]` `docker-compose.yml` 已使用 `pgvector/pgvector:pg16`，生成本计划时 PostgreSQL 容器状态为 `healthy`，端口映射为 `127.0.0.1:5432`。
- `[当前事实]` `.env.example` 已声明 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_PORT`；本次只确认了本地 `.env` 存在，没有读取或展示其中的值。
- `[当前事实]` 仓库没有 `alembic.ini` 和可读的 Alembic 源码，只有被忽略的 `.pyc` 缓存，因此 Day 1 尚未完成。
- `[当前事实]` 工作区已有多项与今天无关的文档删除、修改和未跟踪文件；必须保留，提交时只暂存今天的文件。
- `[待实测]` 新增依赖的实际安装版本、数据库连接、迁移升级/回滚结果都要由你运行后记录，不能根据当前容器健康状态提前判定通过。

下面这个版本更适合直接放进你的学习笔记里：先讲名字怎么来的，再讲它们分别干什么，最后联系到你当前项目。

## 二、核心知识铺垫

### 1. PostgreSQL、psycopg 与 SQLAlchemy

先不要急着记定义，先从三个名字开始理解。

#### 1.1 PostgreSQL：真正保存数据的数据库

**名字由来：**

`PostgreSQL` 可以拆成：

```text
Postgres + SQL
```

Postgres 最早来自一个叫 **POSTGRES** 的数据库项目，可以粗略理解成：

```text
Post + Ingres
```

也就是在早期 Ingres 数据库项目之后继续发展的新数据库。

后来 POSTGRES 加入了对 SQL 的支持，于是逐渐使用了：

```text
PostgreSQL
```

这个名字。

所以看到 PostgreSQL，可以先记成：

> **这是数据库本体。**

比如以后企业 RAG 项目里的：

```text
知识库
文档
Chunk
用户
权限
向量
```

最终都可以真正存进 PostgreSQL。

---

#### 1.2 psycopg：Python 和 PostgreSQL 之间的“连接线”

**名字由来：**

`psycopg` 是 PostgreSQL 的一个经典 Python 驱动项目名。

这个名字本身不需要强行拆词记忆，学习阶段直接把它和：

```text
Python → PostgreSQL
```

绑定起来即可。

它的作用可以理解成：

> **帮 Python 真正和 PostgreSQL 数据库说话。**

例如你的 Python 程序想执行：

```sql
SELECT * FROM documents;
```

最终需要有人把这个请求通过 PostgreSQL 支持的通信方式发送给数据库。

这个底层工作就是 psycopg 负责的。

所以可以记：

```text
Python
  ↓
psycopg
  ↓
PostgreSQL
```

一句话：

> **psycopg 是 Python 连接 PostgreSQL 的数据库驱动。**

---

#### 1.3 SQLAlchemy：让 Python 更方便地操作数据库

**名字由来：**

`SQLAlchemy` 可以拆成：

```text
SQL + Alchemy
```

其中：

```text
SQL
```

就是关系型数据库常用的查询语言。

`Alchemy` 的意思是：

```text
炼金术
```

因此可以把 SQLAlchemy 形象地理解成：

> **把比较底层的 SQL 数据库操作，“炼制”成更适合 Python 程序使用的形式。**

比如原本你可能需要直接写：

```sql
SELECT * FROM documents WHERE id = 1;
```

使用 SQLAlchemy 后，你可以更多地使用 Python 对象、类和方法组织这些数据库操作。

例如概念上可能写成：

```python
document = session.get(Document, 1)
```

因此 SQLAlchemy 不只是“连接数据库”。

它还帮我们处理很多数据库开发中常见的问题，例如：

```text
数据库连接
连接池
事务
Session
SQL 查询
ORM
```

所以可以先记：

> **SQLAlchemy 是 Python 中更高一层的数据库工具。**

---

### 1.4 ORM 是什么？

SQLAlchemy 经常会和一个词一起出现：

```text
ORM
```

ORM 全称：

```text
Object-Relational Mapping
```

中文叫：

```text
对象关系映射
```

先看数据库里的世界。

假设 PostgreSQL 中有一张表：

```text
documents

id | filename | status
1  | a.pdf    | ready
2  | b.pdf    | parsing
```

而 Python 更习惯使用：

```python
class Document:
    id = ...
    filename = ...
    status = ...
```

ORM 做的事情，就是建立两边的对应关系：

```text
Python                         PostgreSQL

Document 类         ↔          documents 表

document 对象       ↔          表中的一行

document.id         ↔          id 列

document.filename   ↔          filename 列
```

因此 ORM 可以简单理解成：

> **让我们用 Python 类和对象的方式表示、查询和修改数据库中的表和记录。**

需要注意：

> SQLAlchemy 不等于 ORM。

SQLAlchemy 是一个完整的数据库工具库，而 ORM 是它提供的一项重要能力。

---

### 1.5 三者到底是什么关系？

现在把三个东西串起来：

```text
FastAPI 业务代码
      ↓
SQLAlchemy
      ↓
psycopg
      ↓
PostgreSQL
```

可以把它们想象成：

```text
FastAPI
“我要查询一个 Document”
        ↓

SQLAlchemy
“我帮你组织数据库操作和 SQL”
        ↓

psycopg
“我负责真正把请求发送给 PostgreSQL”
        ↓

PostgreSQL
“我查询真实数据并返回结果”
```

所以一句话记忆：

> **PostgreSQL 是数据库本体，psycopg 是 Python 到 PostgreSQL 的连接驱动，SQLAlchemy 是我们在 Python 中操作数据库的高级工具层。**

---

### 1.6 为什么安装 SQLAlchemy 之后还要安装 psycopg？

这是一个很容易混淆的地方。

你可能会觉得：

```text
SQLAlchemy 都能操作数据库了，
为什么还需要 psycopg？
```

因为 SQLAlchemy 本身并不负责所有数据库的底层通信。

SQLAlchemy 可以支持：

```text
PostgreSQL
MySQL
SQLite
……
```

但是不同数据库的通信方式不同，因此通常还需要对应的数据库驱动。

例如：

```text
SQLAlchemy + psycopg
        ↓
PostgreSQL

SQLAlchemy + 某个 MySQL 驱动
        ↓
MySQL
```

因此：

```text
安装 SQLAlchemy
```

并不等于：

```text
已经可以连接 PostgreSQL
```

你还需要安装：

```text
psycopg
```

在本项目中使用：

```text
postgresql+psycopg://...
```

也是在明确告诉 SQLAlchemy：

```text
数据库：PostgreSQL
驱动：psycopg
```

---

## 2. Engine、Connection、Session 与连接探针

理解 SQLAlchemy 后，接下来需要理解三个经常出现的词：

```text
Engine
Connection
Session
```

---

### 2.1 Engine：数据库连接的总入口

**名字由来：**

`Engine` 本身就是：

```text
引擎
```

可以把它理解成：

> **驱动整个数据库访问系统工作的核心入口。**

例如：

```python
engine = create_engine(DATABASE_URL)
```

这里不是说：

> “现在已经成功连接数据库了。”

而更像是在创建：

> “以后应该通过什么地址、什么驱动、什么连接池规则去访问数据库。”

Engine 通常负责：

```text
保存数据库连接配置
管理连接池
提供数据库连接
作为应用访问数据库的统一入口
```

可以简单想象成：

```text
Engine
  │
  ├── Connection 1
  ├── Connection 2
  ├── Connection 3
  └── ...
```

因此一个应用通常创建一个可以长期复用的 Engine。

---

### 2.2 Connection：真正的一条数据库连接

Engine 本身更像“连接管理中心”。

真正执行 SQL 时，需要获得一条 Connection：

```python
with engine.connect() as connection:
    ...
```

可以理解成：

```text
Engine
  ↓
借给你一条 Connection
  ↓
Python 真正和 PostgreSQL 通信
```

所以：

> **Engine 管理连接，Connection 才是一条实际数据库连接。**

---

### 2.3 Session：一次业务操作的数据库工作单元

**名字由来：**

`Session` 就是：

```text
会话
```

在 SQLAlchemy ORM 中，可以把 Session 理解成：

> **一段业务操作期间，统一管理查询、修改和事务的工作空间。**

例如以后一个 API 请求可能要：

```text
查询 Document
      ↓
修改 Document 状态
      ↓
新增 Chunk
      ↓
提交事务
```

这些操作可以放在同一个 Session 中。

例如：

```python
with SessionLocal() as session:
    ...
```

完成后：

```text
commit
```

或者发生异常：

```text
rollback
```

最后：

```text
close
```

因此可以这样区分：

```text
Engine
数据库访问的长期基础设施

Session
一次业务操作期间使用的工作单元
```

以后 FastAPI 中通常是：

```text
应用启动
   ↓
创建一个 Engine

请求 A
   ↓
创建 Session A
   ↓
请求结束关闭

请求 B
   ↓
创建 Session B
   ↓
请求结束关闭
```

而不是让所有请求共用同一个长期 Session。

---

### 2.4 为什么 create_engine() 成功不代表 PostgreSQL 已经连接成功？

这是 SQLAlchemy 很重要的一个特点：

> **Engine 通常采用惰性连接。**

所谓“惰性”，就是：

```text
现在先创建配置
真正需要数据库的时候再连接
```

所以：

```python
engine = create_engine(DATABASE_URL)
```

成功只能说明：

```text
数据库 URL 基本可以被 SQLAlchemy 接受
Engine 对象创建成功
```

并不能证明：

```text
PostgreSQL 正在运行
密码正确
端口正确
数据库存在
网络可达
```

必须真正执行：

```python
with engine.connect() as connection:
    connection.execute(...)
```

才能验证完整链路。

---

### 2.5 连接探针是什么？

“探针”可以理解成：

> **做一个非常简单的测试，看看数据库到底能不能访问。**

最经典的是：

```sql
SELECT 1;
```

它几乎不涉及真实业务数据，只是在问 PostgreSQL：

```text
你能不能正常执行一条 SQL？
```

如果：

```text
FastAPI/Python
   ↓
SQLAlchemy
   ↓
psycopg
   ↓
PostgreSQL
   ↓
SELECT 1 成功
```

说明最基础的数据库链路已经打通。

因此：

```text
create_engine() 成功
```

和：

```text
SELECT 1 成功
```

完全不是一回事。

后者才真正证明数据库可达。

---

## 3. Alembic：给数据库结构做“版本管理”

### 3.1 Alembic 这个名字是什么？

`Alembic` 原本指一种传统的蒸馏器具。

它和：

```text
SQLAlchemy
```

名字里的“Alchemy（炼金术）”有一些风格上的呼应。

不过学习时不用纠结名字本身。

直接记：

> **Alembic 是 SQLAlchemy 生态中专门管理数据库结构变化的迁移工具。**

---

### 3.2 为什么数据库还需要“迁移”？

假设 Day 1 你的数据库只有：

```text
documents

id
filename
```

后来你发现还需要：

```text
status
created_at
```

最简单粗暴的方法当然可以直接进入 PostgreSQL 手动执行：

```sql
ALTER TABLE ...
```

但是随着项目越来越复杂，会出现问题：

```text
我到底什么时候加过这个字段？

队友的数据库有没有这个字段？

生产环境数据库现在是什么版本？

这次修改能不能撤回？
```

因此需要把每一次数据库结构变化都保存成代码文件。

例如：

```text
迁移 001
启用 vector 扩展

迁移 002
创建 knowledge_bases 表

迁移 003
创建 documents 表

迁移 004
给 documents 增加 status 字段
```

这就是：

```text
Database Migration
数据库迁移
```

Alembic 就是负责管理这些迁移历史的。

---

### 3.3 Alembic 和 Git 有什么相似？

可以做一个非常粗略的类比：

```text
Git
管理代码版本

Alembic
管理数据库结构版本
```

例如 Git 可以：

```text
查看历史
切换版本
回退代码
```

Alembic 也可以：

```text
upgrade
升级数据库结构

downgrade
回退数据库结构

history
查看迁移历史
```

不过它们不是同一个东西，只是帮助理解。

---

## 4. pgvector：让 PostgreSQL 能保存和检索向量

### 4.1 pgvector 这个名字怎么来的？

名字非常直接：

```text
pg + vector
```

其中：

```text
pg
≈ PostgreSQL

vector
= 向量
```

所以：

> **pgvector = PostgreSQL 的向量能力。**

---

### 4.2 为什么企业 RAG 项目需要 pgvector？

RAG 中，我们会把 Chunk 转换成 Embedding：

```text
文本 Chunk
    ↓
Embedding 模型
    ↓
[0.12, -0.38, 0.91, ...]
```

这个结果就是一个向量。

例如你的 Embedding 模型输出：

```text
512 维向量
```

那么数据库里以后可能需要：

```text
embedding vector(512)
```

普通 PostgreSQL 默认并不认识：

```text
vector(512)
```

这种字段类型。

安装并启用 pgvector 后，PostgreSQL 才获得：

```text
vector 类型
向量距离计算
向量相似度搜索
向量索引
```

等能力。

---

### 4.3 Python 的 pgvector 包和 PostgreSQL 的 vector 扩展不是一回事

这是非常容易混淆的一点。

你的 Python 环境中安装：

```text
pgvector==0.5.0
```

主要解决的是：

> **Python / SQLAlchemy 如何表示和操作 PostgreSQL 中的 vector 类型。**

但是 PostgreSQL 服务器本身还必须执行：

```sql
CREATE EXTENSION vector;
```

才能真正支持：

```text
vector
```

这种数据库类型。

因此这里实际上存在两层：

```text
Python
pgvector Python 包
      ↓
让 SQLAlchemy 理解 vector

PostgreSQL
vector 扩展
      ↓
让数据库真正支持 vector
```

可以记成：

> **Python 包负责“客户端会用”，PostgreSQL 扩展负责“数据库真的会”。**

两边缺一边都不完整。

---

## 5. 把今天所有概念串起来

最终可以得到这样一条完整链路：

```text
FastAPI
业务接口
   ↓

SQLAlchemy
负责 ORM、Engine、Session、事务等
   ↓

psycopg
负责 Python 和 PostgreSQL 的底层通信
   ↓

PostgreSQL
真正保存业务数据
   ↓

pgvector 扩展
让 PostgreSQL 进一步拥有向量能力
```

而数据库结构的变化，例如：

```text
启用 vector 扩展
创建 knowledge_bases 表
创建 documents 表
增加 embedding 字段
```

则交给：

```text
Alembic
```

进行版本化管理。

所以整个关系可以画成：

```text
                    Alembic
                       │
                       │ 管理数据库结构变化
                       ↓

FastAPI → SQLAlchemy → psycopg → PostgreSQL
                                     │
                                     ↓
                                  pgvector
                                  向量能力
```

---

## 6. 在当前项目中的具体职责

当前项目中不要把所有数据库代码一次性改掉。

现阶段可以理解为存在两条链路。

原来的聊天历史：

```text
/chat
/history
   ↓
app/database.py
   ↓
SQLite
```

目前继续保留，不动它。

新的企业 RAG 数据链路：

```text
知识库
文档
Chunk
向量
权限
   ↓
app/db.py
   ↓
SQLAlchemy
   ↓
psycopg
   ↓
PostgreSQL + pgvector
```

这样做的目的不是因为一个项目必须同时使用 SQLite 和 PostgreSQL，而是为了：

> **逐步改造项目，避免在学习 PostgreSQL 的同时顺手破坏原本已经可以工作的聊天接口。**

等新的数据库链路稳定后，再考虑后续是否需要进一步统一。

---

## 7. 今天最需要记住的 6 句话

1. **PostgreSQL 是真正保存数据的数据库。**
    
2. **psycopg 是 Python 连接 PostgreSQL 的底层驱动。**
    
3. **SQLAlchemy 是 Python 操作数据库的高级工具，ORM 是它提供的重要能力之一。**
    
4. **Engine 是数据库访问的长期入口，Session 是一次业务操作使用的工作单元。**
    
5. **Alembic 管理数据库结构的版本变化，可以升级，也可以回滚。**
    
6. **pgvector 让 PostgreSQL 获得存储和检索向量的能力，Python 的 pgvector 包和数据库里的 vector 扩展不是同一个东西。**
    

最后可以用这一张图复习：

```text
FastAPI
   ↓
SQLAlchemy
   │
   ├── Engine
   ├── Session
   └── ORM
   ↓
psycopg
   ↓
PostgreSQL
   ↓
pgvector

Alembic
   ↓
负责管理 PostgreSQL 的结构变化
```

这个版本我特意把 **“名字 → 是什么 → 为什么需要 → 在你项目里干什么”** 串成了一条线，后面你再看到 `Engine`、`Session`、`Alembic`、`vector` 时会更容易定位它们分别处在哪一层。

## 三、逐步完成今天的升级

### 步骤 1：安装并声明四个直接依赖（建议 8 分钟）

**为什么先做这一步**

后面的连接代码和迁移命令都依赖这些包；先固定实际版本，才能区分“代码错误”和“依赖根本不存在”。

**[你来完成]**

1. 在项目根目录确认当前解释器和已有声明：

```powershell
python --version
python -c "import sys; print(sys.executable)"
Get-Content -LiteralPath requirements.txt
```

2. 在你为本项目使用的 Python 环境中安装直接依赖：

```powershell
python -m pip install SQLAlchemy alembic pgvector "psycopg[binary]"
python -m pip show SQLAlchemy alembic pgvector psycopg psycopg-binary
python -c "import sqlalchemy, alembic, psycopg; from pgvector.sqlalchemy import Vector; print('database imports ok')"
```

3. 根据 `pip show` 的真实结果，在 `requirements.txt` 中只新增四条直接依赖并使用精确版本；不要用 `pip freeze > requirements.txt` 覆盖整份文件：

```text
SQLAlchemy==<实际版本>
alembic==<实际版本>
pgvector==<实际版本>
psycopg[binary]==<psycopg 的实际版本>
```

**[AI 辅助]**

如果 `psycopg` 与 `psycopg-binary` 的显示方式让你不确定，把 `pip show` 输出贴给 AI，让 AI 只判断应该如何声明直接依赖，不要让 AI 重写整个 `requirements.txt`。

**预期结果**

- 四类 import 均成功，并输出 `database imports ok`。
- `requirements.txt` 新增精确版本，但原有依赖没有被批量升级或重排。

**理解检查**

> 请用自己的话解释：为什么项目同时需要 SQLAlchemy 和 psycopg，而不是二选一？

### 步骤 2：建立独立的 PostgreSQL 连接层（建议 15 分钟）

**为什么现在做这一步**

先形成唯一、可复用的数据库入口，后续模型、迁移和数据访问层才能共享连接配置；同时隔离已有 SQLite 逻辑，控制今天的改动边界。

**[你来完成]**

1. 打开并对照：`app/config.py`、`app/database.py`、`.env.example`。不要执行 `Get-Content .env`，也不要把真实密码粘贴到终端输出或聊天中。
2. 在 `.env.example` 增加非秘密的主机示例，并在你本地 `.env` 中私下补同名变量：

```dotenv
POSTGRES_HOST=127.0.0.1
```

3. 在 `app/config.py` 中增加 PostgreSQL 配置读取，保持现有 LLM 配置不变：

```python
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
```

4. 新建 `app/db.py`，按下面的职责组织最小结构；使用 `URL.create(...)`，不要手工拼接带密码的 URL，也不要打印 Engine URL：

```python
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def build_database_url() -> URL:
    # [你来完成] 检查 DB、USER、PASSWORD 是否为空；缺失时只报告变量名。
    return URL.create(
        drivername="postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )


class Base(DeclarativeBase):
    pass


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def check_database_connection() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()
```

5. 不要修改 `app/main.py` 的启动流程，也不要删除或改名 `app/database.py`。

**预期结果**

- `app/db.py` 成为 PostgreSQL 的唯一基础设施入口。
- 模块不记录、不打印真实密码；错误只说明缺失的变量名。
- SQLite 与 PostgreSQL 的职责在文件层面清楚分开。

**理解检查**

> 请画出并口述：`.env → app/config.py → URL.create → SQLAlchemy Engine → psycopg → PostgreSQL`，其中每一段负责什么？

### 步骤 3：初始化 Alembic 并创建 pgvector 基线迁移（建议 17 分钟）

**为什么现在做这一步**

连接层可复用以后，迁移工具才能与应用使用同一数据库；第一条迁移只管理扩展，不提前侵入 Day 2 的表模型。

**[你来完成]**

1. 从项目根目录初始化新的 `migrations/` 目录；不要尝试复用只有缓存文件的 `alembic/`，也不要批量删除它：

```powershell
python -m alembic init migrations
```

2. 编辑 `migrations/env.py`：导入 `Base` 和 `engine`，把 `target_metadata` 指向 `Base.metadata`，在线迁移直接复用 Engine。关键形状如下：

```python
from app.db import Base, engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
```

3. 离线迁移分支也应从 `engine.url.render_as_string(hide_password=False)` 取得 URL，但不要 `print`；`alembic.ini` 中不要写真实账号和密码。
4. 创建第一条迁移：

```powershell
python -m alembic revision -m "enable vector extension"
```

5. 打开新生成的 `migrations/versions/<revision>_enable_vector_extension.py`，只实现这一项结构变化：

```python
from alembic import op


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
```

#### 有一个非常重要的点：`revision` 不等于执行迁移

你执行：

```
python -m alembic revision -m "enable vector extension"
```

只是：

> **生成迁移文件。**

还没有真的修改 PostgreSQL。

真正以后执行类似：

```
python -m alembic upgrade head
```

才相当于告诉 Alembic：

> 把数据库升级到最新版本。

这时候才会真正执行：

```
CREATE EXTENSION IF NOT EXISTS vector;
```

所以流程是：

```
revision
↓
创建“修改方案”

upgrade
↓
真正执行“修改方案”
```

这一点非常重要。


**预期结果**

- 根目录出现 `alembic.ini`，并生成可读的 `migrations/env.py` 和一条版本脚本。
- 迁移脚本不包含业务表、不包含密码，`upgrade` 与 `downgrade` 一一对应。

**理解检查**

> 为什么今天只迁移 `vector` 扩展，而不顺便创建三张业务表？

今天想验证的是：

```
SQLAlchemy 能不能连接 PostgreSQL
↓
Alembic 能不能使用同一个 Engine
↓
Alembic 能不能执行一次 upgrade
↓
Alembic 能不能执行一次 downgrade
```

而不是：

> 今天把整个数据库业务模型全部做完。

### 步骤 4：验证正常连接与升级路径（建议 8 分钟）

**为什么要真实运行**

容器 `healthy` 只说明 PostgreSQL 自检成功，不能证明 Python 驱动、应用配置和 Alembic 链路都正确。

**[你来完成]**

```powershell
docker compose ps
python -c "from app.db import check_database_connection; print(check_database_connection())"
python -m alembic upgrade head
python -m alembic current
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

**预期结果**

- `docker compose ps` 显示 PostgreSQL 为 `healthy`。
- 连接探针输出 `1`。
- `alembic current` 显示刚创建的 revision，并带有 `(head)`。
- `\dx vector` 能看到 `vector` 扩展；以上都属于预期，必须用你的真实输出确认后再记为通过。

**理解检查**

> 如果 Engine 创建成功但 `SELECT 1` 失败，能够排除什么，又还不能排除什么？

### 步骤 5：验证回滚和数据库不可用路径（建议 8 分钟）

**为什么不能只测成功路径**

Day 1 的核心承诺包括“可回滚”，同时应用面对错误端口时应明确失败而不是假装连接成功或泄露密码。

**[你来完成]**

1. 先回滚到基线之前，检查扩展消失，再恢复到 head：

```powershell
python -m alembic downgrade base
python -m alembic current
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
python -m alembic upgrade head
python -m alembic current
docker compose exec -T postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dx vector"'
```

2. 在一个独立 Python 进程里覆盖为错误端口，不修改 `.env`，确认探针失败：

```powershell
python -c "import os; os.environ['POSTGRES_PORT']='1'; from app.db import check_database_connection; check_database_connection()"
```

3. 最后再次运行正常探针，证明失败实验没有污染配置：

```powershell
python -c "from app.db import check_database_connection; print(check_database_connection())"
```

**预期结果**

- `downgrade base` 后 `vector` 不再列出；再次 `upgrade head` 后恢复。
- 错误端口命令在约 3 秒内以连接异常失败，不出现真实密码，也不能被吞掉后输出成功。
- 最后的正常探针重新输出 `1`。
- 如果 Day 2 以后已有依赖 `vector` 的列，不要再执行这条 `downgrade base`，更不要用 `CASCADE` 绕过依赖。

**理解检查**

> 正常探针、迁移 current、扩展查询三项证据分别证明了什么，为什么缺一项都不完整？

### 步骤 6：记录结果并准备提交（建议 4 分钟）

- 在本文件“实际完成”上方补充你真实执行的命令与结果摘要；失败就记录失败，不把“预期结果”写成“已经通过”。
- 检查今天的差异和全局状态：

```powershell
git diff -- requirements.txt .env.example app/config.py app/db.py alembic.ini migrations docs/17天每日学习/Day01.md
git status --short
```

- 确认 `.env`、密码、缓存文件和既有文档改动没有进入差异。
- 验收全部通过后，只暂存今天的文件：

```powershell
git add requirements.txt .env.example app/config.py app/db.py alembic.ini migrations docs/17天每日学习/Day01.md
git diff --cached
```

- 建议 commit message：`feat(db): bootstrap PostgreSQL migrations`
- 本计划不替你执行 `git commit`；请在检查暂存差异后自行提交。

## 四、面试高频问题

### 问题 1：为什么选择 SQLAlchemy + psycopg，而不是直接写 psycopg SQL？

- 考察点：抽象层职责、事务管理和工程可维护性。
- 回答要点：psycopg 是 PostgreSQL 驱动；SQLAlchemy 提供 Engine、连接池、Session、类型映射及与 Alembic 的元数据协作；复杂向量查询仍可在 SQLAlchemy 中使用明确 SQL 表达式，而不是完全放弃数据库能力。
- 结合本项目：指出 `app/db.py` 统一连接基础设施，Day 3 的数据访问层会使用 Session，Day 5 再表达 pgvector Top-K 查询。

### 问题 2：为什么创建 Engine 不能证明数据库已经连接？

- 考察点：惰性连接和连接池行为。
- 回答要点：`create_engine` 主要建立配置对象，通常到第一次 `connect()` 或执行 SQL 时才向数据库发起真实连接；因此需要 `SELECT 1` 探针。
- 结合本项目：说明今天的 `check_database_connection()` 如何从 Engine 经 psycopg 到 PostgreSQL，并返回标量 `1`。

### 问题 3：pgvector Python 包和 PostgreSQL 的 vector 扩展有什么区别？

- 考察点：客户端类型适配与服务器端能力的边界。
- 回答要点：Python 包让 SQLAlchemy 理解向量类型和操作；数据库扩展提供 `vector` 列类型、距离运算符和相关索引能力；只安装任一侧都不能形成完整链路。
- 结合本项目：今天安装 Python 包并通过 Alembic 启用扩展，Day 2 才真正建立 `vector(512)` 列。

### 问题 4：为什么数据库结构要使用 Alembic，而不是应用启动时执行 `CREATE TABLE IF NOT EXISTS`？

- 考察点：结构版本、可审计变更和回滚能力。
- 回答要点：启动时建表难以记录变更顺序、评审差异和可靠回滚；Alembic 为每次结构变化提供 revision、依赖关系以及 upgrade/downgrade。
- 结合本项目：第一条 revision 只管理 `vector` 扩展，并用 `upgrade → downgrade → upgrade` 留下真实证据。

## 五、今天结束后应当留下的证据

- 代码或配置：`requirements.txt`、`.env.example`、`app/config.py`、`app/db.py`、`alembic.ini`、`migrations/env.py`、`migrations/versions/<revision>_enable_vector_extension.py`。
- 运行证据：依赖版本、连接探针输出 `1`、Alembic 当前 revision、回滚前后 `\dx vector` 的差异、错误端口连接失败摘要。
- 学习记录：能口述 SQLite 与 PostgreSQL 两条链路，以及 `.env` 到数据库的完整连接数据流。
- Git：只包含 Day 1 产物的暂存差异；不包含 `.env`、缓存或原有无关文档改动。

# Day 1 完成标准

```text
[ ] 能解释 SQLAlchemy、psycopg、PostgreSQL 三者为什么缺一不可
[ ] 能解释 pgvector Python 包与数据库 vector 扩展的职责区别
[ ] requirements.txt 已按实际安装结果声明四个直接依赖的精确版本
[ ] app/db.py 已提供不泄露密码的 URL 构造、Engine、SessionLocal、Base 和连接探针
[ ] 能从 .env、配置模块、Engine、驱动讲到 PostgreSQL 的完整连接数据流
[ ] 正常连接探针真实输出 1，upgrade head 后能查询到 vector 扩展
[ ] downgrade base 后扩展消失，再次 upgrade head 后恢复且 current 位于 head
[ ] 错误端口验证在限定时间内明确失败，错误信息未泄露真实密码，随后正常连接恢复
[ ] git diff 中没有 .env、秘密、缓存或既有无关修改，验收后完成边界清晰的 Git commit
```

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
