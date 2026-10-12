import { useEffect, useRef, useState } from "react";
import { Button, Card, Empty, Form, Input, Modal, Tag } from "antd";
import {
  ArrowRightOutlined,
  FolderOpenOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { errorText, isAbort, json } from "./api";
import { date, ErrorNotice, Loading } from "./components";
import { navigate, useResource } from "./hooks";
import type { KnowledgeBase } from "./types";
export default function Library() {
  const library = useResource<KnowledgeBase[]>("/knowledge-bases");
  const [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [form] = Form.useForm();
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function create(values: { name: string; description?: string }) {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError("");
    try {
      await json<KnowledgeBase>("/knowledge-bases", {
        method: "POST",
        body: JSON.stringify({
          name: values.name.trim(),
          description: values.description?.trim() || null,
        }),
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setOpen(false);
        form.resetFields();
        library.reload();
      }
    } catch (e) {
      if (!controller.signal.aborted && !isAbort(e)) setError(errorText(e));
    } finally {
      if (!controller.signal.aborted) {
        active.current = null;
        setBusy(false);
      }
    }
  }
  return (
    <main className="library-page">
      <section className="page-heading">
        <div>
          <div className="eyebrow">YOUR KNOWLEDGE LIBRARY</div>
          <h1>我的知识库</h1>
          <p className="muted">把分散的文档，整理成随时可用的知识。</p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined aria-hidden="true" />}
          size="large"
          onClick={() => setOpen(true)}
        >
          创建知识库
        </Button>
      </section>
      <ErrorNotice error={library.error} retry={library.reload} />
      {library.loading ? (
        <Loading />
      ) : !library.data?.length ? (
        <div className="empty-library">
          <Empty
            description={
              <>
                <h3>还没有知识库</h3>
                <p className="muted">
                  创建第一个知识库，上传 PDF，让知识开始连接。
                </p>
              </>
            }
          />
          <Button type="primary" onClick={() => setOpen(true)}>
            创建第一个知识库
          </Button>
        </div>
      ) : (
        <>
          <div className="section-label">
            全部知识库 <Tag>{library.data.length}</Tag>
          </div>
          <div className="library-grid">
            {library.data.map((kb) => (
              <Card key={kb.id} className="kb-card">
                <div className="kb-card-top">
                  <span className="folder-icon">
                    <FolderOpenOutlined aria-hidden="true" />
                  </span>
                  <Tag variant="filled">专属空间</Tag>
                </div>
                <h2>{kb.name}</h2>
                <p className="kb-description">
                  {kb.description ||
                    "为制度、流程与团队经验建立有序的知识空间。"}
                </p>
                <div className="kb-card-bottom">
                  <span className="muted">创建于 {date(kb.created_at)}</span>
                  <Button
                    type="text"
                    icon={<ArrowRightOutlined aria-hidden="true" />}
                    aria-label={`打开知识库：${kb.name}`}
                    onClick={() => navigate(`/knowledge-bases/${kb.id}/chat`)}
                  >
                    打开
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
      <aside className="library-tip">
        <FileTip />
        <div>
          <strong>从文档到答案，每一步都有依据</strong>
          <p>
            上传可提取文字的 PDF
            后，在聊天中提问。每条回答都可展开来源，核对文档原文与页码。
          </p>
        </div>
      </aside>
      <Modal
        title="创建知识库"
        open={open}
        onCancel={() => !busy && setOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <ErrorNotice error={error} />
        <Form
          form={form}
          layout="vertical"
          requiredMark={false}
          onFinish={create}
        >
          <Form.Item
            label="知识库名称"
            name="name"
            rules={[
              { required: true, whitespace: true, message: "请输入知识库名称" },
              { max: 200, message: "名称最多 200 个字符" },
            ]}
          >
            <Input
              placeholder="例如：员工制度与 SOP"
              maxLength={200}
              autoFocus
            />
          </Form.Item>
          <Form.Item
            label="知识库描述"
            name="description"
            rules={[{ max: 2000, message: "描述最多 2000 个字符" }]}
          >
            <Input.TextArea
              placeholder="简要描述知识库的内容与用途（选填）"
              rows={3}
              maxLength={2000}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={busy} block>
            确认创建
          </Button>
        </Form>
      </Modal>
    </main>
  );
}
function FileTip() {
  return (
    <span className="tip-icon" aria-hidden="true">
      ↗
    </span>
  );
}
