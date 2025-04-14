"""remove_default_user_credit_from_application

Revision ID: d6b7778d6d34
Revises: 7204bb193797
Create Date: 2025-04-13 14:41:03.466116

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'd6b7778d6d34'
down_revision = '7204bb193797'
branch_labels = None
depends_on = None


def upgrade():
    # Remove the default_user_credit column from the application table
    op.drop_column('application', 'default_user_credit')


def downgrade():
    # Add the default_user_credit column back to the application table
    # with its original properties
    op.add_column('application',
                 sa.Column('default_user_credit', sa.INTEGER(), 
                           server_default=sa.text('10'), 
                           nullable=False))
