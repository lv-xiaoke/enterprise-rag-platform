import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scripts.assign_legacy_knowledge_bases import assign_one


@pytest.fixture
def assignment_session():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)"))
        connection.execute(text("CREATE TABLE knowledge_bases (id INTEGER PRIMARY KEY, owner_id INTEGER)"))
        connection.execute(text("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')"))
        connection.execute(text("INSERT INTO knowledge_bases VALUES (10, NULL), (11, 2)"))
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_assigns_only_explicit_unowned_knowledge_base(assignment_session):
    assign_one(assignment_session, username="alice", knowledge_base_id=10)
    rows = assignment_session.execute(text("SELECT id, owner_id FROM knowledge_bases ORDER BY id")).all()
    assert rows == [(10, 1), (11, 2)]


def test_refuses_to_replace_existing_owner(assignment_session):
    with pytest.raises(ValueError, match="已有归属"):
        assign_one(assignment_session, username="alice", knowledge_base_id=11)
    assert assignment_session.execute(text("SELECT owner_id FROM knowledge_bases WHERE id=11")).scalar_one() == 2


@pytest.mark.parametrize("username, kb_id", [("missing", 10), ("alice", 999)])
def test_missing_user_or_knowledge_base_does_not_assign(assignment_session, username, kb_id):
    with pytest.raises(ValueError):
        assign_one(assignment_session, username=username, knowledge_base_id=kb_id)
    assert assignment_session.execute(text("SELECT owner_id FROM knowledge_bases WHERE id=10")).scalar_one() is None
