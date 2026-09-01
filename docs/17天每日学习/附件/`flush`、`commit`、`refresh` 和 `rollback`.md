这部分是在讲 **SQLAlchemy Session 里四个最容易混淆的动作**：

```text
flush
commit
refresh
rollback
```

你可以先记最简版：

```text
flush    → 先把 SQL 发给数据库，但事务还没结束
commit   → 正式提交，事务完成
refresh  → 再从数据库读一次这个对象
rollback → 撤销当前还没提交的事务
```

拿你现在的 `Document + Chunk` 入库流程讲最容易理解。

假设你要创建一个文档：

```python
document = Document(
    knowledge_base_id=1,
    filename="员工手册.pdf",
)

session.add(document)
```

这时候只是把对象交给 SQLAlchemy 管理，概念上还没真正完成数据库写入。

---

## 1. `flush()`：把 SQL 真正发给数据库

执行：

```python
session.flush()
```

SQLAlchemy 可能向 PostgreSQL 发：

```sql
INSERT INTO documents (...)
VALUES (...);
```

这时候数据库已经执行了 INSERT，所以很多数据库生成的值可以拿到了，比如：

```python
document.id
```

可能从原来的：

```text
None
```

变成：

```text
12
```

这对你的 RAG 项目很重要，因为接下来 Chunk 需要知道：

```python
document_id=document.id
```

流程就是：

```text
创建 Document Python 对象
        ↓
session.add()
        ↓
flush()
        ↓
PostgreSQL 执行 INSERT
        ↓
拿到 document.id = 12
        ↓
创建 chunks，document_id = 12
```

但是非常重要：

> **flush 之后还没有 commit。**

所以：

```text
flush ≠ 永久保存
```

之后仍然可以：

```python
session.rollback()
```

把刚才的 Document 一起撤销。

---

# 2. `commit()`：正式提交整个事务

例如完整流程：

```python
document_repo.create(...)
chunk_repo.create_many(...)
document_repo.update_status(...)

session.commit()
```

意思是：

> 前面这批数据库修改全部成功，我正式确认。

可以理解成盖章：

```text
flush
→ “先执行，但还没最终确认”

commit
→ “确定了，正式生效”
```

例如：

```text
Document 创建 ✅
3 个 Chunk 创建 ✅
状态改成 ready ✅
        ↓
commit
```

这时候整个业务事务完成。

---

# 3. 为什么 Repository 只 `flush`，Service 最后 `commit`

这和你前面学的“事务所有权”正好串起来。

假设：

```text
DocumentRepository.create()
↓
自己 commit
```

然后：

```text
ChunkRepository.create_many()
↓
第 3 个 Chunk 失败
```

你就没办法把已经提交的 Document 撤销。

所以正确思路是：

```text
DocumentRepository
↓ flush

ChunkRepository
↓ flush

DocumentRepository.update_status
↓ flush

Service
↓
全部成功？
├── 是 → commit
└── 否 → rollback
```

这样才能保证：

```text
Document + Chunks

要么全部成功
要么全部失败
```

---

# 4. `refresh()`：重新从数据库读取对象

这个名字其实很好理解：

```text
refresh = 刷新
```

例如：

```python
session.flush()
session.refresh(document)
```

意思是：

> Document 已经写到数据库了，现在再去 PostgreSQL 查一遍，把数据库里的最新值重新装到这个 Python 对象里。

为什么需要这么做？

因为有些字段不是 Python 自己生成的，而是数据库生成的。

比如你的 `documents`：

```python
created_at
updated_at
```

可能使用：

```python
server_default=sa.text("now()")
```

也就是：

> 时间由 PostgreSQL 填。

Python 创建对象时可能是：

```text
document.created_at
→ None
```

数据库 INSERT 后：

```text
created_at
→ 2026-09-01 18:30:21+...
```

运行：

```python
session.refresh(document)
```

以后 Python 对象就能重新拿到数据库里的值。

所以：

```text
flush
↓
数据库写入

refresh
↓
把数据库最新结果重新读回来
```

---

## 一个简单例子

```python
document = Document(
    knowledge_base_id=1,
    filename="员工手册.pdf",
)

session.add(document)

session.flush()
session.refresh(document)

print(document.id)
print(document.created_at)
```

你可能得到：

```text
12
2026-09-01 18:30:21...
```

因此你那句话：

> 单对象再 `refresh` 以取得主键、时间戳和数据库更新后的值

大概就是这个意思。

严格来说，现代 PostgreSQL + SQLAlchemy 有时可以通过 `RETURNING` 在 flush 时直接拿到部分数据库生成值，所以并非所有字段都必须 refresh；但你现阶段把 `refresh` 理解成“确保返回对象和数据库最新状态一致”就够了。

---

# 5. 为什么批量 Chunk 不逐条 `refresh`

假设一个 PDF 被切成：

```text
500 个 Chunk
```

如果你对每个都：

```python
session.refresh(chunk)
```

就可能产生很多额外数据库查询：

