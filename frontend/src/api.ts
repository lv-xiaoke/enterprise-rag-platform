export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : "请求失败，请稍后重试";
export const isAbort = (error: unknown) =>
  error instanceof Error && error.name === "AbortError";
export async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const checkAbort = () => {
    if (options.signal?.aborted)
      throw new DOMException("请求已取消", "AbortError");
  };
  checkAbort();
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      credentials: "same-origin",
      headers: {
        ...(options.body && !(options.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    checkAbort();
    if (isAbort(error)) throw error;
    throw new Error("无法连接服务器，请检查网络后重试");
  }
  checkAbort();
  if (!response.ok) {
    let detail = `请求失败（${response.status}），请重试`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = "输入不符合要求，请检查长度与格式";
    } catch {
      /* Proxy errors may not be JSON. */
    }
    checkAbort();
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(response.status, detail);
  }
  return response;
}
export async function json<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await request(path, options);
  const data = response.status === 204 ? (undefined as T) : await response.json();
  if (options.signal?.aborted)
    throw new DOMException("请求已取消", "AbortError");
  return data;
}
