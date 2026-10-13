"""Browser-test server. Never imported by the production application.

Run with RAG_E2E_TESTING=1. Real routes, authentication, PDF parsing,
repositories and database are exercised; only model inference is replaced.
"""

import asyncio
import json
import math
import os
from pathlib import Path
import tempfile
import logging
import httpx

if os.getenv("RAG_E2E_TESTING") != "1":
    raise RuntimeError("This test server requires RAG_E2E_TESTING=1")

from sqlalchemy import create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.operators import custom_op

from app.db import Base
from app.main import create_app
from app.services.pdf_service import PDFService


class TestEmbedding:
    def embed_query(self, query: str) -> list[float]:
        direction = -1.0 if "宇宙" in query.splitlines()[-1] else 1.0
        return [direction] + [0.0] * 511

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 511 for _ in texts]


class TestLLM:
    def is_configured(self) -> bool:
        return True

    async def chat(self, message: str) -> str:
        return "【测试模型】请按制度提前提交申请，并由负责人审批。"

    async def stream_chat(self, messages):
        if "故障验收" in messages[-1]['content']:
            yield "【测试模型】故障前已保存内容。"
            raise httpx.ReadTimeout('test-only fault, not a real upstream request')
        if "中断验收" in messages[-1]['content']:
            for text in ["【测试模型】中断验收："] + ["尚未完成。"] * 20:
                await asyncio.sleep(0.25)
                yield text
            return
        for text in ["【测试模型】", "请按制度提前提交申请，", "并由负责人审批。"]:
            await asyncio.sleep(0.02)
            yield text


database_url = os.getenv("E2E_DATABASE_URL")
if not database_url:
    # A brand-new temporary file, never the user's data/chat.db or PostgreSQL DB.
    test_directory = Path(tempfile.mkdtemp(prefix="rag-browser-test-"))
    database_url = "sqlite:///" + (test_directory / "browser.db").as_posix()

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
test_engine = create_engine(database_url, connect_args=connect_args)

if test_engine.dialect.name == "sqlite":
    @compiles(BinaryExpression, "sqlite")
    def sqlite_vector_distance(expression, compiler, **kwargs):
        if isinstance(expression.operator, custom_op) and expression.operator.opstring == "<=>":
            return "test_cosine_distance(" + compiler.process(expression.left, **kwargs) + "," + compiler.process(expression.right, **kwargs) + ")"
        return compiler.visit_binary(expression, **kwargs)

    @event.listens_for(test_engine, "connect")
    def sqlite_test_functions(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

        def distance(left, right):
            a, b = json.loads(left), json.loads(right)
            norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
            return 1.0 - sum(x * y for x, y in zip(a, b)) / norm if norm else 1.0

        connection.create_function("test_cosine_distance", 2, distance)

    Base.metadata.create_all(test_engine)

factory = sessionmaker(bind=test_engine, expire_on_commit=False)
app = create_app(
    session_factory=factory,
    embedding_service=TestEmbedding(),
    pdf_service=PDFService(),
    llm_service=TestLLM(),
)

# Test-only capture of the actual application JSON formatter, never a debug API.
from app.observability import configure_logging, JSONFormatter
configure_logging()
log_path = Path(__file__).resolve().parents[1] / 'artifacts/fullstack/request-tracing-e2e.jsonl'
log_path.parent.mkdir(parents=True, exist_ok=True)
log_handler = logging.FileHandler(log_path,encoding='utf-8')
log_handler.setFormatter(JSONFormatter())
logging.getLogger('rag.app').addHandler(log_handler)
