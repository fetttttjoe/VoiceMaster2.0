"""Initial migration

Revision ID: 83a473980604
Revises: 
Create Date: 2025-07-18 18:52:07.682276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83a473980604'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('guilds',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=False),
    sa.Column('voice_category_id', sa.BigInteger(), nullable=True),
    sa.Column('creation_channel_id', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guilds_id'), 'guilds', ['id'], unique=False)
    op.create_table('user_settings',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('custom_channel_name', sa.String(), nullable=True),
    sa.Column('custom_channel_limit', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=False)
    op.create_table('voice_channels',
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('channel_id')
    )
    op.create_index(op.f('ix_voice_channels_channel_id'), 'voice_channels', ['channel_id'], unique=False)
    op.create_index(op.f('ix_voice_channels_owner_id'), 'voice_channels', ['owner_id'], unique=False)
    op.create_table('guild_settings',
    sa.Column('guild_id', sa.BigInteger(), nullable=False),
    sa.Column('default_channel_name', sa.String(), nullable=True),
    sa.Column('default_channel_limit', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ),
    sa.PrimaryKeyConstraint('guild_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('guild_settings')
    op.drop_index(op.f('ix_voice_channels_owner_id'), table_name='voice_channels')
    op.drop_index(op.f('ix_voice_channels_channel_id'), table_name='voice_channels')
    op.drop_table('voice_channels')
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
    op.drop_table('user_settings')
    op.drop_index(op.f('ix_guilds_id'), table_name='guilds')
    op.drop_table('guilds')
    # ### end Alembic commands ###
