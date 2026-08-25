import sqlite3
from typing import Literal

from app.config import BASE_DIR
from app.models import Message

DATABASE_PATH = BASE_DIR / "data" / "chat.db"


def get_connection() -> sqlite3.Connection:
    """创建并返回一个 SQLite 数据库连接。"""
    DATABASE_PATH.parent.mkdir(exist_ok=True) # `exist_ok=True` 表示目录已经存在时不要报错。

    connection = sqlite3.connect(DATABASE_PATH)
    # 连接可以理解成 Python 和 SQLite 之间的一条通道。后面的建表、插入和查询都通过它完成。
    # 如果 `chat.db` 不存在，SQLite 会在第一次连接时创建它；如果已经存在，就打开原来的数据库。

    connection.row_factory = sqlite3.Row
    # 设置以后，查询结果不仅能按位置读取，也可以转换成类似字典的形式：
    # dict(row) 这会让以后构造 `/history` 的 JSON 更方便。

    return connection


def init_database() -> None:
    """创建项目需要的数据库表。"""
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

def save_message(
        role: Literal["user", "assistant"],
        content: str,
    ) -> None:
    """保存一条用户或模型消息。"""
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO messages (role, content)
            VALUES (?, ?)
            """,
            (role, content),
        )
        connection.commit()
    finally:
        connection.close()

def get_messages() -> list[Message]:
    """按消息产生顺序返回全部聊天记录。"""
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        connection.close()

    messages: list[Message] = []

    for row in rows:
        messages.append(
            Message(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
        )

    return messages