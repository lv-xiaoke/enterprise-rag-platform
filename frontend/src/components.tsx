import { Alert, Button, Spin } from "antd";
import { useEffect, useRef, useState } from "react";
export function Loading({ label = "正在加载" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <Spin />
      <span>{label}</span>
    </div>
  );
}
export function ErrorNotice({
  error,
  retry,
  requestId,
}: {
  error: string;
  retry?: () => void;
  requestId?: string;
}) {
  const [copyStatus, setCopyStatus] = useState("");
  const currentId = useRef(requestId);
  currentId.current = requestId;
  useEffect(() => setCopyStatus(""), [error, requestId]);
  async function copy() {
    const id = requestId;
    if (!id) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(id);
      if (currentId.current === id) setCopyStatus("已复制");
    } catch {
      if (currentId.current === id) setCopyStatus("无法自动复制，请手动选择请求 ID 复制");
    }
  }
  return error ? (
    <Alert
      className="notice"
      type="error"
      showIcon
      title={error}
      description={requestId && (
        <div>
          <span>请求 ID：</span><code style={{ overflowWrap: "anywhere", userSelect: "text" }}>{requestId}</code>
          <Button size="small" onClick={copy}>复制请求 ID</Button>
          {copyStatus && <div role="status">{copyStatus}</div>}
        </div>
      )}
      action={
        retry && (
          <Button size="small" aria-label="重试" onClick={retry}>
            重试
          </Button>
        )
      }
    />
  ) : null;
}
export function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark" aria-hidden="true">
        知
      </span>
      <span>
        知序<span className="brand-caption">企业知识工作台</span>
      </span>
    </div>
  );
}
export const date = (value: string) =>
  value ? new Date(value).toLocaleDateString("zh-CN") : "";
