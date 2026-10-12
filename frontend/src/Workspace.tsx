import {
  ArrowLeftOutlined,
  CommentOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { ErrorNotice, Loading } from "./components";
import { useResource } from "./hooks";
import type { KnowledgeBase } from "./types";
import Documents from "./Documents";
import Chat from "./Chat";
export default function Workspace({
  id,
  page,
  conversationId,
}: {
  id: number;
  page: string;
  conversationId?: number;
}) {
  const kb = useResource<KnowledgeBase>(`/knowledge-bases/${id}`);
  if (kb.loading) return <Loading />;
  if (kb.error || !kb.data)
    return (
      <main className="library-page">
        <a href="#/knowledge-bases">返回知识库列表</a>
        <ErrorNotice
          error={kb.error || "知识库不存在或无权访问"}
          retry={kb.reload}
        />
      </main>
    );
  return (
    <main className="workspace">
      <div className="workspace-top">
        <div className="workspace-title">
          <a
            href="#/knowledge-bases"
            aria-label="返回知识库列表"
            className="back-link"
          >
            <ArrowLeftOutlined aria-hidden="true" />
          </a>
          <div>
            <h1>{kb.data.name}</h1>
            <p className="muted">{kb.data.description || "你的专属知识空间"}</p>
          </div>
        </div>
        <nav aria-label="知识库导航">
          <a
            aria-current={page === "chat" ? "page" : undefined}
            href={`#/knowledge-bases/${id}/chat`}
          >
            <CommentOutlined aria-hidden="true" /> 聊天工作台
          </a>
          <a
            aria-current={page === "documents" ? "page" : undefined}
            href={`#/knowledge-bases/${id}/documents`}
          >
            <FileTextOutlined aria-hidden="true" /> 文档管理
          </a>
        </nav>
      </div>
      {page === "documents" ? (
        <Documents key={`documents-${id}`} kbId={id} />
      ) : (
        <Chat key={`chat-${id}`} kbId={id} conversationId={conversationId} />
      )}
    </main>
  );
}
