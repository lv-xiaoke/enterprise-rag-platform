import { useEffect, useRef, useState } from "react";
import { Button, Empty, Tag } from "antd";
import {
  CloudUploadOutlined,
  FilePdfOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { errorText, isAbort, json } from "./api";
import { date, ErrorNotice, Loading } from "./components";
import { useResource } from "./hooks";
import type { DocumentRecord } from "./types";
const statuses = {
  pending: ["等待处理", "default"],
  processing: ["处理中", "processing"],
  ready: ["可检索", "success"],
  failed: ["入库失败", "error"],
} as const;
export default function Documents({ kbId }: { kbId: number }) {
  const docs = useResource<DocumentRecord[]>(
    `/knowledge-bases/${kbId}/documents`,
    true,
  );
  const [uploading, setUploading] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function upload(file: File) {
    if (controller.current) return;
    setError("");
    setSuccess("");
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("请选择 PDF 文件；扫描件需要先转换为可提取文字的 PDF");
      return;
    }
    if (file.size === 0) {
      setError("文件为空，请选择包含文字内容的 PDF");
      return;
    }
    const active = new AbortController();
    controller.current = active;
    setUploading(true);
    const body = new FormData();
    body.append("file", file);
    try {
      const result = await json<{
        document: DocumentRecord;
        page_count: number;
        chunk_count: number;
      }>(`/knowledge-bases/${kbId}/documents`, {
        method: "POST",
        body,
        signal: active.signal,
      });
      if (!active.signal.aborted) {
        setSuccess(
          `“${result.document.filename}”已入库，共 ${result.page_count} 页、${result.chunk_count} 个知识片段。`,
        );
        docs.reload();
      }
    } catch (e) {
      if (!active.signal.aborted && !isAbort(e)) {
        setError(errorText(e));
        docs.reload();
      }
    } finally {
      if (!active.signal.aborted) {
        setUploading(false);
        controller.current = null;
      }
    }
  }
  return (
    <section className="documents-page">
      <div className="section-heading">
        <div>
          <h2>知识文档</h2>
          <p className="muted">上传制度、手册与 SOP，为回答提供可信依据。</p>
        </div>
        <Button
          icon={<ReloadOutlined aria-hidden="true" />}
          onClick={docs.reload}
          disabled={uploading}
        >
          刷新文档
        </Button>
      </div>
      <div className={`upload-zone ${uploading ? "is-uploading" : ""}`}>
        <CloudUploadOutlined aria-hidden="true" className="upload-icon" />
        <h3>
          {uploading ? "正在解析与建立索引…" : "上传一份 PDF，连接新的知识"}
        </h3>
        <p className="muted">
          支持可提取文字的
          PDF。入库完成后即可在聊天中检索。文件大小上限由服务器配置。
        </p>
        <label className="upload-button">
          {uploading ? "处理中，请稍候" : "选择 PDF 文件"}
          <input
            type="file"
            accept=".pdf,application/pdf"
            aria-label="上传 PDF"
            disabled={uploading}
            onChange={(e) => {
              const file = e.currentTarget.files?.[0];
              e.currentTarget.value = "";
              if (file) void upload(file);
            }}
          />
        </label>
        {uploading && (
          <p role="status">同步入库可能需要一些时间，请保持页面打开。</p>
        )}
      </div>
      <ErrorNotice error={error} />
      {success && (
        <p className="success-notice" role="status">
          {success}
        </p>
      )}
      <ErrorNotice error={docs.error} retry={docs.reload} />
      {docs.loading && !docs.data ? (
        <Loading />
      ) : !docs.data?.length ? (
        <Empty description="还没有文档，上传第一份 PDF 开始积累知识" />
      ) : (
        <div className="document-list">
          {docs.data.map((doc) => (
            <article className="document-row" key={doc.id}>
              <span className="pdf-icon">
                <FilePdfOutlined aria-hidden="true" />
              </span>
              <div className="document-details">
                <h3>{doc.filename}</h3>
                <span className="muted">上传于 {date(doc.created_at)}</span>
                {doc.failure_reason && (
                  <p className="failure-reason">{doc.failure_reason}</p>
                )}
              </div>
              <Tag color={statuses[doc.status]?.[1] || "default"}>
                {statuses[doc.status]?.[0] || doc.status}
              </Tag>
            </article>
          ))}
        </div>
      )}
      <p className="document-note">
        提示：扫描图片型 PDF 暂不支持
        OCR。入库失败时请检查文件中的文字是否可复制。
      </p>
    </section>
  );
}
