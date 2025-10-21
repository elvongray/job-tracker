"""replace magic links with codes

Revision ID: 51e99261f8b9
Revises: 2abdd0c64d1b
Create Date: 2025-10-21 12:18:14.730601

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '51e99261f8b9'
down_revision: Union[str, Sequence[str], None] = '2abdd0c64d1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('magic_link_tokens'):
        op.drop_index(op.f('ix_magic_link_tokens_expires_at'), table_name='magic_link_tokens')
        op.drop_table('magic_link_tokens')

    op.create_table(
        'verification_codes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f(
            'fk_verification_codes_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_verification_codes')),
        sa.UniqueConstraint('user_id', 'code', name='uq_verification_codes_user_code'),
    )
    op.create_index('ix_verification_codes_expires_at',
                    'verification_codes', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('verification_codes'):
        op.drop_index('ix_verification_codes_expires_at', table_name='verification_codes')
        op.drop_table('verification_codes')

    if not inspector.has_table('magic_link_tokens'):
        op.create_table(
            'magic_link_tokens',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('used_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f(
                'fk_magic_link_tokens_user_id_users'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_magic_link_tokens')),
            sa.UniqueConstraint('token', name=op.f('uq_magic_link_tokens_token')),
        )
        op.create_index(op.f('ix_magic_link_tokens_expires_at'),
                        'magic_link_tokens', ['expires_at'], unique=False)
