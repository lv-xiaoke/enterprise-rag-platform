import { describe, expect, it, vi } from "vitest";
import { json, request } from "./api";

describe("cookie API isolation", () => {
  it("preserves server request IDs on HTTP errors", async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{"detail":"文档处理失败"}', {
      status: 502, headers: { 'X-Request-ID': 'a'.repeat(32) },
    })));
    await expect(request('/knowledge-bases/1/documents')).rejects.toMatchObject({
      status: 502, requestId: 'a'.repeat(32),
    });
  });

  it("does not invent an ID when no server response arrives", async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network'); }));
    await expect(request('/knowledge-bases')).rejects.toMatchObject({message:'无法连接服务器，请检查网络后重试'});
    await request('/knowledge-bases').catch(error => expect(error.requestId).toBeUndefined());
  });

  it("keeps the response ID when successful JSON cannot be decoded", async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('invalid-json', {
      status: 200, headers: { 'X-Request-ID': 'b'.repeat(32) },
    })));
    await expect(json('/knowledge-bases')).rejects.toMatchObject({requestId:'b'.repeat(32)});
  });

  it("does not expire a new account when an aborted old request returns 401", async () => {
    let deliver!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { deliver = resolve; })));
    const expired = vi.fn();
    window.addEventListener("session-expired", expired);
    const controller = new AbortController();
    const result = request("/knowledge-bases", { signal: controller.signal });
    controller.abort();
    deliver(new Response('{"detail":"登录过期"}', { status: 401 }));
    await expect(result).rejects.toMatchObject({ name: "AbortError" });
    expect(expired).not.toHaveBeenCalled();
    window.removeEventListener("session-expired", expired);
  });

  it("sends same-origin credentials and preserves readable server errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
      if (init.credentials !== "same-origin") return new Response("missing cookie", { status: 500 });
      return new Response('{"detail":"文件超出大小限制，请选择较小文件"}', { status: 413 });
    }));
    await expect(json("/knowledge-bases/1/documents", { method: "POST", body: new FormData() })).rejects.toThrow("文件超出大小限制，请选择较小文件");
  });
});
