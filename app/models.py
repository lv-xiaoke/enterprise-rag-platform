from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal[
    "pending",
    "processing",
    "ready",
    "failed",
]


class Message(BaseModel):
    """一条聊天消息的数据结构。"""

    id: int = Field(gt=0)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)
    created_at: datetime


class ChatRequest(BaseModel):
    """客户端发送的聊天请求。"""

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="用户发送的消息",
    )


class ChatResponse(BaseModel):
    """服务器返回的聊天响应。"""

    reply: str


class UploadResponse(BaseModel):
    """旧 FAISS 上传接口的响应。"""

    filename: str
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)


class RAGChatRequest(BaseModel):
    """旧 FAISS RAG 问答请求。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对已上传 PDF 提出的问题",
    )


class RAGSource(BaseModel):
    """一条可供用户核对的旧 RAG 来源。"""

    text: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float


class RAGChatResponse(BaseModel):
    """旧 FAISS RAG 问答响应。"""

    answer: str
    sources: list[RAGSource]


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库的请求。"""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class KnowledgeBaseResponse(BaseModel):
    """对外公开的知识库字段。"""

    id: int = Field(gt=0)
    name: str
    description: str | None
    created_at: datetime


class DocumentResponse(BaseModel):
    """对外公开的文档元数据和处理状态。"""

    id: int = Field(gt=0)
    knowledge_base_id: int = Field(gt=0)
    filename: str
    status: DocumentStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """数据库版 PDF 上传成功后的响应。"""

    document: DocumentResponse
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)


class KnowledgeBaseQueryRequest(BaseModel):
    """在指定知识库内执行数据库版 RAG 问答。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对指定知识库提出的问题",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=20,
        description="pgvector 最多返回的候选 Chunk 数量",
    )


class KnowledgeBaseQuerySource(BaseModel):
    """一条可以回查数据库和原 PDF 页码的 RAG 来源。"""

    chunk_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    filename: str = Field(min_length=1)
    page_number: int = Field(gt=0)
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)


class KnowledgeBaseQueryResponse(BaseModel):
    """数据库版 RAG 的回答、拒答标记和来源。"""

    answer: str = Field(min_length=1)
    refused: bool
    sources: list[KnowledgeBaseQuerySource]