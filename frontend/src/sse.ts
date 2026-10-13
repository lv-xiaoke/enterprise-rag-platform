import { errorText, isAbort, parseRequestId, RequestError } from "./api";

export type StreamEvent = { event: string; data: Record<string, unknown> };
export async function consumeSSE(
  response: Response,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headerId = parseRequestId(response.headers.get("X-Request-ID"));
  let requestId = headerId;
  if (!response.body) throw new RequestError("浏览器未提供流式响应，请重试", requestId);
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "",
    finished = false;
  const abort = () => {
    void reader.cancel().catch(() => {});
  };
  signal?.addEventListener("abort", abort, { once: true });
  const checkAbort = () => {
    if (signal?.aborted) throw new DOMException("已停止生成", "AbortError");
  };
  const dispatch = (block: string) => {
    let event = "message";
    const lines: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) lines.push(line.slice(5).replace(/^ /, ""));
    }
    if (!lines.length) return;
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(lines.join("\n"));
      if (!data || typeof data !== "object" || Array.isArray(data))
        throw new Error();
    } catch {
      throw new Error("流式数据格式错误，请重新加载历史记录");
    }
    if (!headerId && !requestId && (event === "meta" || event === "error"))
      requestId = parseRequestId(data.request_id);
    onEvent({ event, data });
    if (event === "error")
      throw new Error(
        typeof data.detail === "string" ? data.detail : "生成失败，请重试",
      );
    if (event === "done") finished = true;
  };
  try {
    checkAbort();
    while (!finished) {
      checkAbort();
      const { value, done } = await reader.read();
      checkAbort();
      if (done) {
        buffer += decoder.decode();
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      if (buffer.length > 2_000_000)
        throw new Error("流式事件过大，请重新加载历史记录");
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const block = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        dispatch(block);
        checkAbort();
        if (finished) break;
      }
    }
    if (!finished)
      throw new Error("连接已中断，已收到的内容会保留，请刷新历史记录");
  } catch (error) {
    if (isAbort(error)) throw error;
    throw new RequestError(errorText(error), requestId);
  } finally {
    signal?.removeEventListener("abort", abort);
    try {
      await reader.cancel();
    } catch {
      /* Connection may already be closed. */
    }
    reader.releaseLock();
  }
}
