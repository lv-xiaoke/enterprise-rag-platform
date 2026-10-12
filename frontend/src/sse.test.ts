import { describe, expect, it } from "vitest";
import { consumeSSE } from "./sse";
const encode = new TextEncoder();
function response(text: string, cut = 1) {
  const bytes = encode.encode(text);
  return new Response(
    new ReadableStream({
      start(controller) {
        for (let i = 0; i < bytes.length; i += cut)
          controller.enqueue(bytes.slice(i, i + cut));
        controller.close();
      },
    }),
    { headers: { "Content-Type": "text/event-stream" } },
  );
}
describe("stream protocol", () => {
  it("decodes Chinese across UTF8 bytes and dispatches multiple CRLF events in order", async () => {
    const events: unknown[] = [];
    await consumeSSE(
      response(
        ': heartbeat\r\nevent: meta\r\ndata: {"conversation_id":1,"user_message_id":2,"assistant_message_id":3}\r\n\r\nevent: delta\r\ndata: {"text":"中文依据"}\r\n\r\nevent: done\r\ndata: {"message":{"id":3}}\r\n\r\n',
      ),
      (event) => events.push(event),
    );
    expect(events).toEqual([
      {
        event: "meta",
        data: {
          conversation_id: 1,
          user_message_id: 2,
          assistant_message_id: 3,
        },
      },
      { event: "delta", data: { text: "中文依据" } },
      { event: "done", data: { message: { id: 3 } } },
    ]);
  });
  it("does not mark a truncated connection as completed", async () => {
    await expect(
      consumeSSE(response('event: delta\ndata: {"text":"部分"}\n\n'), () => {}),
    ).rejects.toThrow("连接已中断");
  });
  it("surfaces safe server error and supports batched events", async () => {
    const events: unknown[] = [];
    await expect(
      consumeSSE(
        response(
          'event: sources\ndata: {"sources":[],"refused":true}\n\nevent: error\ndata: {"detail":"模型暂不可用"}\n\n',
          2048,
        ),
        (e) => events.push(e),
      ),
    ).rejects.toThrow("模型暂不可用");
    expect(events).toHaveLength(2);
  });
  it("rejects malformed protocol rather than ignoring model failures", async () => {
    await expect(
      consumeSSE(response("event: delta\ndata: invalid\n\n"), () => {}),
    ).rejects.toThrow("流式数据格式");
  });
  it("releases the reader and propagates abort", async () => {
    const controller = new AbortController();
    const stream = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(encode.encode('event: delta\ndata: {"text":"正在"}\n\n'));
      },
    });
    await expect(
      consumeSSE(
        new Response(stream),
        () => controller.abort(),
        controller.signal,
      ),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(stream.locked).toBe(false);
  });
});
