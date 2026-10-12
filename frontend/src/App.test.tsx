import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
const user = { id: 1, username: "alice" };
const kb = {
  id: 1,
  name: "制度库",
  description: "企业制度",
  created_at: "2026-10-12T00:00:00Z",
};
function api(routes: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      if (!(input in routes)) throw new Error(`Unexpected request ${input}`);
      const value =
        typeof routes[input] === "function"
          ? await (routes[input] as (init?: RequestInit) => unknown)(init)
          : routes[input];
      if (value instanceof Response) return value;
      return new Response(JSON.stringify(value), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
}
describe("knowledge workspace", () => {
  it("registers with cookie API and shows the empty knowledge library", async () => {
    api({
      "/api/auth/me": new Response('{"detail":"请登录"}', { status: 401 }),
      "/api/auth/register": user,
      "/api/knowledge-bases": [],
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "注册新账号" }));
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "alice" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "secure-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建账号" }));
    expect(await screen.findByText("还没有知识库")).toBeInTheDocument();
    expect(screen.getByText("alice")).toBeInTheDocument();
  });
  it("restores interrupted messages and their source text after refresh", async () => {
    window.location.hash = "#/knowledge-bases/1/chat/7";
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases": [kb],
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/conversations": [
        {
          id: 7,
          knowledge_base_id: 1,
          title: "报销规则",
          created_at: "",
          updated_at: "",
        },
      ],
      "/api/conversations/7/messages": [
        {
          id: 10,
          conversation_id: 7,
          role: "assistant",
          content: "已保存的部分回答",
          status: "interrupted",
          sources: [
            {
              chunk_id: 1,
              document_id: 1,
              filename: "制度.pdf",
              page_number: 2,
              chunk_index: 0,
              content: "报销需要发票",
              score: 0.8,
            },
          ],
          created_at: "",
        },
      ],
    });
    render(<App />);
    expect(await screen.findByText("已保存的部分回答")).toBeInTheDocument();
    expect(screen.getByText("已中断")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看来源（1）" }));
    expect(await screen.findByText("报销需要发票")).toBeInTheDocument();
  });
  it("hides old account content immediately when session expires", async () => {
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases": [kb],
      "/api/auth/logout": new Response(null, { status: 204 }),
    });
    render(<App />);
    await screen.findByText("制度库");
    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));
    await waitFor(() =>
      expect(screen.queryByText("制度库")).not.toBeInTheDocument(),
    );
    expect(
      await screen.findByRole("button", { name: "登录工作台" }),
    ).toBeInTheDocument();
  });
  it("applies meta identifiers before batched deltas and renders the persisted final answer", async () => {
    window.location.hash = "#/knowledge-bases/1/chat/7";
    const final = {
      id: 12,
      conversation_id: 7,
      role: "assistant",
      content: "完整的中文答案",
      status: "completed",
      sources: [],
      created_at: "",
    };
    let sent = false;
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/conversations": [
        {
          id: 7,
          knowledge_base_id: 1,
          title: "问答",
          created_at: "",
          updated_at: "",
        },
      ],
      "/api/conversations/7/messages": () => (sent ? [final] : []),
      "/api/conversations/7/messages/stream": () => {
        return new Response(
          new ReadableStream({
            start(controller) {
              streamController = controller;
              controller.enqueue(
                new TextEncoder().encode(
                  'event: meta\ndata: {"conversation_id":7,"user_message_id":11,"assistant_message_id":12}\n\nevent: delta\ndata: {"text":"完整的"}\n\nevent: delta\ndata: {"text":"中文答案"}\n\n',
                ),
              );
            },
          }),
          { headers: { "Content-Type": "text/event-stream" } },
        );
      },
    });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("输入问题"), {
      target: { value: "制度是什么？" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "发送问题" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("完整的中文答案")).toBeInTheDocument();
    expect(screen.getByText("生成中")).toBeInTheDocument();
    sent = true;
    streamController.enqueue(
      new TextEncoder().encode(
        `event: done\ndata: ${JSON.stringify({ message: final })}\n\n`,
      ),
    );
    streamController.close();
    expect(await screen.findByText("已完成")).toBeInTheDocument();
    expect(
      screen.queryByText("正在检索知识与生成回答…"),
    ).not.toBeInTheDocument();
  });
  it("ignores a delayed history response after switching conversations", async () => {
    window.location.hash = "#/knowledge-bases/1/chat/7";
    let resolveOld!: (value: unknown) => void;
    const delayed = new Promise((resolve) => {
      resolveOld = resolve;
    });
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/conversations": [7, 8].map((id) => ({
        id,
        knowledge_base_id: 1,
        title: `会话${id}`,
        created_at: "",
        updated_at: "",
      })),
      "/api/conversations/7/messages": () => delayed,
      "/api/conversations/8/messages": [
        {
          id: 22,
          conversation_id: 8,
          role: "assistant",
          content: "当前会话的回答",
          status: "completed",
          sources: [],
          created_at: "",
        },
      ],
    });
    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", { name: "打开会话：会话8" }),
    );
    expect(await screen.findByText("当前会话的回答")).toBeInTheDocument();
    resolveOld([
      {
        id: 11,
        conversation_id: 7,
        role: "assistant",
        content: "旧会话迟到的回答",
        status: "completed",
        sources: [],
        created_at: "",
      },
    ]);
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText("旧会话迟到的回答")).not.toBeInTheDocument();
  });
  it("stops the real stream reader and restores the interrupted server message", async () => {
    window.location.hash = "#/knowledge-bases/1/chat/7";
    let interrupted = false;
    const partial = {
      id: 12,
      conversation_id: 7,
      role: "assistant",
      content: "停止前的中文内容",
      status: "interrupted",
      sources: [],
      created_at: "",
    };
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'event: meta\ndata: {"conversation_id":7,"user_message_id":11,"assistant_message_id":12}\n\nevent: delta\ndata: {"text":"停止前的中文内容"}\n\n',
          ),
        );
      },
      cancel() {
        interrupted = true;
      },
    });
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/conversations": [
        {
          id: 7,
          knowledge_base_id: 1,
          title: "问答",
          created_at: "",
          updated_at: "",
        },
      ],
      "/api/conversations/7/messages": () => (interrupted ? [partial] : []),
      "/api/conversations/7/messages/stream": new Response(stream, {
        headers: { "Content-Type": "text/event-stream" },
      }),
    });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("输入问题"), {
      target: { value: "请解释制度" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "发送问题" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("停止前的中文内容")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "停止生成" }));
    expect(await screen.findByText("已中断")).toBeInTheDocument();
    await waitFor(() => expect(stream.locked).toBe(false));
    expect(screen.getByText("停止前的中文内容")).toBeInTheDocument();
  });
  it("cancels a live stream when switching and never shows its text in the new conversation", async () => {
    window.location.hash = "#/knowledge-bases/1/chat/7";
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'event: meta\ndata: {"conversation_id":7,"user_message_id":11,"assistant_message_id":12}\n\nevent: delta\ndata: {"text":"旧会话正在生成"}\n\n',
          ),
        );
      },
    });
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/conversations": [7, 8].map((id) => ({
        id,
        knowledge_base_id: 1,
        title: `会话${id}`,
        created_at: "",
        updated_at: "",
      })),
      "/api/conversations/7/messages": [],
      "/api/conversations/8/messages": [
        {
          id: 22,
          conversation_id: 8,
          role: "assistant",
          content: "新会话记录",
          status: "completed",
          sources: [],
          created_at: "",
        },
      ],
      "/api/conversations/7/messages/stream": new Response(stream, {
        headers: { "Content-Type": "text/event-stream" },
      }),
    });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("输入问题"), {
      target: { value: "旧问题" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "发送问题" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    await screen.findByText("旧会话正在生成");
    fireEvent.click(screen.getByRole("button", { name: "打开会话：会话8" }));
    expect(await screen.findByText("新会话记录")).toBeInTheDocument();
    await waitFor(() => expect(stream.locked).toBe(false));
    expect(screen.queryByText("旧会话正在生成")).not.toBeInTheDocument();
  });
  it("creates a knowledge library with the submitted values", async () => {
    let created = false;
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases": (init?: RequestInit) => {
        if (init?.method === "POST") {
          const body = JSON.parse(init.body as string);
          if (body.name !== "制度库" || body.description !== "企业制度")
            return new Response('{"detail":"错误的提交内容"}', { status: 400 });
          created = true;
          return kb;
        }
        return created ? [kb] : [];
      },
    });
    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", { name: "创建知识库" }),
    );
    fireEvent.change(screen.getByLabelText("知识库名称"), {
      target: { value: "制度库" },
    });
    fireEvent.change(screen.getByLabelText("知识库描述"), {
      target: { value: "企业制度" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认创建" }));
    expect(
      await screen.findByRole("button", { name: "打开知识库：制度库" }),
    ).toBeInTheDocument();
  });
  it("uploads the selected PDF as multipart and displays its saved processing status", async () => {
    window.location.hash = "#/knowledge-bases/1/documents";
    let uploaded = false;
    const doc = {
      id: 1,
      knowledge_base_id: 1,
      filename: "流程.pdf",
      status: "ready",
      failure_reason: null,
      created_at: "",
      updated_at: "",
    };
    api({
      "/api/auth/me": user,
      "/api/knowledge-bases/1": kb,
      "/api/knowledge-bases/1/documents": (init?: RequestInit) => {
        if (init?.method === "POST") {
          const file = (init.body as FormData).get("file") as File;
          if (file?.name !== "流程.pdf" || !file.size)
            return new Response('{"detail":"缺少文档"}', { status: 400 });
          uploaded = true;
          return { document: doc, page_count: 2, chunk_count: 3 };
        }
        return uploaded ? [doc] : [];
      },
    });
    render(<App />);
    const input = await screen.findByLabelText("上传 PDF");
    fireEvent.change(input, {
      target: {
        files: [
          new File(["%PDF-1.4 text"], "流程.pdf", { type: "application/pdf" }),
        ],
      },
    });
    expect(await screen.findByText("可检索")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "流程.pdf" }),
    ).toBeInTheDocument();
  });
});
