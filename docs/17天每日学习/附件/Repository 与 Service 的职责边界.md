这部分主要是在讲：**为什么项目里要同时有 Repository 和 Service，而不是把所有逻辑都塞进一个地方。**

你先记最核心的一句：

```text
Repository：负责“怎么读写数据库”
Service：负责“业务流程怎么串起来”
```

拿你这个 RAG 项目举例最容易理解。

假设用户上传一个 PDF，完整流程可能是：

```text
上传 PDF
   ↓
解析 PDF
   ↓
切 Chunk
   ↓
算 Embedding
   ↓
创建 Document
   ↓
创建多个 Chunk
   ↓
更新 Document 状态
   ↓
提交事务
```

这里面明显不是所有步骤都属于“数据库操作”。

比如：

```text
解析 PDF
切 Chunk
算 Embedding
```

这些都是业务流程的一部分，但不是数据库本身的职责。

所以它们应该由 Service 编排，而不是塞进 Repository。

---

## 1. Repository 到底负责什么

假设你有：

```text
KnowledgeBaseRepository
DocumentRepository
ChunkRepository
```

它们分别操作：

```text
knowledge_bases
documents
chunks
```

比如 `DocumentRepository` 可能提供：

```python
create(...)
get_by_id(...)
list_by_knowledge_base(...)
update_status(...)
```

它内部关心的是：

```text
要查询哪张表
WHERE 条件是什么
怎么创建 ORM 对象
怎么 flush
```

例如：

```python
def create(self, session, knowledge_base_id, filename):
    document = Document(
        knowledge_base_id=knowledge_base_id,
        filename=filename,
    )
    session.add(document)
    session.flush()
    return document
```

这个 Repository 不应该关心：

```text
PDF 怎么解析
Embedding 用哪个模型
文件上传接口是什么
失败后返回 HTTP 400 还是 500
```

它只负责：

> “你给我参数，我负责把 Document 正确写进数据库。”

---

## 2. Service 到底负责什么

Service 负责的是：

> **这一整件业务应该按什么顺序做。**

例如：

```python
def ingest_document(...):
    # 1. 创建 document
    # 2. 解析 PDF
    # 3. 切 chunk
    # 4. 算 embedding
    # 5. 写 chunks
    # 6. 更新状态
    # 7. commit / rollback
```

它会调用很多不同组件：

```text
PDFService
ChunkService
EmbeddingService
DocumentRepository
ChunkRepository
```

所以 Service 像“总导演”。

Repository 更像“专门负责数据库这一块的执行人员”。

---

## 3. 为什么结构是 `API → Service → Repository`

你现在可以这样理解：

```text
API
↓
接收 HTTP 请求

Service
↓
执行业务流程

Repository
↓
执行数据库读写

SQLAlchemy
↓
把 Python ORM 操作翻译成 SQL

PostgreSQL
↓
真正存数据
```

例如：

```text
POST /documents/upload
        ↓
API 收到 UploadFile
        ↓
DocumentService.ingest()
        ↓
DocumentRepository.create()
ChunkRepository.create_many()
        ↓
SQLAlchemy
        ↓
PostgreSQL
```

API 不需要知道：

```text
session.add()
session.flush()
select(Document)
```

这些 SQLAlchemy 细节。

这样以后即使数据库访问方式变化，API 层受到的影响也会小很多。

---

## 4. 为什么 PDF、Embedding、LLM 不应该放 Repository

假设你这么写：

```python
class DocumentRepository:
    def create_from_pdf(self, file):
        text = pdf_service.extract(file)
        chunks = split_text(text)
        vectors = embedding_service.embed(chunks)
        ...
```

这就开始变乱了。

因为 Repository 本来应该负责：

```text
数据怎么存
数据怎么查
```

结果现在它又负责：

```text
PDF 解析
Chunk 切分
Embedding
```

职责越来越多。

最后可能变成：

