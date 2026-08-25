# Day 27：Python 与后端面试回答

## 1. list 和 tuple 有什么区别？

`list` 和 `tuple` 都是有顺序的容器，主要区别是 `list` 可以增删或修改元素，而 `tuple` 创建后不能替换其中的元素。项目上传 PDF 时，需要不断向 `chunks` 中加入文本块，所以使用 `list`；`RAGService.answer()` 返回固定的“回答和检索结果”两个值，所以使用 `tuple`。需要注意，tuple 不可变只表示它保存的元素引用不能替换，如果里面放了 list，这个 list 自身仍然可以修改。

## 2. dict 的基本原理和使用场景是什么？

`dict` 用来保存键和值的对应关系，底层核心思路是哈希表，因此查找、插入和删除在平均情况下都是 `O(1)`。项目中 LLM 请求的 `headers` 和 `payload` 都使用 dict，因为可以通过 `"model"`、`"messages"` 等键快速找到对应数据。dict 的键必须是可哈希对象，例如字符串和数字可以作为键，而 list 通常不可以。

## 3. 深拷贝和浅拷贝有什么区别？

浅拷贝只创建一个新的外层容器，内部嵌套的可变对象仍与原数据共享；深拷贝则会递归复制内部对象。比如一个 dict 中包含 list，浅拷贝后修改这个内部 list，原 dict 也会受影响，而深拷贝通常不会。数据没有嵌套可变对象时，浅拷贝往往就够用；深拷贝更独立，但也会占用更多时间和内存。

## 4. generator 是什么？

生成器不会一次把全部结果放进内存，而是在迭代时按需产生一个值，可以用 `yield` 或生成器表达式创建。项目上传 PDF 时，`DocumentChunk(...) for chunk_text in page_chunks` 就是生成器表达式，`chunks.extend()` 会逐个读取它产生的对象。生成器适合处理大量或流式数据，但通常只能按顺序消费一次；它的惰性计算也不等于异步执行。

## 5. decorator 是什么？

装饰器接收一个函数，并在不直接修改函数主体的情况下增加功能，`@decorator` 可以理解为 `func = decorator(func)` 的简写。项目中的 `@app.get()` 和 `@app.post()` 会把下面的函数注册成 FastAPI 路由。自定义装饰器包装函数时，通常使用 `functools.wraps` 保留原函数的名称和说明等信息。

## 6. async 和 await 是什么？

`async def` 用来定义协程函数，调用它会得到协程对象；`await` 用来等待异步操作完成，并在等待期间把执行机会让给事件循环中的其他任务。项目的 `LLMService.chat()` 使用 `await client.post()` 等待 LLM API 返回，这样等待网络时不必一直占住当前请求。异步适合网络和文件等 I/O 等待，但不会让大模型生成更快，也不会自动加速同步的 Embedding 或 FAISS 计算。

## 7. GET 和 POST 有什么区别？

GET 通常用于读取资源，不应该产生预期的状态变化，请求参数常放在 URL 中；POST 通常用于提交数据、创建资源或触发操作，请求数据常放在请求体中。项目使用 `GET /history` 查询聊天记录，使用 `POST /chat` 发送问题，使用 `POST /upload` 上传 PDF 并建立索引。GET 和 POST 本身都不等于安全，敏感数据仍需要 HTTPS、身份认证和权限控制。

## 8. Pydantic 有什么作用？

Pydantic 使用 Python 类型注解定义数据结构，并负责解析和校验输入输出。项目中的 `ChatRequest`、`RAGSource` 和 `RAGChatResponse` 都是 Pydantic 模型，FastAPI 会据此校验字段、生成接口文档，并按响应模型检查返回结果。Pydantic 主要处理字段类型和规则，像“消息不能只包含空格”这样的业务条件仍需要在路由中单独判断。

## 9. FastAPI 有什么优势？

FastAPI 把类型注解、Pydantic 校验、自动生成 OpenAPI/Swagger 文档和异步支持结合在一起，可以用较少代码写出结构清楚的 API。当前项目通过它实现了聊天、历史记录、PDF 上传和 RAG 问答接口，很适合需要调用外部 LLM 服务的 Python 后端。FastAPI 只是接口框架，不会自动做好业务分层，也不会把同步的数据库、Embedding 或 FAISS 操作自动变成异步。
