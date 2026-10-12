"""Real PostgreSQL races using independent connections and test-owned rows only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import delete, event
from sqlalchemy.orm import sessionmaker

from app.conversations import save_progress
from app.db import engine
from app.orm_models import Conversation, ConversationMessage, KnowledgeBase, User


@pytest.mark.parametrize('terminal_status',['failed','interrupted','completed'])
@pytest.mark.parametrize('late_status',['generating','completed'])
def test_terminal_message_survives_late_writer_from_independent_session(terminal_status,late_status):
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    ids={}
    paused,resume=Event(),Event()
    with factory() as session:
        user=User(username='race_'+uuid4().hex,password_hash='test-owned-no-login')
        session.add(user)
        session.flush()
        kb=KnowledgeBase(owner_id=user.id,name='race_'+uuid4().hex)
        session.add(kb)
        session.flush()
        conversation=Conversation(knowledge_base_id=kb.id,title='test-owned race')
        session.add(conversation)
        session.flush()
        message=ConversationMessage(conversation_id=conversation.id,role='assistant',content='',status='generating',sources=[])
        session.add(message)
        session.commit()
        ids={'message':message.id,'conversation':conversation.id,'kb':kb.id,'user':user.id}

    def pause_late_write(connection,cursor,statement,parameters,context,executemany):
        if current_thread().name.startswith('late-writer') and statement.lstrip().upper().startswith('UPDATE CONVERSATION_MESSAGES'):
            paused.set()
            assert resume.wait(5),'terminal writer never released late update'

    event.listen(engine,'before_cursor_execute',pause_late_write)
    try:
        with ThreadPoolExecutor(max_workers=1,thread_name_prefix='late-writer') as executor:
            late=executor.submit(save_progress,factory,ids['message'],'迟到覆盖',late_status,[{'content':'迟到来源'}])
            try:
                assert paused.wait(5),'late writer did not reach database UPDATE'
                saved=save_progress(factory,ids['message'],'已保存部分',terminal_status,[{'content':'原始来源'}])
                assert saved['status'] == terminal_status
            finally:
                resume.set()
            returned=late.result(timeout=5)
        with factory() as session:
            message=session.get(ConversationMessage,ids['message'])
            assert message.status == terminal_status
            assert message.content == '已保存部分'
            assert message.sources == [{'content':'原始来源'}]
        assert returned['status'] == terminal_status
        assert returned['content'] == '已保存部分'
    finally:
        resume.set()
        event.remove(engine,'before_cursor_execute',pause_late_write)
        # These exact IDs were created by this test. No truncate, table/schema
        # drop, broad predicate, or developer record cleanup is performed.
        with factory() as session:
            session.execute(delete(ConversationMessage).where(ConversationMessage.id == ids['message']))
            session.execute(delete(Conversation).where(Conversation.id == ids['conversation']))
            session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == ids['kb']))
            session.execute(delete(User).where(User.id == ids['user']))
            session.commit()
