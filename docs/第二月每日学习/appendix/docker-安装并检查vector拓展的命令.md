
```powershell
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"

docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```


这两条命令是在做一件非常重要的事情：

> **进入正在运行的 PostgreSQL 容器，使用 `rag_app` 用户连接 `enterprise_rag` 数据库，然后先安装/启用 pgvector，再检查它是否真的安装成功。**

可以先把它们记成：

```text
第一条：安装 vector 扩展
第二条：检查 vector 扩展
```

---

# 一、先看整体结构

第一条：

```bash
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

可以拆成：

```text
docker compose
    ↓
找到 Compose 项目

exec
    ↓
在正在运行的容器里执行命令

-T
    ↓
不分配终端

postgres
    ↓
目标服务

psql
    ↓
PostgreSQL 的命令行客户端

-U rag_app
    ↓
使用 rag_app 用户

-d enterprise_rag
    ↓
连接 enterprise_rag 数据库

-c "..."
    ↓
执行一条 SQL
```

所以整句话翻译成人话：

> **在 `postgres` 容器里，使用 `rag_app` 用户连接 `enterprise_rag` 数据库，然后执行一条 SQL，让 PostgreSQL 启用 pgvector。**

---

# 二、`docker compose exec` 是什么？

你之前已经知道：

```bash
docker compose up -d postgres
```

是：

> 启动 postgres 服务。

而：

```bash
docker compose exec postgres ...
```

可以理解成：

> **进入已经运行的 postgres 容器，在里面执行一条命令。**

例如：

```bash
docker compose exec postgres ls
```

就是：

> 在 postgres 容器里面执行 `ls`。

而你现在：

```bash
docker compose exec postgres psql ...
```

就是：

> 在 postgres 容器里面运行 PostgreSQL 的命令行工具 `psql`。

所以它不是：

```text
Windows → PostgreSQL
```

而是：

```text
Windows
   │
   │ docker compose exec
   ↓
postgres Container
   │
   ↓
psql
   │
   ↓
PostgreSQL
```

---

# 三、`-T` 是什么？

```bash
-T
```

表示：

> **不分配伪终端（TTY）。**

你现在执行的是一条非交互式命令：

```bash
psql ... -c "..."
```

你不是准备进去：

```bash
psql
```

然后手动输入 SQL。

而是直接告诉它：

> 执行这一条 SQL，执行完就结束。

所以：

```bash
-T
```

在这种场景下很常见。

你可以暂时把它理解成：

> **让 `docker compose exec` 适合这种一次性执行命令的场景。**

---

# 四、`postgres` 是什么？

这里：

```bash
docker compose exec -T postgres
```

这个：

```text
postgres
```

不是 PostgreSQL 软件名称本身，而是你 `docker-compose.yml` 中定义的：

```yaml
services:
  postgres:
```

所以 Compose 知道：

> 我要进入叫 `postgres` 的那个服务对应的容器。

你之前看到：

```text
SERVICE
postgres
```

就是这个。

---

# 五、`psql` 是什么？

这一部分：

```bash
psql
```

非常重要。

**psql = PostgreSQL Interactive Terminal**

你可以把它理解成：

> **PostgreSQL 的命令行客户端。**

它允许你：

```text
连接 PostgreSQL
      ↓
输入 SQL
      ↓
PostgreSQL 执行
      ↓
返回结果
```

例如：

```bash
psql -U rag_app -d enterprise_rag
```

进入以后，你就可以输入：

```sql
SELECT * FROM documents;
```

---

# 六、`-U rag_app`

```bash
-U rag_app
```

这里的：

```text
-U
```

表示：

> **指定 PostgreSQL 用户（User）。**

所以：

```bash
-U rag_app
```

就是：

> 使用 `rag_app` 用户登录 PostgreSQL。

这个 `rag_app` 就是你 `.env` 里面配置的：

```dotenv
POSTGRES_USER=rag_app
```

所以它们之间的关系是：

```text
.env
 │
 └── POSTGRES_USER=rag_app
          ↓
Docker 创建 PostgreSQL 用户
          ↓
rag_app
          ↓
psql -U rag_app
```

---

# 七、`-d enterprise_rag`

```bash
-d enterprise_rag
```

这里：

```text
-d
```

表示：

> **指定要连接的数据库（database）。**

所以：

```bash
-d enterprise_rag
```

就是：

> 连接名为 `enterprise_rag` 的数据库。

它对应：

```dotenv
POSTGRES_DB=enterprise_rag
```

所以现在：

```text
用户：
rag_app

数据库：
enterprise_rag
```

可以理解成：

```text
PostgreSQL
│
└── enterprise_rag
       │
       └── rag_app 用户操作
```

---

# 八、最重要的：`-c`

第一条最后：

```bash
-c "CREATE EXTENSION IF NOT EXISTS vector;"
```

`-c` 的意思是：

> **直接执行后面这一条 SQL 命令。**

比如：

```bash
psql -U rag_app -d enterprise_rag -c "SELECT 1;"
```

就是：

```text
连接数据库
   ↓
执行 SELECT 1
   ↓
返回结果
   ↓
