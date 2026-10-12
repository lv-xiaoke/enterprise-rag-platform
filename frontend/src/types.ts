export interface User {
  id: number;
  username: string;
}
export interface KnowledgeBase {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}
export interface DocumentRecord {
  id: number;
  knowledge_base_id: number;
  filename: string;
  status: "pending" | "processing" | "ready" | "failed";
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}
export interface Source {
  chunk_id: number;
  document_id: number;
  filename: string;
  page_number: number;
  chunk_index: number;
  content: string;
  score: number;
}
export interface Conversation {
  id: number;
  knowledge_base_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
export interface Message {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  status: "generating" | "completed" | "failed" | "interrupted";
  sources: Source[];
  created_at: string;
}
