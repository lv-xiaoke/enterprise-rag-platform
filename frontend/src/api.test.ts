import { describe, expect, it, vi } from "vitest";
import { json, request } from "./api";

describe("cookie API isolation", () => {
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