退出
```

所以你不需要进入 psql 交互界面。

---

# 九、`CREATE EXTENSION IF NOT EXISTS vector`

这是整个第一条命令真正干的事情。

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

意思：

> **如果 `vector` 扩展还不存在，就创建/启用它。**

这里的：

```text
vector
```

就是：

> **pgvector 提供的 PostgreSQL 扩展名称。**

注意一个非常重要的区别：

```text
pgvector
```

是这个项目/扩展的名称。

而 PostgreSQL 中执行：

```sql
CREATE EXTENSION vector;
```

使用的是扩展名：

```text
vector
```

---

# 十、为什么要写 `IF NOT EXISTS`？

如果你写：

```sql
CREATE EXTENSION vector;
# 给 PostgreSQL 安装并启用 `vector` 这个扩展。PostgreSQL 本身主要是普通数据库,它原本不认识向量这种数据类型。
```



而 `vector` 已经存在，就可能报：

```text
extension "vector" already exists
```

但是：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

意思是：

> 如果已经有了，就什么都不用做。

所以可以反复执行。

第一次：

```text
vector 不存在
   ↓
创建 vector
```

第二次：

```text
vector 已经存在
   ↓
跳过
```

不会因为重复执行而报错。

---

# 十一、第二条命令是在干什么？

第二条：

```bash
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

和第一条前半部分完全一样：

```text
docker compose exec -T postgres psql
-U rag_app
-d enterprise_rag
```

不同的是最后：

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

这次不是安装，而是：

> **查询 PostgreSQL 当前已经安装的扩展，看看 `vector` 在不在。**

---

# 十二、`pg_extension` 是什么？

PostgreSQL 自己有一些系统表。

其中：

```text
pg_extension
```

可以理解成：

> **“PostgreSQL 当前安装了哪些扩展”的登记表。**

里面可能有：

```text
plpgsql
vector
...
```

所以：

```sql
SELECT *
FROM pg_extension;
```

相当于：

> 把 PostgreSQL 已安装的扩展列出来。

---

# 十三、`SELECT extname, extversion`

```sql
SELECT extname, extversion
```

表示：

> 我要查看两个字段。

### `extname`

```text
extname
```

表示：

> 扩展名称。

比如：

```text
vector
```

### `extversion`

```text
extversion
```

表示：

> 扩展版本。

所以查询结果可能是：

```text
 extname | extversion
---------+-----------
 vector  | 0.8.0
```

具体版本取决于你使用的镜像版本。

---

# 十四、`WHERE extname = 'vector'`

```sql
WHERE extname = 'vector';
```

意思：

> **只看名称叫 `vector` 的扩展。**

如果不写：

```sql
WHERE extname = 'vector'
```

那么可能看到：

```text
plpgsql
vector
其他扩展
```

现在加上：

```sql
WHERE extname = 'vector'
```

就是：

```text
只找 vector
```

---

# 十五、所以两条命令实际上是一套“安装 + 验证”

你可以把它们记成：

```text
第一条
       ↓
CREATE EXTENSION
       ↓
“把 vector 扩展启用起来”
       ↓
第二条
       ↓
SELECT
       ↓
“检查 vector 到底在不在”
```

完整流程：

```text
pgvector/pgvector:pg16 镜像
             ↓
       PostgreSQL 启动
             ↓
       docker compose exec
             ↓
             psql
             ↓
     CREATE EXTENSION vector
             ↓
       vector 扩展启用
             ↓
       SELECT pg_extension
             ↓
       检查 vector
             ↓
          成功 ✅
```

---

# 十六、你执行后应该看到什么？

第一条：

```bash
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

如果成功，可能看到：

```text
CREATE EXTENSION
```

第二条：

```bash
docker compose exec -T postgres psql -U rag_app -d enterprise_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

可能看到：

```text
 extname | extversion
---------+------------
 vector  | 0.x.x
(1 row)
```

这就证明：

```text
PostgreSQL
    ↓
vector 扩展
    ↓
已经存在
```

---

# 十七、但是注意：到这里仍然没有“切换 RAG 检索”

这正好对应你前面学的那句话。

你现在完成的是：

```text
① Docker PostgreSQL 启动       ✅
② PostgreSQL healthy          ✅
③ pgvector 扩展可用            ✅
```

但是还没有：

```text
④ 把 FAISS 数据迁移到 PostgreSQL
⑤ 创建 vector 列
⑥ 把 embedding 存进 PostgreSQL
⑦ 修改 RAG 检索代码
⑧ 使用 pgvector 做 Top-K 检索
```

所以现在的状态可以画成：

```text
                    RAG
                     │
                     ↓
                 Embedding
                     │
                     ↓
                   FAISS
                     │
                     ↓
                  Top-K
```

同时你已经准备好了另一个未来可以使用的检索后端：

```text
                PostgreSQL
                     │
                     ↓
                  pgvector
                     │
                     ↓
              【已经安装好了】
```

**但是 RAG 还没有使用它。**

这就是这两条命令真正想让你理解的东西：

> **`CREATE EXTENSION vector` 是“给 PostgreSQL 装上向量能力”；`SELECT ... FROM pg_extension` 是“证明这个能力确实已经存在”。但真正让 RAG 使用 pgvector，还需要后面的数据迁移、表设计和检索代码改造。**