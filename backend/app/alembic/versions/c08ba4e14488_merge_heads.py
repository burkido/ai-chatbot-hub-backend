"""merge heads

Revision ID: c08ba4e14488
Revises: 5e77a7b91e23, f3965c8d1b61
Create Date: 2025-04-21 11:37:05.377329

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c08ba4e14488'
down_revision = ('5e77a7b91e23', 'f3965c8d1b61')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