```text
refresh chunk 1
→ SELECT

refresh chunk 2
→ SELECT

refresh chunk 3
→ SELECT

...

refresh chunk 500
→ SELECT
```

那就很浪费。

而你的 Chunk 批量写入以后，通常只需要：

```text
确定写入成功
```

并不马上需要：

```text
每一个 Chunk 的 created_at
每一个 Chunk 的数据库最新完整状态
```

所以：

```python
session.flush()
```

就够了。

这就是：

> “批量 Chunk 只 flush，避免逐条 refresh 的额外查询。”

---

# 6. `rollback()`：撤销尚未提交的事务

假设：

```text
创建 Document ✅
创建 Chunk 1 ✅
创建 Chunk 2 ✅
创建 Chunk 3 ❌
```

你应该：

```python
session.rollback()
```

结果：

```text
Document 撤销
Chunk 1 撤销
Chunk 2 撤销
Chunk 3 本来就失败

→ 整次事务恢复
```

所以：

```text
rollback
```

就是：

> **这笔事务不算了，恢复到事务开始前。**

---

# 7. 为什么数据库约束通常会在 `flush()` 时发现？

这个很重要。

假设你的数据库规定：

```text
knowledge_bases.name UNIQUE
```

现在已经有：

```text
name = "公司制度"
```

你又：

```python
kb = KnowledgeBase(name="公司制度")
session.add(kb)
```

仅仅 `add()` 时：

```text
可能还不会报错
```

因为 SQL 还没真正发给 PostgreSQL。

执行：

```python
session.flush()
```

才真正执行：

```sql
INSERT INTO knowledge_bases ...
```

PostgreSQL 发现：

```text
UNIQUE 约束冲突
```

于是返回错误，SQLAlchemy 可能抛：

```python
IntegrityError
```

同样的还有：

```text
外键错误
CheckConstraint 错误
唯一约束错误
NOT NULL 错误
```

很多都是在：

```text
flush / commit
```

真正让数据库执行 SQL 时发现。

---

# 8. 为什么 `IntegrityError` 后必须 rollback？

假设：

```python
try:
    session.flush()
except IntegrityError:
    ...
```

flush 失败后，这个事务已经处于失败状态。

可以把 Session 想成：

```text
事务状态：FAILED
```

这时候不能假装什么都没发生，然后继续：

```python
session.add(...)
session.flush()
```

通常会继续报错。

必须：

```python
session.rollback()
```

告诉 SQLAlchemy / PostgreSQL：

> 刚才这笔失败的事务作废，我们恢复正常。

然后 Session 才重新进入可用状态。

典型写法：

```python
try:
    ...
    session.flush()
except IntegrityError:
    session.rollback()
    raise
```

所以你可以记：

```text
IntegrityError
      ↓
rollback
      ↓
Session 恢复
```

---

# 9. 为什么“flush 成功，另一个 Session 还是看不到”？

因为：

```text
flush 了
但还没 commit
```

假设：

```text
Session A
```

执行：

```python
session.add(document)
session.flush()
```

Session A 自己已经知道：

```text
document.id = 10
```

但是：

```text
Session B
```

通常还看不到这个新 Document。

因为事务还没有：

```python
commit()
```

可以理解成：

```text
Session A：
“我已经把修改写到我的事务里了，
但还没正式公开。”
```

等：

```python
session.commit()
```

之后：

```text
Session B
```

才通常能看到。

所以：

```text
flush
→ 当前事务内部可继续使用

commit
→ 对其他事务正式可见
```

---

# 10. 四个动作放在一次真实业务里看

假设你以后写文档入库 Service：

```python
session = SessionLocal()

try:
    document = document_repo.create(session, ...)
    # Repository 内部 flush + refresh

    chunks = chunk_repo.create_many(session, ...)
    # 只 flush

    document_repo.update_status(
        session,
        document,
        "ready",
    )
    # flush

    session.commit()

except Exception:
    session.rollback()
    raise

finally:
    session.close()
```

可以画成：

```text
创建 Document
      ↓
flush
      ↓
拿到 id / 检查数据库约束
      ↓
refresh
      ↓
拿到数据库最新值
      ↓
创建很多 Chunk
      ↓
flush
      ↓
更新 status
      ↓
flush
      ↓
所有业务成功
      ↓
commit
```

如果任何一个 `flush` 失败：

```text
IntegrityError / 其他异常
        ↓
rollback
        ↓
整笔事务撤销
```

---

## 最后记住这四句话

```text
flush
= “执行 SQL，但暂不提交”

commit
= “这批修改正式确认”

refresh
= “从数据库重新读对象最新状态”

rollback
= “这笔未提交事务全部撤销”
```

而放到你的项目架构里：

```text
Repository
→ add / query / flush / 必要时 refresh

Service
→ 编排多个 Repository

Service 最终
→ commit 或 rollback
```

面试时最关键的一句就是：

> 我在 Repository 中用 `flush` 提前执行 SQL、获得主键并暴露约束错误，但不结束事务；只有完整的 Document + Chunk 入库流程都成功后，Service 才统一 `commit`，任何一步失败则 `rollback`。