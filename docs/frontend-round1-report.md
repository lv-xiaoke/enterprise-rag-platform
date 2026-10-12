# 第一轮前端交付记录

日期：2026-10-12。范围为 `docs/AI全栈第一轮升级计划.md` 的 Task 3。

## 已实现

- React / TypeScript / Vite / Ant Design 中文应用；登录、注册、退出及登录恢复。
- 知识库列表、创建弹窗、描述、空态、加载和可重试错误。
- PDF multipart 上传、同步入库等待、页数/片段数量反馈、文档状态与失败原因、列表刷新与轮询。空文件、非 PDF 在浏览器端提示；服务端负责可配置文件大小上限。
- 按知识库隔离的会话列表、新建/选择、持久化历史、真实增量文本、停止生成、来源抽屉。历史保留 generating / completed / failed / interrupted 状态与引用原文。
- 所有业务访问同源 `/api`，`credentials: same-origin`；浏览器不保存认证令牌，不包含模型密钥，不提供生产 mock。来源/模型文本直接作为 React 文本节点显示。
- SSE 使用流式 TextDecoder，支持 UTF-8 跨字节、CRLF、注释心跳、网络片段、同批多个事件；处理 meta/sources/delta/done/error。未收到 done 即断流视为中断，错误后重新查询历史，绝不自动重发模型调用。
- 请求均随页面上下文取消；组件按账户、知识库和会话隔离。旧历史响应不写入新会话；离开旧会话会取消 reader；取消的旧请求即使迟到返回 401，也不能退出新账户。
- 桌面/窄屏布局、键盘焦点、表单标签、Enter 发送/Shift+Enter 换行/IME 防误发；装饰图标对辅助技术隐藏。长用户名在窄屏省略，退出图标保留中文 accessible name。

## 文件索引

| 文件 | 责任 |
| --- | --- |
| `frontend/src/App.tsx`、`Auth.tsx` | 认证生命周期与账户页面 |
| `frontend/src/Library.tsx`、`Workspace.tsx` | 知识库入口与工作台导航 |
| `frontend/src/Documents.tsx` | 文件上传与文档处理状态 |
| `frontend/src/Chat.tsx` | 会话、流式消息、取消、历史和来源 |
| `frontend/src/api.ts`、`hooks.ts`、`types.ts` | Cookie API、上下文取消、资源加载和契约类型 |
| `frontend/src/sse.ts` | SSE 帧/字节解析及终止判定 |
| `frontend/src/styles.css` | 页面样式、响应式与 reduced-motion |
| `frontend/src/*.test.*`、`test/setup.ts` | 行为回归测试与测试环境 |
| `frontend/package.json`、`package-lock.json`、`vite.config.ts` | 安装锁定、测试/构建、开发代理 |

Docker/Nginx、Playwright 与 CI 文件由集成任务负责，本报告不替代整体交付记录。

## 已执行验证

1. 初始 RED：`npm test`，8 项测试失败，分别为尚未实现的 SSE 与空页面行为。
2. 添加账户竞态回归后 RED：取消的旧 401 请求触发登录失效，1 failed / 15 passed；增加取消检查后 GREEN。
3. 最终 `npm test`：3 个文件、16 项测试全部通过。覆盖中文分片、同批事件、error、缺少 done、reader 取消、注册、历史来源/中断、退出、即时增量、迟到历史、停止、切换旧流、知识库创建、multipart 上传和账户竞态。
4. `npm run build`：TypeScript 与 Vite 生产构建成功。Vite 提示主 JS chunk 大于 500 kB（约 727 kB、gzip 238 kB）；这是体积优化提示，不是构建错误，后续可按使用频率拆分组件库。
5. `npm audit`：0 vulnerabilities。安装时旧 Vitest 依赖存在漏洞，已升级至 4.1.11 并锁定依赖树。
6. 集成任务反馈实际 Edge 浏览器主流程已通过：注册→创建知识库→真实 PDF 入库→聊天→来源→刷新→第二用户隔离→拒答→停止→退出。窄屏长用户名溢出先由浏览器测试复现，再修复；最终结果以整体验收记录为准。

本机普通 sandbox 内 npm registry DNS 查询失败，npm 安装/测试需允许环境执行；升级后的完整依赖与 lock 已生成。未执行批量删除，未创建提交或推送。

## 本地使用与选择器契约

```powershell
cd frontend
npm ci
npm run dev
```

开发默认 `http://localhost:5173`；`/api` 代理到 `http://127.0.0.1:8000`，可用 `API_PROXY_TARGET` 覆盖。保持原 Host，不改变浏览器同源 cookie / CSRF 语义。生产由 Web 服务器同源代理。

Hash 页面路径：`#/knowledge-bases`、`#/knowledge-bases/:id/documents`、`#/knowledge-bases/:id/chat/:conversationId?`。

E2E 标签：`用户名`、`密码`、`知识库名称`、`知识库描述`、`上传 PDF`、`输入问题`；按钮：`注册新账号`、`创建账号`、`登录工作台`、`创建知识库`、`确认创建`、`打开知识库：名称`、`新建会话`、`打开会话：标题`、`发送问题`、`停止生成`、`刷新历史`、`查看来源（N）`、`退出登录`。导航链接：`文档管理`、`聊天工作台`；来源抽屉标题：`回答来源`。

真实模型质量、生产 HTTPS/Secure cookie 与容器启动验收不由前端单元测试证明；参见整体交付记录。
