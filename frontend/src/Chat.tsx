import { useEffect, useRef, useState } from "react";
import { Button, Drawer, Empty, Input, Tag } from "antd";
import {
  CommentOutlined,
  FileSearchOutlined,
  PlusOutlined,
  SendOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { errorText, isAbort, json, request, parseRequestId, requestIdOf, RequestError } from "./api";
import { ErrorNotice, Loading } from "./components";
import { navigate, useResource } from "./hooks";
import { consumeSSE } from "./sse";
import type { Conversation, Message, Source } from "./types";
export default function Chat({
  kbId,
  conversationId,
}: {
  kbId: number;
  conversationId?: number;
}) {
  const list = useResource<Conversation[]>(
    `/knowledge-bases/${kbId}/conversations`,
  );
  const [creating, setCreating] = useState(false),
    [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function create() {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setCreating(true);
    setError("");
    try {
      const item = await json<Conversation>(
        `/knowledge-bases/${kbId}/conversations`,
        { method: "POST", body: "{}", signal: controller.signal },
      );
      if (!controller.signal.aborted) {
        list.reload();
        navigate(`/knowledge-bases/${kbId}/chat/${item.id}`);
      }
    } catch (e) {
      if (!controller.signal.aborted) setError(errorText(e));
    } finally {
      if (!controller.signal.aborted) {
        setCreating(false);
        pending.current = null;
      }
    }
  }
  const permitted =
    conversationId && list.data?.some((c) => c.id === conversationId);
  return (
    <div className="chat-layout">
      <aside className="conversation-sidebar">
        <Button
          type="primary"
          icon={<PlusOutlined aria-hidden="true" />}
          block
          onClick={create}
          loading={creating}
        >
          新建会话
        </Button>
        <div className="sidebar-caption">对话记录</div>
        <ErrorNotice error={error} />
        <ErrorNotice error={list.error} retry={list.reload} />
        {list.loading && !list.data ? (
          <Loading />
        ) : !list.data?.length ? (
          <p className="sidebar-empty">每一次思考，都从一个问题开始。</p>
        ) : (
          <nav className="conversation-list" aria-label="会话列表">
            {list.data.map((c) => (
              <button
                type="button"
                key={c.id}
                className={
                  conversationId === c.id
                    ? "conversation active"
                    : "conversation"
                }
                aria-current={conversationId === c.id ? "page" : undefined}
                aria-label={`打开会话：${c.title}`}
                onClick={() =>
                  navigate(`/knowledge-bases/${kbId}/chat/${c.id}`)
                }
              >
                <CommentOutlined aria-hidden="true" />
                <span>{c.title || "新会话"}</span>
              </button>
            ))}
          </nav>
        )}
        <div className="sidebar-bottom">
          <FileSearchOutlined aria-hidden="true" /> 所有对话仅基于当前知识库
        </div>
      </aside>
      {conversationId ? (
        list.loading && !list.data ? (
          <Loading />
        ) : permitted ? (
          <Thread
            key={conversationId}
            id={conversationId}
            onChanged={list.reload}
          />
        ) : (
          <div className="chat-welcome">
            <ErrorNotice error="会话不存在或不属于当前知识库" />
            <Button onClick={() => navigate(`/knowledge-bases/${kbId}/chat`)}>
              返回聊天工作台
            </Button>
          </div>
        )
      ) : (
        <section className="chat-welcome">
          <div className="welcome-symbol">
            <FileSearchOutlined aria-hidden="true" />
          </div>
          <div className="eyebrow">A CLEARER WAY TO KNOW</div>
          <h2>让文档回答你的问题</h2>
          <p className="muted">
            从制度细节到操作流程，找到答案，也找到依据。
            <br />
            新建一个会话，开始探索当前知识库。
          </p>
          <div className="suggestion-grid">
            <div>
              <strong>制度查询</strong>
              <span>报销需要准备哪些材料？</span>
            </div>
            <div>
              <strong>流程梳理</strong>
              <span>请梳理新员工入职流程。</span>
            </div>
            <div>
              <strong>原文核对</strong>
              <span>这项规定出自哪一页？</span>
            </div>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined aria-hidden="true" />}
            onClick={create}
            loading={creating}
          >
            开始新会话
          </Button>
        </section>
      )}
    </div>
  );
}
const statusLabels = {
  generating: "生成中",
  completed: "已完成",
  failed: "生成失败",
  interrupted: "已中断",
};
function validMessage(value: unknown, id: number): value is Message {
  const m = value as Message;
  return (
    !!m &&
    typeof m.id === "number" &&
    m.conversation_id === id &&
    m.role === "assistant" &&
    typeof m.content === "string" &&
    ["completed", "failed", "interrupted"].includes(m.status) &&
    Array.isArray(m.sources)
  );
}
function Thread({ id, onChanged }: { id: number; onChanged: () => void }) {
  const history = useResource<Message[]>(`/conversations/${id}/messages`);
  const [messages, setMessages] = useState<Message[]>([]),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [refused, setRefused] = useState(false),
    [sources, setSources] = useState<Source[] | null>(null);
  const active = useRef<AbortController | null>(null),
    alive = useRef(true),
    bottom = useRef<HTMLDivElement>(null);
  const [requestId, setRequestId] = useState<string>();
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      active.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (history.data && !active.current) setMessages(history.data);
  }, [history.data]);
  const pending = messages.some((m) => m.status === "generating");
  useEffect(() => {
    if (!busy && pending) {
      const timer = setTimeout(history.reload, 1800);
      return () => clearTimeout(timer);
    }
  }, [busy, pending, history.data, history.reload]);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages]);
  async function send() {
    const content = question.trim();
    if (
      !content ||
      active.current ||
      pending ||
      history.loading ||
      history.error
    )
      return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setQuestion("");
    setError("");
    setRequestId(undefined);
    setRefused(false);
    let assistantId = -2;
    const now = new Date().toISOString();
    setMessages((old) => [
      ...old,
      {
        id: -1,
        conversation_id: id,
        role: "user",
        content,
        status: "completed",
        sources: [],
        created_at: now,
      },
      {
        id: -2,
        conversation_id: id,
        role: "assistant",
        content: "",
        status: "generating",
        sources: [],
        created_at: now,
      },
    ]);
    const update = (fn: (message: Message) => Message) => {
      const targetId = assistantId;
      if (alive.current && !controller.signal.aborted)
        setMessages((old) =>
          old.map((m) => (m.id === targetId ? fn(m) : m)),
        );
    };
    try {
      const response = await request(`/conversations/${id}/messages/stream`, {
        method: "POST",
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });
      if (!response.headers.get("content-type")?.includes("text/event-stream"))
        throw new RequestError("服务器未返回流式响应，请刷新历史记录", parseRequestId(response.headers.get("X-Request-ID")));
      await consumeSSE(
        response,
        ({ event, data }) => {
          if (!alive.current || controller.signal.aborted) return;
          if (event === "meta") {
            if (
              data.conversation_id !== id ||
              typeof data.user_message_id !== "number" ||
              typeof data.assistant_message_id !== "number"
            )
              throw new Error("会话数据不匹配，请刷新历史记录");
            const nextId = data.assistant_message_id;
            const previousId = assistantId;
            setMessages((old) =>
              old.map((m) =>
                m.id === -1
                  ? { ...m, id: data.user_message_id as number }
                : m.id === previousId
                    ? { ...m, id: nextId }
                    : m,
              ),
            );
            assistantId = nextId;
            onChanged();
          } else if (event === "sources") {
            if (!Array.isArray(data.sources))
              throw new Error("来源数据格式错误");
            update((m) => ({ ...m, sources: data.sources as Source[] }));
            setRefused(data.refused === true);
          } else if (event === "delta") {
            if (typeof data.text !== "string")
              throw new Error("流式文本格式错误");
            update((m) => ({ ...m, content: m.content + data.text }));
          } else if (event === "done") {
            if (!validMessage(data.message, id))
              throw new Error("最终消息格式错误，请刷新历史记录");
            update(() => data.message as Message);
          }
        },
        controller.signal,
      );
    } catch (e) {
      if (alive.current) {
        setRequestId(isAbort(e) ? undefined : requestIdOf(e));
        setError(
          isAbort(e)
            ? "已停止生成。已收到的内容会保留，可刷新历史核对保存状态。"
            : errorText(e),
        );
        setMessages((old) =>
          old.map((m) =>
            m.id === assistantId
              ? { ...m, status: isAbort(e) ? "interrupted" : "failed" }
              : m,
          ),
        );
        if (assistantId === -2 && !isAbort(e)) setQuestion(content);
      }
    } finally {
      if (alive.current) {
        active.current = null;
        setBusy(false);
        history.reload();
        onChanged();
      }
    }
  }
  return (
    <section className="chat-thread">
      <div className="thread-toolbar">
        <span>
          <span className="live-dot" /> 当前知识库 · 有据问答
        </span>
        <Button size="small" onClick={history.reload} disabled={busy}>
          刷新历史
        </Button>
      </div>
      <div
        className="message-scroll"
        role="log"
        aria-label="聊天消息"
        aria-live="polite"
      >
        <ErrorNotice error={history.error} retry={history.reload} />
        {history.loading && !history.data ? (
          <Loading label="正在加载对话历史" />
        ) : !messages.length ? (
          <Empty description="输入第一个问题，开始这段对话" />
        ) : (
          messages.map((message) => (
            <article
              key={message.id}
              className={`message message-${message.role}`}
            >
              <div className={`message-avatar ${message.role}`}>
                {message.role === "assistant" ? "知" : "你"}
              </div>
              <div className="message-body">
                <div className="message-meta">
                  <strong>
                    {message.role === "assistant" ? "知序助手" : "你"}
                  </strong>
                  {message.role === "assistant" && (
                    <span className={`status status-${message.status}`}>
                      {statusLabels[message.status]}
                    </span>
                  )}
                </div>
                <div className="message-content">
                  {message.content ||
                    (message.status === "generating"
                      ? "正在检索知识与生成回答…"
                      : "本次生成未收到回答内容。")}
                </div>
                {message.role === "assistant" && message.sources.length > 0 && (
                  <Button
                    type="text"
                    size="small"
                    className="source-button"
                    icon={<FileSearchOutlined aria-hidden="true" />}
                    onClick={() => setSources(message.sources)}
                  >
                    查看来源（{message.sources.length}）
                  </Button>
                )}
              </div>
            </article>
          ))
        )}
        <div ref={bottom} />
      </div>
      <div className="composer">
        <ErrorNotice error={error} requestId={requestId} />
        {refused && (
          <div className="refusal-notice">
            当前知识库中未找到足够依据，请尝试补充文档或换一种问法。
          </div>
        )}
        <Input.TextArea
          aria-label="输入问题"
          placeholder="向当前知识库提问…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          maxLength={1000}
          disabled={busy}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <div className="composer-actions">
          <span className="muted">
            Enter 发送 · Shift + Enter 换行 · {question.length}/1000
          </span>
          {busy ? (
            <Button
              danger
              icon={<StopOutlined aria-hidden="true" />}
              onClick={() => active.current?.abort()}
            >
              停止生成
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined aria-hidden="true" />}
              onClick={() => void send()}
              disabled={
                !question.trim() ||
                pending ||
                history.loading ||
                !!history.error
              }
            >
              发送问题
            </Button>
          )}
        </div>
        {pending && !busy && (
          <p role="status" className="muted">
            正在同步服务器生成状态，请稍候或刷新历史。
          </p>
        )}
        <div className="answer-note">AI 回答仅供参考，请结合来源原文核对。</div>
      </div>
      <Drawer
        title="回答来源"
        open={sources !== null}
        onClose={() => setSources(null)}
        size="large"
        className="sources-drawer"
      >
        {sources?.map((source, index) => (
          <article className="source-card" key={`${source.chunk_id}-${index}`}>
            <div className="source-heading">
              <Tag color="green">来源 {index + 1}</Tag>
              <span>第 {source.page_number} 页</span>
            </div>
            <h3>{source.filename}</h3>
            <p className="source-content">{source.content}</p>
            <div className="muted">
              片段 {source.chunk_index + 1} · 相关度{" "}
              {Number.isFinite(source.score) ? source.score.toFixed(3) : "—"}
            </div>
          </article>
        ))}
        <p className="muted">
          展示检索片段原文与页码，可在原文档中进一步核对。
        </p>
      </Drawer>
    </section>
  );
}
