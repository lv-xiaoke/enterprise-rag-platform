# Enterprise RAG Platform 三分钟演示脚本

> 目标时长：2 分 40 秒～3 分 10 秒  
> 演示语料：仓库内 4 份公开虚构制度 PDF  
> 演示主线：架构 → 多文档入库 → 跨文档来源 → 无答案拒答 → API 重启恢复 → 评测结论

## 录制前准备

1. 关闭通知、邮箱、聊天软件、密码管理器和无关终端。
2. 不打开 `.env`，不显示 API Key、数据库密码、完整连接串或真实企业资料。
3. 把终端字号调到观众能看清，预先打开 README 架构图和 `docs/evaluation-report.md`。
4. 确认 Compose 服务就绪：

```powershell
docker compose up --build -d
docker compose ps --all
```

5. 在正式录制前完整预演一次；预演产生的知识库可以保留，不删除数据库数据或 Volume。
6. 正式录制时重新执行 `prepare`，让视频真实展示创建知识库和上传 4 份 PDF。

## 0:00～0:25：业务目标与架构

**画面**：根目录 README 的标题、核心能力和架构图。

**口述**：

> 这是我独立实现的企业制度与 SOP RAG 后端。它支持多知识库、多 PDF 入库，把页码、原文和 512 维向量持久化到 PostgreSQL + pgvector，并在指定知识库的 ready 文档内检索。系统分为 FastAPI、Service、Repository 和数据库四层；今天我用一条真实流程展示入库、跨文档来源、拒答和重启恢复。

## 0:25～1:10：创建知识库并上传四份 PDF

**画面**：PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode prepare
```

**口述**：

> 脚本先检查数据库和 LLM 是否就绪，然后创建一个本次演示专用知识库，上传考勤、差旅报销、采购资产和访客会议室四份虚构 PDF。每份 PDF 都经过按页解析、200/40 重叠切块和 BGE 512 维向量化。只有四个 Document 全部进入 ready 状态，脚本才会继续。

**屏幕上必须看见**：

- 动态知识库 ID。
- `document_count = 4`。
- `ready_count = 4`。
- 不出现 `.env` 内容和任何秘密。

## 1:10～1:45：跨文档问答与来源追溯

**画面**：同一 PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode answerable
```

**口述**：

> 这个问题同时需要采购验收、资产登记和财务付款凭证。查询向量在 SQL 层限定当前知识库和 ready 状态，按余弦相似度取 Top-3。回答之外，我返回文档名、页码、Chunk ID 和分数；脚本还会断言来源同时覆盖《采购与办公资产管理制度》和《差旅与费用报销制度》。分数表示语义相似度，不是答案正确概率。

**屏幕上必须看见**：

- `refused = false`。
- 两个目标 PDF 文件名。
- 页码、Chunk ID 和 score。

## 1:45～2:05：无答案拒答

**画面**：同一 PowerShell 终端。

```powershell
.\scripts\run_enterprise_rag_demo.ps1 -Mode refusal
```

**口述**：

> 知识库没有股票期权制度。最高候选证据不足时，系统会在调用 LLM 前拒答，返回固定文本和空来源，避免模型利用不相关资料编造归属周期。

**屏幕上必须看见**：

- `refused = true`。
- `source_count = 0`。
- 固定拒答文本。

## 2:05～2:35：API 重启后复用同一数据

**画面**：PowerShell 终端。

```powershell
docker compose restart api
.\scripts\run_enterprise_rag_demo.ps1 -Mode verify-after-restart
```

**口述**：

> 现在只重启 API，不重新上传。脚本读取本次演示保存的动态知识库 ID，等待健康检查恢复，再比较重启前后的 Document ID，并重新执行跨文档查询。相同 ID、四个 ready 文档和相同来源类型说明权威数据来自 PostgreSQL + pgvector，而不是 FastAPI 进程内存。数据库进程与 Volume 的重启持久化已经在独立验收中验证。

**屏幕上必须看见**：

- `document_ids_unchanged = true`。
- `ready_document_count = 4`。
- `query_refused = false`。
- 两个目标来源文件名。

## 2:35～3:00：评测与边界

**画面**：`docs/evaluation-report.md` 的结论摘要和失败案例。

**口述**：

> 我用四份两页虚构制度和十八道固定问题评测检索，其中十二道可回答、六道无答案。Top-3 Recall 是 97.22%，MRR 是 95.83%；三十六个预热后的 Query Embedding 加 pgvector 检索样本 P95 是 15.25 毫秒。离线实验推荐阈值 0.65，但生产代码仍是 0.55，我没有把建议包装成已上线配置。当前限制包括只支持文本型 PDF、同步入库、无认证、没有 ANN 索引，也没有把检索延迟说成端到端 SLA。

## 剪辑边界

- 可以剪掉模型加载、四个文件依次处理和 API 重启健康等待中的静默时间。
- 不得替换请求结果、拼接其他知识库输出、修改来源或隐藏失败后假装一次成功。
- 如果断言失败，停止录制，按错误修复后从头重新录；不要只剪掉报错。
- 最终视频保存为 `artifacts/demo/enterprise-rag-demo.mp4`，不要加入 Git。

## 录制后检查

```text
[ ] 视频时长在 2:40～3:10
[ ] 能听清业务目标、两条链路和关键取舍
[ ] 展示 4 个 ready 文档
[ ] 跨文档题包含两个真实来源文件名和页码
[ ] 无答案题为 refused=true 且 sources 为空
[ ] API 重启后使用同一知识库 ID，未重新上传
[ ] 指标口径明确，不把 0.65 说成已部署
[ ] 没有 .env、API Key、数据库密码、完整 URL 凭据、通知或个人隐私
```