```text
DocumentRepository
├── 查数据库
├── 写数据库
├── 解析 PDF
├── 调 Embedding
├── 调 LLM
├── 处理异常
├── 决定状态
└── 甚至返回 HTTP 错误
```

这就是所谓的：

> Repository 变成“垃圾桶”。

以后维护会非常痛苦。

---

## 5. 为什么 Repository 不应该知道 HTTP 状态码

比如：

```python
raise HTTPException(status_code=404)
```

这种东西属于：

```text
HTTP / API 层
```

Repository 不应该知道：

```text
404
400
500
UploadFile
Request
Response
```

因为 Repository 的职责只是数据访问。

例如找不到 Document 时，Repository 可以：

```python
return None
```

然后 Service 决定：

```text
这是业务上的“不存在”
```

再由 API 层最终转成：

```text
HTTP 404
```

所以职责可以理解成：

```text
Repository：
“我没查到数据。”

Service：
“业务上这意味着文档不存在。”

API：
“那我要返回 HTTP 404。”
```

层次很清楚。

---

## 6. 为什么这会让代码更好测试

假设 Service 直接写 SQLAlchemy：

```python
def ingest_document(...):
    session.add(...)
    session.execute(...)
    ...
```

那么测试 Service 时，数据库逻辑和业务流程绑得很死。

而如果分开：

```text
Service
↓
Repository 接口
```

你可以测试：

```text
Service 是否：
先创建 Document
再切 Chunk
再写 Chunk
最后更新 ready
```

不用每次都关心底层 SQL。

Repository 自己再单独测试：

```text
create 是否真的插入
get_by_id 是否查对
update_status 是否正确更新
```

所以：

```text
Repository 测数据访问
Service 测业务流程
```

边界更清晰。

---

## 7. 放到你 Day 4 的入库流程里看

以后你可能会有：

```text
DocumentIngestionService
```

它负责：

```text
1. 创建 Document，状态 pending
2. 改成 processing
3. PDFService 解析
4. ChunkService 切分
5. EmbeddingService 算向量
6. ChunkRepository 批量写入
7. DocumentRepository 改成 ready
8. commit
```

如果中间失败：

```text
DocumentRepository
更新 failed
```

或者根据你的事务设计做相应 rollback / 状态处理。

这里的角色分工就是：

```text
Service：
决定 1 → 2 → 3 → 4 → 5 → 6 → 7 的顺序

Repository：
具体负责步骤 1、2、6、7 里的数据库操作
```

---

## 8. 这句话“稳定的数据访问动作集中到 Repository”是什么意思

所谓“稳定的数据访问动作”，比如：

```text
创建知识库
按 id 查文档
按 knowledge_base_id 查文档
创建 chunk
批量创建 chunk
修改 document status
```

这些动作通常会反复被不同业务使用。

所以集中到 Repository。

而“跨组件流程”例如：

```text
PDF
→ Chunk
→ Embedding
→ Database
```

这种就属于 Service。

---

## 9. 你可以记一张图

```text
API
│
│ “用户想上传 PDF”
↓
Service
│
│ “那我按业务流程：
│  创建文档 → 解析 → 切块 → 向量化 → 入库”
↓
Repository
│
│ “我负责 create / query / update”
↓
SQLAlchemy
↓
PostgreSQL
```

旁边还有：

```text
Service
├── PDFService
├── ChunkService
├── EmbeddingService
└── Repository
```

而不是：

```text
Repository
├── PDF
├── Embedding
├── LLM
├── HTTP
└── Database
```

---

面试时可以直接答：

> Repository 只封装稳定的数据访问动作，比如创建、查询、更新 ORM 对象；Service 负责跨组件的业务编排，比如文档入库时串联 PDF 解析、Chunk 切分、Embedding、状态流转和多个 Repository。这样 API 不直接依赖 SQLAlchemy，也避免 Repository 同时承担业务和 HTTP 职责。

最后压缩成一句最好记：

```text
Repository 管“数据库怎么操作”
Service 管“业务怎么完成”
API 管“请求怎么进、结果怎么出”
```