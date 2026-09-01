from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm_models import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
        description: str | None = None,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            name=name,
            description=description,
        )
        self._session.add(knowledge_base)
        self._session.flush()
        self._session.refresh(knowledge_base)
        return knowledge_base

    def get(self, knowledge_base_id: int) -> KnowledgeBase | None:
        return self._session.get(KnowledgeBase, knowledge_base_id)

    def list_all(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).order_by(KnowledgeBase.id)
        return list(self._session.scalars(statement))