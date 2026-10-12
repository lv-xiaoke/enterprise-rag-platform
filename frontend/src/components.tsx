import { Alert, Button, Spin } from "antd";
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
}: {
  error: string;
  retry?: () => void;
}) {
  return error ? (
    <Alert
      className="notice"
      type="error"
      showIcon
      title={error}
      action={
        retry && (
          <Button size="small" onClick={retry}>
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
