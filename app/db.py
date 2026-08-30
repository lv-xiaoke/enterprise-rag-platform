from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
# DeclarativeBase 用来创建 ORM 模型的共同父类;而 sessionmaker 是：Session 的工厂。
from app.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def build_database_url() -> URL:
    # 根据配置生成 PostgreSQL 数据库地址。
    # [你来完成] 检查 DB、USER、PASSWORD 是否为空；缺失时只报告变量名。
    return URL.create(
        drivername="postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )


class Base(DeclarativeBase):
    # Base：所有 ORM 模型的共同父类
    pass


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,  # 从连接池拿出旧连接之前，先检查它还能不能用。
    connect_args={"connect_timeout": 3}, # 尝试连接 PostgreSQL 时，最多等 3 秒。
)
# 创建整个应用的数据库 Engine。Engine 是：SQLAlchemy 管理数据库连接的核心对象。


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)
# SessionLocal 不是一个具体的 Session, 它是：创建 Session 的工厂

def check_database_connection() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()

# 真正测试 PostgreSQL 能不能连接。