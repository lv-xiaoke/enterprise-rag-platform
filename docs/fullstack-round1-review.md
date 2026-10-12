# 第一轮全栈升级独立代码审查

审查日期：2026-10-12。范围：基线 `9b90318` 至当前工作区，包括尚未跟踪的新后端、前端、迁移、部署及测试文件。仅进行只读代码检查和独立临时 SQLite 复现，没有运行或修改开发数据库。

## 需要修复

### P2：并发终态保存可以覆盖已经提交的失败或中断状态

- 位置：`app/conversations.py:125`，`save_progress` 中先读取 `message.status`，然后通过 ORM 写入状态；相关触发点为同文件第 195、229、236 行。
- 原因：`if message.status != 'generating'` 只检查当前 Session 已读到的值，最终 UPDATE 没有 `status = 'generating'` 条件。两个 Session 同时读取 generating 时，后提交的 completed 能覆盖先提交的 failed/interrupted。`asyncio.timeout` 取消线程池等待并不终止已经执行的数据库线程，因此最终完成保存与超时失败清理可能重叠。
- 可重复验证：临时 SQLite 使用真实 ORM 和 `save_progress`。在线程 A 的 `loaded_as_persistent` 钩子中暂停已读取 generating 的完成保存；线程 B 调用 `save_progress(..., 'failed')` 并提交；随后释放线程 A。实际输出依次为 `first terminal failed`、`late terminal completed`、`final persisted completed`。数据库连接和 Session 均独立，`autoflush=False` 与生产 SessionLocal 一致。
- 影响：客户端已收到 error 或用户已停止生成后，历史仍可能变为 completed，违反终态单调和中断持久化要求。
- 修复建议：通过带 `WHERE id = ... AND status = 'generating'` 的原子条件 UPDATE 实现状态转换，或使用适当行锁。无更新时返回数据库中的既有终态。增加两个独立 Session/线程通过屏障控制交错顺序的回归测试；同时覆盖迟到的 generating 内容更新不能覆写终态快照。

## 已检查的主要边界

- 旧无鉴权业务入口未继续注册；知识库、文档、对话和消息按 owner 校验，不存在及越权统一返回 404。
- 登录令牌只保存摘要；密码使用 PBKDF2；Cookie、Origin/Fetch Metadata 检查与请求体限额均存在。
- 上游使用 HTTPX 真流式响应，异常格式及意外 EOF 不假装正常完成；前端按 SSE 事件而非网络读取次数拆分。
- 前端按用户、知识库、会话重建状态并取消旧请求；生产入口未导入 E2E 模型替身。
- 迁移保留无归属旧知识库；维护脚本只处理指定 ID；Compose 明确迁移先于 API，Nginx 关闭流式缓冲。

单 worker、同步 PDF 入库、无任务队列均为本轮明确边界。Docker 镜像拉取/构建的外部网络限制不作为代码缺陷。本审查不替代主 Agent 的 PostgreSQL、浏览器和构建验收。

本记录是修复前审查快照；主 Agent 应在修复后追加验证结果。

## 修复后独立复核

上述 P2 已修复。`save_progress` 使用同一条带 `status = 'generating'` 条件的 `UPDATE ... RETURNING` 完成检查和写入；条件同时保护状态、文本与来源。未命中时不更新对话时间戳，并在提交后读取数据库中的既有消息。此函数每次创建新 Session，首次加载消息发生在提交后，因此不存在预读 identity map 导致的陈旧返回值。

独立复核另外在临时 SQLite 中运行了真实 ORM 并发探针：通过 `before_cursor_execute` 暂停迟到 UPDATE，让另一个独立 Session 先提交终态，再释放迟到线程。failed/interrupted/completed 三种终态与 generating/completed 两种迟到写入的 6 个组合全部通过，数据库及函数返回的状态、文本、来源均保持先提交的终态快照。未访问或修改开发数据库。

主 Agent 同时报告已在隔离 PostgreSQL 数据库独立运行完整后端测试：37 passed，4.99 秒，其中包含新增的 6 项真实 PostgreSQL 并发回归。该 PostgreSQL 结果来自主 Agent 的实际执行；本审查 Agent 直接执行的验证是上述 6 组合临时数据库探针。

复核结论：本次发现的问题已关闭；没有剩余明确必须修复的审查项。完整交付验收与外部模型、镜像网络限制仍以主 Agent 的最终验收记录为准。
