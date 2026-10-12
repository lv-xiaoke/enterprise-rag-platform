"""Cookie authentication. Tokens are opaque; only SHA-256 digests reach storage."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.orm_models import AuthSession, KnowledgeBase, User

COOKIE_NAME = 'rag_session'
# PBKDF2 is deliberately bounded so attacker-controlled credential lengths cannot
# cause unbounded work. The same work is done for nonexistent accounts at login.
ITERATIONS = 600000
DUMMY_HASH = 'pbkdf2_sha256$600000$' + '00'*16 + '$' + '00'*32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, digest = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or not 100000 <= int(rounds) <= 2000000:
            return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(candidate, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('username')
    @classmethod
    def clean_username(cls, value):
        value = value.strip().casefold()
        if len(value) < 3 or not all(ch.isalnum() or ch in '_-.' for ch in value):
            raise ValueError('用户名需为 3 至 64 个字母、数字或 _-.')
        return value


def authenticated_user_id(request: Request) -> int:
    token = request.cookies.get(COOKIE_NAME, '')
    if len(token) < 40 or len(token) > 128:
        raise HTTPException(401, '请先登录')
    with request.app.state.session_factory() as session:
        user_id = session.scalar(select(AuthSession.user_id).where(
            AuthSession.token_digest == token_digest(token),
            AuthSession.expires_at > datetime.now(timezone.utc),
        ))
        if user_id is None:
            raise HTTPException(401, '登录已过期，请重新登录')
        return user_id


async def current_user(request: Request) -> int:
    return await run_in_threadpool(authenticated_user_id, request)


def require_knowledge_base(session, kb_id: int, user_id: int):
    kb = session.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.owner_id == user_id))
    if kb is None:
        raise HTTPException(404, '知识库不存在')
    return kb


def issue_session(session, user: User, request: Request, response: Response):
    previous = request.cookies.get(COOKIE_NAME)
    if previous and len(previous) <= 128:
        session.execute(delete(AuthSession).where(AuthSession.token_digest == token_digest(previous)))
    token = secrets.token_urlsafe(32)
    settings = request.app.state.settings
    session.add(AuthSession(user_id=user.id, token_digest=token_digest(token), expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)))
    session.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite='lax', max_age=settings.session_hours*3600, path='/')
    return {'id':user.id, 'username':user.username}


router = APIRouter(prefix='/api/auth')


@router.post('/register', status_code=201)
def register(body: Credentials, request: Request, response: Response):
    with request.app.state.session_factory() as session:
        user = User(username=body.username, password_hash=hash_password(body.password))
        session.add(user)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, '用户名已存在') from None
        return issue_session(session, user, request, response)


@router.post('/login')
def login(body: Credentials, request: Request, response: Response):
    with request.app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.username == body.username))
        valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
        if not valid or user is None:
            raise HTTPException(401, '用户名或密码错误')
        return issue_session(session, user, request, response)


@router.get('/me')
def me(request: Request, user_id: int = Depends(current_user)):
    with request.app.state.session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(401, '请重新登录')
        return {'id':user.id,'username':user.username}


@router.post('/logout', status_code=204)
def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME, '')
    with request.app.state.session_factory() as session:
        session.execute(delete(AuthSession).where(AuthSession.token_digest == token_digest(token)))
        session.commit()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path='/', httponly=True, secure=request.app.state.settings.cookie_secure, samesite='lax')
    return response
