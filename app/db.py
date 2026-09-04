from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def build_database_url() -> URL:
    required_settings = {
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    }
    missing_settings = [
        name
        for name, value in required_settings.items()
        if not value.strip()
    ]
    if missing_settings:
        raise RuntimeError(
            "缺少必需的数据库配置: "
            + ", ".join(missing_settings)
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )


class Base(DeclarativeBase):
    pass


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db_session() -> Generator[Session, None, None]:
    # 返回的是一个生成器
    with SessionLocal() as session:
        try:
            yield session
            # yield session 的作用是：把当前创建好的数据库 Session 临时交给外部使用，然后暂停函数；等外部使用完以后，再回来继续执行后面的代码。
        except Exception:
            session.rollback()
            raise


def check_database_connection() -> int:
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise RuntimeError(
            "数据库连接失败，请检查 PostgreSQL 服务状态和 "
            "POSTGRES_* 配置。"
        ) from None