"""add_reset_password_token_table

Revision ID: e2316ba26128
Revises: d67680cd6449
Create Date: 2025-04-13 16:23:59.470485

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import uuid
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'e2316ba26128'
down_revision = 'd67680cd6449'
branch_labels = None
depends_on = None


def upgrade():
    # Create the reset_password_token table
    op.create_table(
        'resetpasswordtoken',
        sa.Column('id', UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('application_id', UUID(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('token', sa.String(6), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['application_id'], ['application.id']),
        sa.Index('ix_resetpasswordtoken_application_id', 'application_id'),
        sa.Index('ix_resetpasswordtoken_email', 'email'),
        sa.Index('ix_resetpasswordtoken_user_id', 'user_id')
    )


def downgrade():
    # Drop the reset_password_token table
    op.drop_table('resetpasswordtoken')
