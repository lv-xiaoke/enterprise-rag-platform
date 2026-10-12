import { useEffect, useRef, useState } from "react";
import {
  ArrowRightOutlined,
  BookOutlined,
  SafetyCertificateOutlined,
  FileSearchOutlined,
} from "@ant-design/icons";
import { Button, Form, Input } from "antd";
import { errorText, isAbort, json } from "./api";
import { Brand, ErrorNotice } from "./components";
import type { User } from "./types";
export default function Auth({ onUser }: { onUser: (user: User) => void }) {
  const [register, setRegister] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function submit(values: { username: string; password: string }) {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError("");
    try {
      const user = await json<User>(
        `/auth/${register ? "register" : "login"}`,
        {
          method: "POST",
          body: JSON.stringify(values),
          signal: controller.signal,
        },
      );
      if (!controller.signal.aborted) onUser(user);
    } catch (e) {
      if (!isAbort(e)) setError(errorText(e));
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
        active.current = null;
      }
    }
  }
  return (
    <main className="auth-page">
      <section className="auth-story">
        <Brand />
        <div className="story-copy">
          <div className="eyebrow">KNOWLEDGE, CONNECTED.</div>
          <h1>
            让企业知识，
            <br />
            成为每一次决策的依据。
          </h1>
          <p>
            把制度与 SOP 变成可查询、可追溯的知识。
            <br />
            从一份文档开始，让团队经验有序生长。
          </p>
          <div className="story-features">
            <span>
              <BookOutlined aria-hidden="true" /> 独立知识空间
            </span>
            <span>
              <FileSearchOutlined aria-hidden="true" /> 回答有据可查
            </span>
            <span>
              <SafetyCertificateOutlined aria-hidden="true" /> 专属账户保护
            </span>
          </div>
        </div>
        <div className="story-footer">YOUR KNOWLEDGE. YOUR CLARITY.</div>
      </section>
      <section className="auth-form-section">
        <div className="auth-form">
          <span className="eyebrow">欢迎来到知序</span>
          <h2>{register ? "创建你的工作空间" : "登录知识工作台"}</h2>
          <p className="muted">
            {register
              ? "创建账号后即可上传文档，开启有依据的问答。"
              : "继续探索你的知识，接续上一次思考。"}
          </p>
          <ErrorNotice error={error} />
          <Form layout="vertical" onFinish={submit} requiredMark={false}>
            <Form.Item
              label="用户名"
              name="username"
              rules={[
                { required: true, whitespace: true, message: "请输入用户名" },
                { max: 64, message: "用户名最多 64 个字符" },
              ]}
            >
              <Input
                autoComplete="username"
                placeholder="输入用户名"
                size="large"
                maxLength={64}
              />
            </Form.Item>
            <Form.Item
              label="密码"
              name="password"
              rules={[
                { required: true, message: "请输入密码" },
                ...(register ? [{ min: 8, message: "密码至少 8 个字符" }] : []),
                { max: 128, message: "密码最多 128 个字符" },
              ]}
            >
              <Input.Password
                autoComplete={register ? "new-password" : "current-password"}
                placeholder={register ? "至少 8 个字符" : "输入密码"}
                size="large"
                maxLength={128}
              />
            </Form.Item>
            <Button
              className="auth-submit"
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={busy}
              icon={<ArrowRightOutlined aria-hidden="true" />}
              iconPlacement="end"
            >
              {register ? "创建账号" : "登录工作台"}
            </Button>
          </Form>
          <div className="auth-switch">
            {register ? "已有账号？" : "第一次使用？"}{" "}
            <Button
              type="link"
              disabled={busy}
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "返回登录" : "注册新账号"}
            </Button>
          </div>
          <p className="auth-footnote">
            <SafetyCertificateOutlined aria-hidden="true" />{" "}
            文档与对话仅对你的账号可见
          </p>
        </div>
      </section>
    </main>
  );
}
