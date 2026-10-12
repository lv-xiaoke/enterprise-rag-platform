import { useEffect, useState } from "react";
import { Button, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { LogoutOutlined } from "@ant-design/icons";
import { ApiError, errorText, json } from "./api";
import { Brand, ErrorNotice, Loading } from "./components";
import { navigate, useHashRoute } from "./hooks";
import Auth from "./Auth";
import Library from "./Library";
import Workspace from "./Workspace";
import type { User } from "./types";
export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [loggingOut, setLoggingOut] = useState(false);
  const route = useHashRoute();
  useEffect(() => {
    const controller = new AbortController();
    json<User>("/auth/me", { signal: controller.signal })
      .then((u) => {
        if (!controller.signal.aborted) setUser(u);
      })
      .catch((e) => {
        if (
          !controller.signal.aborted &&
          !(e instanceof ApiError && e.status === 401)
        )
          setError(errorText(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    const expired = () => {
      setUser(null);
      navigate("/knowledge-bases");
      setError("登录已过期，请重新登录");
    };
    window.addEventListener("session-expired", expired);
    return () => {
      controller.abort();
      window.removeEventListener("session-expired", expired);
    };
  }, []);
  async function logout() {
    setLoggingOut(true);
    setError("");
    try {
      await json("/auth/logout", { method: "POST" });
      setUser(null);
      navigate("/knowledge-bases");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoggingOut(false);
    }
  }
  const match = /^\/knowledge-bases\/(\d+)\/(documents|chat)(?:\/(\d+))?$/.exec(
    route,
  );
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#28584a",
          colorInfo: "#28584a",
          colorBgLayout: "#f4f5f1",
          borderRadius: 9,
          fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
          controlHeight: 38,
        },
      }}
    >
      {loading ? (
        <Loading label="正在恢复登录状态" />
      ) : !user ? (
        <>
          <ErrorNotice error={error} />
          <Auth
            onUser={(u) => {
              setUser(u);
              setError("");
              navigate("/knowledge-bases");
            }}
          />
        </>
      ) : (
        <div className="app-shell" key={user.id}>
          <header className="app-header">
            <a
              className="brand-link"
              href="#/knowledge-bases"
              aria-label="返回知识库列表"
            >
              <Brand />
            </a>
            <div className="account">
              <span className="account-avatar">
                {user.username.slice(0, 1).toUpperCase()}
              </span>
              <span className="account-name" title={user.username}>
                {user.username}
              </span>
              <Button
                type="text"
                icon={<LogoutOutlined aria-hidden="true" />}
                onClick={logout}
                loading={loggingOut}
                aria-label="退出登录"
              >
                <span className="logout-label">退出登录</span>
              </Button>
            </div>
          </header>
          <ErrorNotice error={error} />
          {loggingOut ? (
            <Loading label="正在退出登录" />
          ) : match ? (
            <Workspace
              key={match[1]}
              id={Number(match[1])}
              page={match[2]}
              conversationId={match[3] ? Number(match[3]) : undefined}
            />
          ) : (
            <Library />
          )}
        </div>
      )}
    </ConfigProvider>
  );
}
