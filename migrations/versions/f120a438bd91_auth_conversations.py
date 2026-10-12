"""Authentication, resource ownership, conversations, and message snapshots.

Revision ID: f120a438bd91
Revises: e780fe92751b
"""
from alembic import op
import sqlalchemy as sa

revision = 'f120a438bd91'
down_revision = 'e780fe92751b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('username',sa.String(64),nullable=False,unique=True),
        sa.Column('password_hash',sa.String(256),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_table('auth_sessions',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('token_digest',sa.String(64),nullable=False,unique=True),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_auth_sessions_user_id','auth_sessions',['user_id'])
    op.create_index('ix_auth_sessions_expires_at','auth_sessions',['expires_at'])
    # Nullable intentionally: legacy rows are retained and inaccessible until an
    # operator explicitly assigns each ID to an existing user.
    op.add_column('knowledge_bases',sa.Column('owner_id',sa.Integer(),nullable=True))
    op.create_foreign_key('fk_knowledge_bases_owner_id','knowledge_bases','users',['owner_id'],['id'],ondelete='RESTRICT')
    op.create_index('ix_knowledge_bases_owner_id','knowledge_bases',['owner_id'])
    op.drop_constraint('uq_knowledge_bases_name','knowledge_bases',type_='unique')
    op.create_unique_constraint('uq_knowledge_bases_owner_name','knowledge_bases',['owner_id','name'])
    op.create_table('conversations',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('knowledge_base_id',sa.Integer(),sa.ForeignKey('knowledge_bases.id',ondelete='CASCADE'),nullable=False),
        sa.Column('title',sa.String(200),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_conversations_knowledge_base_id','conversations',['knowledge_base_id'])
    op.create_table('conversation_messages',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('conversation_id',sa.Integer(),sa.ForeignKey('conversations.id',ondelete='CASCADE'),nullable=False),
        sa.Column('role',sa.String(16),nullable=False),
        sa.Column('content',sa.Text(),nullable=False),
        sa.Column('status',sa.String(16),nullable=False),
        sa.Column('sources',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user','assistant')",name='ck_conversation_messages_role'),
        sa.CheckConstraint("status IN ('generating','completed','failed','interrupted')",name='ck_conversation_messages_status'),
        sa.CheckConstraint("role <> 'user' OR status = 'completed'",name='ck_user_messages_completed'))
    op.create_index('ix_conversation_messages_conversation_id_id','conversation_messages',['conversation_id','id'])
    op.create_index('uq_one_generating_message','conversation_messages',['conversation_id'],unique=True,postgresql_where=sa.text("status = 'generating'"))


def downgrade():
    # Downgrade is intentionally guarded: owner-scoped duplicate names can no
    # longer satisfy the original global uniqueness. Never rewrite user data.
    connection=op.get_bind()
    duplicate=connection.execute(sa.text('SELECT name FROM knowledge_bases GROUP BY name HAVING count(*) > 1 LIMIT 1')).first()
    if duplicate:
        raise RuntimeError('知识库名称存在重复，无法安全回退；请先人工处理后重试')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
    op.drop_constraint('uq_knowledge_bases_owner_name','knowledge_bases',type_='unique')
    op.create_unique_constraint('uq_knowledge_bases_name','knowledge_bases',['name'])
    op.drop_index('ix_knowledge_bases_owner_id',table_name='knowledge_bases')
    op.drop_constraint('fk_knowledge_bases_owner_id','knowledge_bases',type_='foreignkey')
    op.drop_column('knowledge_bases','owner_id')
    op.drop_table('auth_sessions')
    op.drop_table('users')
