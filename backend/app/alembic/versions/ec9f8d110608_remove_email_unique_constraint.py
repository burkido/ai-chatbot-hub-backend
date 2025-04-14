"""remove_email_unique_constraint

Revision ID: ec9f8d110608
Revises: c47c938adc92
Create Date: 2025-04-13 20:33:16.952177

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'ec9f8d110608'
down_revision = 'c47c938adc92'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing unique index on email
    op.drop_index('ix_user_email', table_name='user')
    
    # Re-create the index without the unique constraint
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)


def downgrade():
    # Drop the non-unique index
    op.drop_index('ix_user_email', table_name='user')
    
    # Restore the unique index on email
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
