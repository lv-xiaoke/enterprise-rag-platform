from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    """PDF 上传并建立索引后的响应。"""

    filename: str
    page_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)


class RAGChatRequest(BaseModel):
    """RAG 问答请求。"""

    question: str = Field(
        min_length=1,
        max_length=1000,
        description="针对已上传 PDF 提出的问题",
    )

class RAGSource(BaseModel):
    """一条可供用户核对的 RAG 来源。"""

    text: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float

class RAGChatResponse(BaseModel):
    """RAG 问答响应。"""

    answer: str
    sources: list[RAGSource]