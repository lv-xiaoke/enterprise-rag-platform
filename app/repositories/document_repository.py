from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import Document


DocumentStatus = Literal[
    "pending",
    "processing",
    "ready",
    "failed",
]


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        knowledge_base_id: int,
        filename: str,
        status: DocumentStatus = "pending",
    ) -> Document:
        document = Document(
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            status=status,
        )
        self._session.add(document)
        self._session.flush()
        self._session.refresh(document)
        return document

    def get(self, document_id: int) -> Document | None:
        return self._session.get(Document, document_id)

    def list_by_knowledge_base(
        self,
        knowledge_base_id: int,
    ) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(Document.id)
        )
        return list(self._session.scalars(statement))

    def update_status(
        self,
        document_id: int,
        status: DocumentStatus,
        failure_reason: str | None = None,
    ) -> Document | None:
        document = self.get(document_id)
        if document is None:
            return None

        document.status = status
        document.failure_reason = failure_reason
        self._session.flush()
        self._session.refresh(document)
        return document