"""Assign one explicitly named, unowned legacy knowledge base to a user.

python -m scripts.assign_legacy_knowledge_bases --username alice --knowledge-base-id 1
Never replaces existing ownership or assigns all unowned data implicitly.
"""

import argparse

from sqlalchemy import text
from sqlalchemy.orm import Session


def assign_one(session: Session, *, username: str, knowledge_base_id: int) -> None:
    user_id = session.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username.strip()},
    ).scalar_one_or_none()
    if user_id is None:
        raise ValueError("用户不存在，请先在 Web 页面注册")
    record = session.execute(
        text("SELECT owner_id FROM knowledge_bases WHERE id = :id"),
        {"id": knowledge_base_id},
    ).first()
    if record is None:
        raise ValueError("知识库不存在")
    if record.owner_id is not None:
        raise ValueError("知识库已有归属，不允许覆盖")
    result = session.execute(
        text("UPDATE knowledge_bases SET owner_id = :owner WHERE id = :id AND owner_id IS NULL"),
        {"owner": user_id, "id": knowledge_base_id},
    )
    if result.rowcount != 1:
        raise ValueError("知识库归属已变化，请重新检查")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--knowledge-base-id", required=True, type=int)
    args = parser.parse_args()
    if args.knowledge_base_id <= 0:
        parser.error("knowledge-base-id 必须为正整数")
    from app.db import SessionLocal

    try:
        with SessionLocal.begin() as session:
            assign_one(session, username=args.username, knowledge_base_id=args.knowledge_base_id)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print(f"已分配知识库 {args.knowledge_base_id} 给用户 {args.username.strip()}")


if __name__ == "__main__":
    main()
