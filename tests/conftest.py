from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import engine


@pytest.fixture
def db_session() -> Iterator[Session]:
    """为单个集成测试提供真实 Session，并在结束后回滚。"""
    connection = engine.connect()
    transaction = connection.begin()
    testing_session_factory = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
    )
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()