"""add_feedback_table

Revision ID: 5e77a7b91e23
Revises: d0894736bf88
Create Date: 2025-04-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4


# revision identifiers, used by Alembic.
revision = '5e77a7b91e23'
down_revision = 'd0894736bf88'
branch_labels = None
depends_on = None


def upgrade():
    # Create the feedback table
    op.create_table(
        'feedback',
        sa.Column('id', UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(), nullable=False),
        sa.Column('content', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('contact_made', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)
    op.create_index(op.f('ix_feedback_user_id'), 'feedback', ['user_id'], unique=False)


def downgrade():
    # Drop the feedback table
    op.drop_index(op.f('ix_feedback_user_id'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')